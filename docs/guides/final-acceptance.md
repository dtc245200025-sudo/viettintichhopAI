# Nghiệm thu và dữ liệu thử / Acceptance and synthetic data

Ngày / Date: 29/10/2026. FastAPI + MySQL Community Server 8.0.46.

## Chạy lại tự động / Repeat automated acceptance

```powershell
.\scripts\final-test.ps1
```

Script tạo MySQL **riêng** tại 127.0.0.1:33316, thư mục mới trong `.mysql-test/`, chạy migration, nạp dữ liệu giả, chạy toàn bộ pytest, sao lưu bằng mysqldump, khôi phục vào database khác và đối chiếu SHA-256 nội dung **từng bảng**. Sau cùng dừng đúng server do nó tạo, sau khi kiểm tra `@@datadir`. Cần MySQL Server 8.0.46 và các công cụ client ở vị trí cài mặc định, Python đã cài `requirements-dev.txt`, cổng 33316 đang trống. Không dùng `DROP` trên database ứng dụng, không sửa mật khẩu/tài khoản đang dùng. Thư mục dữ liệu/backup thử được giữ ngoài theo dõi tại `.mysql-test/`.

The script starts its own loopback-only MySQL instance, seeds synthetic data, runs every pytest, restores a dump into another isolated database, verifies every table's content hash, and stops only the instance it created. The application database is not reset. Test database files are retained in the ignored `.mysql-test/` folder.

Kết quả / Results: [`../reports/final-acceptance-20261029/result.json`](../reports/final-acceptance-20261029/result.json), `pytest.xml`, `pytest.log`, `performance-simulation.json`. Báo cáo được ghi lại cho lần chạy mới nhất, không phải lịch sử của mọi lần chạy.

## Dữ liệu demo / Demo dataset

Mỗi database mới được nạp 9 tài khoản: `customer1@demo.invalid` đến `customer5@demo.invalid`, `agent1@demo.invalid`, `agent2@demo.invalid`, `supervisor@demo.invalid`, `admin@demo.invalid`. Customer 5 bị vô hiệu hóa để thử nhánh từ chối đăng nhập. Có 48 Ticket đủ bốn trạng thái/bốn mức ưu tiên phân bố cho các khách hàng, 8 hội thoại, phản hồi/lịch sử/phân công, 4 FAQ, 1.000 chunk và 16 đánh giá ban đầu; có 3 phân tích AI Pending/Selected/Dismissed, 3 cảnh báo và dữ liệu cảm xúc/hàng chờ. Mọi tên/liên hệ/nội dung là giả lập, không có giao dịch ngân hàng thật.

The isolated acceptance runner uses the deliberately public, **test-only** password `Synthetic-Test-Only-2026!`. This is not an application credential and must never be reused for real accounts. Production passwords/API keys are never written to these reports.

Database demo do script tạo có tiền tố `vietincare_demo_...`; tên cụ thể có trong `result.json`. Khi server thử đã dừng, dữ liệu còn trong datadir, không xuất hiện tự động ở database `qlkhviettin` trên cổng 3306.

## Nạp vào database ứng dụng / Seed the application database

Trong phiên nghiệm thu chưa có credential database chính, nên không tự nạp hay migrate database 3306. Khi có mật khẩu, chạy từ thư mục project:

```powershell
.\scripts\manage-local.ps1 -Action migrate
.\scripts\seed-demo.ps1
```

Script thứ nhất hỏi mật khẩu quản trị MySQL. Script thứ hai hỏi mật khẩu `vietincare_app` và mật khẩu **riêng cho tài khoản demo** bằng trường ẩn. Loader ghi trong một transaction, chạy lại theo marker sẽ không tạo trùng, không xóa bản ghi, không đổi credential của tài khoản có sẵn. Email demo đã tồn tại nhưng không có marker sẽ làm loader dừng thay vì ghi đè.

Apply migrations before seeding. Both scripts request secrets using hidden prompts and restore their process environment afterwards. The loader preserves existing rows and refuses ambiguous demo-account collisions.

## Simulation khác Gemini thật / Simulation versus live Gemini

`SimulationAI` chỉ được tiêm trong test và server demo riêng; không phải fallback của `backend.main`. Vector demo dùng model `vietincare-demo-embedding-v1`, 768 chiều; truy xuất Gemini/OpenAI thật sẽ **không dùng lẫn** vector này. Muốn dùng FAQ demo với Gemini thật: tạo bản nháp thay thế trong CMS, tạo embedding bằng Gemini, thử câu có/không có nguồn, rồi xuất bản. Không thay nhãn model của vector giả thành Gemini.

The simulated provider validates workflows and load handling, not answer quality, provider availability, Internet latency or banking-policy accuracy. Test transport cases exercise request/response contracts of the real adapters without sending data to the Internet.

Sau khi backend thật chạy với khóa nhập cục bộ, có thể đo HTTP 50 câu/5 phiên bằng tài khoản Customer demo:

```powershell
.\.venv-1\Scripts\python.exe -m backend.benchmark --email customer1@demo.invalid
```

Script hỏi mật khẩu ẩn hoặc nhận `VC_BENCH_PASSWORD` trong môi trường; không lưu mật khẩu. Nó tạo chat/tin nhắn kiểm thử, nên chỉ dùng dữ liệu demo. Báo cáo `performance-live.json` chỉ Pass khi đủ 50 câu thành công, p95 ≤5 giây và provider thật. Phải ghi lại model đang cấu hình, mạng và đánh giá chất lượng/căn cứ nguồn trước khi nghiệm thu AI thật; một phép đo không chứng minh uptime 99,9%.

## Kiểm tra giao diện / Browser acceptance

`scripts/browser-acceptance.cjs` chạy với Node + Playwright và Edge có sẵn, mặc định kiểm tra `http://localhost:3001`, bốn vai trò, VI/EN, desktop 1366×900 và mobile 390×844. Đặt `VC_PLAYWRIGHT_MODULE` trỏ tới module Playwright đã cài nếu không nằm trong đường tìm module. Nó dùng tài khoản demo ở trên, có tạo/sửa dữ liệu thử; không chạy nhầm vào hệ thống ngân hàng hoặc môi trường có dữ liệu thật.

Server phục vụ kiểm tra giao diện chỉ nhận database có tiền tố demo:

```powershell
.\.venv-1\Scripts\python.exe -m backend.demo_server --database TEN_DATABASE_DEMO --mysql-port 33316 --port 3001
```

Lệnh này cần MySQL demo đang chạy; tài khoản MySQL phục vụ web chỉ được cấp CRUD trên database demo. Các ảnh và kết quả trình duyệt nằm trong `docs/reports/final-acceptance-20261029/browser/`.
