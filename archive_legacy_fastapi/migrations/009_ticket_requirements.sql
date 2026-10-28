-- Align the ticket lifecycle with de_tai_10.md and TongHop.docx without deleting existing records.
UPDATE Ticket SET TrangThai='Đã đóng', NgayDong=COALESCE(NgayDong,NgayCapNhat,UTC_TIMESTAMP(3)) WHERE TrangThai='Đã giải quyết';
UPDATE TicketStatusHistory SET TrangThaiCu='Đã đóng' WHERE TrangThaiCu='Đã giải quyết';
UPDATE TicketStatusHistory SET TrangThaiMoi='Đã đóng' WHERE TrangThaiMoi='Đã giải quyết';
ALTER TABLE Ticket DROP CHECK CK_Ticket_Status, ADD CONSTRAINT CK_Ticket_Status CHECK(TrangThai IN ('Mới','Đang xử lý','Chờ khách hàng','Đã đóng'));
ALTER TABLE TicketStatusHistory DROP CHECK TicketStatusHistory_chk_1, DROP CHECK TicketStatusHistory_chk_2, ADD CONSTRAINT CK_TicketStatusHistory_Previous CHECK(TrangThaiCu IS NULL OR TrangThaiCu IN ('Mới','Đang xử lý','Chờ khách hàng','Đã đóng')), ADD CONSTRAINT CK_TicketStatusHistory_Current CHECK(TrangThaiMoi IN ('Mới','Đang xử lý','Chờ khách hàng','Đã đóng'));
