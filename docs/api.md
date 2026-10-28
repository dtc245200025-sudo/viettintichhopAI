# API hiện hành

Mọi mutation yêu cầu session hợp lệ, `Origin` đúng, `X-Vietincare-Request: 1`, JSON và idempotency key ở các luồng hỗ trợ chống gửi trùng.

| Nhóm | Endpoint chính | Quyền |
|---|---|---|
| Auth | `/api/auth/register`, `/login`, `/logout`, `/me`, `/otp/*` | Public/session |
| Accounts | `/api/admin/users`, `/api/admin/settings`, `/api/admin/audit-logs` | Admin |
| Customers | `/api/customers`, `/api/customers/{id}` | Admin, Supervisor |
| Tickets | `/api/tickets`, `/{id}`, `/claim`, `/assign`, `/replies`, `/status`, `/priority`, `/details`, `/evaluation` | Theo vai trò/sở hữu |
| Ticket AI | `/api/tickets/{id}/ai-assist`, `/ai-assist/{analysisId}/review` | Agent được giao |
| Reports | `/api/reports/summary` | Supervisor |
| Chat | `/api/chats`, `/{id}/messages`, `/answer`, `/close` | Customer sở hữu |
| Handover | `/api/chats/{id}/handover`, `/api/handovers/*` | Customer/Agent/Supervisor |
| Knowledge | `/api/knowledge/*` | Admin |
| Health | `/api/health` | Public, read-only |

Không có `/api/ai/classify`. Ticket mới kích hoạt tác vụ tự phân loại; `/ai-assist` vẫn là nháp/phân tích do Agent yêu cầu. Lỗi AI không xóa Ticket.

## Bổ sung nghiệm thu 29/10/2026

| Endpoint | Quyền/hành vi |
|---|---|
| `POST /api/presence` | Agent heartbeat; online trong 2 phút và phải có session hợp lệ |
| `GET /api/supervisor/alerts` | Supervisor xem cảnh báo chưa xác nhận |
| `POST /api/supervisor/alerts/{id}/acknowledge` | Supervisor xác nhận, ghi audit |
| `GET /api/supervisor/automation` | Ticket Mới, chưa gán và cần phân loại/thử lại |
| `POST /api/tickets/{id}/automation/retry` | Supervisor chủ động chạy lại; không đè ca đã nhận/sửa |
| `POST /api/chats/{id}/evaluation` | Customer chủ sở hữu; chat đã kết thúc; một lần, 1–5 sao |
| `GET /api/tickets/customers` | Agent chọn Customer đang active để tạo hộ; chỉ tên/ID |

`POST /api/tickets` nhận tùy chọn `categoryId`, `sessionId`; Agent phải gửi `customerId`, Customer không được chọn ID của người khác. Phiên chat phải đúng khách hàng. `POST .../replies` và `POST .../messages` nhận `correctionOf`; tạo bản ghi mới, kiểm tra tác giả/đối tượng, không cập nhật bản gốc.

`GET /api/handovers/{id}?before=...` trả `messages` cũ→mới trong trang, `next` để tải phần trước (50 tin/trang), gồm cảm xúc nếu có. `GET /api/chats/{id}` có `summary` và `evaluation`. `GET /api/tickets/{id}` có `automation` cho nhân viên. Dashboard có thêm `ticketsByPriority`.

Settings allowlist: `rag.threshold` 0–1, `ai.timeout_seconds` 5–120, `auth.session_hours` 1–24 (ảnh hưởng phiên đăng nhập mới). Free-text API trả về được che secret; trường liên hệ có quyền truy cập vẫn giữ để chỉnh sửa. Lỗi khóa đồng thời trả 409 `CONCURRENT_UPDATE`, lỗi database trả 503 `DATABASE_UNAVAILABLE`, không trả SQL/credential cho client.
