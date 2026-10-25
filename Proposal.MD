# Proposal: Trợ lý luyện phỏng vấn bằng giọng nói cho ứng viên Intern/Fresher

## 1. Tóm tắt

Xây dựng một web app giúp sinh viên và người mới tốt nghiệp luyện phỏng vấn cho các vị trí intern/fresher. Người dùng tải CV và mô tả công việc (JD), chọn ngôn ngữ và cấp độ phỏng vấn, sau đó tham gia một buổi mô phỏng bằng giọng nói.

Người phỏng vấn AI tạo câu hỏi theo CV, JD và kho tiêu chí theo ngành/vị trí. Trong buổi tập, AI hỏi tiếp dựa trên câu trả lời để đào sâu kinh nghiệm học tập, đồ án, hoạt động ngoại khóa hoặc việc làm thêm. Buổi phỏng vấn diễn ra liền mạch; hệ thống chỉ chấm và đưa phản hồi sau khi kết thúc.

Sản phẩm nhắm đến việc giúp ứng viên mới biết cách trình bày năng lực và chuẩn bị tốt hơn cho một buổi phỏng vấn cụ thể. Đây là công cụ thực hành, không phải hệ thống tuyển chọn hoặc quyết định ứng viên.

## 2. Người dùng và nhu cầu

**Người dùng chính:** sinh viên và người mới tốt nghiệp đang ứng tuyển thực tập hoặc vị trí fresher.

Nhóm này có thể chưa có kinh nghiệm phỏng vấn, chưa biết cách cấu trúc câu trả lời, hoặc khó kết nối kinh nghiệm từ trường học với yêu cầu trong JD. Hệ thống cần đánh giá được ví dụ từ:

- Đồ án, bài tập và môn học.
- Câu lạc bộ, hoạt động ngoại khóa và tình nguyện.
- Công việc bán thời gian hoặc thực tập trước đó.
- Tự học, sản phẩm cá nhân và cuộc thi.

## 3. Trải nghiệm chính

1. Người dùng tải CV và JD lên dưới dạng PDF hoặc DOCX có text. Hai tài liệu này là context bắt buộc cho phiên để câu hỏi gắn với hồ sơ và vị trí ứng tuyển; POC chưa xử lý tài liệu scan bằng OCR.
2. Người dùng chọn ngôn ngữ phỏng vấn: tiếng Việt hoặc tiếng Anh.
3. Người dùng chọn cấp độ phỏng vấn. Cấp độ quyết định độ khó, tỷ lệ câu hỏi behavioral/chuyên môn và cách hỏi follow-up.
4. Hệ thống trích xuất kỹ năng, kinh nghiệm và yêu cầu trong JD; truy xuất tiêu chí liên quan từ kho kiến thức.
5. AI mở đầu, hỏi lần lượt và đặt câu hỏi follow-up dựa trên câu trả lời. Không đưa gợi ý hay điểm số giữa buổi.
6. Khi hoàn tất, hệ thống tạo báo cáo với điểm theo rubric, dẫn chứng từ câu trả lời và hướng cải thiện.

### Luồng hội thoại

```text
CV + JD + ngôn ngữ + cấp độ
            |
            v
Phân tích tài liệu -> Truy xuất rubric/câu hỏi phù hợp
            |
            v
Phỏng vấn bằng giọng nói <-> Follow-up thích ứng theo câu trả lời
            |
            v
Tổng hợp transcript -> Đánh giá theo rubric -> Báo cáo cuối buổi
```

## 4. Cấp độ phỏng vấn có thể cấu hình

Người dùng chọn cấp độ trước mỗi phiên. Các cấp độ bên dưới là cấu hình khởi đầu; tỷ lệ và rubric phải nằm trong file cấu hình hoặc kho dữ liệu, không gắn cứng vào mã nguồn.

