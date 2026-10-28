# Luồng ticket / Ticket workflow

## Cập nhật máy hiện tại / Upgrade this installation

Database cũ cần các migration còn thiếu; schema hiện tại có 25 bước, gồm migration 007 lưu lịch sử phân công. Không chạy lại `SQLQuery1.sql`. Dừng server rồi chạy trong thư mục project:

Existing installations may have earlier migration versions. The current schema has 25 journaled steps, including migration 007 for ticket assignment history. Do not rerun `SQLQuery1.sql`. Stop the server, then run from the project directory:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\manage-local.ps1 -Action migrate
```

Nhập mật khẩu MySQL root. Runner kiểm tra trước và chỉ áp dụng bước còn thiếu. Nếu có lỗi, giữ thông báo lỗi và xem [hướng dẫn migration](migrations/README.md), không chạy lại khởi tạo.

Enter the MySQL root password. The runner checks first and applies only missing steps. On error, keep the error code and follow the migration guide.

## Tài khoản nhân viên / Agent account

Tạo tài khoản website Agent bằng công cụ quản trị cục bộ:

Create a website Agent account using the local administrative tool:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\manage-local.ps1 -Action create-agent
```

Nhập mật khẩu root, họ tên, email đăng nhập và mật khẩu website nhân viên (12–128 ký tự), rồi xác nhận mật khẩu. Mật khẩu không lưu vào file; backend chỉ lưu bản băm. Công cụ không đổi vai trò hoặc mật khẩu tài khoản có email đã tồn tại. Đây là tài khoản đăng nhập website, khác với tài khoản MySQL `vietincare_app`. Cần ghi nhớ thông tin nhân viên vừa tạo.

Enter the root password, agent name, login email and website password (12–128 characters), then confirm. Passwords are never written to files; the database stores a hash. Existing emails are rejected without role or password changes. Website Agent credentials are distinct from MySQL `vietincare_app` credentials.

## Quản lý tài khoản / Account management

Đăng nhập bằng tài khoản Admin, mở Tổng quan và dùng mục **Quản lý tài khoản** để tìm/lọc, tạo hoặc cập nhật tài khoản Customer, Agent, Supervisor, Admin; thay role, khóa/mở hoặc đặt lại mật khẩu. Mật khẩu mới tối thiểu 12 ký tự. Hệ thống không xóa tài khoản để giữ lịch sử ticket/audit; thay đổi tài khoản sẽ thu hồi các phiên đăng nhập khác. Không thể tự khóa/hạ quyền tài khoản đang dùng hoặc khóa/hạ quyền Admin cuối cùng.

Sign in as Admin and use **Account management** on the Overview page to search/filter, create or update Customer, Agent, Supervisor and Admin accounts; change roles, disable/enable accounts or reset passwords. New passwords must be at least 12 characters. Accounts are not deleted so ticket/audit history remains intact; changes revoke the account's other sessions. The current Admin cannot disable/demote itself or disable/demote the last active Admin.

## Khởi động và demo / Launch and demonstrate

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

Nhập mật khẩu MySQL ứng dụng. Mở **http://localhost:3000/VI/login-vi.html** (không dùng cổng 5500 hoặc host 127.0.0.1 nếu APP_ORIGIN là localhost). Dùng hai hồ sơ trình duyệt hoặc cửa sổ thường/ẩn danh để không ghi đè phiên của nhau.

Enter the MySQL app password. Open **http://localhost:3000/EN/login-en.html**. Use two browser profiles or normal/private windows so customer and agent sessions do not overwrite each other.

1. Customer: đăng nhập → Yêu cầu hỗ trợ → nhập tiêu đề/nội dung → nhận mã `TK-000001` dạng hiển thị. / Sign in → Support tickets → enter subject/description → receive a tracking code.
2. Supervisor: mở ticket Mới → chọn Agent đang hoạt động → Giao yêu cầu. Ticket vẫn ở trạng thái Mới cho tới khi Agent nhận ca. / Open a New ticket → choose an active Agent → Assign. The ticket stays New until the Agent accepts it.
3. Agent: mở ticket được giao → Nhận ca được giao → gửi phản hồi; có thể sửa ưu tiên. / Open the assigned ticket → Accept assigned ticket → send a reply; priority is editable.
4. Agent: Đánh dấu đã giải quyết → Đóng yêu cầu. Phải có phản hồi của nhân viên trước khi giải quyết. / Mark resolved → Close ticket. An agent reply is required before resolution.
5. Customer: Làm mới → đọc phản hồi/trạng thái/lịch sử. F5 vẫn còn dữ liệu. / Refresh → read replies, status and activity. Reloading preserves saved data.

## Phạm vi và quyền / Scope and authorization

