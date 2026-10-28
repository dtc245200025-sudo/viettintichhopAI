# Đối chiếu yêu cầu và bằng chứng

Ngày 29/10/2026. Nguồn: [yeu_cau.txt được lưu nguyên nội dung](../../requirements/acceptance-user-20261029.txt). Người dùng chọn **thêm chức năng tự động** trong phiên làm việc. Các từ “đạt” dưới đây giới hạn trong môi trường demo MySQL thật, dữ liệu giả, AI mô phỏng/transport giả; không có ý nghĩa nghiệm thu Gemini thật.

| ID | Hành vi đã đối chiếu/hoàn thiện | Bằng chứng chính |
|---|---|---|
| UC001 | 4 vai trò, tài khoản active, session, 5 lần sai khóa 15 phút; đăng nhập đúng không cộng bộ đếm sai | `test_final_acceptance` lockout, unit auth/security, UI login 4 vai trò VI/EN |
| UC002 | Chat có nguồn xuất bản; fallback thiếu nguồn, lưu lịch sử; chỉ chủ sở hữu; UI widget/chat | MySQL RAG flow, no_sources/display masking, 50 câu đồng thời, UI Customer |
| UC003 | Customer tạo cho mình, Agent tạo hộ khách active, nhóm/ưu tiên, liên kết chat đúng chủ sở hữu | MySQL agent creation + idempotency, UI Agent tạo Ticket |
| UC004 | Tự phân loại/ưu tiên và giao Agent online ít tải; không đè Ticket đã được nhận/sửa; AI lỗi giữ hàng chờ thử lại | Auto assignment/failure/retry test; Supervisor vẫn chỉnh nhóm/ưu tiên |
| UC005 | 4 nhãn cảm xúc, cảnh báo bức xúc cao, Supervisor xác nhận, hiển thị trên Ticket/lịch sử chuyển giao | Classifier schema/PII, persisted MessageAutomation/TicketAutomation/alerts, UI |
| UC006 | Heartbeat/phiên xác thực, gợi ý Agent, hàng chờ khi không online; tiếp nhận, phản hồi; toàn bộ lịch sử qua phân trang | End-to-end handover; no-agent test; 205 tin qua pagination; UI mở lịch sử |
| UC007 | Nội dung, ưu tiên, phân công, nhận ca, phản hồi, chờ khách, đóng; giữ lịch sử; đính chính append-only | MySQL lifecycle cũ và acceptance mới, unit state machine, UI Agent |
| UC008 | Nháp có ngữ cảnh Ticket/chat và RAG xuất bản; chọn/bỏ/chỉnh; duyệt không tự tạo phản hồi | MySQL review test so sánh số TicketReply trước/sau; UI Use draft rồi Send |
| UC009 | Tóm tắt tự động khi handover/kết thúc, lưu lại; lịch sử dài chia nhóm thay vì chỉ lấy 200 tin đầu | MySQL summary persisted; helper phân nhóm, UI nguồn tóm tắt |
| UC010 | CSAT 1–5 cho chat kết thúc/Ticket đóng; chống trùng, đúng chủ; form chat tự ẩn 60 giây | Chat/Ticket rating MySQL tests, UI Customer gửi đánh giá; đồng hồ ảo tiến 61 giây xác nhận form ẩn |
| UC011 | FAQ/văn bản, nháp/phiên bản, index MySQL, preview, publish/unpublish; giữ nguồn lịch sử | Knowledge domain tests + MySQL CMS/RAG flow, UI Admin |
| UC012 | Tạo/sửa/khóa/mở/phân quyền; không tự nâng quyền; bảo vệ Admin cuối | Admin API tests, MySQL managed account, UI Admin |
| UC013 | Dashboard theo trạng thái/nhóm/ưu tiên, thời gian xử lý, SLA, chat và CSAT, lọc thời gian | Reports unit + MySQL seeded dataset + UI Supervisor |
| UC014 | Audit thao tác quan trọng và đọc tài nguyên có xác thực; Admin tra cứu; không có sửa/xóa log qua API | Persisted ACCESS_READ, demo seed audit, role rejection, UI Admin |
| UC015 | Ngưỡng RAG, timeout AI, thời hạn phiên 1–24 giờ; allowlist/range, audit; không lưu secret | Settings unit + session Max-Age test + UI Admin |
| UC016 | Tìm kiếm tên/email/phone, sửa liên hệ, lịch sử Ticket và danh sách chat; chỉ Admin/Supervisor | Customer API tests, MySQL contact/history, UI quản lý khách hàng |

## Phi chức năng và giới hạn kiểm chứng

- **PII:** che CVV/CVC/PIN/OTP/CMND/CCCD, mật khẩu, số tài khoản/thẻ trước AI và trong free-text trả cho UI; email/phone liên hệ chỉ trả theo quyền để vẫn sửa được. Có test VI/EN, cách ghi tự nhiên, thẻ che một phần và câu hỏi hỗ trợ không chứa secret. Regex vẫn có giới hạn, không phải DLP/chứng nhận.
- **Quyền MySQL:** ca mới chạy bằng user chỉ CRUD; lệnh CREATE TABLE bị từ chối. Setup/migration/backup dùng admin của server cách ly.
- **Hiệu năng:** 50 câu, 5 phiên đồng thời, 1.000 chunk, không bỏ qua lỗi. Kết quả trong `performance-simulation.json`; ASGI TestClient + MySQL TCP cục bộ, không bao gồm mạng/provider Gemini thật. Đã cung cấp benchmark HTTP riêng.
- **Backup/restore:** mysqldump vào database khác, so sánh số hàng và SHA-256 toàn bộ nội dung 32 bảng; kiểm tra migration khôi phục.
- **UI:** 4 vai trò × VI/EN × desktop/mobile, thêm điều hướng menu điện thoại; không ghi nhận lỗi JavaScript từ trang. Không coi screenshot hoặc test đếm phần tử là nghiệm thu mọi tình huống truy cập.
- **Mở rộng không bắt buộc:** upload PDF/DOCX/Excel, SMS/email/OTP thật, Core Banking, NPS, microservices/Kubernetes và backup tự động.
- **Mâu thuẫn đã xử lý:** giữ 4 trạng thái Ticket; dùng 4 nhãn cảm xúc theo lựa chọn bổ sung của người dùng. Cam kết AI dưới 2 giây/uptime 99,9% và chứng nhận không được suy ra từ kết quả demo. Các phê duyệt cũ không tự trở thành phê duyệt release mới.

## Chưa thể chốt ngoài môi trường demo

1. Gemini thật: chưa có key được cung cấp cho phiên chạy; chưa đo quyền/quota, chất lượng nguồn hoặc p95 qua Internet.
2. Database ứng dụng 3306: chưa có credential phiên này; chưa áp dụng 010–011 hoặc nạp demo vào `qlkhviettin`. Đã cung cấp script có lời nhắc mật khẩu ẩn; dữ liệu đã nạp thật vào database test riêng.
3. Hàng chờ demo chưa có chính sách dung lượng/định tuyến chuyên môn được chốt; hiện ưu tiên theo số Ticket mở, không tuyên bố có hệ thống phân ca ngân hàng. Có retry Ticket và yêu cầu tóm tắt thủ công; không phải hàng đợi phân tán bảo đảm giao việc sau mọi sự cố tiến trình.
