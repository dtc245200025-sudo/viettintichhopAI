# Phạm vi VietinCare AI phiên bản 1.1

Cập nhật: 2026-09-21. Áp dụng chung cho tài liệu 02, 03, 04 và kế hoạch triển khai. Đây là phạm vi yêu cầu, không phải xác nhận tính năng đã hoàn thành.

## Nền tảng và giới hạn

- Website VI/EN, một backend chia module, **MySQL Community Server 8.0.46 duy nhất**, InnoDB, utf8mb4, database `QLKHViettin`.
- MySQL lưu nghiệp vụ, phiên, tri thức, embedding JSON, cấu hình không chứa bí mật và audit log. Backend gọi mô hình AI, kiểm tra embedding và tính cosine similarity. Không dùng database hoặc kho vector khác.
- Dùng dữ liệu giả lập. Không thực hiện giao dịch, tra cứu số dư hoặc khóa thẻ thật.
- Mốc 27/09/2026 giữ theo kế hoạch gốc; tiến độ thực tế nằm trong `PROJECT_CHECKLIST.md`.

## Phạm vi nghiệm thu

| ID | Phạm vi cốt lõi | Tiêu chí |
|---|---|---|
| UC001 | Đăng ký, đăng nhập email/mật khẩu, đăng xuất, hết hạn phiên, giới hạn thử đăng nhập | Băm mật khẩu; backend từ chối sai vai trò và dữ liệu khách khác |
| UC002 | Chat RAG sau đăng nhập, lưu lịch sử | Chỉ dùng tri thức đã xuất bản; phản hồi có nguồn; xử lý lỗi và thiếu nguồn |
| UC003 | Tạo ticket khi khách yêu cầu/đồng ý | Lưu MySQL, trả mã, không tạo trùng khi thử lại |
| UC004–005 | Gợi ý chủ đề, ưu tiên, cảm xúc | Agent sửa được; lỗi AI về hàng chờ chung; có bộ câu hỏi gán nhãn |
| UC006 | Chuyển giao chat cho Agent | Giữ lịch sử, tránh nhận trùng, xử lý không có Agent |
| UC007 | Nhận, phản hồi, giải quyết và đóng ticket; khách xem lịch sử | Lưu phản hồi và lịch sử trạng thái, còn sau tải lại |
| UC010 | Đánh giá CSAT | Chủ sở hữu gửi một lần, 1–5 sao, đúng mục tiêu đã hoàn thành |
| UC011 | Nhập FAQ/văn bản, chia đoạn, embedding, thử và xuất bản | `KnowledgeBase` và `KnowledgeChunk` trong MySQL |
| UC012 | Quản lý tài khoản và bốn vai trò | Admin tạo/sửa/khóa; kiểm tra quyền ở backend |
| UC013 | Dashboard cơ bản cho Supervisor | Ticket theo trạng thái/chủ đề, số phiên, CSAT thực tế |
| UC014 | Ghi và tra cứu audit log | Ghi ai, việc gì, đối tượng, thời điểm; không sửa log qua UI |
| UC015 | Cấu hình hệ thống | Ngưỡng truy xuất và thời gian chờ hợp lệ; ghi audit; bí mật ngoài mã nguồn |

UC008 Copilot, UC009 tóm tắt, tải PDF/DOCX, tệp đính kèm ticket, OTP/SSO, quên mật khẩu qua email, NPS, xuất Excel/PDF thuộc mở rộng. Core Banking/CRM, iPay/eFAST, Voicebot, SMS/email thật, sinh trắc học, định tuyến VIP và hạ tầng Kubernetes/GPU không thuộc nghiệm thu cốt lõi. Không cam kết 5.000 phiên hoặc uptime sản xuất 99,9%.

## Quy tắc thống nhất

1. Customer đăng nhập trước khi chat/tạo ticket; chỉ xem dữ liệu của mình. FAQ công khai không yêu cầu đăng nhập. Chat khách vãng lai là mở rộng.
2. Agent xử lý ca được giao; Supervisor giám sát và phân công; Admin quản lý tài khoản, tri thức, cấu hình và log. Quyền được kiểm tra tại backend.
3. Chat không tạo ticket cho mọi tin nhắn. Ticket được tạo khi khách yêu cầu hoặc đồng ý theo dõi vấn đề; không bắt buộc có phiên chat.
4. Ticket: **Mới → Đang xử lý → Đã giải quyết → Đã đóng**. Ghi tác nhân/thời điểm mỗi lần chuyển. Mở lại là mở rộng.
5. Ưu tiên: Thấp, Trung bình, Cao, Khẩn cấp. Cảm xúc: Tích cực, Trung tính, Tiêu cực. Hai trường độc lập; không dùng nhãn cảm xúc thứ tư.
6. Handover: Chờ tiếp nhận, Đã tiếp nhận, Đã kết thúc, Đã hủy. Một phiên chỉ có một lượt chuyển giao đang chờ/đang xử lý.
7. Đánh giá chỉ liên kết một phiên kết thúc hoặc một ticket đóng. Một lượt/khách/mục tiêu; CSAT = tỷ lệ đánh giá 4–5 sao trên tổng đánh giá hợp lệ. Mẫu số bằng 0 hiển thị Chưa có dữ liệu.
8. Cosine không phải xác suất đúng. Hiệu chỉnh ngưỡng truy xuất trên bộ câu hỏi; thiếu nguồn phải báo chưa có thông tin và gợi ý Agent/ticket. Bỏ quy tắc độ tin cậy mặc định 70%.
9. Thông báo cốt lõi hiển thị trong web; chỉ xác nhận lưu sau khi MySQL ghi thành công. API thử lại phải chống gửi trùng.
10. Dữ liệu lưu thời gian UTC; giao diện đổi sang giờ Việt Nam. Khóa nội bộ dùng INT; nếu cần mã hiển thị dạng chuỗi thì định nghĩa riêng, không thay kiểu khóa SQL.

