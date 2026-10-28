# Kiến trúc hiện hành

```text
Browser VI/EN
    │ session cookie + JSON API
FastAPI (backend/app.py)
    ├─ auth/admin/customers
    ├─ tickets/reports
    ├─ chats/support
    ├─ knowledge/system_admin
    ├─ AIProvider (Gemini hoặc OpenAI)
    └─ Database/Transaction
             │
       MySQL 8.0.46
```

- FastAPI phục vụ API và allowlist file tĩnh; không dùng Flask/SQLite ở runtime chính.
- Middleware kiểm tra Origin/header/JSON cho mutation và thêm header bảo mật.
- Policy xác thực, RBAC và quyền sở hữu nằm tại route backend.
- MySQL pool dùng transaction/rollback; placeholder `?` được đổi sang `%s` tại data layer.
- AI provider chỉ gọi host cố định, che PII, ép structured output và không gửi ticket thay Agent.
- RAG lưu tài liệu/chunk/vector/citation trong MySQL; không dùng vector database khác.
- Migration 001–009 có checksum, journal và named lock; database có dữ liệu không chạy lại initializer.
