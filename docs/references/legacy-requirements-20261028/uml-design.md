# Tài liệu Thiết kế Biểu đồ UML (UML Design Specification) - Đề tài 10

Tài liệu này đặc tả toàn bộ hệ thống quản lý hỗ trợ khách hàng ViettinCare thông qua các biểu đồ UML chuẩn hóa (chuẩn Mermaid): Use Case, Sequence, Class, State Machine, Activity và ERD.

---

## 1. Biểu đồ Ca sử dụng (Use Case Diagram)

Hệ thống có 5 tác nhân chính:
- **Admin**: Quản trị viên hệ thống
- **Team Lead**: Quản lý nhóm hỗ trợ
- **Support Agent**: Nhân viên chăm sóc và hỗ trợ kỹ thuật
- **Customer**: Khách hàng sử dụng dịch vụ
- **Gemini LLM**: Hệ thống AI bên thứ ba

```mermaid
graph TD
    subgraph System ["Hệ thống Quản lý Hỗ trợ Khách hàng (ViettinCare)"]
        UC1["Đăng nhập & Xác thực RBAC"]
        UC2["Quản lý thông tin Khách hàng"]
        UC3["Tạo mới & Theo dõi Ticket"]
        UC4["Phân công Ticket cho Nhân viên"]
        UC5["Trao đổi Phản hồi (Comments)"]
        UC6["Tìm kiếm & Lọc nâng cao"]
        UC7["Xem Báo cáo Thống kê SLA & Sự cố"]
        UC8["AI Tự động Phân loại & Mức ưu tiên"]
        UC9["AI Soạn thảo Câu trả lời Nháp (RAG)"]
        UC10["Phê duyệt Phản hồi (Human Gate)"]
        UC11["AI Tóm tắt Lịch sử Trao đổi Dài"]
        UC12["Tra cứu Cơ sở Tri thức FAQ"]
    end

    Customer --> UC3
    Customer --> UC5
    
    SupportAgent --> UC1
    SupportAgent --> UC2
    SupportAgent --> UC3
    SupportAgent --> UC5
    SupportAgent --> UC6
    SupportAgent --> UC9
    SupportAgent --> UC10
    SupportAgent --> UC11

    TeamLead --> UC1
    TeamLead --> UC4
    TeamLead --> UC6
    TeamLead --> UC7

    Admin --> UC1
    Admin --> UC2
    Admin --> UC4
    Admin --> UC7
    Admin --> UC12

    UC9 -.->|<<include>>| UC12
    UC9 -.->|<<include>>| UC8
    UC9 -.->|<<include>>| UC10
    
    UC8 -.-> GeminiLLM["Gemini LLM API"]
    UC9 -.-> GeminiLLM
    UC11 -.-> GeminiLLM
```

---

## 2. Biểu đồ Tuần tự (Sequence Diagram)

### Luồng xử lý: Nhân viên sử dụng Trợ lý AI & Phê duyệt Phản hồi (Human Gate)

