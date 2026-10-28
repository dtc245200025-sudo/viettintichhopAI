# Báo cáo đánh giá bảo mật (Security Review Report) - Đề tài 10

> **Cập nhật 2026-10-28:** Runtime chính là FastAPI/MySQL tại `backend/`; các nhận xét về `app.py`, `database/db.py` và Flask phía dưới là lịch sử của bản demo đã lưu. FastAPI dùng session cookie, role gate, password hashing, query tham số hóa, cấu hình secret qua biến môi trường và không fallback SQLite. Kết quả 110 pass/1 skip không thay thế kiểm thử MySQL, trình duyệt, provider AI, Twilio, prompt injection và dependency audit.

## 1. Mục tiêu kiểm tra
Thực hiện đánh giá bảo mật theo checklist của `security-review` skill dựa trên chuẩn OWASP Top 10 và các nguy cơ đặc thù của ứng dụng AI/LLM.

## 2. Kết quả kiểm tra theo Checklist

### 1. SQL Injection (Phòng chống tiêm mã SQL)
- **Đánh giá**: **ĐẠT TRONG PHẠM VI MÃ ĐÃ ĐỌC; CHƯA KIỂM THỬ MYSQL THẬT**.
- **Bằng chứng**: Toàn bộ các câu lệnh truy vấn trong `services/ticket_service.py`, `services/auth_service.py`, `services/customer_service.py`, và `services/ai_support_service.py` đều sử dụng cú pháp tham số hóa với dấu `?` (`cursor.execute(sql, params)`). Không có câu lệnh nào nối chuỗi thô.

### 2. Cross-Site Scripting (XSS)
- **Đánh giá**: **CẦN KIỂM TRA THÊM**.
- **Bằng chứng**: Template Jinja2 mặc định bật tính năng auto-escaping cho toàn bộ biến văn bản. Chỉ các chuỗi xuống dòng `replace('\n', '<br>')` trong bình luận được đánh dấu `|safe` sau khi đã được kiểm soát.

### 3. Authentication & Password Storage (Xác thực & Mật khẩu)
- **Đánh giá**: **CHƯA ĐẠT**. Password hashing dùng Werkzeug, nhưng một số AI endpoint chưa yêu cầu đăng nhập và RBAC chưa đầy đủ.
- **Bằng chứng**: Mật khẩu được băm bằng thuật toán bảo mật của Werkzeug (`generate_password_hash` / `check_password_hash` dựa trên PBKDF2/SHA-256). Mật khẩu không bao giờ được lưu trữ dưới dạng bản rõ (plaintext).

### 4. Secrets Management (Quản lý khóa bí mật)
- **Đánh giá**: **CHƯA ĐẠT**.
- **Bằng chứng**: `app.py` có `SECRET_KEY` fallback cố định; `database/db.py` có mật khẩu MySQL mặc định. `GEMINI_API_KEY` đọc từ môi trường nhưng provider thật chưa kiểm chứng.

### 5. AI Guardrails & PII Sanitization (Bảo vệ dữ liệu cá nhân & Hallucination)
- **Đánh giá**: **MỘT PHẦN; CHƯA ĐỦ ĐỂ KẾT LUẬN AN TOÀN**.
- **Bằng chứng**:
  - Dữ liệu trước khi gửi sang Gemini LLM đều chạy qua bộ lọc `sanitize_pii` để ẩn mật khẩu, số thẻ ngân hàng, số điện thoại.
  - Áp dụng nguyên tắc **Human-in-the-Loop**: AI chỉ đóng vai trò trợ lý sinh bản nháp (`draft_response`), bắt buộc nhân viên hỗ trợ phải đọc, biên tập và bấm nút phê duyệt mới được gửi chính thức đến khách hàng.
  - Prompt hệ thống được thiết lập nghiêm ngặt: Tuyệt đối cấm AI tự ý cam kết bồi thường hoàn tiền hoặc bịa đặt chính sách trái với cơ sở tri thức FAQ.

### 6. CSRF, Authorization và Dependency Audit
- **Đánh giá**: **CHƯA ĐẠT/CHƯA KIỂM TRA**.
- Chưa thấy CSRF token cho form POST; quyền vai trò và quyền truy cập ticket chưa được kiểm tra đầy đủ. Phiên này chưa chạy công cụ audit dependency.

Không coi báo cáo này là chứng nhận an toàn. Ưu tiên: bắt buộc authentication/RBAC, thêm CSRF, bỏ secret/mật khẩu mặc định, kiểm thử MySQL quyền tối thiểu và kiểm thử PII/prompt injection với provider thật.

