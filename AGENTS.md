# Hướng dẫn làm việc cho coding agent

Tài liệu này là context thường trực cho agent làm việc trong repository. Mỗi phiên hãy đọc tài liệu này cùng Proposal.MD và PLAN.md trước khi sửa code. Proposal là nguồn product intent; PLAN là nguồn thứ tự triển khai, acceptance conditions và quyết định còn mở.

## Sứ mệnh

Xây web app luyện phỏng vấn bằng giọng nói cho sinh viên/người mới tốt nghiệp apply intern/fresher. App dùng CV và JD, cho người dùng chọn tiếng Việt/Anh và cấp độ, mô phỏng buổi phỏng vấn có follow-up thích ứng, rồi trả báo cáo theo rubric sau phiên.

Đây là công cụ luyện tập, không phải hệ thống tuyển chọn ứng viên.

## Quyết định đã chốt

- Cần cả CV và JD làm context cho phiên cá nhân hóa.
- Hỗ trợ tiếng Việt hoặc tiếng Anh, người dùng chọn theo từng phiên.
- Hỗ trợ đa ngành bằng kho tiêu chí mở rộng, không gắn logic vào một ngành.
- Hướng POC: React + Vite, Python FastAPI, LangGraph.
- User chọn level. Profile điều khiển difficulty, behavioral/role-specific mix, rubric profile và follow-up strategy.
- Cấp độ, question mix, pressure/timing, follow-up depth/count đọc từ config/data; không hard-code vào prompt, API handler hay UI.
- Follow-up theo câu trả lời, CV, JD và criteria là core capability.
- Trong buổi không coach/chấm; phản hồi chỉ sau khi kết thúc.
- Report gồm relevance/domain skill, cấu trúc/dẫn chứng, giao tiếp, language khi phù hợp.
- Chấp nhận evidence từ môn học, đồ án, hoạt động, tình nguyện, project cá nhân, cuộc thi, part-time và internship; không mặc định phải có kinh nghiệm công ty.
- Nguồn retrieval giai đoạn đầu là kho có kiểm soát/provenance; không tự thêm web search.

## Source of truth và quyết định mở

- Đọc Proposal.MD cho mục tiêu và trải nghiệm.
- Đọc PLAN.md cho phases, dependencies, acceptance và open decisions.
- Đọc configs/interview_levels.yaml và configs/pressure_profiles.yaml trước khi sửa interview/timing.
- Đọc knowledge_base/README.md, schemas và templates trước khi thêm dữ liệu.
- Chưa tự quyết provider LLM/STT/TTS, file formats, database, retention, deployment region hay score weights.
- Nếu công việc phụ thuộc quyết định chưa chốt, liệt kê option và hỏi trong một lần tổng hợp ngắn; không hỏi rải rác từng lượt.
- Khi chốt một quyết định, cập nhật config/docs và bảng quyết định trong PLAN.md.

## Ràng buộc hành vi sản phẩm

- Không hiện điểm, corrective hint hay câu trả lời mẫu giữa phiên.
- Không bịa kinh nghiệm, chứng chỉ, số liệu hay thành tích của ứng viên.
- Mọi nhận xét/điểm phải dựa trên transcript evidence và rubric đã chọn.
- Phân biệt thiếu evidence với năng lực yếu; không ép chấm khi không đủ thông tin.
- Follow-up gắn với câu vừa trả lời, CV/JD và role; tôn trọng depth/count limit.
- Nếu kho không có tiêu chí role, dùng tiêu chí chung đã được duyệt hoặc thể hiện hạn chế; không giả vờ có chuyên môn đặc thù.
- Thời gian được tính từ độ khó, level, loại câu và pressure profile. Mọi ngưỡng đọc từ cấu hình; không tạo timeout dùng chung.
- Language session điều khiển câu hỏi, speech configuration và feedback language.
- CV, JD, transcript, audio là dữ liệu nhạy cảm. Không log toàn văn hoặc tự quyết định retention dài hạn.

## Hướng dẫn kiến trúc

- Dùng LangGraph làm workflow hữu hạn, inspectable, có state/transition rõ; không xây agent tự chủ không giới hạn.
- Tách parser, LLM, STT, TTS và retrieval sau các interfaces/adapters có thể thay.
- Frontend trình bày profile từ API/config; không tạo bản sao business rules hard-code.
- Giữ provenance cho criteria/questions/rubrics bằng IDs, source và version.
- Session state phải minh bạch: language, level/profile, CV/JD context, retrieved IDs, turn history, câu hiện tại, timing decision, transcript và report.
- Không đưa provider secrets lên browser hoặc commit vào repo.
- Chọn retrieval đơn giản nhất đáp ứng quy mô dữ liệu; không thêm vector DB nếu chưa có nhu cầu thực.
- File trong knowledge_base/roles/_template là ví dụ cấu trúc, không phải nội dung ngành đã kiểm chứng.

## Cách làm việc

1. Đọc docs và file liên quan trước khi sửa; giữ nguyên thay đổi sẵn có.
2. Chia việc thành thay đổi nhỏ theo phase đang làm trong PLAN.md.
3. Đồng bộ schema, config mẫu, API contract và hành vi UI.
4. Khi đổi decision, config field, workflow state hay API contract, cập nhật docs cùng lúc.
5. Không mở rộng sang accounts, payments, history dài hạn, live web search hoặc advanced analytics nếu chưa được yêu cầu.
6. Không thêm hoặc chạy tests trừ khi user yêu cầu test/verification. Không tuyên bố đã chạy check nếu chưa chạy.
7. Khi bàn giao, nêu thay đổi, file liên quan, quyết định còn mở và checks chưa chạy.

## Giao tiếp

- Mặc định phản hồi bằng tiếng Việt.
- User thích một danh sách câu hỏi cần thiết được gom lại thay vì bị hỏi từng câu qua nhiều lượt.
- Không hỏi lại quyết định đã có trong tài liệu.
- Nêu assumption rõ; không gọi dữ liệu demo là rubric đã được xác thực.