| Cấp độ | Định hướng ban đầu | Nội dung chính |
|---|---|---|
| 1 – Nền tảng | Thiên về behavioral | Động lực ứng tuyển, giới thiệu bản thân, học tập, hoạt động và tình huống cơ bản |
| 2 – Cân bằng | Trộn behavioral và chuyên môn | Kinh nghiệm trong CV, kỹ năng trong JD, tình huống áp dụng và câu hỏi đào sâu |
| 3 – Chuyên sâu | Thiên về chuyên môn | Kiến thức/kỹ năng theo vị trí, cách giải quyết vấn đề, trade-off và follow-up kỹ thuật |

Tỷ lệ câu hỏi là giá trị cấu hình theo cấp độ và có thể điều chỉnh theo ngành/vị trí. Ví dụ cấu hình:

```yaml
id: level_1
name: Nền tảng
difficulty: beginner
question_mix:
  behavioral: 0.8
  role_specific: 0.2
follow_up:
  enabled: true
  strategy: clarify_then_probe
  max_depth: <cấu hình theo sản phẩm>
rubric_profile: entry_level
```

Các trường và giá trị trên minh họa cấu trúc, chưa phải bộ rubric hoàn chỉnh. Cần cho phép thêm/sửa cấp độ bằng cấu hình mà không cần thay đổi workflow.

## 5. Áp lực và thời lượng thích ứng

Không đặt một thời gian trả lời cố định cho mọi câu. Thời lượng cần phản ánh độ khó, cấp độ, loại câu hỏi và mức độ áp lực của phiên. Ví dụ, câu hỏi giới thiệu ngắn không cần cùng thời lượng với câu hỏi phân tích một tình huống kỹ thuật.

Một bước riêng trong workflow sẽ phân bổ thời gian cho từng câu dựa trên metadata của câu hỏi và cấu hình pressure profile. Có thể cấu hình thời gian suy nghĩ, thời gian trả lời, giới hạn tối thiểu/tối đa và mức áp lực. Mọi ngưỡng đều đọc từ cấu hình; không hard-code trong prompt hoặc logic giao diện.

Các cấp độ, pressure profile và chiến lược tính thời lượng nên tách riêng, để có thể thử nghiệm nhiều cách tính mà không viết lại luồng phỏng vấn. Cấu hình ban đầu có thể để ở `configs/interview_levels.yaml` và `configs/pressure_profiles.yaml`; workflow LangGraph chịu trách nhiệm chọn/áp dụng cấu hình cho từng câu.

## 6. Follow-up thích ứng

Follow-up là năng lực cốt lõi và điểm khác biệt của sản phẩm. Sau mỗi câu trả lời, hệ thống có thể:

- Yêu cầu làm rõ vai trò cá nhân trong một đồ án nhóm.
- Hỏi cách ứng viên xử lý trở ngại hoặc lựa chọn một giải pháp.
- Đào sâu kỹ năng được nêu trong CV hoặc JD.
- Hỏi về kết quả, tác động hoặc bài học rút ra.
- Chuyển sang câu tiếp theo khi câu trả lời đã đủ thông tin.

Agent cần duy trì ngữ cảnh hội thoại, cấp độ đã chọn và tiêu chí đang đánh giá. Follow-up phải liên quan đến câu trả lời và vị trí ứng tuyển; số lần/độ sâu hỏi tiếp được giới hạn bằng cấu hình để phiên có nhịp độ dự đoán được.

## 7. Đánh giá và báo cáo cuối buổi

Không hiển thị điểm hay hướng dẫn trong lúc mô phỏng. Sau khi kết thúc, hệ thống tổng hợp:

1. **Mức độ liên quan và năng lực chuyên môn:** câu trả lời có đáp ứng yêu cầu JD và đúng với cấp độ ứng tuyển không.
2. **Cấu trúc và dẫn chứng:** lập luận có mạch lạc, nêu rõ vai trò và có ví dụ cụ thể không.
3. **Giao tiếp:** câu trả lời có rõ ràng, súc tích và dễ theo dõi không.
4. **Năng lực ngôn ngữ:** chỉ áp dụng khi phiên dùng ngoại ngữ; có thể nhận xét từ vựng, ngữ pháp và cách diễn đạt.

