# Nâng cấp database / Database migrations

Không sửa file migration đã áp dụng. `001_auth_and_support.sql` giữ nguyên checksum cũ; `002_ticket_requests.sql` bổ sung bảng chống gửi trùng. Bộ chạy kiểm tra checksum, thứ tự version/step và nhật ký `running/done`, giữ khóa MySQL trong lúc chạy. Version 3 (003_chat_history.sql) bổ sung tiêu đề/index và khóa chống trùng cho hội thoại, giữ dữ liệu cũ. Version 4 bổ sung phiên bản tri thức, journal quản trị và liên kết phản hồi AI. Sau version 4 có tổng 22 bước được ghi nhận.

Do not edit applied migration files. Version 1 retains its original checksum. Version 2 adds persistent ticket retry keys. The runner validates checksums and version/step order and holds a MySQL lock during migration. Version 3 adds conversation titles/indexes and persistent chat retry keys while preserving existing history. Version 4 adds knowledge revisions, admin retry keys and AI reply links. All four versions total 22 journaled steps.

Trong project, dừng server rồi chạy bằng tài khoản quản trị (hỏi mật khẩu ẩn):

Stop the server, then run from the project directory (hidden administrator password prompt):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\manage-local.ps1 -Action migrate
```

Công cụ chỉ nâng cấp database hiện có `qlkhviettin` ở 127.0.0.1:3306, không khởi tạo lại. Database mới cần `SQLQuery1.sql` trước. Sao lưu database có dữ liệu quan trọng trước khi nâng cấp. MySQL DDL không được rollback như dữ liệu trong transaction.

This upgrades the existing `qlkhviettin` database at 127.0.0.1:3306 without reinitializing it. A new database needs `SQLQuery1.sql` first. Back up important data before upgrading. MySQL DDL is not rolled back like ordinary transactional data.

Nếu lỗi giữa chừng, không xóa database, không chạy trực tiếp file SQL và không tự sửa checksum/state. Đọc `SchemaMigration` và đối chiếu `SHOW CREATE TABLE` với đúng bước lỗi. Chỉ sửa nhật ký sau khi người quản trị xác minh trạng thái DDL thực tế và lập phương án khôi phục. Bộ chạy cố ý dừng khi còn bước `running`.

On interruption, do not delete the database, rerun SQL directly, or blindly change checksums/state. Inspect `SchemaMigration` and the affected table's `SHOW CREATE TABLE`. Journal repair requires administrator verification of actual DDL state and a recovery plan. A `running` step intentionally blocks automatic retries.
