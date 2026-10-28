# Kế hoạch kiểm thử (Test Plan) - Đề tài 10

## Bổ sung nghiệm thu 29/10/2026

Chạy `scripts/final-test.ps1`: MySQL riêng, toàn bộ pytest không skip, dữ liệu giả đủ vai trò/trạng thái, 50 câu/5 phiên/1.000 chunk với simulation, backup/restore và hash từng bảng. Chạy `scripts/browser-acceptance.cjs` trên server demo: login bốn vai trò VI/EN, desktop/mobile/menu, Agent tạo/nhận/gợi ý/duyệt/gửi, lịch sử chuyển giao, Customer chat/đóng/CSAT và timer 60 giây bằng đồng hồ ảo. Kết quả tại `docs/reports/final-acceptance-20261029/`.

Phân biệt kiểm chứng luồng bằng simulation với nghiệm thu provider thật. Gemini thật cần khóa/mạng/nguồn đã index đúng model; `backend.benchmark` đo HTTP riêng, không dùng số đo mock làm bằng chứng SLA thật.

## 1. Mục tiêu kiểm thử
Xác minh tính đúng đắn của toàn bộ các chức năng nghiệp vụ quản lý ticket và các tính năng AI tăng cường (phân loại, gợi ý trả lời RAG, tóm tắt chuỗi trao đổi, cơ chế duyệt của con người).

## 2. Phạm vi kiểm thử
- **Xác thực & Phân quyền**: Đăng nhập, session, vai trò Admin/Lead/Agent (FR-001).
- **Quản lý Ticket & Vòng đời**: Tạo mới, chuyển đổi trạng thái (New -> In Progress -> Waiting Customer -> Closed), gán việc, thêm trao đổi (FR-003, FR-004, FR-005).
- **Trợ lý AI & RAG**:
  - Khử định danh dữ liệu cá nhân PII (NFR-003).
  - Phân loại danh mục và mức ưu tiên tự động (FR-008).
  - Gợi ý câu trả lời nháp từ cơ sở tri thức FAQ (FR-009).
  - Cơ chế con người phê duyệt trước khi gửi (FR-010).
  - Tóm tắt chuỗi trao đổi dài (FR-011).

## 3. Chiến lược kiểm thử
- Sử dụng Framework **pytest**.
- Tách biệt kiểm thử Unit, Integration và API Simulation.
- Mocking và Fallback an toàn cho tầng dịch vụ AI bên ngoài khi không có kết nối internet hoặc API key.

