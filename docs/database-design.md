# Thiết kế database hiện hành

Hệ quản trị duy nhất: MySQL Community Server 8.0.46, InnoDB, utf8mb4. `SQLQuery1.sql` khởi tạo database mới; database có dữ liệu dùng migration 001–011, tổng 43 bước. Nghiệm thu cách ly có 32 bảng, gồm SchemaMigration.

## Nhóm bảng

- Danh tính: `Role`, `UserAccount`, `Customer`, `AuthSession`, `AuthThrottle`, `AuthOtpChallenge`.
- Ticket: `Ticket`, `TicketCategory`, `TicketReply`, `TicketStatusHistory`, `TicketAssignmentHistory`, `Evaluation`, `TicketRequest`, `TicketAIAnalysis`.
- Chat/handover: `ChatSession`, `Message`, `MessageSource`, `ChatRequest`, `Handover`.
- RAG: `KnowledgeBase`, `KnowledgeChunk`, `KnowledgeRequest`.
- Quản trị: `AuditLog`, `SystemSetting`, `SchemaMigration`.
- Tự động: `AgentPresence`, `TicketAutomation`, `MessageAutomation`, `SupervisorAlert`.

Migration 011 thêm `CorrectionOf` cho TicketReply/Message; đính chính tạo bản ghi mới. API kiểm tra đúng tác giả và Ticket/chat. `auth.session_hours` là cấu hình không chứa bí mật. Migration 001–009 giữ nguyên checksum.

## Ràng buộc chính

- Email đăng nhập chuẩn hóa là duy nhất; Customer liên kết tối đa một UserAccount.
- Ticket/chat/evaluation có khóa ngoại quyền sở hữu và check trạng thái/ưu tiên/điểm.
- Một ticket có lịch sử trạng thái/phân công; một Customer chỉ đánh giá một lần trên ticket.
- Một chat chỉ có một handover đang hoạt động; câu trả lời AI gắn `ReplyTo` duy nhất.
- Ticket/Chat/Knowledge request key chống gửi trùng.
- Vector là JSON kèm model/số chiều; citation lưu snapshot nội dung nguồn.

Không có các bảng Flask cũ `ticket_comments`, `faqs`, `ai_logs` trong runtime hiện hành.
