# Ghi nhận vấn đề yêu cầu & Kiểm tra giả định (Requirements Issues & Assumptions) - Đề tài 10

## 1. Các điểm mơ hồ trong yêu cầu ban đầu (Ambiguities Identified)
1. **Quy trình đóng ticket**: Khách hàng có quyền tự đóng ticket không hay chỉ có nhân viên hỗ trợ mới được phép chuyển trạng thái thành `Closed`?
   - *Giải pháp*: Cho phép cả hai; nhân viên có quyền đóng sau khi xác nhận khách đã được hỗ trợ; khách hàng có nút xác nhận "Đã hài lòng & Đóng ticket".
2. **Quy tắc phân công (Assignment Logic)**: Tự động phân công theo kiểu Round-Robin hay phân công thủ công bởi Quản lý nhóm?
   - *Giải pháp*: Mặc định hỗ trợ phân công thủ công bởi Team Lead/Admin, đồng thời hỗ trợ nút "Nhận xử lý ticket này" (Self-assign) cho nhân viên trực ca.
3. **Mức độ hỗ trợ tệp đính kèm (Attachments)**: Đề tài 10 ghi rõ "file đính kèm ở mức mô tả".
   - *Giải pháp*: Lưu tên file, mô tả định dạng và URL liên kết, tránh lưu trữ tệp binary quá lớn trong CSDL gây nghẽn hiệu năng.

## 2. Các giả định nghiệp vụ (Assumptions)
- Hệ thống hỗ trợ đa ngôn ngữ nhưng giao diện chính và prompt AI ưu tiên Tiếng Việt chuẩn.
- Dịch vụ AI (Google Gemini API) có thể có độ trễ mạng nhất định (1-3s), do đó giao diện web cần hiển thị animation trạng thái tải (Loading spinner / Typing indicator).
- Đã cấu hình kho kiến thức FAQ mẫu ban đầu với các tình huống phổ biến (quên mật khẩu, lỗi thanh toán, cài đặt ứng dụng, chính sách đổi trả).

## 3. Kiểm chứng AI Hallucination & Requirement Invention (Giống Bước 7 trong Mẫu Word)
Trong quá trình chạy Codex phân tích yêu cầu ban đầu:
- **Nguy cơ Hallucination phát hiện được**: AI đề xuất thêm tính năng "Tự động gọi điện thoại cho khách hàng qua VoIP" và "Tự động hoàn tiền vào tài khoản ngân hàng của khách khi phát hiện lỗi thanh toán".
- **Biện pháp xử lý của con người**: Loại bỏ ngay 2 tính năng tự ý bịa đặt này. Hệ thống hỗ trợ khách hàng không được tự động chuyển tiền hoặc can thiệp tổng đài viễn thông ngoài phạm vi quy định của đề tài. Mọi quyết định bồi hoàn tài chính phải do con người phê duyệt ngoại tuyến.

