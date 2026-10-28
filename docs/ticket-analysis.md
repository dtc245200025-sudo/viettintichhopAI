# Tài liệu phân tích cấu trúc Ticket (Ticket Analysis Specification) - Đề tài 10

## 1. Mục tiêu
Thiết kế bộ phân tích ngữ nghĩa trung gian (Intermediate Representation) chuyển đổi văn bản khiếu nại/yêu cầu của khách hàng thành JSON có cấu trúc để phục vụ RAG và phân loại.

## 2. Dữ liệu Đầu vào & Đầu ra
- **Đầu vào (Input)**:
  `Tiêu đề: Không đăng nhập được sau khi đổi mật khẩu, đã thử reset nhưng chưa nhận email`
  `Mô tả: Tôi vừa thực hiện đổi mật khẩu lúc 9h sáng nay... hòm thư hoang.pm@gmail.com vẫn không thấy email gửi về...`
- **Đầu ra có cấu trúc (Structured Intent Output)**:
```json
{
  "category": "Tài khoản & Đăng nhập",
  "suggested_priority": "High",
  "keywords": ["đổi mật khẩu", "reset", "email", "otp"],
  "sanitized_summary": "Khách hàng không thể đăng nhập sau khi đổi mật khẩu, chưa nhận được email reset."
}
```

## 3. Quy tắc trích xuất
- Không tự bịa đặt danh mục ngoài 4 danh mục chính quy định.
- Nếu chứa các từ khóa liên quan đến "tiền", "thanh toán bị trừ hai lần", "ngân hàng" -> tự động nâng mức ưu tiên lên `Urgent`.
- Mọi chuỗi nhạy cảm (mật khẩu tạm, số tài khoản) được khử định danh thành nhãn mask `[MASKED_INFO]`.

