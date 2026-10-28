# Yêu cầu nghiệp vụ của khách hàng (Customer Requirements) - Đề tài 10

## 1. Bối cảnh bài toán
Doanh nghiệp cung cấp dịch vụ trực tuyến cần một hệ thống quản lý yêu cầu hỗ trợ khách hàng tập trung (Customer Support Ticket Management System). Trước đây, việc tiếp nhận qua email, tin nhắn mạng xã hội rời rạc dẫn đến tình trạng ticket bị thất lạc, bỏ sót, nhân viên không nắm được mức độ khẩn cấp, mất nhiều thời gian đọc lại lịch sử dài dòng khi chuyển giao ca trực.

## 2. Yêu cầu nghiệp vụ cụ thể
1. **Phân quyền người dùng**:
   - Quản trị viên (Admin): Toàn quyền cấu hình hệ thống, quản lý tài khoản nhân viên, cấu hình FAQ kiến thức hỗ trợ.
   - Quản lý nhóm (Team Lead): Phân công ticket cho nhân viên hỗ trợ, theo dõi tiến độ xử lý và xem báo cáo SLA, thống kê hiệu suất.
   - Nhân viên hỗ trợ (Support Agent): Xem danh sách ticket được giao, cập nhật trạng thái (Mới, Đang xử lý, Chờ khách hàng, Đã đóng), trao đổi với khách qua comment, sử dụng trợ lý AI.
   - Khách hàng (Customer): Gửi yêu cầu hỗ trợ (ticket), theo dõi tiến độ và trao đổi phản hồi.
2. **Quản lý khách hàng**:
   - Lưu trữ hồ sơ khách hàng: họ tên, email, số điện thoại, công ty, phân hạng (VIP/Standard).
3. **Quản lý Ticket**:
   - Tạo mới ticket: Tiêu đề, mô tả chi tiết, phân loại (Tài khoản, Thanh toán, Lỗi kỹ thuật, Tư vấn...), mức ưu tiên (Thấp, Trung bình, Cao, Khẩn cấp).
   - Theo dõi vòng đời trạng thái: `Mới` (New) -> `Đang xử lý` (In Progress) <-> `Chờ khách hàng` (Waiting Customer) -> `Đã đóng` (Closed).
   - Lịch sử trao đổi (Comments): Cho phép trao đổi nhiều lượt giữa khách hàng và nhân viên hỗ trợ, lưu vết thời gian và người gửi.
   - Tìm kiếm & lọc: Tìm kiếm theo từ khóa tiêu đề, lọc theo trạng thái, mức ưu tiên, khách hàng, nhân viên xử lý và khoảng thời gian.
   - Thống kê & Báo cáo: Tổng số ticket, phân bố theo trạng thái, thời gian xử lý trung bình, top vấn đề thường gặp.
4. **Tích hợp Trợ lý Trí tuệ Nhân tạo (AI Support Assistant)**:
   - **AI Phân loại & Gợi ý Mức ưu tiên**: Khi ticket được tạo, AI đọc tiêu đề & mô tả để gợi ý phân loại nhóm vấn đề và đề xuất mức ưu tiên phù hợp.
   - **AI Gợi ý câu trả lời nháp (Draft Response Suggester)**: AI phân tích câu hỏi của khách hàng, đối chiếu với cơ sở tri thức FAQ/chính sách hỗ trợ (RAG) và soạn thảo câu trả lời mẫu lịch sự, chính xác.
   - **Cơ chế Nhân viên duyệt (Human-in-the-Loop)**: Nhân viên hỗ trợ bắt buộc phải xem xét, chỉnh sửa câu trả lời nháp trước khi bấm nút gửi chính thức cho khách hàng. AI không được tự động gửi tin nhắn mà chưa có sự kiểm duyệt của nhân viên. AI tuyệt đối không cam kết hoàn tiền hoặc chính sách chưa được xác thực.
   - **AI Tóm tắt lịch sử hỗ trợ (Thread Summarization)**: Với các ticket có chuỗi trao đổi dài, AI tóm tắt ngắn gọn các ý chính, hành động đã thực hiện và nút thắt hiện tại để nhân viên mới nhận ca nắm bắt tức thì.
   - **Bảo mật & Quyền riêng tư (PII Sanitization)**: Ẩn/che thông tin cá nhân nhạy cảm (mật khẩu, thẻ tín dụng, số điện thoại cá nhân) trước khi truyền dữ liệu sang LLM bên ngoài.

## 3. Ràng buộc công nghệ
- Backend hiện hành: Python FastAPI.
- CSDL duy nhất: MySQL Community Server 8.0.46, InnoDB, utf8mb4.
- Frontend: HTML5, CSS3, JavaScript (giao diện hiện đại, responsive, trực quan).
- AI Engine: Google Gemini API (sử dụng biến môi trường `GEMINI_API_KEY`).

