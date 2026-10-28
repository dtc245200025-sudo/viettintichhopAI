# Hướng dẫn sử dụng hệ thống (User Guide) - Đề tài 10

## 1. Đăng nhập hệ thống
Truy cập `http://127.0.0.1:5000/login` và sử dụng một trong các tài khoản:
- **Admin**: `admin` / `Admin@123` (Toàn quyền quản trị, xem tất cả báo cáo và quản lý FAQ).
- **Team Lead**: `tuan.lead` / `Lead@123` (Quản lý nhóm, phân công ticket, theo dõi SLA).
- **Support Agent**: `agent_lan` / `Agent@123` (Nhân viên hỗ trợ, tiếp nhận ticket và sử dụng Trợ lý AI).

## 2. Quy trình xử lý Ticket bằng AI-Augmented SDLC
1. **Tiếp nhận & Phân loại**:
   - Khi tạo ticket mới, bấm nút **"AI Gợi ý Phân loại & Mức ưu tiên"**. AI sẽ đọc mô tả để tự động chọn đúng nhóm vấn đề (Tài khoản, Thanh toán, Kỹ thuật...) và mức độ khẩn cấp.
2. **Xem chi tiết & Sử dụng Trợ lý AI**:
   - Mở ticket cần xử lý, chuyển qua cột bên phải mang tên **"Trợ lý Hỗ trợ AI (ViettinCare AI)"**.
3. **Quy trình Human Gate (Kiểm duyệt phản hồi AI)**:
   - Bước 1: Bấm nút **"AI Soạn thảo Câu trả lời Nháp"**. AI sẽ tra cứu cơ sở tri thức FAQ và đưa ra bản nháp.
   - Bước 2: Nhân viên đọc kỹ bản nháp trong ô soạn thảo, chỉnh sửa/bổ sung thông tin nếu cần thiết.
   - Bước 3: Bấm nút màu xanh **"Phê duyệt & Gửi cho Khách hàng"**. Phản hồi được ghi nhận chính thức vào lịch sử trao đổi của ticket, trạng thái ticket tự động chuyển sang `Chờ khách hàng` (Waiting Customer).
4. **Tóm tắt chuỗi trao đổi (Thread Summarization)**:
   - Khi nhận ca trực từ đồng nghiệp với ticket có nhiều trao đổi, chuyển sang tab **"Tóm tắt Lịch sử"** và bấm nút **"Tạo Tóm tắt bằng AI"** để nắm bắt nhanh 3 ý chính mà không mất thời gian đọc từng tin nhắn cũ.

