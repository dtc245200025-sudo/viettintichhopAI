# Luồng ticket / Ticket workflow

## Cập nhật máy hiện tại / Upgrade this installation

Database của bạn đã có version 1 (15 bước). Ticket cần thêm version 2 (1 bước). Không chạy lại `SQLQuery1.sql`. Dừng server với Ctrl+C rồi chạy trong thư mục project:

Your database already has version 1 (15 steps). Tickets require version 2 (one additional step). Do not rerun `SQLQuery1.sql`. Stop the server with Ctrl+C, then run from the project directory:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\manage-local.ps1 -Action migrate
```

Nhập mật khẩu MySQL root. Kết quả lần đầu dự kiến `ready, remaining: 1`, rồi `applied, steps: 16`. Nếu có lỗi, giữ thông báo lỗi và xem [hướng dẫn migration](migrations/README.md), không chạy lại khởi tạo.

Enter the MySQL root password. The first upgrade should report `ready, remaining: 1`, then `applied, steps: 16`. On error, keep the error code and follow the migration guide.

## Tài khoản nhân viên / Agent account

Tạo tài khoản website Agent bằng công cụ quản trị cục bộ:

Create a website Agent account using the local administrative tool:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\manage-local.ps1 -Action create-agent
```

Nhập mật khẩu root, họ tên, email đăng nhập và mật khẩu website nhân viên (12–128 ký tự), rồi xác nhận mật khẩu. Mật khẩu không lưu vào file; backend chỉ lưu bản băm. Công cụ không đổi vai trò hoặc mật khẩu tài khoản có email đã tồn tại. Đây là tài khoản đăng nhập website, khác với tài khoản MySQL `vietincare_app`. Cần ghi nhớ thông tin nhân viên vừa tạo.

Enter the root password, agent name, login email and website password (12–128 characters), then confirm. Passwords are never written to files; the database stores a hash. Existing emails are rejected without role or password changes. Website Agent credentials are distinct from MySQL `vietincare_app` credentials.

## Khởi động và demo / Launch and demonstrate

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

Nhập mật khẩu MySQL ứng dụng. Mở **http://localhost:3000/VI/login-vi.html** (không dùng cổng 5500 hoặc host 127.0.0.1 nếu APP_ORIGIN là localhost). Dùng hai hồ sơ trình duyệt hoặc cửa sổ thường/ẩn danh để không ghi đè phiên của nhau.

Enter the MySQL app password. Open **http://localhost:3000/EN/login-en.html**. Use two browser profiles or normal/private windows so customer and agent sessions do not overwrite each other.

1. Customer: đăng nhập → Yêu cầu hỗ trợ → nhập tiêu đề/nội dung → nhận mã `TK-000001` dạng hiển thị. / Sign in → Support tickets → enter subject/description → receive a tracking code.
2. Agent: đăng nhập → Yêu cầu hỗ trợ → chọn ca Mới → Nhận yêu cầu → gửi phản hồi; có thể sửa ưu tiên. / Sign in → Support tickets → claim a New ticket → send a reply; priority is editable.
3. Agent: Đánh dấu đã giải quyết → Đóng yêu cầu. Phải có phản hồi của nhân viên trước khi giải quyết. / Mark resolved → Close ticket. An agent reply is required before resolution.
4. Customer: Làm mới → đọc phản hồi/trạng thái/lịch sử. F5 vẫn còn dữ liệu. / Refresh → read replies, status and activity. Reloading preserves saved data.

## Phạm vi và quyền / Scope and authorization

- Customer chỉ xem/gửi ticket của mình; có thể bổ sung phản hồi khi Mới/Đang xử lý. / Customers access their own tickets and may reply while New/In progress.
- Agent xem hàng chờ Mới chưa nhận và các ca của mình; chỉ xử lý ca đã nhận. / Agents see unclaimed New tickets plus their own cases; only assigned agents may process a case.
- Supervisor xem toàn bộ ticket; phân công lại chưa thuộc đợt triển khai này. Admin không được tự động cấp quyền đọc nội dung hỗ trợ. / Supervisors have read access; reassignment is not implemented in this increment. Admins do not automatically receive support-content access.
- Trạng thái: Mới → Đang xử lý → Đã giải quyết → Đã đóng. Ca đã giải quyết/đóng chỉ đọc; mở lại là mở rộng. / Status: New → In progress → Resolved → Closed. Completed tickets are read-only; reopening is out of scope.
- Danh sách có lọc trạng thái và phân trang 30 mục. Bấm Làm mới để nhận thay đổi; không cập nhật realtime. / Lists filter by status and paginate 30 items at a time. Refresh to fetch changes; no real-time updates.
- Mọi ghi ticket dùng transaction, ghi lịch sử/audit và khóa chống nhận đồng thời. Khóa thử lại lưu MySQL; gửi lại cùng khóa/nội dung trả kết quả cũ, nội dung khác trả 409. Trình duyệt giữ khóa của thao tác chưa biết kết quả trong sessionStorage (chỉ hash và UUID, không lưu nội dung). / Mutations use transactions, history/audit records and concurrency locks. MySQL stores retry keys. Repeated identical requests reuse their result; conflicting payloads return 409. The browser retains uncertain retry keys in sessionStorage, storing only hashes and UUIDs.
- Giới hạn: tiêu đề 200 ký tự, nội dung/phản hồi 3.000 ký tự; thời gian hiển thị GMT+7. / Limits: subject 200 characters; description/reply 3,000 characters; timestamps display in GMT+7.
- Chưa có AI phân loại/RAG, đính kèm, chuyển giao chat, CSAT hoặc dashboard trong luồng này. / AI classification/RAG, attachments, chat handover, CSAT and dashboards are not included.

## Kiểm thử / Testing

Trong phiên quản trị có cấu hình DB hợp lệ: `$env:RUN_MYSQL_TESTS='1'` rồi `npm.cmd test`. Bộ test tạo database riêng `vietincare_test_<random>` và tự dọn; không dùng dữ liệu ứng dụng làm dữ liệu thử. Không cấp quyền tạo/xóa database cho runtime app chỉ để chạy test.

In an administrative session with valid DB settings, set `RUN_MYSQL_TESTS=1` and run `npm.cmd test`. Tests create and remove isolated databases named `vietincare_test_<random>`. Do not grant runtime accounts database-creation privileges for testing.

Bằng chứng đợt triển khai 2026-09-22: xem PROJECT_CHECKLIST.md. Kết quả trên MySQL tạm không có nghĩa migration đã chạy trên database cổng 3306 của bạn.

See PROJECT_CHECKLIST.md for verification dated 2026-09-22. Passing tests on temporary MySQL does not imply migration has been applied to your database on port 3306.
