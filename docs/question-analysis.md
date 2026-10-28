# Tài liệu Phân tích Câu hỏi & Yêu cầu Người dùng (Question Analysis) - Đề tài 10

## 1. Mục tiêu
Đặc tả chi tiết bộ phân tích câu hỏi người dùng (Question Analyzer) theo quy định của kỹ năng `question-analysis`. Module này bóc tách câu hỏi ngôn ngữ tự nhiên thành biểu diễn trung gian có cấu trúc dạng JSON (Structured Intent).

## 2. Đầu vào & Đầu ra

### Đầu vào (Natural Language Question):
> *"Khách hàng không nhận được email đổi mật khẩu sau khi bấm quên mật khẩu nhiều lần, đang cần đăng nhập gấp"*

### Đầu ra có cấu trúc (Structured Intent):
```json
{
  "category": "Tài khoản & Đăng nhập",
  "keywords": ["đổi mật khẩu", "reset", "email", "quên mật khẩu"],
  "suggested_priority": "High",
  "sanitized_summary": "Khách hàng không nhận được email đổi mật khẩu sau khi bấm quên mật khẩu, cần xử lý gấp."
}
```

## 3. Các quy tắc trích xuất
1. **Lọc thông tin cá nhân (PII Sanitization)**: Khử định danh mật khẩu, số thẻ ngân hàng, số điện thoại.
2. **Gán nhãn danh mục**: Dựa trên từ khóa cốt lõi (Tài khoản, Thanh toán, Lỗi kỹ thuật, Tư vấn).
3. **Đánh giá mức ưu tiên**: Nếu có từ "gấp", "tiền", "lỗi 500", "sập" -> Tự động đề xuất mức `High` hoặc `Urgent`.

