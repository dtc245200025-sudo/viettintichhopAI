# VietinCare AI

Backend chính của project là Python FastAPI, giao diện HTML/CSS/JavaScript song ngữ Việt–Anh và MySQL Community Server 8.0.46. Đây là bản ứng dụng đầy đủ đã được khôi phục từ project trước; bản Flask rút gọn được giữ tại `archive_flask_demo_20261028/` để có thể đối chiếu hoặc phục hồi.

## Chức năng hiện có

- Xác thực bằng session, bốn vai trò Customer, Agent, Supervisor và Admin; tùy chọn OTP qua Twilio.
- Quản lý khách hàng, ticket, phân công, lịch sử trạng thái, tìm kiếm/lọc và báo cáo SLA.
- Chat Customer, chuyển giao sang Agent, hàng chờ hỗ trợ và CSAT.
- Kho tri thức MySQL, phiên bản tài liệu, KnowledgeChunk, RAG và nguồn trích dẫn.
- Gemini hoặc OpenAI cho embedding/sinh nội dung; AI phân loại, gợi ý ưu tiên, trả lời nháp và tóm tắt.
- Nhân viên phải duyệt nội dung AI trước khi gửi.
- Tự động phân loại/ưu tiên Ticket mới, phân công Agent có heartbeat gần đây, phân tích cảm xúc và cảnh báo Supervisor khi bức xúc cao; giữ hàng chờ/thử lại khi AI lỗi.
- Đánh giá chat/Ticket, tóm tắt khi chuyển giao/kết thúc và đính chính tương tác giữ nguyên bản gốc.
- Quản trị tài khoản, audit và cấu hình hệ thống.
- Giao diện VI/EN tại `VI/` và `EN/`.

## Cấu trúc chính

```text
backend/       FastAPI, nghiệp vụ, MySQL, AI và migration runner
migrations/    001–011 (43 bước); database có dữ liệu phải nâng cấp bằng migration
tests/         Unit, API và MySQL integration có điều kiện
scripts/       Khởi động, migration, tạo tài khoản và kiểm thử MySQL
VI/, EN/       Giao diện song ngữ
docs/          Artifact AI-Augmented SDLC
.agents/       Skills của project
```

Tài liệu được phân nhóm tại `docs/guides/`, `docs/requirements/`, `docs/reports/`, `docs/references/` và `docs/diagrams/`. Xem [yêu cầu hiện hành](docs/requirements.md), [ticket](docs/guides/tickets.md), [chat](docs/guides/chat.md) và [RAG](docs/guides/rag.md).

`SQLQuery1.sql` là script khởi tạo. Không xóa database đang có để chạy lại script; hãy dùng migration trong `migrations/`.

## Chuẩn bị môi trường

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Sao chép `.env.example` thành `.env` nếu muốn tự quản lý biến môi trường. Không lưu mật khẩu hoặc API key thật vào repository.

## Khởi tạo hoặc nâng cấp database

```powershell
.\scripts\manage-local.ps1 -Action migrate
```

Script hỏi mật khẩu MySQL bằng trường nhập ẩn, kiểm tra migration trước khi áp dụng và không ghi secret vào project.

## Khởi động

```powershell
.\scripts\start-local.ps1
```
==================================================================================================================
Bật Gemini:

```powershell
.\scripts\start-local.ps1 -EnableAI -AIProvider gemini
```

Ứng dụng phục vụ tại `http://localhost:3000` theo cấu hình mặc định.

## Kiểm thử

Nghiệm thu 29/10/2026: **165 test đạt, 0 lỗi, 0 skip**, có MySQL 8.0.46 thật và kiểm tra trình duyệt bốn vai trò VI/EN trên desktop/mobile. Provider nghiệm thu là **mô phỏng**, không phải bằng chứng chất lượng/độ trễ Gemini thật. Xem [báo cáo cuối](docs/reports/final-acceptance-20261029/summary.md).

Chạy lại toàn bộ bằng MySQL cách ly, cần MySQL Server 8.0.46 cài tại vị trí mặc định và cổng 33316 đang trống:

```powershell
.\scripts\final-test.ps1
```

Nạp dữ liệu giả vào database ứng dụng **sau khi đã chạy migration**; script hỏi mật khẩu ẩn, không xóa dữ liệu hoặc đặt lại tài khoản hiện có:

```powershell
.\scripts\seed-demo.ps1
```

Xem [hướng dẫn dữ liệu thử và nghiệm thu](docs/guides/final-acceptance.md) để phân biệt embedding mô phỏng và Gemini thật.

```powershell
.\.venv-1\Scripts\python.exe -m pytest -q
```

MySQL integration chỉ chạy khi cung cấp môi trường kiểm thử cách ly theo `scripts/test-mysql.ps1`. Kết quả unit/API không thay thế kiểm thử MySQL, trình duyệt, SMS hoặc provider AI thật.

## Trạng thái nghiệm thu

Mã FastAPI đã được khôi phục làm nguồn chính. Việc áp migration lên database người dùng, kiểm thử trình duyệt và provider thật vẫn phải được thực hiện trước Human Gate phát hành. Xem [PROJECT_CHECKLIST.md](PROJECT_CHECKLIST.md) và [docs/human-gates.md](docs/human-gates.md).