Biểu đồ mô tả chi tiết tương tác khi nhân viên mở ticket, yêu cầu AI gợi ý câu trả lời, đối chiếu FAQ, lọc PII và bấm nút phê duyệt gửi cho khách hàng.

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Khách hàng
    actor Agent as Nhân viên Hỗ trợ
    participant UI as Giao diện Web (Browser)
    participant Ctrl as Ticket & AI Controller
    participant AISvc as AI Support Service
    participant San as PII Sanitizer
    participant DB as MySQL 8.0.46
    participant LLM as Google Gemini API

    Customer->>DB: Gửi yêu cầu hỗ trợ (Ticket #1001)
    Note over DB: Ticket trạng thái 'New'

    Agent->>UI: Mở xem chi tiết Ticket #1001
    UI->>Ctrl: GET /tickets/1001
    Ctrl->>DB: Truy vấn Ticket & Lịch sử Comments
    DB-->>Ctrl: Trả về thông tin Ticket & Comments
    Ctrl-->>UI: Hiển thị giao diện 2 cột (Ticket + AI Panel)

    Agent->>UI: Bấm "AI Soạn thảo Câu trả lời Nháp"
    UI->>Ctrl: POST /api/ai/suggest {"ticket_id": 1001}
    Ctrl->>AISvc: suggest_response(ticket, comments)

    AISvc->>San: sanitize_pii(title + description)
    San-->>AISvc: Văn bản đã che Mật khẩu, SĐT, Số thẻ

    AISvc->>DB: retrieve_faqs(intent) - SQL Tham số hóa
    DB-->>AISvc: Trả về bài viết FAQ phù hợp

    AISvc->>AISvc: ContextBuilder: Đóng gói Ticket + 4 Comments + FAQ
    AISvc->>AISvc: PromptBuilder: Áp đặt quy tắc cấm bịa đặt, cấm hứa hoàn tiền

    AISvc->>LLM: Gửi Prompt và Ngữ cảnh qua API
    LLM-->>AISvc: Trả về nội dung phản hồi nháp (Draft)
    AISvc->>DB: Ghi ai_logs (latency, raw_output)
    AISvc-->>Ctrl: Trả về draft_response
    Ctrl-->>UI: Render câu trả lời vào ô soạn thảo

    Note over Agent, UI: HUMAN GATE (ĐIỂM KIỂM SOÁT CỦA CON NGƯỜI)
    Agent->>UI: Xem xét, chỉnh sửa bổ sung thông tin hotline
    Agent->>UI: Bấm nút "Phê duyệt & Gửi cho Khách hàng"

    UI->>Ctrl: POST /api/ai/approve-and-send {"ticket_id": 1001, "content": "..."}
    Ctrl->>DB: INSERT INTO ticket_comments (nội dung đã duyệt)
    Ctrl->>DB: UPDATE tickets SET status = 'Waiting Customer'
    Ctrl->>DB: UPDATE ai_logs SET is_approved = 1
    DB-->>Ctrl: Xác nhận thành công
    Ctrl-->>UI: Thông báo "Đã gửi phản hồi thành công!"
    UI-->>Customer: Khách hàng nhìn thấy phản hồi chính thức
```

---

## 3. Biểu đồ Lớp (Class Diagram)

Biểu đồ biểu diễn các lớp thực thể (Entities), các lớp dịch vụ (Services) và quan hệ cấu trúc trong mã nguồn.

```mermaid
classDiagram
    class User {
        +int id
        +string username
        +string email
        +string password_hash
        +string full_name
        +string role
        +datetime created_at
        +datetime updated_at
    }

    class Customer {
        +int id
        +string full_name
        +string email
        +string phone
        +string company
        +string tier
        +datetime created_at
    }

    class Ticket {
        +int id
        +string ticket_number
        +int customer_id
        +string title
        +string description
        +string category
        +string priority
        +string status
        +int assigned_to
        +datetime created_at
        +datetime updated_at
        +datetime resolved_at
    }

    class TicketComment {
        +int id
        +int ticket_id
        +int user_id
        +string author_role
        +string author_name
        +string content
        +bool is_internal
        +datetime created_at
    }

    class FAQ {
        +int id
        +string category
        +string question
        +string answer
        +string keywords
        +datetime created_at
    }

    class AILog {
        +int id
        +int ticket_id
        +string action_type
        +string input_context
        +string raw_ai_output
        +string approved_output
        +bool is_approved
        +int agent_id
        +int latency_ms
        +datetime created_at
    }

    class AuthService {
        +authenticate(username, password) User
        +get_user_by_id(user_id) User
        +list_agents() List~User~
    }

    class CustomerService {
        +get_all_customers() List~Customer~
        +get_customer_by_id(customer_id) Customer
        +create_customer(full_name, email, phone, company, tier) int
    }

    class TicketService {
        +get_tickets(status, priority, search, assigned_to) List~Ticket~
        +get_ticket_by_id(ticket_id) Ticket
        +create_ticket(customer_id, title, desc, cat, prio, assigned) int
        +update_ticket_status(ticket_id, status) void
        +update_ticket_classification(ticket_id, cat, prio) void
        +assign_ticket(ticket_id, user_id) void
        +get_comments(ticket_id) List~TicketComment~
        +add_comment(ticket_id, user_id, role, name, content) int
        +get_statistics() Dict
    }

    class AISupportService {
        +sanitize_pii(text) string
        +analyze_ticket(title, description) Dict
        +retrieve_faqs(intent) List~FAQ~
        +build_context(ticket, comments, faqs) string
        +generate_with_gemini(system_prompt, user_prompt) string
        +suggest_response(ticket, comments) Dict
        +summarize_history(ticket, comments) Dict
        +classify_ticket(title, description) Dict
        +log_ai_action(ticket_id, action, input, raw, approved) void
    }

    Customer "1" -- "0..*" Ticket : tạo ra
    User "1" -- "0..*" Ticket : phụ trách
    Ticket "1" -- "0..*" TicketComment : chứa
    User "0..1" -- "0..*" TicketComment : gửi
    Ticket "1" -- "0..*" AILog : phát sinh
    User "0..1" -- "0..*" AILog : kiểm duyệt
    
    TicketService ..> Ticket : thao tác
    CustomerService ..> Customer : thao tác
    AuthService ..> User : thao tác
    AISupportService ..> FAQ : tra cứu RAG
    AISupportService ..> AILog : ghi nhật ký
```

---

## 4. Biểu đồ Máy trạng thái (State Machine Diagram)

Vòng đời trạng thái của một Ticket trong hệ thống ViettinCare:

```mermaid
stateDiagram-v2
    [*] --> New : Khách hàng gửi yêu cầu / Nhân viên tạo ticket

    New --> InProgress : Nhân viên nhận việc / Bắt đầu xử lý
    New --> Closed : Hủy bỏ / Trùng lặp sự cố

    InProgress --> WaitingCustomer : Nhân viên gửi phản hồi (hoặc duyệt phản hồi AI)
    InProgress --> InProgress : Thêm ghi chú nội bộ / Đổi nhân viên phụ trách
    InProgress --> Closed : Xử lý xong và đóng ticket

    WaitingCustomer --> InProgress : Khách hàng phản hồi lại thông tin mới
    WaitingCustomer --> Closed : Khách hàng xác nhận hài lòng / Hết hạn chờ

    Closed --> InProgress : Khách hàng mở lại ticket trong vòng 48h
    Closed --> [*] : Hoàn tất lưu trữ
```

---

## 5. Biểu đồ Hoạt động (Activity Diagram)

Quy trình xử lý phản hồi AI và quyết định của con người:

```mermaid
flowchart TD
    Start([Nhân viên mở chi tiết Ticket]) --> CheckStatus{Ticket có đang mở?}
    CheckStatus -- Không --> ViewOnly[Chỉ xem lịch sử] --> EndNode([Kết thúc])
    CheckStatus -- Có --> ChooseMode{Chọn hình thức phản hồi}

    ChooseMode -- Thủ công --> TypeReply[Nhập nội dung phản hồi thủ công]
    TypeReply --> SubmitManual[Bấm Gửi phản hồi] --> SaveDB[Lưu vào ticket_comments]

    ChooseMode -- Sử dụng Trợ lý AI --> TriggerAI[Bấm 'AI Soạn thảo Câu trả lời Nháp']
    TriggerAI --> Sanitize[Khử định danh PII: che mật khẩu, SĐT, số thẻ]
    Sanitize --> SearchFAQ[(Tra cứu Cơ sở Tri thức FAQ)]
    SearchFAQ --> BuildCtx[Đóng gói Ngữ cảnh Ticket + Trao đổi + FAQ]
    BuildCtx --> CallGemini{Gọi Google Gemini API}
    
    CallGemini -- Thành công --> GetDraft[Nhận câu trả lời nháp từ Gemini]
    CallGemini -- Mất kết nối / Lỗi --> UseFallback[Kích hoạt Fallback Engine chuẩn mực]
    
    GetDraft --> DisplayEditor[Hiển thị bản nháp trong ô soạn thảo]
    UseFallback --> DisplayEditor

    DisplayEditor --> HumanReview{Nhân viên kiểm tra Human Gate}
    HumanReview -- Chưa ưng ý --> EditDraft[Chỉnh sửa trực tiếp nội dung trên ô soạn thảo]
    EditDraft --> HumanDecision{Quyết định}
    HumanReview -- Hài lòng --> HumanDecision
    
    HumanDecision -- Hủy bỏ / Tạo lại --> TriggerAI
    HumanDecision -- Phê duyệt --> ClickApprove[Bấm 'Phê duyệt & Gửi cho Khách hàng']
    
    ClickApprove --> SaveApproved[Lưu nội dung đã duyệt vào ticket_comments]
    SaveApproved --> UpdateTicketStatus[Cập nhật trạng thái Ticket: 'Waiting Customer']
    UpdateTicketStatus --> LogAudit[Ghi nhận vào ai_logs: is_approved = 1]
    LogAudit --> SaveDB
    
    SaveDB --> RefreshUI[Làm mới giao diện & Thông báo thành công]
    RefreshUI --> EndNode
```

---

## 6. Biểu đồ Thực thể Liên kết (Entity Relationship Diagram - ERD)

```mermaid
erDiagram
    USERS ||--o{ TICKETS : "phụ trách"
    USERS ||--o{ TICKET_COMMENTS : "viết"
    USERS ||--o{ AI_LOGS : "kiểm duyệt"
    CUSTOMERS ||--o{ TICKETS : "gửi"
    TICKETS ||--o{ TICKET_COMMENTS : "chứa"
    TICKETS ||--o{ AI_LOGS : "ghi nhận"

    USERS {
        int id PK
        string username UK
        string email UK
        string password_hash
        string full_name
        string role
        datetime created_at
        datetime updated_at
    }

    CUSTOMERS {
        int id PK
        string full_name
        string email UK
        string phone
        string company
        string tier
        datetime created_at
    }

    TICKETS {
        int id PK
        string ticket_number UK
        int customer_id FK
        string title
        text description
        string category
        string priority
        string status
        int assigned_to FK
        datetime created_at
        datetime updated_at
        datetime resolved_at
    }

    TICKET_COMMENTS {
        int id PK
        int ticket_id FK
        int user_id FK
        string author_role
        string author_name
        text content
        boolean is_internal
        datetime created_at
    }

    FAQS {
        int id PK
        string category
        string question
        text answer
        string keywords
        datetime created_at
    }

    AI_LOGS {
        int id PK
        int ticket_id FK
        string action_type
        text input_context
        text raw_ai_output
        text approved_output
        boolean is_approved
        int agent_id FK
        int latency_ms
        datetime created_at
    }
```