- Customer chỉ xem/gửi ticket của mình; có thể bổ sung phản hồi khi Mới/Đang xử lý. / Customers access their own tickets and may reply while New/In progress.
- Agent xem hàng chờ Mới chưa nhận và các ca của mình; chỉ xử lý ca đã nhận. / Agents see unclaimed New tickets plus their own cases; only assigned agents may process a case.
- Supervisor xem toàn bộ ticket, giao/đổi Agent xử lý các ticket Mới/Đang xử lý; lịch sử ghi Agent trước/sau và người thực hiện. Ticket Mới chỉ chuyển sang Đang xử lý khi Agent được giao nhận ca. Admin không được tự động cấp quyền đọc nội dung hỗ trợ. / Supervisors can view all tickets and assign/reassign active Agents on New/In-progress tickets; history records the previous/new Agent and actor. A New ticket moves to In progress only when its assigned Agent accepts it. Admins do not automatically receive support-content access.
- Trạng thái: Mới → Đang xử lý ↔ Chờ khách hàng → Đã đóng. Phản hồi của Customer khi đang chờ sẽ đưa ticket về Đang xử lý; ticket đã đóng chỉ đọc. / Status: New → In progress ↔ Waiting for customer → Closed. A Customer reply while waiting resumes processing; closed tickets are read-only.
- Danh sách có lọc trạng thái và phân trang 30 mục. Bấm Làm mới để nhận thay đổi; không cập nhật realtime. / Lists filter by status and paginate 30 items at a time. Refresh to fetch changes; no real-time updates.
- Mọi ghi ticket dùng transaction, ghi lịch sử/audit và khóa chống nhận đồng thời. Khóa thử lại lưu MySQL; gửi lại cùng khóa/nội dung trả kết quả cũ, nội dung khác trả 409. Trình duyệt giữ khóa của thao tác chưa biết kết quả trong sessionStorage (chỉ hash và UUID, không lưu nội dung). / Mutations use transactions, history/audit records and concurrency locks. MySQL stores retry keys. Repeated identical requests reuse their result; conflicting payloads return 409. The browser retains uncertain retry keys in sessionStorage, storing only hashes and UUIDs.
- Giới hạn: tiêu đề 200 ký tự, nội dung/phản hồi 2.000 ký tự; thời gian hiển thị GMT+7. / Limits: subject 200 characters; description/reply 2,000 characters; timestamps display in GMT+7.
- Agent có thể tạo gợi ý phân loại/ưu tiên/cảm xúc, bản nháp và tóm tắt; AI không tự cập nhật/gửi ticket. Agent phải duyệt và chủ động gửi phản hồi. / Agents can generate classification/priority/sentiment, reply-draft and summary suggestions; AI never updates or sends a ticket itself. Agents must review and explicitly send.
- Vòng đời ticket là Mới → Đang xử lý ↔ Chờ khách hàng → Đã đóng. Sau khi ticket đóng, Customer có thể gửi một đánh giá 1–5 sao và nhận xét tùy chọn. Supervisor có thể lọc ticket theo khách hàng, trạng thái, ưu tiên, thời gian và xem số ticket quá SLA demo (Khẩn cấp 4 giờ, Cao 8 giờ, Trung bình 24 giờ, Thấp 48 giờ). Các luồng này vẫn cần kiểm thử trên MySQL và trình duyệt. Tệp đính kèm chưa triển khai. / The ticket lifecycle is New → In progress ↔ Waiting for customer → Closed. After closure, the Customer can submit one 1–5 star rating with an optional comment. Supervisors can filter by customer, status, priority and date, and view tickets over the demo SLA (Urgent 4h, High 8h, Normal 24h, Low 48h). These flows still require MySQL and browser verification. Attachments remain unimplemented.

## Kiểm thử / Testing

Chạy unit test Python bằng `\.venv\Scripts\python.exe -m pytest`. Chạy migration/lifecycle trên MySQL cách ly bằng `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-mysql.ps1`; script nhập root password ẩn và tự tạo/xóa database ngẫu nhiên, không dùng database nghiệp vụ.

Run unit tests with `\.venv\Scripts\python.exe -m pytest`. Run MySQL migration/lifecycle integration with `scripts/test-mysql.ps1`; it prompts for the root password and creates/removes a random isolated database. Never use the application database for destructive tests or grant database creation privileges to the runtime account.

Bằng chứng đợt triển khai 2026-09-22: xem PROJECT_CHECKLIST.md. Kết quả trên MySQL tạm không có nghĩa migration đã chạy trên database cổng 3306 của bạn.

See PROJECT_CHECKLIST.md for verification dated 2026-09-22. Passing tests on temporary MySQL does not imply migration has been applied to your database on port 3306.
