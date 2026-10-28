# Yêu cầu Trợ lý AI Hỗ trợ Khách hàng (AI Support Assistant Requirements) - Đề tài 10

## 1. Mục tiêu
Cung cấp module trí tuệ nhân tạo tăng cường cho nhân viên hỗ trợ khách hàng, giải quyết bài toán:
- Quá tải khi tiếp nhận lượng lớn ticket mới.
- Mất thời gian tìm kiếm câu trả lời chuẩn trong quy định FAQ của doanh nghiệp.
- Mất thời gian đọc lại chuỗi lịch sử trao đổi dài dòng khi bàn giao ca trực.
- Ngăn chặn triệt để tình trạng AI tự ý bịa đặt cam kết bồi thường sai chính sách.

## 2. Các chức năng AI chi tiết
1. **AI Phân loại & Gợi ý Mức ưu tiên (FR-008)**:
   - Phân tích ngữ nghĩa tự nhiên của tiêu đề và mô tả ticket.
   - Gán vào một trong các nhóm: `Tài khoản & Đăng nhập`, `Thanh toán & Hóa đơn`, `Lỗi kỹ thuật & Phần mềm`, `Tư vấn & Hướng dẫn sử dụng`.
   - Đề xuất mức ưu tiên: `Low`, `Medium`, `High`, `Urgent`.
2. **AI Gợi ý câu trả lời nháp (RAG Draft Response) (FR-009)**:
   - Truy xuất cơ sở tri thức FAQ/chính sách phù hợp bằng phương pháp tra cứu ngữ cảnh (RAG).
   - Soạn câu trả lời lịch sự, đầy đủ quy trình giải quyết.
3. **Cơ chế Duyệt của Nhân viên (Human Gate / Approval) (FR-010)**:
   - Nhân viên trực tiếp biên tập (edit) câu trả lời nháp trên giao diện trước khi bấm xác nhận gửi.
   - AI TUYỆT ĐỐI KHÔNG tự động gửi tin nhắn mà chưa có sự kiểm duyệt của con người.
4. **AI Tóm tắt lịch sử trao đổi (FR-011)**:
   - Trích xuất ngắn gọn 3 gạch đầu dòng: Vấn đề ban đầu, Hành động đã thực hiện, Trạng thái & nút thắt hiện tại.
5. **Quyền riêng tư & Khử định danh PII (NFR-003)**:
   - Loại bỏ mật khẩu, số thẻ ngân hàng, số điện thoại cá nhân trước khi gửi tới API LLM bên ngoài.

