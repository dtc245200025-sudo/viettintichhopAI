# Tiêu chí chấp nhận (Acceptance Criteria) - Đề tài 10

## Chi tiết các tiêu chí kiểm thử chấp nhận (Given - When - Then)

### AC-001: Đăng nhập và phân quyền hợp lệ (FR-001)
- **Given**: Tài khoản nhân viên hỗ trợ `agent1@viettincare.vn` tồn tại với mật khẩu hợp lệ và vai trò `agent`.
- **When**: Người dùng nhập đúng email, mật khẩu và bấm "Đăng nhập".
- **Then**: Hệ thống cấp session, chuyển hướng tới màn hình danh sách ticket với quyền hạn xem/cập nhật ticket được gán, không được truy cập trang cấu hình quản trị của Admin.

### AC-002: Thêm mới ticket và kiểm tra dữ liệu đầu vào (FR-003)
- **Given**: Người dùng đã đăng nhập hoặc khách hàng gửi biểu mẫu tạo ticket.
- **When**: Gửi tiêu đề "Lỗi không đăng nhập được sau khi đổi mật khẩu" và mô tả chi tiết, để trống danh mục.
- **Then**: Hệ thống ghi nhận ticket mới với trạng thái mặc định là `New`, kích hoạt AI để phân tích và đề xuất danh mục `Tài khoản & Đăng nhập`, mức ưu tiên `High`.

### AC-003: Chuyển đổi trạng thái Ticket theo quy trình (FR-003)
- **Given**: Ticket #105 đang ở trạng thái `New` và được giao cho nhân viên `agent1`.
- **When**: Nhân viên bắt đầu xử lý và cập nhật trạng thái sang `In Progress`.
- **Then**: Hệ thống cập nhật timestamp `updated_at`, hiển thị trạng thái `Đang xử lý` trên giao diện và lưu lịch sử thay đổi trạng thái.

### AC-004: Trao đổi comment và cập nhật luồng sự kiện (FR-005)
- **Given**: Ticket #105 đang mở.
- **When**: Nhân viên hỗ trợ nhập nội dung giải thích: "Chúng tôi đã gửi lại liên kết kích hoạt, vui lòng kiểm tra hộp thư Spam" và bấm Gửi.
- **Then**: Hệ thống thêm một bản ghi vào bảng `ticket_comments`, cập nhật trạng thái ticket sang `Waiting Customer`.

### AC-005: AI phân loại sự cố và mức ưu tiên gợi ý (FR-008)
- **Given**: Ticket có tiêu đề: "Hệ thống thanh toán báo trừ tiền nhưng không kích hoạt gói dịch vụ".
- **When**: Gọi API phân loại AI `POST /api/ai/classify`.
- **Then**: AI trả về phân loại `Thanh toán & Hóa đơn` và mức ưu tiên gợi ý `Urgent` hoặc `High`, kèm lý do tóm tắt liên quan đến giao dịch tài chính.

### AC-006: AI gợi ý câu trả lời nháp có đối chiếu FAQ (RAG) (FR-009)
- **Given**: Cơ sở dữ liệu FAQ có bài viết về "Xử lý sự cố không nhận được email kích hoạt/OTP".
- **When**: Nhân viên bấm nút "AI Gợi ý trả lời" tại Ticket #105.
- **Then**: Hệ thống truy xuất bài viết FAQ liên quan, gửi kèm ngữ cảnh vào mô hình Gemini, sinh ra bản nháp phản hồi lịch sự, đúng quy trình kỹ thuật.

### AC-007: Cơ chế phê duyệt của nhân viên (Human Gate / Approval) (FR-010)
- **Given**: Trợ lý AI hiển thị bản nháp câu trả lời trong ô soạn thảo.
- **When**: Nhân viên đọc, chỉnh sửa bổ sung thông tin số điện thoại hotline, sau đó bấm nút "Duyệt & Gửi phản hồi".
- **Then**: Hệ thống lưu nội dung đã được con người duyệt vào bảng `ticket_comments` và ghi nhận trong `ai_logs` với cờ `is_approved = 1`. Tuyệt đối không có hành động tự động gửi tin nhắn mà thiếu sự xác nhận này.

### AC-008: AI tóm tắt chuỗi trao đổi dài (FR-011)
- **Given**: Ticket có từ 4 trao đổi trở lên giữa khách hàng và các bộ phận kỹ thuật.
- **When**: Nhân viên mới tiếp nhận mở chi tiết ticket và yêu cầu "AI Tóm tắt".
- **Then**: AI trả về bản tóm tắt từ 3-4 gạch đầu dòng nêu rõ: (1) Vấn đề ban đầu, (2) Các bước đã thử nghiệm, (3) Nút thắt kỹ thuật hiện tại cần giải quyết.

### AC-009: Ẩn thông tin cá nhân PII trước khi gửi AI (NFR-003)
- **Given**: Nội dung ticket chứa chuỗi thông tin nhạy cảm: mật khẩu cũ `Pass@123456`, số thẻ ngân hàng `4532-xxxx-xxxx-1234`.
- **When**: Pipeline Context Builder chuẩn bị payload gửi sang Gemini API.
- **Then**: Các chuỗi nhạy cảm bị che thành `[MASKED_PASSWORD]` và `[MASKED_CARD]`. Không gửi thông tin nhạy cảm ở dạng thô sang máy chủ LLM bên thứ ba.

