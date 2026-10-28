# Lịch sử hội thoại / Conversation history

## Tiếng Việt

Phần này dành cho Customer đã đăng nhập: tạo hội thoại bằng tin nhắn đầu tiên, lưu tin nhắn vào MySQL, mở lại lịch sử, yêu cầu Agent hỗ trợ và kết thúc phiên. Agent nhận hàng chờ tại trang tổng quan, phản hồi, tạo tóm tắt và kết thúc lượt chuyển giao.

**Chế độ không bật -EnableAI vẫn lưu lịch sử và cho phép Agent hỗ trợ.** Để dùng câu trả lời hoặc tóm tắt Gemini/OpenAI, làm theo RAG_GUIDE.md.

Trong thư mục project, dừng backend rồi nâng cấp database hiện có:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\manage-local.ps1 -Action migrate
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

Migration 003 thêm tiêu đề/index cho ChatSession, index Message và ChatRequest. Migration 008 hoàn thiện vòng đời chuyển giao, lưu tóm tắt và cấu hình vận hành; migration 009 chuẩn hóa trạng thái ticket. Các migration hiện hành (001–009) có **33 bước**; `manage-local.ps1 -Action migrate` chỉ chạy bước còn thiếu, không chạy lại SQLQuery1.sql. Công cụ hỏi mật khẩu MySQL root khi migrate; script khởi động hỏi mật khẩu vietincare_app. Không nhập mật khẩu website vào các lời nhắc MySQL.

Đăng nhập Customer tại http://localhost:3000/VI/login-vi.html, mở **Lịch sử trò chuyện**. Tài khoản nhân viên không được đọc lịch sử riêng của khách qua trang này. Tạo tin nhắn thử, tải lại trang, mở hội thoại cũ và kết thúc phiên; phiên đã kết thúc chỉ được xem. Giao diện EN ở /EN/chat-en.html. Ctrl+F5 nếu trình duyệt giữ tài nguyên cũ.

Hộp chat nổi ở trang chủ VI/EN dùng cùng API này: chỉ Customer đã đăng nhập mới gửi được; tin nhắn được lưu vào MySQL rồi route RAG gọi Gemini và trả nguồn. Hộp chat không gọi Gemini trực tiếp từ trình duyệt và không chứa khóa API. Nếu chưa đăng nhập, hộp chat hướng dẫn đăng nhập thay vì tạo câu trả lời mẫu. Liên kết dưới phản hồi mở đúng hội thoại đã lưu để xem lại hoặc thử hỏi AI khi provider lỗi.

Tin nhắn chỉ được báo đã lưu sau khi MySQL ghi thành công. Lỗi mạng giữ nội dung đang nhập và khóa chống trùng để thử lại; khóa/hash được lưu trong sessionStorage, không lưu nội dung chat ở đó. Tải lại trang sẽ mất nội dung chưa gửi. Khi đã lưu nhưng tải lịch sử lỗi, nhấn Làm mới, không gửi lại nội dung như một tin mới. Khi bật AI, giao diện phân biệt chờ lưu và chờ câu trả lời.

## English

Authenticated Customers can create a conversation, request a support agent, continue messaging, revisit history and end a session. Agents can accept one pending handover, reply, generate a redacted AI summary and finish the handover; Supervisors can monitor the queue.

**Without -EnableAI, this is history-only mode.** To enable sourced Gemini/OpenAI responses, follow RAG_GUIDE.md. Live agent chat remains pending; support tickets are available.

Stop the backend, run the two PowerShell commands above, then sign in as a Customer at http://localhost:3000/EN/login-en.html and open **Conversations**. Migration 003 adds three steps, bringing the v3 total to 19; the current v4 total is **22**; existing data is retained. Do not rerun the initializer on an existing database. Migration uses the MySQL root password; startup uses the vietincare_app password. Neither prompt asks for a website password.

Reload and revisit a conversation to verify persistence. Ended conversations are read-only. Each write requires a per-user retry key committed with the change. Network errors preserve the typed text and retry key for retrying; sessionStorage stores only keys/hashes, not message text. Reloading discards unsent text. If a save succeeds but refreshing history fails, use Refresh. With AI enabled, separate messages indicate saving and waiting for an AI response.

The VI/EN landing-page chat popup uses the same authenticated flow. A signed-in Customer message is stored in MySQL before the RAG route asks Gemini and returns published sources. The browser never receives the Gemini key. Signed-out users receive a sign-in instruction instead of a canned answer, and saved conversations can be opened from the response link.

## Kiểm thử / Tests

Run unit tests with `\.venv\Scripts\python.exe -m pytest`. For database-backed migration and API checks, use `scripts/test-mysql.ps1`; it prompts for the MySQL root password and creates/removes a uniquely named test database. Never point the integration suite at the application database.

## Cập nhật RAG / RAG update

AI/RAG hiện dùng Gemini/OpenAI và kho tri thức Admin; migration 008 đưa tổng số bước lên 28. Dùng `start-local.ps1 -EnableAI -AIProvider gemini` (hoặc `openai`) để nhập khóa ẩn. Tóm tắt chuyển giao cần AI được cấu hình; nhắn tin và chuyển giao vẫn hoạt động khi AI tắt. Xem [RAG_GUIDE.md](RAG_GUIDE.md).

Gemini/OpenAI integration uses Python provider adapters and the current 23-step migration set. Start with `start-local.ps1 -EnableAI -AIProvider gemini` (or `openai`) to enter a hidden key. Without a key, history-only mode remains available.
