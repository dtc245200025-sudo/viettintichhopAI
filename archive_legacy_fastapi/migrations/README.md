# Nâng cấp database / Database migrations

Không sửa file migration đã áp dụng. `001_auth_and_support.sql` giữ nguyên checksum cũ; `002_ticket_requests.sql` bổ sung bảng chống gửi trùng. Runner Python kiểm tra checksum, thứ tự version/step và journal `running/done`, giữ khóa MySQL trong lúc chạy. Version 3 thêm lịch sử chat, version 4 thêm phiên bản tri thức/RAG, version 5 thêm bảng gợi ý AI ticket và trạng thái duyệt của Agent, version 6 thêm challenge OTP chỉ lưu mã băm có salt, version 7 ghi lịch sử phân công ticket, version 8 hoàn thiện chuyển giao/tóm tắt và cấu hình hệ thống. Version 9 chuyển dữ liệu Đã giải quyết sang Đã đóng và chuẩn hóa vòng đời có Chờ khách hàng. Sau version 9 có tổng 33 bước.

Do not edit applied migration files. Version 1 retains its original checksum. The Python runner validates checksums and version/step order and holds a MySQL lock during migration. Version 3 preserves conversation history, version 4 adds knowledge/RAG revisions, version 5 stores ticket AI suggestions plus Agent review state, version 6 adds salted OTP challenge hashes, version 7 records ticket assignments, version 8 completes handovers/summaries plus system settings, and version 9 aligns the ticket lifecycle with Waiting for customer. All nine versions total 33 journaled steps.

Trong project, dừng server rồi chạy bằng tài khoản quản trị (hỏi mật khẩu ẩn):

Stop the server, then run from the project directory (hidden administrator password prompt):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\manage-local.ps1 -Action migrate
```

> Lưu ý: chú thích `npm run db:migrate` nằm trong migration 001 là dấu vết lịch sử trước khi chuyển sang Python. Không dùng lệnh đó và không sửa migration 001–004 đã áp dụng vì runner kiểm tra checksum; chỉ dùng lệnh PowerShell ở trên.

Công cụ chỉ nâng cấp database hiện có `qlkhviettin` ở 127.0.0.1:3306, không khởi tạo lại. Database mới cần `SQLQuery1.sql` trước. Sao lưu database có dữ liệu quan trọng trước khi nâng cấp. MySQL DDL không được rollback như dữ liệu trong transaction.

This upgrades the existing `qlkhviettin` database at 127.0.0.1:3306 without reinitializing it. A new database needs `SQLQuery1.sql` first. Back up important data before upgrading. MySQL DDL is not rolled back like ordinary transactional data.

Nếu lỗi giữa chừng, không xóa database, không chạy trực tiếp file SQL và không tự sửa checksum/state. Đọc `SchemaMigration` và đối chiếu `SHOW CREATE TABLE` với đúng bước lỗi. Chỉ sửa nhật ký sau khi người quản trị xác minh trạng thái DDL thực tế và lập phương án khôi phục. Bộ chạy cố ý dừng khi còn bước `running`.

On interruption, do not delete the database, rerun SQL directly, or blindly change checksums/state. Inspect `SchemaMigration` and the affected table's `SHOW CREATE TABLE`. Journal repair requires administrator verification of actual DDL state and a recovery plan. A `running` step intentionally blocks automatic retries.