## Thiết kế cần triển khai bằng migration

`SQLQuery1.sql` hiện có 15 bảng, chưa đại diện cho toàn bộ thiết kế đích:

- `Customer.MaUser`: khóa ngoại duy nhất đến `UserAccount`, tài khoản Customer và hồ sơ tạo trong cùng transaction. Email đăng nhập cần duy nhất theo quy tắc chuẩn hóa đã chọn.
- Phản hồi ticket độc lập với chat: bảng đích `TicketReply` gồm ticket, tài khoản gửi, nội dung, thời gian.
- `TicketStatusHistory`: ticket, trạng thái trước/sau, tài khoản thực hiện, thời điểm.
- Định danh người gửi trong `Message`; phân biệt người dùng và AI, kiểm tra quyền với phiên.
- `MessageSource`: liên kết phản hồi với `KnowledgeChunk` và phiên bản/nội dung nguồn để truy vết khi tri thức thay đổi.
- `SystemSetting`: khóa, giá trị, người cập nhật, thời điểm; không chứa mật khẩu/khóa API. Phiên đăng nhập lưu MySQL nếu dùng phiên server.
- Ràng buộc quyền sở hữu, đánh giá một mục tiêu, phạm vi điểm và trạng thái; kiểm tra đồng thời nhận ticket/handover ở backend.

Migration 001 đã triển khai một phần thiết kế này và được xác nhận trên máy người dùng; migration 002 bổ sung TicketRequest để chống gửi trùng trong luồng ticket. Trạng thái kiểm thử/áp dụng chi tiết nằm trong PROJECT_CHECKLIST.md. Chỉ dùng migration cho database đã có dữ liệu; không tự xóa hoặc chạy lại script khởi tạo.

## Kiểm thử và bàn giao

- Mục tiêu hiệu năng: p95 từ gửi câu hỏi đến nhận đủ câu trả lời ≤ 5 giây, 50 câu hỏi, 5 phiên đồng thời, tối đa 1.000 đoạn. Ghi máy, mô hình, mạng, độ dài phản hồi và tỷ lệ lỗi. Đây là mục tiêu chưa đo.
- Bộ ít nhất 50 câu hỏi có nhãn để đo phân loại; báo cáo kết quả thực tế và lỗi, không mặc định đạt 90%.
- Kiểm thử đăng nhập sai, quyền sai, dữ liệu khách khác, trạng thái sai, gửi trùng, lỗi AI, thiếu nguồn, không có Agent, đánh giá lặp và lưu dữ liệu sau tải lại.
- Demo toàn luồng: đăng nhập → chat → tạo ticket → Agent nhận/phản hồi → giải quyết/đóng → khách đánh giá → Supervisor xem số liệu.
- Hướng dẫn chạy, cấu hình mẫu không chứa bí mật, dữ liệu demo, sao lưu và khôi phục MySQL trên môi trường thử nghiệm.
- Không suy ra chứng nhận bảo mật hoặc tuân thủ ngân hàng từ demo. Chỉ ghi Pass có bằng chứng thực thi.

## Đồng bộ hồ sơ

Ba Word hiện có: `02_ban2.docx`, `03_ban2.docx`, `04_ban1.docx`. Chưa có file kiểm thử 05 trong thư mục. Các sơ đồ ảnh phiên bản trước được thay bằng luồng/quan hệ chữ có thể sửa trong Word; bản gốc lưu trong `.mysql-sync/scope-before-2026-09-21.zip`. Cần hoàn thiện sơ đồ UML/ERD và kiểm tra bố cục trước nghiệm thu tài liệu.

Cập nhật triển khai 2026-09-22: migration 003 bổ sung lịch sử hội thoại có tiêu đề/index và khóa chống gửi trùng. CHAT-01 đã có API/giao diện lưu tin nhắn Customer; đây là nền tảng của UC002, chưa hoàn thành toàn bộ UC002 vì AI-01/RAG chưa được nối. Implementation update: migration 003 adds persistent customer conversations and safe retries; AI/RAG remains pending.

Cập nhật triển khai tiếp theo 2026-09-22: đã có mã OpenAI Embeddings/Responses, kho tri thức văn bản phiên bản/xuất bản và phản hồi lưu nguồn. Migration 004 nâng tổng số bước lên 22. AI-01/UC002 vẫn chờ thử API thật, hiệu chỉnh ngưỡng và bộ câu hỏi chất lượng; không coi provider giả là bằng chứng chất lượng AI. English: OpenAI RAG and versioned knowledge management are implemented; live provider validation and quality calibration remain pending.
