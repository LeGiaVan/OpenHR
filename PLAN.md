# Kế hoạch triển khai chi tiết

Roadmap này chuyển proposal thành các giai đoạn POC có đầu ra và điều kiện hoàn tất. PDF/DOCX dạng text đã được chọn cho CV/JD; provider, giới hạn upload, database, retention và thị trường vẫn mở.

## 1. Mục tiêu và nguyên tắc đã chốt

- Người dùng: sinh viên/người mới tốt nghiệp apply intern/fresher.
- Cả CV và JD là đầu vào bắt buộc để cá nhân hóa.
- Tiếng Việt/Anh; user chọn ngôn ngữ và cấp độ.
- Multi-industry dựa trên kho tiêu chí có thể mở rộng, có provenance.
- Level quyết định độ khó, question mix, rubric profile và follow-up strategy.
- Follow-up thích ứng là năng lực cốt lõi.
- Phỏng vấn liền mạch; không coaching/chấm giữa buổi; báo cáo ở cuối.
- Đánh giá: JD relevance/chuyên môn, cấu trúc/dẫn chứng, giao tiếp, ngôn ngữ khi phù hợp.
- Thời lượng thay đổi theo difficulty/question type/level và cấu hình; không hard-code.
- POC hướng React/Vite + FastAPI + LangGraph.
- Không giả định có sẵn dữ liệu ngành đã được xác thực.

### Ngoài MVP trừ khi có yêu cầu mới

Live web search, agent tự chủ không giới hạn, accounts/payments, lịch sử dài hạn, persona nâng cao, speech analytics nâng cao, thương mại hóa.

## 2. Quyết định mở

Chốt đúng giai đoạn và ghi vào bảng cuối, không tự khóa trong code:

1. Giới hạn file/MIME cụ thể, parser package và UX sửa text; OCR scan không thuộc POC.
2. LLM/STT/TTS provider theo chất lượng VI/EN, latency, chi phí, quotas.
3. Session persistence, database, resume và retention transcript/audio.
4. Retrieval: metadata/keyword trước; tiêu chí cần để thêm vector store.
5. Ánh xạ job title từ JD sang taxonomy.
6. Formula/fallback cho phân bổ thời gian.
7. Thang điểm/trọng số rubric và cách xử lý thiếu evidence.
8. Pressure/persona options thuộc MVP đến đâu.

## 3. Kế hoạch theo giai đoạn

### Phase 0 — Hợp đồng sản phẩm và dữ liệu

**Trạng thái: Hoàn tất.** Hợp đồng payload, quy ước ID/version, schema cấu hình và boundary services được phác thảo trong contracts/ và configs/schemas/. Định dạng POC đã chốt là PDF/DOCX dạng text, không OCR scan. Provider cụ thể là gate trước vendor integration; skeleton/workflow có thể dùng mock cho đến khi lựa chọn đó được chốt.

**Việc:** đọc Proposal.MD, AGENTS.md, configs, knowledge_base; định nghĩa/version model cho level, pressure profile, question, competency, rubric, session, report; thống nhất ID/reference; xác định validate lỗi config; chốt file/provider trước integration; vẽ boundary UI/API/graph/adapters.

**Đầu ra:** contracts/README.md, session/turn/report schemas, schema cho level/pressure config, quy ước ID/reference, semantic validation rules, ranh giới API/workflow/adapters và bảng quyết định cập nhật.

**Hoàn tất Phase 0:** UI/API/workflow có contract và ID conventions thống nhất; semantic validation/error behavior được đặc tả; business rules được tách khỏi prompt. Việc hiện thực validator chạy lúc backend startup thuộc Phase 1. Định dạng CV/JD đã chốt; vendor cụ thể là gate trước vendor integration.

**Provider gate:** giữ LLM/STT/TTS provider-neutral, chạy mock trong skeleton/workflow; chọn vendor trước khi tích hợp dựa trên chất lượng VI/EN, latency và chi phí.

### Phase 1 — App skeleton và config

**Trạng thái:** Skeleton frontend/backend, config loader/validation, API contract routes, mock adapters và in-memory session lifecycle đã được tạo. Chưa chạy runtime/build check; upload/parser, interview turns và report vẫn là placeholder thuộc các phase sau.

**Việc:** tạo React/Vite và FastAPI; API contracts cho upload/setup/turn/end/report; backend đọc level và pressure YAML; frontend nhận config từ API; validate mix/bands/limits/references; tạo adapter interfaces cho LLM/STT/TTS/retrieval; secrets an toàn; UI skeleton upload/setup/interview/report.

**Đầu ra:** app tối thiểu, mock session chạy được.

**Hoàn tất:** sửa profile không cần sửa UI; invalid config trả lỗi rõ; mock có thể đi qua state chính.

### Phase 2 — CV/JD parsing và session context

**Việc:** upload riêng CV/JD; parser theo định dạng đã chốt; preview/sửa extracted text; phân tích CV thành skills/projects/study/activities/experience và JD thành requirements/responsibilities/skills; giữ provenance khi có; xử lý file rỗng/hỏng, JD mơ hồ, CV thiếu việc làm.

**Đầu ra:** context theo phiên gồm language, level, CV evidence, JD requirements và role mapping.

**Hoàn tất:** cả hai tài liệu được xử lý trước session; không bịa kinh nghiệm; đồ án/hoạt động là evidence hợp lệ cho fresher.

### Phase 3 — Knowledge base và retrieval

