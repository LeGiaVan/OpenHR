# Hợp đồng dữ liệu và ranh giới dịch vụ

Đây là data contract cho POC, chưa phải OpenAPI endpoint spec. JSON Schemas bên cạnh định nghĩa payload ổn định giữa API, LangGraph và UI. Khi field thay đổi, cập nhật schema, config/example liên quan và PLAN.md cùng lúc.

## Quy ước ID và thời gian

- Config/knowledge-base ID dùng slug lowercase snake_case, ổn định sau khi được tham chiếu.
- Session, document, turn và report dùng UUID do backend tạo.
- ID unique trong namespace resource; tham chiếu bằng field hậu tố _id.
- contract_version là version payload; version trong YAML là version của tài liệu cấu hình/kho.
- Timestamp API dùng RFC 3339/ISO 8601 có timezone; backend lưu UTC.
- Language code là vi hoặc en.
- Score theo rubric config: contract nhận số, nhãn chuỗi hoặc null. insufficient_evidence phải có score null; thang và trọng số chưa khóa.

## Contracts

- configs/schemas/interview_levels.schema.json: level và question mix.
- configs/schemas/pressure_profiles.schema.json: time bands và timing workflow.
- session.schema.json: lựa chọn phiên, document references, trạng thái, role mapping.
- turn.schema.json: question/answer transcript và timing decision của một lượt.
- report.schema.json: feedback cuối phiên, evidence và dimension status.
- knowledge_base/schemas: competency, question và rubric được lưu trong kho.

## Semantic validation

JSON Schema không thể biểu diễn mọi ràng buộc quan hệ. Loader cần kiểm tra:

1. Version được hỗ trợ; ID không trùng trong namespace.
2. default_level/default_profile tham chiếu record hiện có.
3. Tổng question_mix bằng 1, sai số tối đa 0.000001.
4. Rubric, competency, source và question references tồn tại hoặc được đánh dấu optional.
5. Preparation time không âm; answer time dương; đủ low/medium/high bands.
6. insufficient_evidence thì score null; scored thì score không null.
7. Lifecycle timestamp hợp lệ; completed session có ended_at.
8. Turn language khớp session language trừ khi có quyết định hỗ trợ code-switching.

## Validation và lỗi

- Static configs/schema được validate lúc backend khởi động. Sai schema, duplicate ID, default/reference hỏng hoặc mix sai thì fail fast; không mở session.
- Request sai trả lỗi validation gồm code, message, request_id và field errors; không trả stack trace hoặc secret.
- HTTP status đề xuất: 422 input sai, 404 không tồn tại, 409 chuyển state không hợp lệ, 413 file vượt giới hạn, 503 provider tạm không sẵn sàng.
- Provider errors được chuyển thành message an toàn. Log chỉ giữ mã lỗi/latency cần thiết; không ghi toàn văn CV/JD/transcript/audio.
- File size, MIME type, upload storage và retry policy còn phụ thuộc quyết định định dạng/provider.
- POC chỉ nhận PDF và DOCX có text; tài liệu scan/OCR nằm ngoài phạm vi.

## Ranh giới hệ thống

    Browser (React/Vite)
      | upload, setup, audio, report
      v
    FastAPI (API contracts, validation, session boundary)
      |                 |                 |
      |                 |                 +--> Parser / LLM / STT / TTS adapters
      |                 +--> LangGraph (explicit state and transitions)
      |                                   |
      |                                   +--> Config profiles
      |                                   +--> Retrieval interface
      |                                               |
      +-----------------------------------------------+--> Knowledge base

FastAPI sở hữu public API và request validation. LangGraph sở hữu workflow stateful. Adapters cô lập vendor code. Knowledge base trả records kèm provenance. Browser không giữ secrets hoặc bản sao business rules.

## Lifecycle phiên

preparing → ready → running → completed

Lỗi xử lý có thể chuyển sang failed; user rời/hủy có thể chuyển sang cancelled. Session terminal không nhận thêm turn. Persistence và resume chưa chốt.

## Chưa quyết định ở Phase 0

Endpoint paths/methods, multipart field names, file-size limits, provider payload formats, database, retention và score scale được chốt trước integration tương ứng. File format POC đã chốt là PDF/DOCX có text, không OCR scan. Adapter giữ ranh giới độc lập provider cho tới lúc chọn vendor.
