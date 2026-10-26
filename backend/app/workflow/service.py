from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, TypedDict
from uuid import UUID, uuid4

from langgraph.graph import END, START, StateGraph

from ..api.schemas import InterviewStateResponse, SessionResponse, TurnResponse
from ..core.session_store import (
    InMemorySessionStore,
    SessionConflictError,
    SessionNotFoundError,
)


class WorkflowState(TypedDict, total=False):
    action: Literal["start", "submit", "timeout", "end"]
    session_id: UUID
    turn_id: UUID | None
    answer_text: str | None
    session: SessionResponse
    context: dict[str, Any]
    cv_evidence: list[dict[str, Any]]
    jd_evidence: list[dict[str, Any]]
    criteria: list[Any]
    workflow: dict[str, Any]
    result: InterviewStateResponse
    error: str


class InterviewWorkflow:
    """Finite, request-scoped interview flow. State is kept in the in-memory session store."""

    def __init__(self, store: InMemorySessionStore, config: dict[str, Any], retriever: Any):
        self.store = store
        self.config = config
        self.retriever = retriever
        graph = StateGraph(WorkflowState)
        graph.add_node("validate_session", self._validate_session)
        graph.add_node("analyze_cv_jd", self._analyze_cv_jd)
        graph.add_node("retrieve_criteria", self._retrieve_criteria)
        graph.add_node("build_plan", self._build_plan)
        graph.add_node("capture_answer", self._capture_answer)
        graph.add_node("decide_follow_up_or_next", self._decide_follow_up_or_next)
        graph.add_node("ask_question", self._ask_question)
        graph.add_node("allocate_question_time", self._allocate_question_time)
        graph.add_node("final_evaluation", self._final_evaluation)
        graph.add_edge(START, "validate_session")
        graph.add_conditional_edges(
            "validate_session",
            self._route_action,
            {
                "start": "analyze_cv_jd",
                "submit": "capture_answer",
                "timeout": "capture_answer",
                "end": "final_evaluation",
            },
        )
        graph.add_edge("analyze_cv_jd", "retrieve_criteria")
        graph.add_edge("retrieve_criteria", "build_plan")
        graph.add_edge("build_plan", "ask_question")
        graph.add_edge("ask_question", "allocate_question_time")
        graph.add_edge("allocate_question_time", END)
        graph.add_edge("capture_answer", "decide_follow_up_or_next")
        graph.add_conditional_edges(
            "decide_follow_up_or_next",
            self._route_after_answer,
            {"ask": "ask_question", "finish": "final_evaluation"},
        )
        graph.add_edge("final_evaluation", END)
        self.graph = graph.compile()

    async def start(self, session_id: UUID) -> InterviewStateResponse:
        return await self._invoke("start", session_id)

    async def submit(self, session_id: UUID, turn_id: UUID, answer_text: str) -> InterviewStateResponse:
        return await self._invoke("submit", session_id, turn_id=turn_id, answer_text=answer_text)

    async def timeout(self, session_id: UUID, turn_id: UUID) -> InterviewStateResponse:
        return await self._invoke("timeout", session_id, turn_id=turn_id)

    async def end_early(self, session_id: UUID) -> InterviewStateResponse:
        return await self._invoke("end", session_id)

    def get(self, session_id: UUID) -> InterviewStateResponse:
        session = self.store.get(session_id)
        workflow = self.store.get_workflow(session_id)
        return self._response(session, workflow)

    async def _invoke(
        self,
        action: Literal["start", "submit", "timeout", "end"],
        session_id: UUID,
        *,
        turn_id: UUID | None = None,
        answer_text: str | None = None,
    ) -> InterviewStateResponse:
        state = await self.graph.ainvoke(
            {"action": action, "session_id": session_id, "turn_id": turn_id, "answer_text": answer_text}
        )
        if "error" in state:
            raise SessionConflictError(state["error"])
        return state["result"]

    def _validate_session(self, state: WorkflowState) -> WorkflowState:
        session = self.store.get(state["session_id"])
        action = state["action"]
        if action == "start":
            if session.status != "ready":
                raise SessionConflictError(f"Cannot start a session in state '{session.status}'")
        elif session.status != "running":
            raise SessionConflictError(f"Cannot {action} a session in state '{session.status}'")
        if action in {"submit", "timeout"}:
            workflow = self.store.get_workflow(session.session_id)
            current = self._current_turn(workflow)
            if current is None or current["turn_id"] != state.get("turn_id"):
                raise SessionConflictError("The submitted turn is not the current interview question")
            if current["status"] not in {"asking", "answering"}:
                raise SessionConflictError("The current turn is already complete")
        return {**state, "session": session, "context": self.store.get_context(session.session_id)}

    @staticmethod
    def _route_action(state: WorkflowState) -> str:
        return state["action"]

    def _analyze_cv_jd(self, state: WorkflowState) -> WorkflowState:
        return {**state, "cv_evidence": self._context_lines(state["context"].get("cv_context", {})),
                "jd_evidence": self._context_lines(state["context"].get("jd_context", {}))}

    async def _retrieve_criteria(self, state: WorkflowState) -> WorkflowState:
        session = state["session"]
        context = state["context"]
        jd_lines = self._context_lines(context.get("jd_context", {}))
        records = await self.retriever.retrieve(
            query=" ".join(item["text"] for item in jd_lines),
            industry_id=None,
            job_family_id=None,
            role_id=None,
            level_id=session.level_id,
            limit=20,
        )
        return {**state, "criteria": records}

    def _build_plan(self, state: WorkflowState) -> WorkflowState:
        session = state["session"]
        level = self._level(session.level_id)
        count = level["primary_question_count"]
        mix = level["question_mix"]
        plan: list[dict[str, Any]] = []
        behavioral_credit = 0.0
        role_credit = 0.0
        for _ in range(count):
            behavioral_credit += mix["behavioral"]
            role_credit += mix["role_specific"]
            kind = "behavioral" if behavioral_credit >= role_credit else "role_specific"
            if kind == "behavioral":
                behavioral_credit -= 1
            else:
                role_credit -= 1
            plan.append({"type": kind})
        question_records: dict[str, list[Any]] = {"behavioral": [], "role_specific": []}
        mapped_role_id = (state["session"].role_mapping or {}).get("role_id")
        for record in state.get("criteria", []):
            role_matches = mapped_role_id and record.metadata and record.metadata.get("role_id") == mapped_role_id
            if record.record_type == "question" and role_matches and record.content.get("type") in question_records:
                question_records[record.content["type"]].append(record)
        criteria_warning = not any(question_records.values())
        record_indexes = {"behavioral": 0, "role_specific": 0}
        for spec in plan:
            available = question_records[spec["type"]]
            if available:
                spec["criteria_record"] = available[record_indexes[spec["type"]] % len(available)]
                record_indexes[spec["type"]] += 1
        workflow = {
            "plan": plan,
            "next_primary_index": 0,
            "turns": [],
            "criteria_warnings": [
                "Chưa có câu hỏi role được duyệt khớp role mapping của phiên; câu hỏi chuyên môn chỉ bám vào nội dung JD/CV và không khẳng định chuyên môn ngành."
            ] if criteria_warning else [],
            "retrieved_criteria_ids": [record.record_id for record in state.get("criteria", [])],
            "cv_evidence": state.get("cv_evidence", []),
            "jd_evidence": state.get("jd_evidence", []),
            "follow_up_counts": {},
            "completion_reason": None,
        }
        session = self.store.start(session.session_id)
        self.store.set_workflow(session.session_id, workflow)
        return {**state, "session": session, "workflow": workflow}

    def _capture_answer(self, state: WorkflowState) -> WorkflowState:
        session = state["session"]
        workflow = self.store.get_workflow(session.session_id)
        turn = self._current_turn(workflow)
        if turn is None:
            raise SessionConflictError("There is no active interview question")
        turns = list(workflow["turns"])
        turn = dict(turn)
        turn["status"] = "timed_out" if state["action"] == "timeout" else "submitted"
        turn["completed_at"] = self._now()
        if state["action"] == "submit":
            turn["answer"] = {"transcript": (state.get("answer_text") or "").strip(),
                               "language": session.language, "submitted_at": self._now(),
                               "speech_confidence": None}
        turns[-1] = turn
        workflow = {**workflow, "turns": turns}
        self.store.set_workflow(session.session_id, workflow)
        return {**state, "workflow": workflow}

    def _decide_follow_up_or_next(self, state: WorkflowState) -> WorkflowState:
        workflow = self.store.get_workflow(state["session"].session_id)
        previous = workflow["turns"][-1]
        counts = dict(workflow["follow_up_counts"])
        primary_id = previous.get("parent_turn_id") or previous["turn_id"]
        used = counts.get(str(primary_id), 0)
        level = self._level(state["session"].level_id)
        pressure = self._pressure(state["session"].pressure_profile_id)
        followup_limit = min(level["follow_up"]["max_depth"], pressure["max_followups_per_question"])
        is_submitted = previous["status"] == "submitted"
        should_follow = is_submitted and level["follow_up"]["enabled"] and used < followup_limit
        if should_follow:
            counts[str(primary_id)] = used + 1
            next_turn = self._make_follow_up(state["session"], previous, counts[str(primary_id)], workflow)
            workflow = {**workflow, "follow_up_counts": counts, "pending_turn": next_turn,
                        "decision_reason": "follow_up_within_configured_depth"}
        else:
            workflow["next_primary_index"] += 1
            workflow["pending_turn"] = None
            exhausted = workflow["next_primary_index"] >= len(workflow["plan"])
            workflow["decision_reason"] = "plan_completed" if exhausted else "next_primary_question"
        self.store.set_workflow(state["session"].session_id, workflow)
        return {**state, "workflow": workflow}

    @staticmethod
    def _route_after_answer(state: WorkflowState) -> str:
        workflow = state["workflow"]
        return "finish" if workflow.get("decision_reason") == "plan_completed" else "ask"

    def _ask_question(self, state: WorkflowState) -> WorkflowState:
        session = state["session"]
        workflow = dict(state.get("workflow") or self.store.get_workflow(session.session_id))
        pending = workflow.pop("pending_turn", None)
        if pending is None:
            index = workflow["next_primary_index"]
            if index >= len(workflow["plan"]):
                workflow["decision_reason"] = "plan_completed"
                self.store.set_workflow(session.session_id, workflow)
                return {**state, "workflow": workflow}
            pending = self._make_primary(session, workflow, index)
        workflow["pending_turn"] = None
        workflow["turns"] = [*workflow["turns"], pending]
        self.store.set_workflow(session.session_id, workflow)
        return {**state, "workflow": workflow}

    def _allocate_question_time(self, state: WorkflowState) -> WorkflowState:
        session = self.store.get(state["session"].session_id)
        workflow = self.store.get_workflow(session.session_id)
        turns = list(workflow["turns"])
        if turns and turns[-1]["status"] == "queued":
            turn = dict(turns[-1])
            level = self._level(session.level_id)
            pressure = self._pressure(session.pressure_profile_id)
            band = turn["question"].get("difficulty") or level["fallback_question_band"]
            allowance = pressure["difficulty_bands"][band]
            turn["status"] = "asking"
            turn["asked_at"] = self._now()
            turn["timing"] = {"difficulty_band": band,
                               "preparation_seconds": allowance["preparation_seconds"],
                               "answer_seconds": allowance["answer_seconds"],
                               "profile_id": session.pressure_profile_id,
                               "decision_source": "configured_band" if turn["question"].get("difficulty") else "level_fallback"}
            turns[-1] = turn
            workflow["turns"] = turns
            self.store.set_workflow(state["session"].session_id, workflow)
            session = self.store.get(session.session_id)
        return {**state, "session": session, "workflow": workflow, "result": self._response(session, workflow)}

    def _final_evaluation(self, state: WorkflowState) -> WorkflowState:
        session = self.store.get(state["session_id"])
        workflow = self.store.get_workflow(session.session_id)
        reason = "user_ended_early" if state["action"] == "end" else "plan_completed"
        if state["action"] == "end" and workflow.get("turns"):
            turns = list(workflow["turns"])
            current = turns[-1]
            if current["status"] in {"asking", "answering"}:
                current = {**current, "status": "skipped", "completed_at": self._now()}
                turns[-1] = current
                workflow["turns"] = turns
        workflow["completion_reason"] = reason
        self.store.set_workflow(session.session_id, workflow)
        session = self.store.complete(session.session_id, completion_reason=reason)
        return {**state, "session": session, "workflow": workflow,
                "result": self._response(session, workflow)}

    def _make_primary(self, session: SessionResponse, workflow: dict[str, Any], index: int) -> dict[str, Any]:
        spec = workflow["plan"][index]
        kind = spec["type"]
        evidence = workflow["cv_evidence"] if kind == "behavioral" else workflow["jd_evidence"]
        text = evidence[index % len(evidence)]["text"] if evidence else None
        language = session.language
        record = spec.get("criteria_record")
        if record:
            prompts = record.content.get("prompt", {})
            question_text = prompts.get(language) or prompts.get("en") or prompts.get("vi")
            return {"turn_id": uuid4(), "sequence": len(workflow["turns"]) + 1, "kind": "primary",
                    "status": "queued", "question": {"text": question_text, "type": kind,
                    "difficulty": record.content.get("difficulty"),
                    "competency_ids": record.content.get("competency_ids", []),
                    "source_question_ids": [record.record_id]},
                    "answer": None, "timing": None, "parent_turn_id": None,
                    "criteria_provenance": [{"record_id": record.record_id, "version": record.version,
                                             "source_ids": list(record.source_ids), "sources": list(record.sources)}],
                    "asked_at": None, "completed_at": None}
        if kind == "behavioral":
            question_text = (f"Kể về một trải nghiệm liên quan đến nội dung này trong CV: “{text}”. Bạn đã đóng góp điều gì?" if language == "vi" else
                             f"Tell me about an experience related to this item in your CV: “{text}”. What did you contribute?") if text else (
                "Hãy kể về một dự án, môn học hoặc hoạt động bạn đã tham gia và phần việc cụ thể của bạn." if language == "vi" else
                "Tell me about a project, course, or activity you took part in and the specific work you contributed.")
        else:
            question_text = (f"JD có đề cập: “{text}”. Bạn sẽ tiếp cận yêu cầu này như thế nào dựa trên kiến thức hoặc dự án đã có?" if language == "vi" else
                             f"The job description mentions: “{text}”. How would you approach this requirement based on your current knowledge or projects?") if text else (
                "Yêu cầu cụ thể trong JD chưa được nhận diện; bạn hiểu vai trò này cần giải quyết vấn đề gì?" if language == "vi" else
                "The JD did not yield a specific requirement; what problem do you understand this role to solve?")
        return {"turn_id": uuid4(), "sequence": len(workflow["turns"]) + 1, "kind": "primary",
                "status": "queued", "question": {"text": question_text, "type": kind,
                "difficulty": None, "competency_ids": [], "source_question_ids": []},
                "answer": None, "timing": None, "parent_turn_id": None, "asked_at": None, "completed_at": None}

    def _make_follow_up(self, session: SessionResponse, parent: dict[str, Any], depth: int,
                        workflow: dict[str, Any]) -> dict[str, Any]:
        answer = parent.get("answer", {}).get("transcript", "")
        evidence = answer.strip().replace("\n", " ")[:120]
        language = session.language
        style = self._pressure(session.pressure_profile_id)["interviewer_behavior"]["challenge_style"]
        pressure_depth = self._pressure(session.pressure_profile_id)["interviewer_behavior"]["follow_up_depth"]
        level_strategy = self._level(session.level_id)["follow_up"]["strategy"]
        if (style == "probe_assumptions_and_tradeoffs"
                or pressure_depth == "rigorous_probe"
                or level_strategy == "probe_assumptions_and_tradeoffs"):
            question_text = (f"Bạn vừa nói: “{evidence}”. Giả định hoặc đánh đổi quan trọng nhất trong lựa chọn đó là gì, và bạn kiểm chứng nó ra sao?" if language == "vi" else
                             f"You mentioned: “{evidence}”. What was the key assumption or trade-off in that choice, and how did you validate it?")
        else:
            question_text = (f"Bạn vừa nói: “{evidence}”. Hãy cho tôi một ví dụ hoặc bằng chứng cụ thể để làm rõ phần bạn trực tiếp thực hiện." if language == "vi" else
                             f"You mentioned: “{evidence}”. Could you give a concrete example or evidence that clarifies what you personally did?")
        return {"turn_id": uuid4(), "sequence": len(workflow["turns"]) + 1, "kind": "follow_up",
                "status": "queued", "question": {"text": question_text, "type": parent["question"]["type"],
                "difficulty": parent["question"]["difficulty"], "competency_ids": parent["question"]["competency_ids"],
                "source_question_ids": parent["question"]["source_question_ids"]},
                "answer": None, "timing": None, "parent_turn_id": parent.get("parent_turn_id") or parent["turn_id"],
                "follow_up_depth": depth, "criteria_provenance": parent.get("criteria_provenance", []),
                "asked_at": None, "completed_at": None}

    def _response(self, session: SessionResponse, workflow: dict[str, Any]) -> InterviewStateResponse:
        turns = [TurnResponse.model_validate(item) for item in workflow.get("turns", [])]
        current = turns[-1] if turns and turns[-1].status in {"asking", "answering"} else None
        completed = sum(1 for turn in turns if turn.kind == "primary" and turn.status in {"submitted", "timed_out"})
        return InterviewStateResponse(session=session, turns=turns, current_turn=current,
            primary_question_count=len(workflow.get("plan", [])), primary_questions_completed=completed,
            retrieved_criteria_ids=workflow.get("retrieved_criteria_ids", []),
            transition_reason=workflow.get("decision_reason"),
            criteria_warnings=workflow.get("criteria_warnings", []))

    def _level(self, level_id: str) -> dict[str, Any]:
        return next(item for item in self.config["interview_levels"]["levels"] if item["id"] == level_id)

    def _pressure(self, profile_id: str) -> dict[str, Any]:
        return self.config["pressure_profiles"]["profiles"][profile_id]

    @staticmethod
    def _context_lines(context: dict[str, Any]) -> list[dict[str, Any]]:
        return [item for key, items in context.items() if isinstance(items, list) and key != "warnings"
                for item in items if isinstance(item, dict) and item.get("text")]

    @staticmethod
    def _current_turn(workflow: dict[str, Any]) -> dict[str, Any] | None:
        turns = workflow.get("turns", [])
        return turns[-1] if turns and turns[-1]["status"] in {"asking", "answering"} else None

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
