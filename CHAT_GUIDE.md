# Lịch sử hội thoại / Conversation history

## Tiếng Việt

Phần này dành cho Customer đã đăng nhập: tạo hội thoại bằng tin nhắn đầu tiên, lưu tin nhắn vào MySQL, mở lại lịch sử, tải tin cũ và kết thúc phiên. Agent tiếp tục xử lý ở trang ticket; chuyển giao chat chưa triển khai.

**Chế độ không bật -EnableAI chỉ lưu lịch sử.** Để dùng câu trả lời Gemini/OpenAI có nguồn, làm theo RAG_GUIDE.md. Nhân viên trực trong hội thoại chưa triển khai; có liên kết tạo ticket.

Trong thư mục project, dừng backend rồi nâng cấp database hiện có:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\manage-local.ps1 -Action migrate
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

Migration 003 thêm tiêu đề/index cho ChatSession, index Message và ChatRequest. Thêm 3 bước sau version 2, tổng 19 bước ở mốc version 3; phiên bản hiện tại có **22 bước** sau migration 004. Không chạy lại SQLQuery1.sql trên dữ liệu hiện có. Công cụ hỏi mật khẩu MySQL root khi migrate; script khởi động hỏi mật khẩu vietincare_app. Không nhập mật khẩu website vào các lời nhắc MySQL.

Đăng nhập Customer tại http://localhost:3000/VI/login-vi.html, mở **Lịch sử trò chuyện**. Tài khoản nhân viên không được đọc lịch sử riêng của khách qua trang này. Tạo tin nhắn thử, tải lại trang, mở hội thoại cũ và kết thúc phiên; phiên đã kết thúc chỉ được xem. Giao diện EN ở /EN/chat-en.html. Ctrl+F5 nếu trình duyệt giữ tài nguyên cũ.

Tin nhắn chỉ được báo đã lưu sau khi MySQL ghi thành công. Lỗi mạng giữ nội dung đang nhập và khóa chống trùng để thử lại; khóa/hash được lưu trong sessionStorage, không lưu nội dung chat ở đó. Tải lại trang sẽ mất nội dung chưa gửi. Khi đã lưu nhưng tải lịch sử lỗi, nhấn Làm mới, không gửi lại nội dung như một tin mới. Khi bật AI, giao diện phân biệt chờ lưu và chờ câu trả lời.

## English

Authenticated Customers can create a conversation with their first message, save messages in MySQL, revisit history, load older messages and end a session. Agents continue using tickets; live chat handover is not implemented.

**Without -EnableAI, this is history-only mode.** To enable sourced Gemini/OpenAI responses, follow RAG_GUIDE.md. Live agent chat remains pending; support tickets are available.

Stop the backend, run the two PowerShell commands above, then sign in as a Customer at http://localhost:3000/EN/login-en.html and open **Conversations**. Migration 003 adds three steps, bringing the v3 total to 19; the current v4 total is **22**; existing data is retained. Do not rerun the initializer on an existing database. Migration uses the MySQL root password; startup uses the vietincare_app password. Neither prompt asks for a website password.

Reload and revisit a conversation to verify persistence. Ended conversations are read-only. Each write requires a per-user retry key committed with the change. Network errors preserve the typed text and retry key for retrying; sessionStorage stores only keys/hashes, not message text. Reloading discards unsent text. If a save succeeds but refreshing history fails, use Refresh. With AI enabled, separate messages indicate saving and waiting for an AI response.

## Kiểm thử / Tests

With an isolated MySQL 8.0.46 test server and administrator credentials supplied through environment variables, set RUN_MYSQL_TESTS=1 and run npm.cmd test. Tests create and remove uniquely named temporary databases/accounts; do not use a production test target. See PROJECT_CHECKLIST.md for actual execution results and unverified deployment steps.

## Cập nhật RAG / RAG update

Phần mô tả AI chưa nối ở trên là mốc triển khai lịch sử trước đó. Hiện đã bổ sung tích hợp Gemini/OpenAI, bật bằng -EnableAI -AIProvider gemini (hoặc openai) sau migration 004 (22 bước), cùng kho tri thức Admin. Xem [RAG_GUIDE.md](RAG_GUIDE.md). Khi không bật/cấu hình khóa, chế độ lưu lịch sử vẫn hoạt động.

The earlier AI-not-connected notes describe the history-only milestone. Gemini/OpenAI integration is now available with -EnableAI -AIProvider gemini (or openai) and migration 004 (22 steps). See RAG_GUIDE.md. Without a key, history-only mode remains available.
