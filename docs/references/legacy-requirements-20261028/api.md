# Đặc tả API hệ thống (REST API Specification) - Đề tài 10

## 1. Authentication APIs
- `GET /login`: Trang đăng nhập
- `POST /login`: Xử lý đăng nhập (`username`, `password`)
- `GET /logout`: Đăng xuất và xóa session

## 2. Ticket APIs
- `GET /tickets`: Lấy danh sách ticket (Hỗ trợ query: `status`, `priority`, `search`, `assigned_to`)
- `POST /tickets/create`: Tạo ticket mới (`customer_id`, `title`, `description`, `category`, `priority`, `assigned_to`)
- `GET /tickets/<id>`: Xem chi tiết ticket, lịch sử trao đổi và khung trợ lý AI
- `POST /tickets/<id>/status`: Cập nhật trạng thái ticket (`New`, `In Progress`, `Waiting Customer`, `Closed`)
- `POST /tickets/<id>/assign`: Gán nhân viên phụ trách ticket
- `POST /tickets/<id>/comment`: Gửi phản hồi bình luận thủ công

## 3. AI Support & Human Gate APIs
- `POST /api/ai/classify`:
  - Request: `{"title": "...", "description": "..."}`
  - Response: `{"category": "...", "suggested_priority": "...", "keywords": [...], "latency_ms": 12}`
- `POST /api/ai/suggest`:
  - Request: `{"ticket_id": 105}`
  - Response: `{"draft_response": "...", "intent": {...}, "matched_faqs": 1, "latency_ms": 150}`
- `POST /api/ai/summarize`:
  - Request: `{"ticket_id": 105}`
  - Response: `{"summary": "• ...\n• ...", "latency_ms": 120}`
- `POST /api/ai/approve-and-send` *(Human Gate)*:
  - Request: `{"ticket_id": 105, "content": "Nội dung sau khi nhân viên đã kiểm duyệt và chỉnh sửa"}`
  - Response: `{"success": true, "message": "Đã duyệt và gửi phản hồi thành công cho khách hàng!"}`
- `POST /api/ai/apply-classification`:
  - Request: `{"ticket_id": 105, "category": "...", "priority": "..."}`
  - Response: `{"success": true, "message": "..."}`

