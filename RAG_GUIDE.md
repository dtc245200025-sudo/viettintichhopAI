# Gemini và kho tri thức / Gemini and knowledge base

## Chạy Gemini (lựa chọn hiện tại)

Dừng backend bằng Ctrl+C. Nếu chưa nâng cấp migration 004, chạy manage-local.ps1 -Action migrate như phần bên dưới. Schema vẫn tổng 22 bước; tích hợp Gemini không thêm migration.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local.ps1 -EnableAI -AIProvider gemini
```

Nhập mật khẩu MySQL vietincare_app, sau đó Google Gemini API Key tại lời nhắc ẩn. Không nhập mật khẩu website ở bước này. Khóa chỉ được truyền cho backend; không gửi khóa trong chat, không lưu khóa thật vào project. Có thể tạo khóa tại [Google AI Studio](https://aistudio.google.com/apikey).

Đăng nhập Admin ở http://localhost:3000/VI/login-vi.html → Kho tri thức → lưu bản nháp → Tạo dữ liệu tìm kiếm → Thử trả lời → Xuất bản cho AI. Sau đó đăng nhập Customer và hỏi trong Lịch sử trò chuyện.

**Nếu tài liệu đã dùng OpenAI:** vector cũ không tương thích với Gemini. Bản nháp: chọn Tạo dữ liệu tìm kiếm để tạo lại. Tài liệu đã xuất bản: Tạo phiên bản mới → lưu → tạo dữ liệu tìm kiếm bằng Gemini → thử → xuất bản. Nội dung và trích nguồn lịch sử được giữ; tài liệu dùng model cũ không tham gia truy xuất Gemini. Không cần xóa database hay chạy lại SQLQuery1.sql.

Mặc định script -EnableAI hiện chọn Gemini. Muốn dùng lại OpenAI, thêm -AIProvider openai. Chạy bằng npm start thì đặt AI_PROVIDER=gemini và GEMINI_API_KEY trong môi trường cục bộ. Không tự chuyển sang nhà cung cấp khác khi lỗi hoặc thiếu khóa. Giao diện VI/EN nêu đúng nhà cung cấp nhận nội dung.

Cấu hình Gemini: gemini-2.5-flash (có thể đổi qua GEMINI_CHAT_MODEL), gemini-embedding-001 768 chiều. Câu hỏi và tài liệu dùng loại embedding query/document riêng. API REST chỉ gửi khóa trong header x-goog-api-key, không trong URL. Chỉ gửi câu hỏi hiện tại và nguồn được chọn; chưa có bộ nhớ đa lượt. Ngưỡng cosine 0,35 vẫn cần đánh giá trên tài liệu thực. Chất lượng, hạn mức và quyền model chưa được xác nhận với khóa thật.

## Gemini setup (English)

Stop the backend and run the Gemini command above. Enter the MySQL application password, then your Google Gemini API key at the hidden prompt. The key stays on the backend. The launcher now defaults to Gemini; use -AIProvider openai for the previous provider. Direct npm startup uses AI_PROVIDER=gemini and GEMINI_API_KEY in your local environment.

As Admin, save a draft, prepare search data, preview and publish, then test as Customer. Existing OpenAI vectors cannot be reused: reindex drafts, or create and index a replacement version for published documents. Old chat citation snapshots remain intact. No new schema migration is required beyond 004 (22 steps). Gemini defaults: gemini-2.5-flash and gemini-embedding-001 with 768 dimensions. Real credentials, quota and answer quality still require a live check.

References: [Google embeddings API](https://ai.google.dev/api/embeddings), [structured responses](https://ai.google.dev/gemini-api/docs/generate-content/structured-output?hl=en).

---

## Luồng OpenAI có sẵn / Existing OpenAI workflow

## Chạy trên Windows

Trong thư mục project, dừng backend cũ bằng Ctrl+C rồi chạy lần lượt:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\manage-local.ps1 -Action migrate
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\manage-local.ps1 -Action create-admin
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local.ps1 -EnableAI -AIProvider openai
```

- Migration 004 thêm 3 bước sau version 3, tổng **22 bước**, giữ dữ liệu cũ. Không chạy lại SQLQuery1.sql. Nếu đã có tài khoản Admin, bỏ qua create-admin; đăng ký công khai không tạo Admin.
- migrate/create-admin hỏi mật khẩu **MySQL root**. create-admin hỏi thêm tên, email và mật khẩu website mới (12–128 ký tự).
- start-local hỏi mật khẩu **MySQL vietincare_app**, rồi hỏi **OpenAI API key** trong ô nhập ẩn. Khóa chỉ nằm trong môi trường tiến trình khi chạy; script khôi phục môi trường khi thoát. Không gửi khóa trong chat hoặc lưu vào project.
- Không thêm -EnableAI thì script chạy chế độ lưu lịch sử, không gọi OpenAI. Khóa API cần quyền truy cập các model đã cấu hình và hạn mức API; tài khoản ChatGPT không thay thế khóa API của ứng dụng.

Mở http://localhost:3000/VI/login-vi.html và đăng nhập **Admin**. Vào **Kho tri thức**:

1. Tạo tài liệu mới: nhập tiêu đề và FAQ/văn bản đã được kiểm tra, tối đa 16.000 ký tự. Lưu bản nháp.
2. Chọn **Tạo dữ liệu tìm kiếm**. Backend chia đoạn và gửi các đoạn đến OpenAI Embeddings; vector và nội dung được lưu trong MySQL.
3. Nhập **Câu hỏi thử**, chọn **Thử trả lời**. Xem nguồn; bản nháp này chưa được dùng cho khách.
4. Chọn **Xuất bản cho AI**. Chỉ tài liệu đã xuất bản và có embedding đúng model/số chiều mới tham gia truy xuất.
5. Khi sửa tài liệu đã xuất bản, chọn **Tạo phiên bản mới**, sửa và lưu bản nháp, tạo lại dữ liệu tìm kiếm, thử rồi xuất bản. Bản cũ chỉ ngừng được sử dụng khi bản mới xuất bản thành công. **Ngừng sử dụng** loại tài liệu khỏi các câu trả lời mới; các trích nguồn cũ vẫn được giữ.

