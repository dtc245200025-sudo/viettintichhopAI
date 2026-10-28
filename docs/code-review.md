# Rà soát mã nguồn hiện hành

## Kiến trúc

- `backend/`: FastAPI routes/policy nghiệp vụ, MySQL access, AI provider và migration runner.
- `VI/`, `EN/` cùng các module JavaScript gốc: frontend song ngữ.
- `migrations/001–011`: 43 bước có checksum/journal/lock; không sửa migration đã áp dụng.
- `tests/`: unit, API double và MySQL integration có điều kiện.

## Điểm đạt

- Transaction/rollback cho mutation; khóa hàng và idempotency cho ticket/chat/knowledge.
- RBAC/quyền sở hữu đặt ở backend, không dựa vào việc ẩn nút frontend.
- Human Gate tách review AI khỏi request gửi phản hồi.
- Lỗi provider/database được ánh xạ thành mã an toàn.
- Secret nhập ẩn và giữ trong môi trường tiến trình.
- Tự động hóa tách khỏi mutation lưu Ticket/chat; dữ liệu được giữ khi AI lỗi, không tự gửi nháp Agent. Kiểm tra lại trạng thái/nội dung trước áp dụng để không đè thao tác nhận/sửa.
- RAG cho nháp chỉ lấy nguồn xuất bản đúng model/số chiều, kiểm tra lại phiên bản trước lưu phân tích.
- Đính chính là insert có tham chiếu, kiểm tra tác giả/cùng đối tượng, không UPDATE bản gốc. Lịch sử chuyển giao phân trang, tóm tắt chia nhóm khi dài.
- Chữ ký lớp/module thực tế được kiểm tra; mã Python thay đổi được Black định dạng, xác nhận AST không đổi sau định dạng.

## Điểm còn mở

- Nghiệm thu 29/10: 165 test đạt, không skip, có MySQL thật và quyền CRUD; trình duyệt đủ 4 vai trò VI/EN desktop/mobile. Provider thật và database ứng dụng còn chờ credential; xem báo cáo cuối.
- Chưa có upload/file metadata riêng cho attachment.
- `backend/tickets.py`, `backend/chats.py`, `account.js` khá lớn; có thể tách policy/query/view ở giai đoạn bảo trì sau.
- Tài liệu lịch sử đã được chuyển vào `docs/references/legacy-requirements-20261028/`; không dùng làm mô tả runtime hiện hành.
- Tác vụ nền FastAPI không phải hàng đợi phân tán bền vững; Supervisor có retry Ticket chưa xử lý, không bảo đảm giao việc sau mọi sự cố tiến trình. Khóa đồng thời MySQL được ánh xạ lỗi an toàn để thử lại.
- Dataset/server SimulationAI chỉ phục vụ test, marker/model khác Gemini; mật khẩu fixture là dữ liệu công khai giả lập, không phải credential ứng dụng.
