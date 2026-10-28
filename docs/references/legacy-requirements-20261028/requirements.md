# Đặc tả yêu cầu phần mềm (Software Requirements Specification) - Đề tài 10

## 1. Yêu cầu chức năng (Functional Requirements)

| Mã yêu cầu | Tên chức năng | Mô tả chi tiết | Tác nhân liên quan |
|---|---|---|---|
| **FR-001** | Đăng nhập và Phân quyền (RBAC) | Xác thực người dùng qua JWT/Session; phân quyền Admin, Team Lead, Support Agent, Customer. | Tất cả người dùng |
| **FR-002** | Quản lý thông tin khách hàng | Thêm, sửa, xem chi tiết hồ sơ khách hàng (họ tên, email, điện thoại, phân hạng, ghi chú). | Admin, Team Lead, Agent |
| **FR-003** | Tạo và quản lý vòng đời Ticket | Tạo ticket với tiêu đề, mô tả, danh mục, mức ưu tiên; cập nhật trạng thái (`Mới`, `Đang xử lý`, `Chờ khách`, `Đã đóng`). | Customer, Agent, Team Lead |
| **FR-004** | Phân công xử lý Ticket | Quản lý nhóm hoặc Admin gán ticket cho Support Agent phụ trách; hỗ trợ nhận việc tự nguyện. | Admin, Team Lead, Agent |
| **FR-005** | Quản lý trao đổi và bình luận | Lưu chuỗi trao đổi giữa khách hàng và nhân viên hỗ trợ; hiển thị thời gian, vai trò người gửi và tệp mô tả. | Customer, Agent |
| **FR-006** | Tìm kiếm và Lọc nâng cao | Tìm kiếm ticket theo từ khóa tiêu đề, lọc theo khách hàng, trạng thái, mức độ ưu tiên và thời gian tiếp nhận. | Agent, Team Lead, Admin |
| **FR-007** | Báo cáo thống kê hỗ trợ | Thống kê số lượng ticket theo trạng thái, thời gian phản hồi trung bình, tỷ lệ xử lý đúng SLA, biểu đồ nhóm lỗi thường gặp. | Team Lead, Admin |
| **FR-008** | AI Phân loại & Gợi ý Ưu tiên | AI phân tích nội dung ticket để dự đoán danh mục (Account, Billing, Bug, General) và đề xuất mức ưu tiên (Low, Medium, High, Urgent). | Hệ thống AI, Agent |
| **FR-009** | AI Gợi ý câu trả lời nháp (RAG) | AI đối chiếu nội dung ticket với cơ sở dữ liệu FAQ để sinh câu trả lời nháp chuẩn mực, thân thiện. | Hệ thống AI, Agent |
| **FR-010** | Cơ chế Con người phê duyệt (Human Gate) | Nhân viên hỗ trợ xem trước (preview), chỉnh sửa câu trả lời của AI và bấm duyệt trước khi hệ thống lưu/gửi cho khách. AI không được tự gửi. | Support Agent |
| **FR-011** | AI Tóm tắt lịch sử trao đổi | Với các ticket có từ 3 trao đổi trở lên, AI tự động trích xuất tóm tắt ngắn gọn các sự kiện chính và vấn đề đang vướng mắc. | Hệ thống AI, Agent |

## 2. Yêu cầu phi chức năng (Non-Functional Requirements)

| Mã yêu cầu | Loại | Tiêu chí kỹ thuật |
|---|---|---|
| **NFR-001** | Hiệu năng (Performance) | Thời gian phản hồi các truy vấn quản lý CRUD < 1.0 giây; thời gian xử lý AI (RAG + Gemini) < 4.0 giây. |
| **NFR-002** | Bảo mật (Security) | Mật khẩu băm bằng SHA-256/bcrypt; kiểm tra quyền hạn (Role check) trên mọi API; phòng chống SQL Injection bằng tham số hóa. |
| **NFR-003** | Quyền riêng tư (Privacy) | Tự động khử định danh (PII Masking) các dữ liệu nhạy cảm (mật khẩu, số thẻ ngân hàng, số điện thoại) trước khi gửi tới API LLM bên ngoài. |
| **NFR-004** | Khả năng sẵn sàng (Reliability) | Khi dịch vụ AI bên ngoài gặp sự cố hoặc timeout, hệ thống vẫn hoạt động bình thường ở chế độ thủ công, thông báo lỗi an toàn không lộ secret key. |
| **NFR-005** | Khả năng mở rộng (Scalability) | CSDL phân tách rõ ràng các bảng nghiệp vụ và bảng log kiểm toán AI (`ai_logs`); thiết kế hỗ trợ tích hợp thêm kho tri thức tài liệu (RAG Vector/Full-text). |
| **NFR-006** | Tính khả dụng (Usability) | Giao diện hai cột trực quan: cột trái hiển thị thông tin & lịch sử trao đổi của ticket, cột phải là trợ lý AI (phân loại, tóm tắt, câu trả lời nháp kèm nút bấm duyệt). |

