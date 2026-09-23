# VietinCare AI

## Theo dõi tiến độ

Xem [checklist công việc](PROJECT_CHECKLIST.md) để biết phần đã làm, phần còn thiếu và thứ tự ưu tiên. Quy tắc đọc, tự cập nhật checklist và nhắc tiến độ sau mỗi đợt sửa được lưu trong [AGENTS.md](AGENTS.md).

## Phạm vi phiên bản 1.1

Xem [phạm vi và tiêu chí nghiệm thu](PROJECT_SCOPE.md). Bản cốt lõi gồm web VI/EN, bốn vai trò, chat RAG, ticket, chuyển giao, CSAT, quản lý FAQ, dashboard cơ bản, audit log và cấu hình. Backend Express đã có xác thực/session/phân quyền dùng MySQL; luồng ticket VI/EN đã có tạo, nhận, phản hồi, giải quyết/đóng và lịch sử. Đã có chat lưu lịch sử, quản trị tri thức và mã tích hợp Gemini/OpenAI RAG; báo cáo/chuyển giao chưa triển khai, AI thật chưa kiểm chứng. Log người dùng ngày 2026-09-21 xác nhận 10/10 test đạt và luồng đăng nhập/giữ phiên/đăng xuất trên giao diện VI hoạt động.

## Ticket (2026-09-22)

Xem [hướng dẫn nâng cấp và chạy ticket / upgrade and ticket workflow](TICKET_GUIDE.md). Database cũ cần chạy migration mới nhất để đạt 22 bước, sau đó khởi động lại server. Công cụ tạo Agent và các bước demo Customer → Agent → Customer nằm trong hướng dẫn. Đã kiểm thử trên MySQL tạm; chưa áp dụng migration mới lên database của người dùng.

Ticket creation, claim, replies, resolution/closure and history are implemented in VI/EN. Apply the new migration (16 total steps) and restart before use. See the guide for local Agent provisioning and the demo workflow. The new migration has been tested on temporary MySQL but has not yet been applied to the user's database.

## Chạy backend trên Windows / Run locally on Windows

Cần Node.js 24+, MySQL Community Server 8.0.46 và các dependency (`npm.cmd ci` khi cài mới). Database hiện tại trên máy người dùng đã khởi tạo và migration báo `current, steps: 15`; không chạy lại script khởi tạo.

Requires Node.js 24+, MySQL Community Server 8.0.46 and dependencies (`npm.cmd ci` on a fresh installation). The current local database is already initialized and migrated; do not initialize it again.

### Tạo tài khoản ứng dụng một lần / One-time app account setup

Từ PowerShell trong thư mục project, dừng server bằng Ctrl+C nếu đang chạy, rồi thực hiện:

From PowerShell in the project directory, stop the running server with Ctrl+C, then run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-db-user.ps1
```

Công cụ hỏi mật khẩu root, mật khẩu mới riêng cho ứng dụng (ít nhất 12 ký tự) và xác nhận mật khẩu mới. Chỉ gõ mật khẩu ở ô nhập ẩn, không thay lời nhắc bằng mật khẩu. Ghi nhớ mật khẩu ứng dụng bằng trình quản lý mật khẩu. Script không lưu mật khẩu vào project. ExecutionPolicy chỉ áp dụng cho tiến trình này, không đổi chính sách máy.

The tool prompts for the root password, a new app password (12+ characters), then confirmation. Type passwords only at the hidden prompts. Keep the app password in your password manager; scripts do not save it in the project. The execution policy applies only to this process.

Đích cố định: MySQL 127.0.0.1:3306, database `qlkhviettin`, tài khoản `vietincare_app`@`127.0.0.1`. Cấp SELECT/INSERT/UPDATE/DELETE chỉ trong database này; không cấp quyền thay đổi cấu trúc, tạo database hay quản lý tài khoản. Công cụ kiểm tra đăng nhập bằng tài khoản mới và đọc AuthSession. Nếu đã có tài khoản cùng tên ở bất kỳ host nào, công cụ dừng và báo `APP_USER_ALREADY_EXISTS`, không đổi mật khẩu hoặc quyền tài khoản cũ. Nếu lỗi sau khi tạo tài khoản, cần kiểm tra quyền trước khi thử lại; công cụ không tự xóa tài khoản.

Fixed target: MySQL 127.0.0.1:3306, database `qlkhviettin`, account `vietincare_app`@`127.0.0.1`. Only database SELECT/INSERT/UPDATE/DELETE privileges are granted. Setup verifies a new connection and an AuthSession read. Existing same-name accounts stop setup without password or permission changes. A failure after account creation requires inspection before retrying; no automatic account deletion is performed.

### Mỗi lần chạy / Each launch

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

Nhập mật khẩu **ứng dụng**, giữ cửa sổ mở và truy cập http://localhost:3000. Ctrl+C để dừng. Script dành cho phát triển cục bộ; tự đặt DB_USER, host, port và origin để không dùng nhầm biến root còn trong cửa sổ cũ. Không cần file .env. Đăng ký tài khoản website khác với tài khoản MySQL ứng dụng.

Enter the **app database password**, keep the window open and visit http://localhost:3000. Stop with Ctrl+C. This local development launcher explicitly sets the app user and connection settings; no .env is needed. Website users are separate from the MySQL app account.

Migration (`npm.cmd run db:check`, `npm.cmd run db:migrate`) cần tài khoản quản trị trong phiên riêng. Test tích hợp (`$env:RUN_MYSQL_TESTS="1"`, `npm.cmd test`) cần quyền tạo/xóa database thử. Không cấp thêm quyền này cho tài khoản ứng dụng. Tài khoản ứng dụng mới và script chạy phải được kiểm tra thực tế sau thiết lập; kết quả 10 test trước đây dùng tài khoản quản trị, không chứng minh quyền tài khoản mới.

Run migrations and integration tests with an administrative connection in a separate session. Integration tests create and remove an isolated test database. Do not grant those privileges to the runtime app user. The earlier 10 passing tests used an administrative connection and do not validate the new runtime account.

Copilot, tóm tắt, tải tài liệu/tệp đính kèm, OTP/SSO, NPS, tích hợp ngân hàng thật và hạ tầng lớn thuộc mở rộng. Không dùng các mục này để ghi nhận bản cốt lõi đã hoàn thành.

## Cấu hình MySQL

Project thống nhất dùng **MySQL Community Server 8.0.46** cho dữ liệu nghiệp vụ và dữ liệu phục vụ RAG. Tất cả bảng dùng InnoDB, bộ ký tự `utf8mb4` và collation `utf8mb4_0900_ai_ci`.

- Script khởi tạo: `SQLQuery1.sql`.
- Tên database: `QLKHViettin`.
- Script khởi tạo có 15 bảng; migration `001_auth_and_support.sql` bổ sung bảng và ràng buộc cho xác thực/hỗ trợ, với nhật ký `SchemaMigration`.
- Khóa tự tăng dùng `INT AUTO_INCREMENT`; văn bản dùng `VARCHAR` hoặc `LONGTEXT`; thời gian dùng `DATETIME(3)`.
- Mỗi kết nối backend phải đặt `SET NAMES utf8mb4` và `SET SESSION time_zone = '+00:00'`. Thời gian lưu theo UTC; giao diện chuyển sang giờ Việt Nam.
- Giữ nguyên cách viết tên bảng trong script khi truy vấn, đặc biệt khi triển khai trên Linux.

## Khởi tạo

Mở `SQLQuery1.sql` bằng MySQL Workbench, kết nối máy chủ MySQL và chạy toàn bộ script trên môi trường mới. Tài khoản thực thi cần quyền tạo database và bảng.

Hoặc mở MySQL CLI từ thư mục project:

```text
mysql --default-character-set=utf8mb4 -u root -p
```

Sau khi nhập mật khẩu:

```sql
SOURCE SQLQuery1.sql;
```

Script không xóa bảng hay dữ liệu. `CREATE DATABASE IF NOT EXISTS` chỉ xử lý việc database đã tồn tại; các lệnh tạo bảng vẫn yêu cầu bảng chưa tồn tại. Khi cập nhật database đã có dữ liệu, cần một migration riêng, không chạy lại script khởi tạo để thay đổi cấu trúc.

## Thiết kế RAG dùng MySQL

`KnowledgeBase` lưu tài liệu. `KnowledgeChunk` lưu nội dung từng đoạn, thứ tự, embedding dạng JSON, tên mô hình, số chiều và thời gian tạo. Backend tạo embedding, kiểm tra các phần tử là số, chọn các đoạn từ tài liệu đã xuất bản, rồi tính cosine similarity và lấy các đoạn phù hợp để tạo phản hồi. Chỉ so sánh embedding cùng mô hình và cùng số chiều; vector có độ dài bằng 0 phải được xử lý trước khi tính cosine.

Thiết kế này dành cho quy mô đồ án với tập tài liệu nhỏ. MySQL lưu dữ liệu; phép tìm kiếm tương đồng dự kiến thực hiện ở backend, không giả định MySQL 8.0 có chỉ mục vector tích hợp. Luồng RAG đã được nối vào backend; kiểm thử hiện dùng provider giả, chưa xác nhận API OpenAI thật.

## Tài liệu

- `02_ban2.docx`: thu thập yêu cầu và phạm vi đồ án phiên bản 1.1.
- `03_ban2.docx`: đặc tả use case, phạm vi cốt lõi/mở rộng và RAG dùng MySQL.
- `04_ban1.docx`: thiết kế lớp, quan hệ và các phần cần migration trên MySQL.
- `PROJECT_SCOPE.md`: quy tắc dùng chung và tiêu chí nghiệm thu.
- Chưa tìm thấy `05_GenAI_SoftwareDevelopment_functional-testing.docx` trong thư mục hiện tại. Kết quả kiểm thử cũ không được dùng làm bằng chứng cho phiên bản mới.

Các Word đã sửa nội dung ngày 2026-09-21; chưa xác nhận bố cục bằng render. Bản trước sửa lưu tại `.mysql-sync/scope-before-2026-09-21.zip`. Script khởi tạo có 15 bảng; migration xác thực/hỗ trợ đã được xác nhận current theo log người dùng. Toàn bộ thiết kế đích vẫn cần đối chiếu và kiểm thử nghiệp vụ.

Tài liệu cú pháp chính thức: [CREATE TABLE](https://dev.mysql.com/doc/refman/8.0/en/create-table.html), [JSON](https://dev.mysql.com/doc/refman/8.0/en/json.html).

## Lịch sử hội thoại / Conversation history

Đã có lưu/tải lại/kết thúc hội thoại Customer bằng MySQL, UI VI/EN và chống gửi trùng. Nâng cấp migration mới nhất (004, tổng 22 bước) trước khi khởi động. Hướng dẫn: [CHAT_GUIDE.md](CHAT_GUIDE.md). AI/RAG có thể bật bằng -EnableAI theo RAG_GUIDE.md; chuyển giao chat chưa nối.

Customer conversations now persist in MySQL, with VI/EN history, ending sessions and safe retries. Apply the latest migration (004, 22 total steps) before starting. See [CHAT_GUIDE.md](CHAT_GUIDE.md). Gemini RAG can be enabled with -EnableAI -AIProvider gemini (OpenAI remains available with -AIProvider openai); live agent handover remains pending.

## Gemini/OpenAI và kho tri thức / Gemini/OpenAI and knowledge base

Đã có giao diện Admin VI/EN nhập văn bản, tạo embedding, thử câu hỏi, xuất bản/ngừng dùng và tạo phiên bản mới; chat Customer nối Responses API với nguồn lưu trong MySQL. Dùng migration mới nhất (004, tổng 22 bước), tạo Admin nếu cần và chạy start-local.ps1 -EnableAI để nhập khóa ẩn. Hướng dẫn: [RAG_GUIDE.md](RAG_GUIDE.md). Không có khóa thật trong project; kiểm thử hiện dùng provider giả, chưa xác nhận API thật hoặc chất lượng câu trả lời.

Admin knowledge management and sourced Customer chat are implemented. Apply migration 004 (22 total steps), provision an Admin if needed and launch with -EnableAI for a hidden key prompt. See [RAG_GUIDE.md](RAG_GUIDE.md). Current tests use a fake provider; real OpenAI access and answer quality remain unverified.

Gemini: chạy `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local.ps1 -EnableAI -AIProvider gemini`, nhập khóa ẩn. Tài liệu dùng embedding OpenAI cần tạo dữ liệu tìm kiếm lại bằng Gemini; với tài liệu xuất bản, tạo phiên bản mới. Xem RAG_GUIDE.md. / Enter your Gemini key at startup; reindex drafts or publish replacement versions of existing OpenAI documents.
