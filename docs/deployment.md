# Hướng dẫn triển khai hệ thống (Deployment Guide) - Đề tài 10

## 1. Yêu cầu môi trường
- Python 3.10 trở lên
- Hệ điều hành: Windows, Linux hoặc macOS
- Kết nối Internet (để gọi Google Gemini API nếu sử dụng AI Engine trực tuyến)

## 2. Các bước cài đặt và khởi chạy cục bộ (Local Run)

1. **Clone mã nguồn hoặc mở thư mục dự án**:
   ```bash
   cd F:/ViettinCare
   ```

2. **Tạo và kích hoạt môi trường ảo Python**:
   ```bash
   python -m venv venv
   # Trên Windows PowerShell:
   venv\Scripts\activate
   # Trên Linux/macOS:
   source venv/bin/activate
   ```

3. **Cài đặt các gói phụ thuộc**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Cấu hình biến môi trường (`.env`)**:
   Tạo file `.env` tại thư mục gốc với nội dung:
   ```env
   SECRET_KEY=viettincare-super-secret-key-2026
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
   *(Lưu ý: Nếu chưa có `GEMINI_API_KEY`, hệ thống sẽ tự động kích hoạt Rule-based Fallback Engine mô phỏng câu trả lời RAG chuẩn mực mà không gây crash hệ thống).*

5. **Khởi tạo cơ sở dữ liệu và dữ liệu mẫu**:
   ```bash
   python database/db.py
   ```

6. **Chạy kiểm thử tự động (Pytest)**:
   ```bash
   python -m pytest -v
   ```

7. **Khởi động ứng dụng FastAPI**:
   ```powershell
   .\scripts\start-local.ps1
   ```
   Mở trình duyệt truy cập: `http://127.0.0.1:5000`