Mỗi điểm số cần đi cùng dẫn chứng cụ thể từ transcript, nhận xét điểm mạnh, khoảng trống và gợi ý luyện tập tiếp theo. Có thể đưa một phiên bản trả lời mẫu để tham khảo, nhưng cần dựa trên trải nghiệm thật trong CV và câu trả lời của người dùng, không tự bịa thành tích.

Thang điểm và trọng số chưa được chốt; chúng cần được định nghĩa trong rubric theo cấu hình, không gắn cứng trong ứng dụng.

Thống kê từ đệm, tốc độ nói và khoảng ngắt nghỉ là chỉ số phụ để tham khảo, không thay thế đánh giá nội dung. Rubric phải được truy xuất theo ngành, vị trí và cấp độ; không dùng một tiêu chuẩn chuyên môn chung cho mọi ngành.

## 8. Khung kho tiêu chí đa ngành

Kho tiêu chí là nguồn context chính để hỗ trợ nhiều ngành. Bản đầu cần có cấu trúc để bổ sung dữ liệu sau này; hiện chưa giả định có sẵn bộ dữ liệu hoàn chỉnh. Mỗi mục nên có nguồn, ngày cập nhật và phiên bản để nội dung có thể rà soát.

### Đơn vị dữ liệu đề xuất

- **Ngành và vị trí:** phân cấp ngành → nhóm vị trí → chức danh.
- **Năng lực:** kỹ năng/chủ đề liên quan, mô tả năng lực và cấp độ kỳ vọng.
- **Rubric:** tiêu chí, mô tả từng mức đạt, bằng chứng cần tìm và lỗi thường gặp.
- **Câu hỏi:** câu hỏi gợi ý, loại câu hỏi, độ khó, năng lực được đánh giá và follow-up mẫu.
- **Nguồn:** nơi lấy/biên soạn nội dung, người phụ trách, ngày cập nhật, trạng thái rà soát và phiên bản.

### Cấu trúc thư mục có thể mở rộng

```text
knowledge_base/
  README.md
  schemas/
    competency.schema.json
    rubric.schema.json
    question.schema.json
  taxonomies/
    industries.yaml
    job_families.yaml
  roles/
    <industry>/<role>/
      competencies.yaml
      rubrics.yaml
      questions.yaml
  sources/
    manifest.yaml
  ingestion/
    README.md
```

CV và JD của phiên là context cá nhân; kho tiêu chí cung cấp khung chuyên môn và rubric. Hệ thống kết hợp hai nguồn theo ngành/vị trí/cấp độ, rồi chỉ đưa các phần liên quan vào context của từng bước. Có thể bắt đầu với tìm kiếm từ khóa và metadata; thêm vector search khi lượng nội dung và nhu cầu truy xuất đòi hỏi.

Chưa gắn kho với một nguồn bên ngoài cụ thể. Cấu trúc trên cho phép bổ sung dữ liệu được biên soạn nội bộ hoặc nguồn khác trong tương lai, kèm kiểm duyệt và quản lý phiên bản.

## 9. Kiến trúc đề xuất

