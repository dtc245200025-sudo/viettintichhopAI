# Tiêu chí chấp nhận VietinCare AI

## AC-001 — Xác thực và RBAC (FR-001)

- Đăng nhập đúng tạo session cookie HttpOnly; tài khoản khóa/sai mật khẩu bị từ chối.
- Mỗi vai trò chỉ truy cập API và dữ liệu thuộc phạm vi của mình.

## AC-002 — Tạo và cập nhật ticket (FR-003)

- Customer tạo ticket có tiêu đề, mô tả và ưu tiên hợp lệ; ticket bắt đầu ở `Mới`.
- Agent chỉ sửa ticket đã nhận; ticket đóng không chỉnh sửa.

## AC-003 — Phân công và vòng đời (FR-004)

- Supervisor giao ticket mở cho Agent hoạt động và hệ thống ghi lịch sử phân công.
- Agent nhận ticket mới để chuyển sang `Đang xử lý`.
- Chỉ cho phép `Mới → Đang xử lý ↔ Chờ khách hàng → Đã đóng`; đóng yêu cầu phản hồi Agent.

## AC-004 — Trao đổi và lịch sử (FR-005)

- Customer/Agent hợp lệ gửi phản hồi và xem lại sau tải lại trang.
- Customer trả lời ticket đang chờ sẽ khôi phục trạng thái `Đang xử lý` và ghi lịch sử.
- Chưa đánh dấu đạt đối với upload/file metadata riêng.

## AC-005 — Lọc và báo cáo (FR-006, FR-007)

- Bộ lọc nhận khách hàng, trạng thái, ưu tiên, ngày hợp lệ và từ chối ngày không tồn tại.
- Supervisor xem ticket theo trạng thái/nhóm, thời gian xử lý và số quá SLA demo.

## AC-006 — AI hỗ trợ ticket (FR-008, FR-009, FR-011)

- Agent của ticket Đang xử lý nhận category, priority, sentiment, draft và summary.
- Payload provider che email, điện thoại, số tài khoản, thẻ và mật khẩu.
- Output sai schema/provider lỗi trả lỗi an toàn và không tự thay đổi ticket.

## AC-007 — Human Gate (FR-010)

- Gợi ý mới được lưu `Pending`; Agent có thể `Selected` hoặc `Dismissed` một lần.
- Chọn nháp chỉ điền ô phản hồi; request gửi riêng của Agent mới lưu nội dung cho Customer.

## AC-008 — Chat RAG và chuyển giao

- Customer chat chỉ nhận câu trả lời từ nguồn đã xuất bản và xem được nguồn.
- Customer yêu cầu Agent; Agent tiếp nhận/phản hồi/kết thúc; Supervisor giám sát/tóm tắt/kết thúc theo quyền.

## Bằng chứng

- Pytest và kiểm tra cú pháp phải đạt toàn bộ test cốt lõi không bị skip.
- MySQL integration, browser có đăng nhập và provider thật được ghi riêng; unit test không thay thế các bằng chứng này.
