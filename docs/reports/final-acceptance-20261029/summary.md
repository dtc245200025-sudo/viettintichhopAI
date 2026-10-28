# Báo cáo chốt nghiệm thu bản demo VietinCare AI

Ngày **29/10/2026 (Asia/Saigon)**. Nguồn yêu cầu: `yeu_cau.txt` và lựa chọn bổ sung tự động của người dùng.

## Kết quả thực thi cuối

| Hạng mục | Kết quả |
|---|---|
| Toàn bộ pytest | **165 đạt, 0 lỗi, 0 bỏ qua** |
| MySQL | **8.0.46**, server cách ly 127.0.0.1:33316 |
| Migration | 11 version / **43 bước**, khởi tạo mới và chạy lại/check |
| Runtime MySQL chỉ CRUD | Đạt; CREATE TABLE bị từ chối |
| Trình duyệt | **8 phiên vai trò/ngôn ngữ, 16 tổ hợp desktop/mobile**, 0 lỗi JavaScript từ trang |
| Chuyển giao dài | Truy xuất đủ 205 tin qua phân trang; Agent/Supervisor mở lịch sử được trên UI |
| CSAT | Chat/Ticket, chống trùng/chéo chủ; UI gửi được; form chat ẩn sau đồng hồ ảo 61 giây |
| Sao lưu/khôi phục | **32 bảng, 1367 hàng**; số hàng và SHA-256 nội dung từng bảng khớp |
| Kiểm tra tĩnh | Python compileall; 9 JS/CJS; 7 PowerShell; Black cho các file Python thay đổi; pip check không phát hiện xung đột |

Chạy chốt bằng **chính `scripts/final-test.ps1`**: tự tạo MySQL/datadir riêng, nạp dữ liệu giả, chạy pytest, mysqldump/restore, kiểm tra hash và tự dừng đúng server sau khi kiểm tra datadir. Các server thử 3001/33316 đã dừng; không để chế độ simulation chạy thay backend thật. Các file dữ liệu/backup test giữ tại `.mysql-test/`, không đụng database ứng dụng.

## Dữ liệu đã nạp thật trong MySQL thử

- 9 tài khoản / 5 Customer; có bốn vai trò và một Customer khóa.
- 48 Ticket đủ trạng thái/ưu tiên, lịch sử/phản hồi/phân công và các nhóm yêu cầu.
- 8 chat, 4 tài liệu đã xuất bản và **1000 KnowledgeChunk**.
- 16 CSAT ban đầu, 3 phân tích AI Pending/Selected/Dismissed, 3 cảnh báo, cảm xúc và hàng chờ mẫu.
- Vector có model riêng `vietincare-demo-embedding-v1`, không giả mạo embedding Gemini. Credential fixture công khai chỉ dành cho dữ liệu giả, không phải tài khoản thực.

Tên database seed: `vietincare_demo_20261028_221059_df14e9`. Datadir/backup và cấu hình máy có trong JSON kết quả. Database này đã được lưu trên ổ đĩa nhưng server test hiện đã dừng; không đồng nghĩa đã nạp vào `qlkhviettin` cổng 3306.

## Thay đổi chính

- Tự phân loại/ưu tiên Ticket mới; chọn Agent có heartbeat/phiên hợp lệ và ít tải; không đè ca đã nhận/sửa. AI lỗi giữ Ticket và cho Supervisor thử lại.
- Cảm xúc bốn mức, cảnh báo bức xúc cao, xác nhận Supervisor; xem cảm xúc/lịch sử chat khi chuyển giao.
- Tóm tắt khi chuyển giao/kết thúc; tóm tắt theo nhóm cho hội thoại dài. Chat CSAT và liên kết tạo Ticket theo lựa chọn khách.
- RAG nguồn xuất bản cho nháp; kiểm tra lại nguồn; **duyệt nháp không tự gửi**.
- Agent tạo Ticket hộ Customer active; nhóm/phiên đúng sở hữu; Supervisor sửa ưu tiên; lịch sử liên hệ/chat của khách.
- Đính chính chat/phản hồi bằng bản ghi mới, không ghi đè bản gốc.
- Che CVV/OTP/CMND/CCCD/thẻ/mật khẩu trong free-text UI và trước AI; lọc cả tên nhóm trước gọi AI; tránh che nhầm một số câu hỏi hỗ trợ thông thường.
- Giới hạn đăng nhập chỉ đếm lần sai, audit truy cập/chỉnh sửa, session duration allowlist và lỗi MySQL an toàn.

## Số đo hiệu năng và giới hạn

**50 câu / 5 phiên đồng thời / 1.000 chunk**, provider **SIMULATION**, ASGI TestClient + MySQL TCP cục bộ: **p95 = 0.5564 giây, 0 lỗi**. Đây là số đo xử lý demo, **không gồm Internet/Gemini thật** và không chứng minh chất lượng câu trả lời ngân hàng. Lần trước tối ưu ghi nhận p95 5,8259 giây và được giữ tại before-optimization.json/performance-before-optimization.json. Sau chuẩn hóa vector, cache vector số học theo toàn bộ giá trị embedding và math.sumprod, lần chạy cuối bắt đầu với cache rỗng và đạt ngưỡng demo ≤5 giây. Có kiểm thử hồi quy xếp hạng/đổi embedding/vector lỗi; quyền và trạng thái xuất bản vẫn truy vấn lại. Báo cáo ghi máy/CPU/Python/OS; benchmark HTTP thật được cung cấp riêng.

Chưa chốt các phần cần điều kiện bên ngoài:

1. Gemini thật: chưa có khóa cung cấp cho phiên này; chưa xác nhận model/quota/chất lượng/p95 qua Internet.
2. Database ứng dụng 3306: chưa có credential phiên này; **chưa áp dụng migration 010–011 hoặc seed ở đó**. Có script nhập mật khẩu ẩn, không cần gửi mật khẩu trong chat.
3. Không tuyên bố AI dưới 2 giây, uptime 99,9%, chứng nhận/tuân thủ hoặc release sản xuất. Upload/OTP/SMS/email/NPS/Core Banking vẫn là mở rộng đã được tài liệu gốc phân loại.
4. Còn cảnh báo deprecation Starlette/AnyIO. Regex PII không thay thế DLP; hàng đợi nền demo không phải hạ tầng giao việc bền vững phân tán.

## Bằng chứng và chạy lại

- [Kết quả máy đọc](result.json), [JUnit](pytest.xml), [log test](pytest.log), [số đo simulation](performance-simulation.json).
- [Kết quả trình duyệt](browser/result.json), ảnh theo vai trò/ngôn ngữ/kích thước tại `browser/`.
- [Ma trận 16 use case](requirements-matrix.md), [hướng dẫn chạy/nạp demo/Gemini](../../guides/final-acceptance.md).
- Chạy lại: `scripts/final-test.ps1`. Nâng cấp database chính: `scripts/manage-local.ps1 -Action migrate`, rồi `scripts/seed-demo.ps1`; sau đó cấu hình provider thật và chạy `backend.benchmark`.

Kết luận: **đạt vòng nghiệm thu tự động của bản demo**, không biến kết quả simulation thành nghiệm thu provider thật hoặc database chính chưa được truy cập.
