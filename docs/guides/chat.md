# Hướng dẫn chat và chuyển giao

## Chuẩn bị

```powershell
.\scripts\manage-local.ps1 -Action migrate
.\scripts\start-local.ps1
```

Để bật Gemini:

```powershell
.\scripts\start-local.ps1 -EnableAI -AIProvider gemini
```

Các migration 001–009 có 33 bước. Database có dữ liệu chỉ dùng migration, không chạy lại `SQLQuery1.sql`.

## Luồng sử dụng

1. Customer đăng nhập, mở **Lịch sử trò chuyện**, gửi tin nhắn đầu tiên.
2. Không bật AI: tin vẫn lưu MySQL và Customer vẫn yêu cầu Agent.
3. Bật AI: hệ thống tìm nguồn đã xuất bản, lưu câu trả lời và nguồn; thiếu nguồn/provider lỗi không tạo câu trả lời giả.
4. Customer chọn **Yêu cầu nhân viên**. Agent nhận hàng chờ tại Tổng quan, tiếp nhận và phản hồi.
5. Agent hoặc Supervisor tạo tóm tắt khi AI bật và kết thúc lượt chuyển giao theo quyền.

Customer chỉ đọc chat của mình. Agent chỉ đọc handover đang chờ hoặc do mình tiếp nhận; Supervisor giám sát hàng chờ. Phiên chat kết thúc chỉ đọc.

## Kiểm tra

- VI: `http://localhost:3000/VI/chat-vi.html`
- EN: `http://localhost:3000/EN/chat-en.html`
- Unit/API: `.\.venv-1\Scripts\python.exe -m pytest -q`
- MySQL cách ly: `.\scripts\test-mysql.ps1`
