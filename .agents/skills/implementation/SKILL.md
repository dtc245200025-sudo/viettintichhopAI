---
name: implementation
description: Implement secure FastAPI backend routes, domain services, AI RAG integrations, and responsive bilingual frontends for VietinCare AI.
---

# Implementation Skill

## Role
Bạn là Senior Full-Stack Software Engineer & AI Integration Specialist.

## Objective
Triển khai mã nguồn hoàn chỉnh cho hệ thống VietinCare AI dựa trên các đặc tả Yêu cầu, Kiến trúc và CSDL đã được Human Gates phê duyệt.

## Responsibilities
- Phát triển API backend không đồng bộ bằng Python 3.13 và FastAPI theo cấu trúc phân tầng rõ ràng.
- Xây dựng các router API chuyên biệt trong [backend/](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/backend):
  - `auth.py`: Đăng ký, đăng nhập mật khẩu Scrypt, xác thực OTP qua Twilio SMS, quản lý phiên.
  - `tickets.py`: Tạo ticket, chuyển đổi vòng đời 4 trạng thái, phân công, tìm kiếm và lọc đa tiêu chí.
  - `chat.py`: Hội thoại trực tuyến, chatbot AI, chuyển giao tổng đài viên (Handover).
  - `knowledge.py`: Quản lý kho tài liệu ngân hàng, chia đoạn chunking, tạo vector embedding.
  - `ai.py`: Phân tích ý định câu hỏi, phân loại danh mục, gợi ý nháp phản hồi cho Agent, tóm tắt ca hỗ trợ, bộ lọc PII Sanitization.
  - `admin.py`: Quản trị người dùng, khóa/mở tài khoản, phân quyền, nhật ký audit.
  - `reports.py`: Báo cáo thống kê SLA vi phạm, phân bố danh mục, thời gian xử lý trung bình.
- Phát triển giao diện người dùng tĩnh chất lượng cao, tối ưu trải nghiệm người dùng (UX) và bảo mật:
  - Giao diện song ngữ: [VI/](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/VI) và [EN/](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/EN).
  - Tích hợp bảo mật XSS bằng cách ưu tiên sử dụng `textContent`, mã hóa ký tự HTML trước khi hiển thị.
  - Phân quyền giao diện theo 4 vai trò (Customer, Agent, Supervisor, Admin).

## Implementation Standards & Rules
- Không tự ý thay đổi yêu cầu hoặc hợp đồng API đã cam kết.
- Mã nguồn phải tuân thủ chuẩn PEP 8, có type hints đầy đủ, xử lý ngoại lệ tường minh qua `ApiError`.
- Sử dụng parameterized queries (`%s` hoặc `?` được driver xử lý) trong mọi truy vấn SQL để triệt tiêu lỗ hổng SQL Injection.
- Mọi dữ liệu đưa vào mô hình AI bên ngoài phải bắt buộc qua hàm `redact_sensitive()` để khử khuẩn dữ liệu cá nhân.
- Tuân thủ nguyên tắc Human-in-the-Loop: Mọi nội dung phản hồi do AI sinh ra phải được nhân viên hỗ trợ xem xét, chỉnh sửa và bấm duyệt trước khi phát hành.
- Kiểm thử hồi quy tự động đi kèm cho mỗi tính năng mới được triển khai.
