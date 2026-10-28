# Hướng dẫn Gemini/OpenAI và kho tri thức

## Khởi động

```powershell
.\scripts\start-local.ps1 -EnableAI -AIProvider gemini
```

Launcher hỏi mật khẩu `vietincare_app`, sau đó hỏi API key bằng trường ẩn. Khóa chỉ tồn tại trong môi trường tiến trình và không được gửi xuống trình duyệt. Có thể dùng `-AIProvider openai`.

## Xuất bản nguồn

1. Admin đăng nhập → **Kho tri thức**.
2. Tạo/lưu bản nháp.
3. **Tạo dữ liệu tìm kiếm** để backend gửi đoạn đã che PII tới embedding provider và lưu vector trong MySQL.
4. **Thử trả lời**, kiểm tra câu trả lời và nguồn.
5. **Xuất bản cho AI**. Chỉ nguồn đã xuất bản, đúng provider/model/số chiều tham gia truy xuất.

Khi đổi OpenAI ↔ Gemini, tạo lại embedding; vector khác model không dùng lẫn. Bản đã xuất bản cần tạo phiên bản mới trước khi sửa.

## Phạm vi

- Gemini mặc định: `gemini-3.8-flash`, thinking `low`; embedding `gemini-embedding-001`, 768 chiều.
- OpenAI mặc định: `gpt-4.1-mini`; embedding `text-embedding-3-small`, 512 chiều; Responses đặt `store:false`.
- Vector lưu MySQL; backend tính cosine. Ngưỡng 0,35 là cấu hình ban đầu, chưa phải xác suất hay bằng chứng chất lượng.
- Chat Customer dùng RAG nguồn xuất bản. Ticket-assist hiện dùng ticket, reply, chat liên kết và danh sách category; không tuyên bố truy xuất nội dung kho tri thức.
- Email, điện thoại, số tài khoản, thẻ và mật khẩu được che trước khi gửi provider.

Quota, độ trễ và chất lượng provider thật phải kiểm thử riêng với khóa của người dùng.
