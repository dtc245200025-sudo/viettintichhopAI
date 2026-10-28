# Yêu cầu hệ thống VietinCare AI

Nguồn chuẩn: [`requirements/source-topic-10.md`](requirements/source-topic-10.md). Nội dung dưới đây phản ánh mã FastAPI hiện hành; phần chưa triển khai được ghi rõ và không được hiểu là đã nghiệm thu.

Bổ sung 29/10/2026: [yêu cầu người dùng](requirements/acceptance-user-20261029.txt). Người dùng chọn triển khai thêm chức năng tự động; xem [ma trận nghiệm thu](reports/final-acceptance-20261029/requirements-matrix.md).

## Yêu cầu chức năng

| ID | Yêu cầu hiện hành | Vai trò |
|---|---|---|
| FR-001 | Đăng ký Customer; đăng nhập/đăng xuất bằng session; phân quyền Customer, Agent, Supervisor, Admin. | Tất cả |
| FR-002 | Xem, tìm/cập nhật thông tin liên hệ, lịch sử ticket và danh sách hội thoại của khách hàng. | Admin, Supervisor |
| FR-003 | Customer tạo Ticket cho mình; Agent tạo hộ Customer đang hoạt động; có thể liên kết chat đúng chủ sở hữu. Agent được giao sửa nội dung/trạng thái; Supervisor điều chỉnh nhóm/ưu tiên. | Customer, Agent, Supervisor |
| FR-004 | Supervisor giao/đổi Agent; Agent nhận ticket mới được giao hoặc chưa có người nhận. | Supervisor, Agent |
| FR-005 | Lưu phản hồi, lịch sử trạng thái và lịch sử phân công. “File đính kèm ở mức mô tả” hiện chỉ là mô tả văn bản; chưa có upload/metadata file riêng. | Customer, Agent, Supervisor |
| FR-006 | Lọc ticket theo khách hàng, trạng thái, ưu tiên và khoảng ngày; quyền xem phụ thuộc vai trò/sở hữu. | Customer, Agent, Supervisor |
| FR-007 | Báo cáo ticket theo trạng thái/nhóm/ưu tiên, thời gian xử lý, quá SLA demo, phiên chat và CSAT. | Supervisor |
| FR-008 | Tự động phân loại, gán ưu tiên và chọn Agent online ít tải cho Ticket mới; vẫn có AI assist theo yêu cầu và phân công tay. AI lỗi giữ Ticket để thử lại/thủ công. | Agent, Supervisor, AI Engine |
| FR-009 | Nháp dựa trên ticket, phản hồi/chat và tri thức đã xuất bản đúng model embedding; kiểm tra lại phiên bản/xuất bản trước lưu phân tích. | Agent, AI Engine |
| FR-010 | Gợi ý AI bắt đầu ở Pending; Agent chọn hoặc bỏ. Chọn nháp không tự gửi; Agent phải kiểm tra/chỉnh sửa và gửi phản hồi riêng. | Agent |
| FR-011 | Tóm tắt khi yêu cầu/kết thúc handover hoặc kết thúc chat; có yêu cầu thủ công. Lịch sử dài được tóm tắt theo nhóm thay vì bỏ tin nhắn. | Agent, Supervisor, AI Engine |
| FR-012 | Cảm xúc chat/Ticket: Tích cực, Trung tính, Tiêu cực, Bức xúc cao; cảnh báo Supervisor và xác nhận tiếp nhận. | Agent, Supervisor |
| FR-013 | Đánh giá chat kết thúc hoặc Ticket đóng một lần 1–5 sao; form chat tự ẩn sau 60 giây. NPS là mở rộng. | Customer |
| FR-014 | Đính chính tin chat/phản hồi Ticket bằng bản ghi mới tham chiếu bản gốc; chỉ tác giả, đúng đối tượng, còn mở. | Customer, Agent |
| FR-015 | Agent heartbeat 45 giây; online khi heartbeat trong 2 phút và còn phiên hợp lệ. Toàn bộ lịch sử chuyển giao truy xuất được qua phân trang. | Agent, Supervisor |

## Quy tắc nghiệp vụ đã triển khai

- Ticket: `Mới → Đang xử lý ↔ Chờ khách hàng → Đã đóng`.
- Ticket mới chuyển sang Đang xử lý khi Agent nhận ca; đóng ticket yêu cầu đã có phản hồi Agent.
- Customer trả lời khi Chờ khách hàng sẽ đưa ticket về Đang xử lý.
- Ticket đóng chỉ đọc; Customer được đánh giá một lần từ 1–5 sao.
- AI không tự gửi phản hồi Ticket. Tự động chỉ áp dụng nhóm/ưu tiên/phân công khi Ticket vẫn Mới và chưa bị nhận/sửa; trạng thái xử lý theo nghiệp vụ/Agent.
- MySQL Community Server 8.0.46, InnoDB, utf8mb4 là hệ quản trị duy nhất.

## Yêu cầu phi chức năng

| ID | Yêu cầu |
|---|---|
| NFR-001 | Mật khẩu website lưu bằng scrypt có salt; session token và OTP chỉ lưu dạng hash. |
| NFR-002 | API kiểm tra RBAC/quyền sở hữu ở backend; truy vấn dữ liệu dùng tham số hóa. |
| NFR-003 | Email, điện thoại, số tài khoản, thẻ và mật khẩu phải được che trước khi gửi Gemini/OpenAI. |
| NFR-004 | Khi AI lỗi, CRUD/ticket/chat thủ công vẫn hoạt động và không lộ phản hồi upstream hoặc khóa API. |
| NFR-005 | Giao diện VI/EN dùng chung API và đồng bộ chức năng chung. |
| NFR-006 | Hiệu năng/độ chính xác AI phải đo; chưa có bằng chứng để cam kết ngưỡng sản xuất. |

## Phần chưa nghiệm thu

- Upload hoặc metadata file đính kèm riêng.
- MySQL integration cách ly đang là test có điều kiện.
- Chất lượng, quota và độ trễ Gemini/OpenAI thật.
- Browser có đăng nhập cho đủ bốn vai trò sau thay đổi gần nhất.
