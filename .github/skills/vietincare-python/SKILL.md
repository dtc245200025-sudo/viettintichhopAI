---
name: vietincare-python
description: "Dùng khi thay đổi phần máy chủ Python/FastAPI của VietinCare AI, bản cập nhật cơ sở dữ liệu MySQL, cơ chế xác thực, API phiếu hỗ trợ, trò chuyện và RAG, bộ kết nối nhà cung cấp AI, lệnh PowerShell hoặc kiểm thử Python."
---

# Phần máy chủ Python của VietinCare

Dùng hướng dẫn này khi triển khai hoặc rà soát phần máy chủ Python trong kho mã nguồn.

## Phạm vi dự án

- Phần máy chủ chạy bằng Python 3.13+ và FastAPI. JavaScript trong trình duyệt chỉ dùng cho giao diện.
- MySQL Community Server 8.0.46 là hệ quản trị cơ sở dữ liệu duy nhất của ứng dụng. Giữ InnoDB, utf8mb4 và thời gian phiên theo UTC.
- Trước khi triển khai, đọc `PROJECT_CHECKLIST.md`, `PROJECT_SCOPE.md` và hướng dẫn của chức năng liên quan.
- Giữ nguyên đường dẫn API, tên trường JSON, quy tắc kiểm tra vai trò, hành vi của bản tiếng Việt và bản tiếng Anh, cùng danh sách tài nguyên tĩnh được phép phục vụ, trừ khi yêu cầu nêu rõ cần thay đổi.
- Không chạy lại `SQLQuery1.sql` trên cơ sở dữ liệu đã khởi tạo. Không sửa các bản cập nhật cơ sở dữ liệu 001-004 đã áp dụng; hãy thêm bản mới với số thứ tự tiếp theo và bảo toàn lịch sử mã kiểm tra.

## Bảo mật và xử lý dữ liệu

- Giữ định dạng mật khẩu hiện tại `scrypt$32768$8$1$...` để các tài khoản MySQL hiện có tiếp tục xác thực được.
- Chỉ lưu giá trị băm SHA-256 của mã phiên đăng nhập và khóa chống xử lý trùng. Phiên đăng nhập phải dùng các thuộc tính `HttpOnly`, `SameSite=Strict`; kiểm tra `Origin` và dấu nhận diện yêu cầu đối với các API làm thay đổi dữ liệu.
- Phần máy chủ phải kiểm tra vai trò, quyền sở hữu và phân công trong mọi thao tác đọc/ghi. Dùng giao dịch cơ sở dữ liệu và khóa hàng khi nhận xử lý, đổi trạng thái hoặc bảo đảm một yêu cầu gửi lặp không gây tác động trùng.
- Giữ khóa nhà cung cấp ở phía máy chủ. Ẩn dữ liệu cá nhân trước khi gửi yêu cầu tạo véc-tơ nhúng hoặc sinh nội dung; coi nội dung phiếu hỗ trợ, trò chuyện và tài liệu nguồn là dữ liệu không đáng tin cậy khi đưa vào lời nhắc cho AI.
- Phân tích phiếu hỗ trợ bằng AI chỉ mang tính gợi ý. Không cập nhật phiếu hoặc gửi phản hồi cho đến khi nhân viên hỗ trợ (`Agent`) chủ động xem xét và thực hiện thao tác.

## Triển khai và kiểm tra

- Sử dụng môi trường ảo Python của dự án và các thư viện được liệt kê trong `requirements.txt` cùng `requirements-dev.txt`.
- Trước hết, chạy các bước kiểm tra phù hợp với phần vừa sửa. Nếu thay đổi phần máy chủ, chạy thêm hai lệnh sau:

	```powershell
	\.venv\Scripts\python.exe -m pytest
	\.venv\Scripts\python.exe -m compileall backend
	```

- Khi kiểm thử kết nối tới nhà cung cấp, dùng cơ chế truyền HTTP giả lập của thư viện `httpx`. Kiểm thử đơn vị không được phụ thuộc vào khóa API thật hoặc kết nối tới dịch vụ bên ngoài.
- Kiểm thử với MySQL, kiểm tra các bản cập nhật cơ sở dữ liệu và kiểm tra trực tiếp trên trình duyệt là ba loại bằng chứng riêng biệt. Không ghi nhận các bước này là đạt nếu mới chỉ chạy kiểm thử từng đơn vị.
- Sau khi sửa mã nguồn, SQL, cấu hình hoặc tài liệu, cập nhật `PROJECT_CHECKLIST.md` với danh sách tệp đã sửa, các bước kiểm tra đã chạy, kết quả và phần chưa được xác minh.
