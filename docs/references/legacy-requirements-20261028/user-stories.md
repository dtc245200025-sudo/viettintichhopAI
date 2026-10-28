# Danh sách User Stories (User Stories Specification) - Đề tài 10

## Danh sách User Stories chi tiết

### US-001: Đăng nhập và phân quyền hệ thống
- **Là một** nhân viên hoặc quản lý hệ thống,
- **Tôi muốn** đăng nhập bằng tài khoản và mật khẩu được cấp,
- **Để** truy cập đúng các chức năng tương ứng với vai trò của mình (Admin / Team Lead / Support Agent).
- *Truy vết: FR-001*

### US-002: Quản lý hồ sơ khách hàng
- **Là một** nhân viên hỗ trợ hoặc quản lý,
- **Tôi muốn** xem và cập nhật hồ sơ khách hàng cùng thông tin liên hệ,
- **Để** nắm rõ lịch sử dịch vụ và dễ dàng tương tác trong quá trình xử lý sự cố.
- *Truy vết: FR-002*

### US-003: Tạo và theo dõi tiến độ ticket
- **Là một** khách hàng hoặc nhân viên đại diện,
- **Tôi muốn** tạo ticket hỗ trợ với tiêu đề, mô tả và chọn mức độ ưu tiên,
- **Để** vấn đề của tôi được ghi nhận vào hệ thống và theo dõi trạng thái từ lúc tiếp nhận đến khi hoàn tất.
- *Truy vết: FR-003*

### US-004: Phân công ticket cho nhân viên xử lý
- **Là một** quản lý nhóm (Team Lead),
- **Tôi muốn** gán ticket mới cho nhân viên hỗ trợ phù hợp trong nhóm,
- **Để** tối ưu hóa nguồn lực và đảm bảo ticket được giải quyết đúng cam kết thời gian.
- *Truy vết: FR-004*

### US-005: Trao đổi trong ticket
- **Là một** nhân viên hỗ trợ hoặc khách hàng,
- **Tôi muốn** gửi tin nhắn phản hồi trong luồng trao đổi của ticket,
- **Để** cung cấp thêm thông tin kỹ thuật và hướng dẫn giải quyết vấn đề.
- *Truy vết: FR-005*

### US-006: Tìm kiếm và lọc danh sách ticket
- **Là một** nhân viên hỗ trợ,
- **Tôi muốn** lọc ticket theo trạng thái (Mới, Đang xử lý, Chờ khách, Đã đóng) và độ ưu tiên,
- **Để** ưu tiên xử lý các trường hợp khẩn cấp trước.
- *Truy vết: FR-006*

### US-007: Báo cáo thống kê quản lý
- **Là một** quản trị viên hoặc quản lý nhóm,
- **Tôi muốn** xem biểu đồ thống kê số lượng ticket, tỷ lệ hoàn thành và thời gian xử lý,
- **Để** đánh giá chất lượng dịch vụ chăm sóc khách hàng và phát hiện các sự cố phần mềm phổ biến.
- *Truy vết: FR-007*

### US-008: AI tự động phân loại và gợi ý ưu tiên
- **Là một** nhân viên hỗ trợ hoặc quản lý,
- **Tôi muốn** AI tự động phân tích nội dung ticket để gán nhãn danh mục và gợi ý mức ưu tiên,
- **Để** giảm thiểu thao tác nhập liệu thủ công và không bỏ sót các sự cố nghiêm trọng.
- *Truy vết: FR-008*

### US-009: AI gợi ý câu trả lời nháp từ FAQ (RAG)
- **Là một** nhân viên hỗ trợ,
- **Tôi muốn** AI đề xuất câu trả lời mẫu dựa trên cơ sở tri thức FAQ và mô tả sự cố,
- **Để** tôi có thể phản hồi khách hàng nhanh chóng, chuẩn mực và chính xác theo chính sách doanh nghiệp.
- *Truy vết: FR-009, FR-010*

### US-010: Nhân viên duyệt câu trả lời trước khi gửi (Human-in-the-Loop)
- **Là một** nhân viên hỗ trợ,
- **Tôi muốn** xem trước, biên tập lại câu trả lời nháp của AI và chủ động bấm xác nhận gửi,
- **Để** kiểm soát chất lượng thông tin, ngăn chặn tình trạng AI tự ý cam kết bồi thường sai quy định.
- *Truy vết: FR-010*

### US-011: AI tóm tắt chuỗi trao đổi dài
- **Là một** nhân viên mới nhận ca trực của ticket,
- **Tôi muốn** xem tóm tắt ngắn gọn lịch sử trao đổi do AI sinh ra,
- **Để** hiểu ngay bối cảnh sự cố mà không mất 15-20 phút đọc từng tin nhắn cũ.
- *Truy vết: FR-011*

