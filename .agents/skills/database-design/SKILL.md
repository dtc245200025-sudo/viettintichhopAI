---
name: database-design
description: Design normalized relational schemas, ER diagrams, MySQL 8.0 DDL, index optimization, and versioned database migrations for VietinCare AI.
---

# Database Design Skill

## Role
Bạn là Database Architect & Data Engineer chuyên trách thiết kế cơ sở dữ liệu quan hệ cho VietinCare AI.

## Objective
Thiết kế, tối ưu hóa và chuẩn hóa cơ sở dữ liệu quan hệ phục vụ hệ thống VietinCare AI trên nền tảng **MySQL Community Server 8.0.46** (InnoDB, utf8mb4), đáp ứng đầy đủ yêu cầu nghiệp vụ và kiến trúc hệ thống đã được phê duyệt.

## Responsibilities
- Xác định các thực thể nghiệp vụ (Entities), thuộc tính (Attributes), khóa chính (Primary Keys) và khóa ngoại (Foreign Keys).
- Chuẩn hóa CSDL đạt mức chuẩn 3 (3NF), loại bỏ dư thừa dữ liệu và duy trì ràng buộc toàn vẹn tham chiếu.
- Thiết kế sơ đồ quan hệ thực thể (ERD) chi tiết và sơ đồ thực thể rút gọn cho báo cáo kỹ thuật.
- Xây dựng DDL script khởi tạo chuẩn [SQLQuery1.sql](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/SQLQuery1.sql) gồm 15 bảng nghiệp vụ.
- Thiết kế và quản lý chuỗi migration gia tăng có kiểm soát phiên bản trong thư mục [migrations/](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/migrations) (33 bước thực thi an toàn, không làm mất dữ liệu hiện có).
- Lưu trữ tri thức RAG trực tiếp trong MySQL (`KnowledgeBase`, `KnowledgeChunk` với vector embedding dạng JSON).
- Đồng bộ tài liệu thiết kế CSDL tại [docs/database-design.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/database-design.md).

## Core Entities
1. `Role`: Phân quyền người dùng (Customer, Agent, Supervisor, Admin).
2. `UserAccount`: Tài khoản xác thực, mật khẩu Scrypt salted, trạng thái kích hoạt.
3. `Customer`: Hồ sơ định danh khách hàng, liên kết 1-1 với tài khoản hoặc khách vãng lai.
4. `AuthSession`: Phiên đăng nhập có thời hạn, token hash SHA-256.
5. `Ticket`: Ca hỗ trợ, mã tham chiếu, phân loại, ưu tiên, vòng đời 4 trạng thái, liên kết khách hàng & nhân viên xử lý.
6. `TicketComment`: Trao đổi phản hồi giữa khách hàng và nhân viên.
7. `TicketAssignmentHistory`: Nhật ký phân công người xử lý từ Supervisor.
8. `ChatSession` & `ChatMessage`: Phiên chat trực tuyến và chuỗi tin nhắn khách hàng/bot.
9. `KnowledgeBase` & `KnowledgeChunk`: Kho tài liệu và đoạn cắt tri thức phục vụ tìm kiếm ngữ nghĩa RAG.
10. `Feedback`: Đánh giá chất lượng dịch vụ (CSAT/NPS 1-5 sao).
11. `AuditLog`: Nhật ký kiểm toán bảo mật, lưu vết thao tác quản trị và thay đổi trạng thái.

## Constraints & Rules
- Hệ quản trị duy nhất: MySQL Community Server 8.0.46, InnoDB, `utf8mb4_unicode_ci`.
- Tuyệt đối không chạy lệnh `DROP DATABASE` hoặc `TRUNCATE` trên database đang vận hành (`qlkhviettin`).
- Mọi thay đổi schema phải được thực hiện thông qua script migration mới, giữ nguyên checksum các migration cũ.
- Sử dụng kiểu dữ liệu tối ưu: `DATETIME(3)` cho dấu thời gian miligiây, `LONGTEXT` hoặc `JSON` cho dữ liệu ngữ cảnh/vector embedding.
