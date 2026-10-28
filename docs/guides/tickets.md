# Hướng dẫn ticket

## Chuẩn bị và tài khoản

```powershell
.\scripts\manage-local.ps1 -Action migrate
.\scripts\manage-local.ps1 -Action create-agent
.\scripts\manage-local.ps1 -Action create-supervisor
.\scripts\start-local.ps1
```

Lệnh quản trị hỏi mật khẩu MySQL root và mật khẩu website bằng trường ẩn. Database hiện có chỉ dùng migration.

## Luồng demo

1. Customer tạo ticket, chọn ưu tiên; trạng thái ban đầu `Mới`.
2. Supervisor mở ticket và giao Agent hoạt động; trạng thái vẫn `Mới`.
3. Agent nhận ca; ticket chuyển `Đang xử lý`.
4. Agent sửa chi tiết/nhóm/ưu tiên, gửi phản hồi và có thể yêu cầu AI hỗ trợ.
5. Agent chọn hoặc bỏ gợi ý AI. Chọn nháp không tự gửi; Agent kiểm tra/chỉnh sửa và gửi riêng.
6. Agent chuyển `Chờ khách hàng`; Customer phản hồi sẽ đưa về `Đang xử lý`.
7. Agent đóng sau khi có phản hồi; Customer đánh giá một lần từ 1–5 sao.

## Quyền và bộ lọc

- Customer chỉ xem ticket của mình.
- Agent xem ticket Mới chưa nhận, ticket được giao và ticket của mình.
- Supervisor xem toàn bộ, giao/đổi Agent, quản lý liên hệ khách hàng và xem báo cáo.
- Admin quản lý tài khoản/tri thức/cấu hình/audit, không mặc nhiên đọc nội dung ticket.
- Lọc theo khách hàng, trạng thái, ưu tiên và khoảng ngày; phân trang 30 ticket.

Vòng đời: `Mới → Đang xử lý ↔ Chờ khách hàng → Đã đóng`. Upload/file metadata riêng chưa triển khai; mô tả ticket vẫn lưu văn bản.
