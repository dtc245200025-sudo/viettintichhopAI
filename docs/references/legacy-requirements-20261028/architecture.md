# Tài liệu thiết kế kiến trúc hệ thống (System Architecture Design) - Đề tài 10

## 1. Phong cách kiến trúc (Architectural Style)
Hệ thống quản lý hỗ trợ khách hàng ViettinCare áp dụng phong cách kiến trúc **Layered Architecture (Phân lớp)** kết hợp **Service-Oriented AI Pipeline** và **Human-in-the-Loop Pattern**:
- **Presentation Layer (Giao diện người dùng)**: HTML5/CSS3/JavaScript hiện đại, giao diện trực quan hỗ trợ phân tích ticket và bảng điều khiển trợ lý AI.
- **Application / Controller Layer (FastAPI)**: Tiếp nhận HTTP/JSON, xác thực session cookie, kiểm tra vai trò Customer/Agent/Supervisor/Admin và điều phối các module nghiệp vụ.
- **Domain Service Layer**:
  - `AuthService`: Quản lý tài khoản, mật khẩu băm, phân quyền (Admin, Team Lead, Agent).
  - `CustomerService`: Quản lý thông tin hồ sơ và danh sách khách hàng.
  - `TicketService`: Nghiệp vụ cốt lõi quản lý vòng đời ticket, phân công, trạng thái, bình luận.
  - `AISupportService`: Tích hợp các khả năng AI:
    - *Ticket Analyzer*: Phân tích cấu trúc vấn đề, trích xuất thực thể và lọc PII.
    - *FAQ Retriever*: Truy vấn cơ sở tri thức RAG để lấy chính sách liên quan.
    - *Context & Prompt Builder*: Đóng gói ngữ cảnh an toàn và áp đặt quy tắc phòng chống hallucination.
    - *AI Provider*: Hỗ trợ Gemini hoặc OpenAI cho embedding và sinh nội dung; không tự chuyển provider khi lỗi.
- **Data Access & Persistence Layer**: MySQL Community Server 8.0.46, InnoDB, utf8mb4; migration 001–009 quản lý schema, gồm KnowledgeBase/KnowledgeChunk, chat, ticket, phân công, audit và cấu hình.

## 2. Sơ đồ kiến trúc tổng thể (Architecture Diagram)

```
+-------------------------------------------------------------------------+
|                              Web Browser                                |
|          (Support Dashboard, Ticket Workspace, AI Assistant UI)         |
+-------------------------------------------------------------------------+
                                    │  HTTP / JSON
                                    ▼
+-------------------------------------------------------------------------+
|                           FastAPI Application                           |
|             (Session Auth, RBAC Middleware, Error Handlers)             |
+---------------------------------+---------------------------------------+
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
+------------------+     +------------------+     +-----------------------+
|   Auth Service   |     | Customer Service |     |    Ticket Service     |
+--------+---------+     +--------+---------+     +-----------+-----------+
         │                        │                           │
         │                        │                           ▼
         │                        │               +-----------------------+
         │                        │               |   AI Support Service  |
         │                        │               +-----------+-----------+
         │                        │                           │
         │                        │                 ┌─────────┴─────────┐
         │                        │                 ▼                   ▼
         │                        │        +----------------+  +----------------+
         │                        │        |  Ticket & PII  |  |  FAQ Knowledge |
         │                        │        |    Analyzer    |  |  RAG Retriever |
         │                        │        +--------+-------+  +--------+-------+
         │                        │                 │                   │
         │                        │                 └─────────┬─────────┘
         │                        │                           ▼
         │                        │                 +-------------------+
         │                        │                 | Context & Prompt  |
         │                        │                 |      Builder      |
         │                        │                 +---------+---------+
         │                        │                           │
         │                        │                           ▼
         │                        │                 +-------------------+
         │                        │                 | Gemini LLM Client |
         │                        │                 +---------+---------+
         │                        │                           │
         ▼                        ▼                           ▼
+───────────────────────────────────────────────────────────+ │ (External API)
|                      Relational DB                        | │
|   (users, customers, tickets, comments, faqs, ai_logs)   | │
+───────────────────────────────────────────────────────────+ ▼
                                                    +-------------------+
                                                    |  Google Gemini    |
                                                    |     LLM Cloud     |
                                                    +-------------------+
```

## 3. Luồng dữ liệu và Phê duyệt của con người (Human Gate Data Flow)

```
Customer Ticket / Update
           │
           ▼
     Ticket Service
           │
           ▼
   AI Support Service ──> [PII Filter] ──> [FAQ RAG Lookup] ──> [Gemini API]
                                                                     │
                                                                     ▼
                                                             AI Draft Response
                                                                     │
                                                                     ▼
                                                          +---------------------+
                                                          |  HUMAN VERIFICATION |
                                                          |   (Support Agent)   |
                                                          |  Review, Edit, OK   |
                                                          +----------+----------+
                                                                     │
                                                      Approved? ─────┴───── Rejected?
                                                          │                     │
                                                          ▼                     ▼
                                                 Post to Ticket        Discard / Re-prompt
                                                 (DB Saved & Sent)     (Log feedback)
```

## 4. Biên giới bảo mật (Security Boundaries)
1. **Kiểm tra vai trò người dùng (RBAC)**: Chỉ Admin mới được quản lý tài khoản nhân viên và FAQ; chỉ Team Lead và Admin mới được phân công lại ticket cho nhân viên khác.
2. **Khử định danh PII (Privacy Boundary)**: Trước khi gửi văn bản khách hàng ra Internet tới máy chủ của Google Gemini, tầng `PII Filter` tự động loại bỏ mật khẩu, số định danh, thông tin thanh toán.
3. **Cô lập CSDL đối với AI**: Gemini API không bao giờ được phép trực tiếp thực thi câu lệnh SQL trên cơ sở dữ liệu. Mọi dữ liệu chỉ được cung cấp dưới dạng ngữ cảnh văn bản thuần túy (Context Injection) được kiểm soát chặt chẽ.