**Việc:** validate YAML theo schemas; kiểm tra IDs/references/version/source/review status; loader cho taxonomy/roles/competencies/questions/rubrics/manifest; metadata filter + keyword search đầu tiên; retrieval interface thay backend được; trả source IDs cùng nội dung; thiếu role data thì nói rõ hoặc chỉ dùng rubric chung đã duyệt; dữ liệu demo gắn nhãn.

**Đầu ra:** query theo industry/job family/role/level, provenance và báo lỗi liên kết.

**Hoàn tất:** thêm role theo template không sửa workflow; không trình bày dữ liệu chưa có như chuyên môn đã xác thực.

### Phase 4 — Interview workflow dạng text

**Nodes dự kiến:** validate_session → analyze_cv_jd → retrieve_criteria → build_plan → ask_question → capture_answer → decide_follow_up_or_next → allocate_question_time → final_evaluation → build_report.

**Việc:** LangGraph state rõ ràng (profile, context, retrieved IDs, plan, turns, current question, timer, transcript/report); câu hỏi chính theo mix; follow-ups thích ứng theo answer/CV/JD/competency; xử lý off-topic, thiếu thông tin, im lặng, timeout, end; follow-up depth/count từ config; difficulty classifier chọn band từ pressure profile; không lộ coaching/score.

**Đầu ra:** text interview end-to-end, state/transition reasons có thể debug.

**Hoàn tất:** ngôn ngữ/cấp độ/context đúng; follow-up không lặp/chệch; mọi lối kết thúc đi qua final evaluation.

### Phase 5 — Voice loop

**Việc:** browser microphone/permission; STT adapter gắn transcript với đúng turn; quyết định UX sửa transcript; TTS câu hỏi và replay; timer đồng bộ với speaking/thinking/recording/submitting; xử lý audio rỗng, mạng, timeout, quota, permission; VI/EN theo session.

**Đầu ra:** voice session hoàn chỉnh và recovery state khi provider hỏng.

**Hoàn tất:** không mất turn; STT/TTS dùng đúng language; timer theo state/profile.

### Phase 6 — Đánh giá và report

**Việc:** rubric bốn trục; role rubric bổ sung chuyên môn; score/nhận xét gắn transcript evidence; phân biệt thiếu evidence với câu yếu; strengths/gaps/next practice; sample answer chỉ dùng sự kiện trong CV/transcript; language feedback phù hợp; speech stats phụ; version report contract.

**Đầu ra:** báo cáo cuối có điểm, dẫn chứng, khuyến nghị.

**Hoàn tất:** đánh giá chuyên môn có rubric đã truy xuất; không có coaching giữa phiên; nhận xét có thể kiểm tra nguồn.

### Phase 7 — POC tích hợp và hiệu chỉnh

**Việc:** hoàn thiện UI states; review thủ công bằng hồ sơ/JD tổng hợp cho cả VI/EN; nhận phản hồi về follow-up, rubric, timer, report; xem latency/chi phí theo logging đã duyệt; hướng dẫn setup/config; backlog giới hạn.

**Đầu ra:** bản demo POC và danh sách giới hạn/backlog.

**Hoàn tất:** upload → setup → voice interview → report hoạt động; profile đọc từ config; chỉ tuyên bố hỗ trợ phần đã có dữ liệu/chất lượng.

## 4. Vertical slice ưu tiên

1. CV/JD tổng hợp + role demo có nhãn chưa xác thực.
2. Chọn language/level từ config.
3. Một câu hỏi text, một answer, một follow-up.
4. Difficulty band lấy từ pressure config.
5. Final report có transcript evidence.
6. Thêm STT/TTS sau khi text workflow ổn.
7. Thêm role thứ hai qua template để kiểm tra extensibility.

## 5. Session state gợi ý

    id, status, language, level_id, pressure_profile_id
    cv_context, jd_context, role_mapping
    retrieved_competency_ids, retrieved_question_ids, rubric_version
    interview_plan, current_question, follow_up_depth
    turn_history, transcript_segments, timing_decisions
    started_at, ended_at, report_version

Transcript/CV/JD là nguồn gốc; LLM summary không thay thế chúng.

## 6. Definition of Done xuyên suốt

- Không mặc định fresher có kinh nghiệm chuyên nghiệp.
- Không bịa achievement, nguồn hoặc chuyên môn chưa có.
- Follow-up liên quan và tôn trọng giới hạn cấu hình.
- Level, mix, language, rubric, timing không hard-code.
- Nhận xét gắn evidence; thiếu evidence hiển thị rõ.
- File/provider lỗi có trạng thái dễ hiểu.
- Chốt retention trước khi phát hành thật.

## 7. Bảng quyết định kỹ thuật

| Chủ đề | Trạng thái | Ghi chú |
|---|---|---|
| Frontend/backend | Đã chọn hướng | React + Vite / Python FastAPI |
| Workflow | Đã chọn hướng | LangGraph có state và giới hạn |
| Level/timing | Đã chốt nguyên tắc | User chọn; timer theo câu/config |
| Retrieval | Đã chốt hướng đầu | Kho có provenance; chưa web search |
| Contract và ID conventions | Đã phác thảo | Xem contracts/README.md và JSON Schemas |
| LLM/STT/TTS | Chưa chốt | Dùng adapters/mock; chọn trước vendor integration |
| CV/JD format | Đã chốt | PDF + DOCX text-based; không OCR scan |
| Database/persistence | Chưa chốt | Trước history/resume |
| Region/retention | Chưa chốt | Trước public release |