Đăng xuất, đăng nhập **Customer**, mở **Lịch sử trò chuyện** và gửi câu hỏi đầy đủ. Tin nhắn được lưu trước khi gọi AI. Câu trả lời và bản chụp các đoạn nguồn được lưu cùng transaction; mở **Nguồn tham khảo** để kiểm tra. F5 vẫn giữ câu trả lời. Nếu dịch vụ lỗi, dùng **Thử hỏi AI** dưới tin nhắn, không gửi lại nội dung thành tin mới. Phiên đã kết thúc không tạo thêm câu trả lời.

Nên thử đầu tiên với tài liệu mô tả cách dùng chính ứng dụng này, không tự tạo chính sách/lãi suất/phí ngân hàng. Giao diện EN: /EN/knowledge-en.html và /EN/chat-en.html.

## Phạm vi hiện tại

- Chỉ dùng MySQL 8.0.46: KnowledgeBase, KnowledgeChunk, Message, MessageSource và nhật ký chống trùng. Không có kho vector bên ngoài.
- Embedding: text-embedding-3-small, 512 chiều. Sinh câu trả lời: gpt-4.1-mini mặc định; có thể đặt OPENAI_CHAT_MODEL trong môi trường trước khi chạy nếu model hỗ trợ Responses và structured outputs. Không truyền khóa xuống trình duyệt.
- Requests dùng HTTPS cố định tới api.openai.com. Responses đặt store:false, không bật công cụ ngoài. Backend chỉ gửi câu hỏi hiện tại và tối đa 3 đoạn được truy xuất, không gửi toàn bộ lịch sử hoặc hồ sơ tài khoản. Nội dung nguồn dùng để tạo embedding cũng được gửi đến OpenAI. store:false không phải cam kết không có mọi loại lưu giữ phía nhà cung cấp.
- Mỗi đoạn tối đa 800 ký tự Unicode, chồng 100 ký tự. Truy xuất cosine tại backend, ngưỡng ban đầu **0,35**; đây không phải xác suất đúng và chưa được hiệu chỉnh trên bộ câu hỏi thực. Tối đa 1.000 đoạn đã xuất bản cho truy xuất; vượt giới hạn trả lỗi rõ ràng, không cắt bỏ âm thầm.
- Thiếu nguồn phù hợp hoặc model không đưa nguồn hợp lệ: lưu thông báo chưa đủ thông tin và đề nghị ticket. Lỗi provider không lưu phản hồi giả; khách có thể thử lại. Model có thể trả lời sai dù có nguồn, nên cần kiểm tra chất lượng bằng câu hỏi/đáp án chuẩn trước nghiệm thu.
- Khóa MySQL và unique ReplyTo ngăn lưu hai câu trả lời cho một tin nhắn. Gọi lại sau khi đã lưu trả kết quả cũ. Nếu tiến trình chết trước khi lưu hoặc lỗi mạng phía provider, lần thử lại có thể tạo thêm cuộc gọi API tính phí; không cam kết đúng một lần tính phí.
- Tối đa 4 lượt sinh câu trả lời đồng thời trên một tiến trình. Timeout mỗi cuộc gọi OpenAI 30 giây; giao diện chờ tối đa 70 giây. Chưa đo mục tiêu p95 ≤ 5 giây.
- Chưa có bộ nhớ hội thoại đa lượt cho mô hình, tải PDF/DOCX, tự phân loại ticket, chuyển giao chat, báo cáo hoặc đánh giá CSAT.

## English

Stop the backend and run the commands above. Migration 004 brings the journal to **22 steps** without reinitializing the database. Skip create-admin if an administrator already exists. Administrative commands use the MySQL root password; startup uses the vietincare_app password followed by a hidden OpenAI API key prompt. The key is kept in the process environment and never sent to the browser. Without -EnableAI, the launcher disables AI calls.

As Admin, open **Knowledge base**: save a draft, prepare search data, test a question, then publish. Published content is immutable; create a new version to revise it. Publishing the replacement atomically unpublishes its predecessor. Unpublished sources are excluded from future answers while historical citation snapshots remain intact.

As Customer, open **Conversations** and ask a complete question. The message is saved first; then the backend retrieves published chunks from MySQL and asks OpenAI for a sourced answer. Review **Sources**, reload, and verify persistence. Provider failure leaves the original message saved; use **Retry AI**. Ended sessions remain read-only.

The defaults are text-embedding-3-small with 512 dimensions and gpt-4.1-mini through Responses with store:false. Current questions and selected excerpts are sent to OpenAI; the full chat history and account profile are not sent. Search indexing also sends document chunks. The provisional cosine threshold is 0.35, not a probability or measured confidence. The current limit is 1,000 published chunks, three retrieved sources and four concurrent generations per process. Actual provider quality, latency, costs and account access require a live test with your API key. No real OpenAI request was made during the isolated implementation tests.

## Tài liệu API đã đối chiếu / API references

- [OpenAI Embeddings](https://developers.openai.com/api/docs/guides/embeddings)
- [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini)

Kết quả kiểm tra cụ thể nằm trong PROJECT_CHECKLIST.md. Unit tests dùng transport giả; integration/browser tests dùng MySQL thật và provider giả. Không coi chúng là kiểm thử chất lượng AI thật.
