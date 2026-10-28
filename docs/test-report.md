# Báo cáo kiểm thử hiện hành

Ngày 29/10/2026. Python 3.13/FastAPI, MySQL Community Server 8.0.46, giao diện VI/EN.

- **165 test đạt, 0 lỗi, 0 skip**, gồm migration/MySQL thật và kiểm thử tài khoản chỉ CRUD.
- **16 tổ hợp trình duyệt**: bốn vai trò × VI/EN × desktop/mobile; không có lỗi JavaScript từ trang. Có tạo Ticket bằng Agent, duyệt rồi chủ động gửi nháp, xem lịch sử chuyển giao và gửi CSAT chat. Menu điện thoại được mở/đóng; timer CSAT kiểm thử bằng đồng hồ ảo tiến 61 giây.
- Dataset: 9 tài khoản, 5 Customer (một tài khoản khóa), 48 Ticket, 8 chat, 4 tài liệu, 1.000 chunk, 16 đánh giá, gợi ý AI đủ Pending/Selected/Dismissed và cảnh báo mẫu. Dữ liệu hoàn toàn giả lập.
- Sao lưu/khôi phục: đối chiếu số hàng và SHA-256 nội dung **32 bảng**, kiểm tra migration khôi phục.
- Python được định dạng và kiểm tra tương đương AST; `compileall` và kiểm tra cú pháp JS/PowerShell đạt.

Chi tiết số đo, cấu hình máy và kết quả lần chạy cuối tại [báo cáo tổng hợp](reports/final-acceptance-20261029/summary.md), [JSON kết quả](reports/final-acceptance-20261029/result.json), [JUnit](reports/final-acceptance-20261029/pytest.xml) và [trình duyệt](reports/final-acceptance-20261029/browser/result.json).

AI dùng trong nghiệm thu là **mô phỏng/transport giả**, không phải bằng chứng Gemini thật. Còn một cảnh báo deprecation của Starlette/AnyIO, không làm test lỗi. Không suy ra đạt SLA dưới 2 giây, uptime 99,9%, chứng nhận hoặc môi trường sản xuất từ kết quả này. Database chính 3306 chưa được migrate/seed trong phiên thiếu credential; script chạy lại và nạp demo có trong hướng dẫn.
