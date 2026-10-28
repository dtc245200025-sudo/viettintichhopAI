# Đánh giá bảo mật hiện hành

## Đã có

- Session token/OTP lưu hash; mật khẩu website dùng scrypt có salt.
- Cookie HttpOnly, SameSite Strict; production bắt buộc HTTPS/Secure cookie.
- RBAC và quyền sở hữu kiểm tra ở backend.
- Query nghiệp vụ dùng tham số hóa; tên database/model được allowlist/validate.
- API ghi yêu cầu kiểm tra Origin, header ứng dụng, JSON và giới hạn kích thước.
- Header CSP, nosniff, frame deny, referrer policy và no-store cho API.
- Gemini/OpenAI dùng host cố định, chặn redirect, lỗi an toàn không trả body upstream.
- PII masking hiện che `[MASKED_PASSWORD]`, `[MASKED_CREDIT_CARD]`, `[MASKED_EMAIL]`, `[MASKED_PHONE]`, `[MASKED_ACCOUNT_NO]` trước provider.
- Bổ sung CVV/CVC/PIN/OTP/CMND/CCCD bằng `[MASKED_SECRET_CODE]`, cách ghi tiếng Việt/Anh tự nhiên và nhãn category cũng được lọc trước provider. API/UI che secret trong free-text, không vô hiệu hóa việc chỉnh sửa email/phone của người có quyền.
- Bộ đếm đăng nhập email chỉ tăng khi sai mật khẩu; khóa 15 phút sau 5 lần sai, đăng nhập đúng xóa bộ đếm. Có kiểm thử MySQL cho đúng/sai/khôi phục sau thời hạn.
- Tài khoản runtime nghiệm thu chỉ có SELECT/INSERT/UPDATE/DELETE; CREATE TABLE bị từ chối. Mọi schema thay đổi qua migration mới.
- 165 test đạt, gồm IDOR, CSRF, quyền vai trò, quá cỡ body, trạng thái, replay và ràng buộc duyệt; trình duyệt kiểm tra dữ liệu demo. Đây là phạm vi kiểm thử, không phải tuyên bố không còn lỗ hổng.
- Ticket AI luôn cần Agent duyệt/chủ động gửi.

## Còn mở

- CSP còn `'unsafe-inline'` vì HTML hiện dùng handler/style inline.
- Chưa chạy dependency audit và prompt-injection/provider thật trong đợt hiện hành.
- Regex PII giảm rủi ro nhưng không thay thế DLP; cần bộ dữ liệu Việt Nam có nhãn để đo false positive/negative.
- Free-text gốc trong MySQL phục vụ lịch sử có thể chứa thông tin người gửi nhập nhầm; không dùng dữ liệu thật trong bản demo. Việc mã hóa ổ đĩa/quy trình xử lý dữ liệu sản xuất chưa được nghiệm thu.
- Script setup MySQL dùng root cục bộ để tạo/đặt lại hai danh tính local; chỉ runtime user nhận CRUD trên `qlkhviettin`.

Không coi báo cáo này là chứng nhận bảo mật ngân hàng.