- **Frontend:** React + Vite; giao diện tải CV/JD, chọn ngôn ngữ/cấp độ, phòng phỏng vấn, timer và báo cáo.
- **Backend:** Python FastAPI; quản lý phiên, xử lý tài liệu, API hội thoại và báo cáo.
- **Workflow:** LangGraph điều phối các bước có trạng thái: phân tích CV/JD, truy xuất context, lập kế hoạch câu hỏi, phỏng vấn/follow-up, phân bổ thời lượng và đánh giá cuối buổi.
- **STT/TTS:** dùng adapter để có thể thay nhà cung cấp Speech-to-Text và Text-to-Speech mà không đổi luồng nghiệp vụ. Chọn nhà cung cấp sau khi thử chất lượng tiếng Việt/Anh, độ trễ và chi phí.
- **LLM:** chọn model qua cấu hình; cần đánh giá chất lượng tạo câu hỏi, follow-up và chấm rubric trên cả hai ngôn ngữ trước khi chốt.
- **Retrieval:** lớp truy xuất theo metadata ngành/vị trí/cấp độ, hỗ trợ thay đổi backend tìm kiếm khi kho phát triển.
- **Cấu hình:** cấp độ, tỷ lệ loại câu hỏi, chiến lược follow-up, pressure profile và cách phân bổ thời gian được quản lý ngoài mã nguồn.

LangGraph được dùng để điều phối workflow rõ ràng và có thể kiểm soát, không phải yêu cầu xây một hệ agent tự chủ. Các bước đánh giá nên nhận rubric cụ thể và transcript làm đầu vào; không để LLM tự đặt tiêu chuẩn chấm.

## 10. Phạm vi MVP

### Bao gồm

- Web app chạy được trên trình duyệt.
- Tải CV và JD để cá nhân hóa phiên.
- Nhận CV/JD dạng PDF hoặc DOCX có text; chưa hỗ trợ OCR tài liệu scan.
- Chọn tiếng Việt hoặc tiếng Anh.
- Chọn một trong các cấp độ phỏng vấn từ cấu hình.
- Buổi phỏng vấn giọng nói có câu hỏi theo CV/JD và follow-up thích ứng.
- Áp lực/thời lượng được cấu hình và phân bổ theo từng câu.
- Báo cáo cuối phiên theo rubric, có dẫn chứng từ câu trả lời.
- Khung schema, thư mục và quy trình để bổ sung tiêu chí/ngành/vị trí sau này.

### Để giai đoạn sau

- Hoàn thiện dữ liệu cho nhiều ngành và kiểm định rubric với người có chuyên môn.
- Tài khoản người dùng, lưu lịch sử và theo dõi tiến bộ qua nhiều phiên.
- Tìm kiếm web trực tiếp trong phiên.
- Tùy chỉnh persona người phỏng vấn.
- Báo cáo nâng cao về cách phát âm, tốc độ và filler words.
- Triển khai thương mại, quản lý thanh toán và chính sách lưu trữ dài hạn.

Thị trường triển khai ban đầu và chính sách lưu CV/JD, transcript, bản ghi âm cần được quyết định riêng trước khi phát hành rộng rãi; proposal này chưa khóa các lựa chọn đó.

## 11. Tiêu chí đánh giá POC

- Người dùng hoàn thành được một phiên từ tải tài liệu đến báo cáo.
- Câu hỏi và follow-up bám được thông tin trong CV/JD, đúng cấp độ đã chọn.
- Follow-up giữ ngữ cảnh và không lặp hoặc đi chệch vị trí ứng tuyển.
- Điểm số gắn với rubric và có dẫn chứng từ transcript.
- Thời lượng mỗi câu thay đổi theo cấu hình/độ khó, không dùng một hằng số cho mọi câu.
- Chất lượng nhận dạng và tổng hợp giọng nói đạt mức dùng được cho tiếng Việt và tiếng Anh.
- Người dùng đánh giá được báo cáo là cụ thể và có thể hành động.

## 12. Các quyết định mở sau POC

- Nguồn dữ liệu cụ thể, quy trình kiểm duyệt và người sở hữu nội dung kho tiêu chí.
- Giá trị mặc định cho các cấp độ và pressure profile sau thử nghiệm.
- Nhà cung cấp LLM, STT, TTS và retrieval phù hợp về chất lượng/chi phí.
- Khu vực tuyển dụng ưu tiên và chính sách lưu/xóa dữ liệu.
- Cách người dùng xem lại transcript, báo cáo và tiến độ giữa các phiên.
