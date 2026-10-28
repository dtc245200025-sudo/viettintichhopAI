# Thiết kế luồng hiện hành

## Ticket

```mermaid
sequenceDiagram
    Customer->>FastAPI: Tạo ticket
    FastAPI->>MySQL: Ticket(Mới) + audit/idempotency
    Supervisor->>FastAPI: Giao Agent
    FastAPI->>MySQL: AssignmentHistory
    Agent->>FastAPI: Nhận ca
    FastAPI->>MySQL: Đang xử lý + StatusHistory
    Agent->>FastAPI: Yêu cầu AI assist
    FastAPI->>AI: Context đã che PII
    AI-->>FastAPI: Category/priority/draft/summary
    FastAPI->>MySQL: TicketAIAnalysis(Pending)
    Agent->>FastAPI: Selected/Dismissed
    Agent->>FastAPI: Gửi phản hồi đã kiểm tra
    FastAPI->>MySQL: TicketReply
```

## Chat RAG và handover

```mermaid
sequenceDiagram
    Customer->>FastAPI: Gửi tin nhắn
    FastAPI->>MySQL: Lưu Message
    FastAPI->>MySQL: Tìm KnowledgeChunk đã xuất bản
    FastAPI->>AI: Câu hỏi + nguồn đã che PII
    AI-->>FastAPI: Answer + source IDs
    FastAPI->>MySQL: AI Message + MessageSource
    Customer->>FastAPI: Yêu cầu Agent
    Agent->>FastAPI: Tiếp nhận/phản hồi
    FastAPI->>MySQL: Handover + Message + AuditLog
```

## Quan hệ vai trò

- Customer sở hữu ticket/chat và đánh giá ticket đóng.
- Agent xử lý ticket/handover được giao.
- Supervisor phân công, giám sát, quản lý liên hệ và báo cáo.
- Admin quản lý tài khoản, tri thức, cấu hình và audit.
