# Tài liệu thiết kế cơ sở dữ liệu (Database Design Specification) - Đề tài 10

## 1. Mô hình thực thể và quan hệ (Entity-Relationship Model)

### Sơ đồ thực thể quan hệ (ERD - Mermaid)

```mermaid
erDiagram
    USERS ||--o{ TICKETS : "is assigned to"
    USERS ||--o{ TICKET_COMMENTS : "writes"
    USERS ||--o{ AI_LOGS : "reviews"
    CUSTOMERS ||--o{ TICKETS : "creates"
    TICKETS ||--o{ TICKET_COMMENTS : "contains"
    TICKETS ||--o{ AI_LOGS : "triggers"

    USERS {
        int id PK
        string username UK
        string email UK
        string password_hash
        string full_name
        string role
        timestamp created_at
        timestamp updated_at
    }

    CUSTOMERS {
        int id PK
        string full_name
        string email UK
        string phone
        string company
        string tier
        timestamp created_at
        timestamp updated_at
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
        timestamp created_at
        timestamp updated_at
        timestamp resolved_at
    }

    TICKET_COMMENTS {
        int id PK
        int ticket_id FK
        int user_id FK
        string author_role
        string author_name
        text content
        boolean is_internal
        timestamp created_at
    }

    FAQS {
        int id PK
        string category
        string question
        text answer
        string keywords
        timestamp created_at
        timestamp updated_at
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
        timestamp created_at
    }
```

## 2. Chuẩn hóa dữ liệu (Normalization)
- **1NF**: Mọi thuộc tính đều mang giá trị nguyên tử (atomic), không chứa mảng hay chuỗi lặp không chuẩn.
- **2NF**: Mọi thuộc tính không khóa đều phụ thuộc hoàn toàn vào khóa chính của từng bảng.
- **3NF**: Không có sự phụ thuộc bắc cầu giữa các thuộc tính không khóa (ví dụ thông tin công ty khách hàng gắn với `customers`, không lặp lại trong `tickets`).

## 3. Ràng buộc toàn vẹn và Chỉ mục (Constraints & Indexes)
1. **Khóa ngoại (Foreign Keys)**:
   - `tickets.customer_id` -> `customers.id` (ON DELETE CASCADE)
   - `tickets.assigned_to` -> `users.id` (ON DELETE SET NULL)
   - `ticket_comments.ticket_id` -> `tickets.id` (ON DELETE CASCADE)
   - `ai_logs.ticket_id` -> `tickets.id` (ON DELETE SET NULL)
2. **Kiểm tra hợp lệ (CHECK Constraints)**:
   - `users.role` IN (`admin`, `lead`, `agent`)
   - `customers.tier` IN (`Standard`, `VIP`)
   - `tickets.priority` IN (`Low`, `Medium`, `High`, `Urgent`)
   - `tickets.status` IN (`New`, `In Progress`, `Waiting Customer`, `Closed`)
3. **Chỉ mục (Indexes)**:
   - Tối ưu hóa truy vấn tìm kiếm lọc ticket theo `status`, `priority`, `customer_id`, `assigned_to`.
   - Tối ưu hóa truy vấn chuỗi trao đổi theo `ticket_id`.

