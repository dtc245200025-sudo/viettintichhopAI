# Báo cáo đánh giá mã nguồn (Code Review Report) - Đề tài 10

> **Cập nhật 2026-10-28:** Backend chính đã chuyển lại sang FastAPI tại `backend/`. Các phát hiện phía dưới trỏ tới `app.py`, `routes/`, `services/` hoặc SQLite thuộc bản Flask đã lưu ở `archive_flask_demo_20261028/` và không còn áp dụng cho runtime chính. FastAPI có session/RBAC theo route, cấu hình database không chứa mật khẩu mặc định và chỉ dùng MySQL. Bộ test hiện hành đạt 110, skip 1 MySQL integration; các rủi ro còn mở là chưa áp migration trên DB người dùng, chưa chạy browser/provider/SMS thật và chưa hoàn tất dependency audit.

## 1. Phương pháp & Mục tiêu
Sử dụng bộ tiêu chuẩn `code-review` skill để đánh giá mã nguồn về: tính đúng đắn, tuân thủ kiến trúc phân tầng, phân tách trách nhiệm (Separation of Concerns), xử lý ngoại lệ và chất lượng mã nguồn.

## 2. Kết quả đánh giá theo phân loại rủi ro

| Mức độ | Vị trí | Vấn đề phát hiện | Giải pháp đã khắc phục | Trạng thái |
|---|---|---|---|---|
| **CRITICAL** | `services/ai_support_service.py` | Regex lọc PII ban đầu không bắt được chuỗi "mật khẩu của tôi là Pass@...", có nguy cơ rò rỉ secret lên máy chủ LLM công cộng. | Bổ sung regex nhận diện pattern `(?:của tôi là\|là)?\s*` và nhận diện riêng `Pass@\w+`. Đã viết test case kiểm chứng lại. | **ĐÃ XỬ LÝ** |
| **HIGH** | `routes/ai_routes.py` | Nguy cơ nhân viên bấm gửi duyệt nhưng nội dung bị rỗng hoặc ticket không tồn tại gây crash máy chủ. | Thêm validate dữ liệu `not ticket_id or not approved_content` và trả về HTTP 400 Bad Request kèm thông báo lỗi rõ ràng. | **ĐÃ XỬ LÝ** |
| **MEDIUM** | `services/ticket_service.py` | Chưa sắp xếp ưu tiên hiển thị theo mức độ khẩn cấp (Urgent lên đầu). | Bổ sung mệnh đề `ORDER BY CASE t.priority WHEN 'Urgent' THEN 1 WHEN 'High' THEN 2 ...` | **ĐÃ XỬ LÝ** |
| **LOW** | `templates/base.html` | Thẻ badge trạng thái hiển thị chưa đồng bộ màu sắc chuẩn thiết kế. | Chuẩn hóa bảng màu CSS cho các trạng thái New, In Progress, Waiting Customer, Closed. | **ĐÃ XỬ LÝ** |

## 3. Đánh giá tuân thủ kiến trúc (Architecture Compliance)
- Mã nguồn đã hình thành phân tầng Controller (`routes/`) -> Service (`services/`) -> Data Access (`database/`), nhưng chưa thể kết luận tuân thủ hoàn toàn vì route còn thiếu policy quyền và lớp database còn hỗ trợ SQLite.
- Tầng AI không bao giờ được phép thực thi SQL tự do mà luôn giao tiếp qua intermediate representation và context injection.

## 4. Phát hiện mở ngày 2026-10-28

| Mức độ | Vị trí | Phát hiện | Trạng thái |
|---|---|---|---|
| **CRITICAL** | `app.py` | Có fallback `SECRET_KEY` cố định; session có thể bị giả mạo nếu triển khai thiếu biến môi trường. | **CHƯA XỬ LÝ** |
| **HIGH** | `routes/ai_routes.py` | `/classify`, `/suggest`, `/summarize`, `/apply-classification` chưa kiểm tra đăng nhập; apply-classification thay đổi dữ liệu. | **CHƯA XỬ LÝ** |
| **HIGH** | `routes/ticket_routes.py`, `routes/customer_routes.py` | Chưa áp quyền vai trò đầy đủ cho phân công, trạng thái và quản lý khách hàng. | **CHƯA XỬ LÝ** |
| **HIGH** | `database/db.py` | Mặc định/fallback SQLite và có mật khẩu MySQL mặc định, trái quyết định MySQL-only. | **CHƯA XỬ LÝ** |
| **MEDIUM** | Các route POST | Chưa thấy cơ chế CSRF cho form dùng session cookie. | **CHƯA XỬ LÝ** |
| **MEDIUM** | `database/schema_mysql.sql` | Schema runtime chưa có attachment, lịch sử trạng thái và lịch sử phân công riêng. | **CHỜ QUYẾT ĐỊNH/MIGRATION** |

13 test cục bộ đạt không đóng các phát hiện trên và không thay thế kiểm thử MySQL, trình duyệt, RBAC hay provider AI thật.

