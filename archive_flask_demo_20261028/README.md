# ViettinCare - Hệ thống Quản lý Hỗ trợ Khách hàng bằng AI-Augmented SDLC (Đề tài 10)

Hệ thống quản lý ticket hỗ trợ khách hàng được xây dựng theo mô hình **AI-Augmented SDLC**, biến AI thành AI Agent có kiểm soát chặt chẽ thông qua các Skill chuyên biệt, cơ chế kiểm duyệt của con người (**Human-in-the-Loop Gate**), bảo vệ thông tin riêng tư (**PII Masking**) và cơ sở tri thức tăng cường (**RAG Support**).

---

## 1. Cấu trúc thư mục chuẩn AI-Augmented SDLC

```
viettintichhopAI/
├── .agents/                      # Chứa các Skill của AI-Agent (AI-Augmented SDLC)
│   └── skills/                   # Danh mục Skill chuẩn hóa
│       ├── requirements-analysis/    # Phân tích yêu cầu & user stories
│       ├── architecture-design/      # Thiết kế kiến trúc & phân tầng
│       ├── database-design/          # Thiết kế CSDL & quan hệ
│       ├── implementation/           # Triển khai mã nguồn
│       ├── testing/                  # Kế hoạch & kiểm thử tự động
│       ├── code-review/              # Đánh giá chất lượng mã nguồn
│       ├── security-review/          # Kiểm tra bảo mật PII & OWASP
│       └── documentation/            # Tài liệu hóa kỹ thuật
│
├── docs/                        # Toàn bộ tài liệu SDLC của Đề tài 10
│   ├── acceptance-criteria.md       # Tiêu chí chấp nhận
│   ├── ai-support-requirements.md   # Yêu cầu hỗ trợ AI
│   ├── architecture-decisions.md    # Quyết định kiến trúc (ADR)
│   ├── architecture.md              # Kiến trúc hệ thống
│   ├── code-review.md               # Kiểm tra mã nguồn
│   ├── customer-requirement.md      # Yêu cầu của khách hàng
│   ├── database-design.md           # Thiết kế cơ sở dữ liệu
│   ├── deployment.md                # Hướng dẫn triển khai
│   ├── product-retrieval.md         # Truy xuất sản phẩm
│   ├── question-analysis.md         # Phân tích câu hỏi
│   ├── requirements-issues.md       # Danh sách issues yêu cầu
│   ├── requirements.md              # Yêu cầu chức năng & phi chức năng
│   ├── security-review.md           # Kiểm tra bảo mật
│   ├── test-plan.md                 # Kế hoạch kiểm thử
│   ├── test-report.md               # Báo cáo kiểm thử
│   ├── ticket-analysis.md           # Phân tích ticket hỗ trợ
│   ├── uml-design.md                # Thiết kế UML chi tiết
│   ├── user-guide.md                # Hướng dẫn sử dụng
│   ├── user-stories.md              # Câu chuyện người dùng
│   └── diagrams/                    # Sơ đồ kiến trúc, ERD SVG/PNG
│
├── database/                    # Cơ sở dữ liệu hợp nhất
│   ├── db.py                        # Lớp kết nối hợp nhất (hỗ trợ cả MySQL & SQLite)
│   ├── schema.sql                   # Cấu trúc CSDL SQLite
│   ├── schema_mysql.sql             # Cấu trúc CSDL MySQL 8.0.46 (InnoDB, utf8mb4)
│   └── viettincare.db               # CSDL SQLite cục bộ phục vụ chạy thử & kiểm thử
│
├── routes/                      # Định tuyến Flask theo chức năng
│   ├── ai_routes.py                 # Đường dẫn AI: phân loại, gợi ý trả lời, tóm tắt
│   ├── auth_routes.py               # Đường dẫn xác thực (đăng nhập/đăng xuất)
│   ├── customer_routes.py           # Đường dẫn quản lý khách hàng
│   └── ticket_routes.py             # Đường dẫn quản lý vòng đời ticket
│
├── services/                    # Lớp nghiệp vụ (Domain Services)
│   ├── ai_support_service.py        # Dịch vụ AI (PII masking, FAQ RAG, Gemini LLM)
│   ├── auth_service.py              # Dịch vụ xác thực & RBAC
│   ├── customer_service.py          # Dịch vụ quản lý hồ sơ khách hàng
│   └── ticket_service.py            # Dịch vụ quản lý ticket & comments
│
├── static/                      # Tài nguyên tĩnh
│   ├── css/
│   │   └── style.css                # CSS giao diện người dùng
│   └── js/
│       └── ticket.js                # JavaScript điều khiển xử lý ticket & AI modal
│
├── templates/                   # Giao diện Jinja2
│   ├── base.html                    # Layout chuẩn
│   ├── customers.html               # Trang quản lý khách hàng
│   ├── dashboard.html               # Bảng điều khiển SLA & thống kê
│   ├── login.html                   # Đăng nhập
│   ├── tickets.html                 # Danh sách ticket & lọc
│   └── ticket_detail.html           # Chi tiết ticket & trợ lý AI
│
├── tests/                       # Kiểm thử tự động (pytest)
│   ├── test_ai_support.py           # Kiểm thử PII, phân loại, RAG FAQ, guardrail
│   ├── test_auth.py                 # Kiểm thử đăng nhập, phân quyền RBAC
│   └── test_tickets.py              # Kiểm thử vòng đời ticket, trạng thái, bình luận
│
├── scripts/                     # Tiện ích vận hành
│   ├── init_db.py                   # Khởi tạo CSDL
│   ├── seed_data.py                 # Nạp dữ liệu mẫu
│   └── run_tests.py                 # Chạy bộ kiểm thử
│
├── archive_legacy_fastapi/      # Toàn bộ mã nguồn & dữ liệu FastAPI cũ được lưu trữ
│
├── app.py                       # Điểm vào chính của ứng dụng Flask
├── generate_report.py           # Tạo báo cáo tổng hợp SDLC DOCX
├── requirements.txt             # Danh sách thư viện phụ thuộc
├── .env.example                 # Mẫu cấu hình môi trường
└── README.md                    # Tài liệu dự án
```

---

## 2. Hỗ trợ Cơ sở dữ liệu Đa môi trường

Hệ thống hỗ trợ 2 chế độ cơ sở dữ liệu thông qua cấu hình `DB_TYPE` trong file `.env`:
1. **SQLite (`DB_TYPE=sqlite`)**: Chế độ mặc định, sẵn sàng chạy ngay lập tức mà không cần cài đặt thêm dịch vụ, thích hợp cho kiểm thử tự động `pytest` và demo nhanh.
2. **MySQL (`DB_TYPE=mysql`)**: Kết nối tới **MySQL Community Server 8.0.46** với cấu trúc `InnoDB`, bảng mã `utf8mb4_unicode_ci` theo đúng tiêu chuẩn đề tài đã thống nhất trong `AGENTS.md`.

---

## 3. Các tính năng cốt lõi (Đề tài 10)

1. **Quản lý Vòng đời Ticket**: Tạo mới, gán nhân viên phụ trách, cập nhật trạng thái (`New`, `In Progress`, `Waiting Customer`, `Closed`), phân loại danh mục và mức độ ưu tiên.
2. **Quản lý Hồ sơ Khách hàng & Phân quyền RBAC**: Quản trị viên (Admin), Quản lý nhóm (Team Lead), Nhân viên hỗ trợ (Support Agent).
3. **AI Phân loại & Gợi ý Mức ưu tiên**: Phân tích tự động nội dung ticket đề xuất danh mục và độ khẩn cấp.
4. **AI Gợi ý Trả lời (RAG) & Human Gate**: AI đối chiếu cơ sở tri thức FAQ/chính sách và soạn thảo câu trả lời nháp. Nhân viên hỗ trợ xem trước, chỉnh sửa và bấm duyệt trước khi gửi cho khách.
5. **AI Tóm tắt Lịch sử**: Tóm tắt chuỗi trao đổi dài thành 3 gạch đầu dòng then chốt cho nhân viên nhận ca trực mới.
6. **Bảo mật & Quyền riêng tư (PII Sanitization)**: Khử định danh mật khẩu, số thẻ ngân hàng, số điện thoại trước khi truyền dữ liệu ra LLM bên ngoài.

---

## 4. Hướng dẫn khởi chạy

### Bước 1: Kích hoạt môi trường và cài đặt thư viện
```bash
.\.venv-1\Scripts\activate
pip install -r requirements.txt
```

### Bước 2: Khởi tạo CSDL
```bash
python scripts/init_db.py
```

### Bước 3: Chạy bộ kiểm thử tự động
```bash
python -m pytest -v
```

### Bước 4: Khởi động ứng dụng
```bash
python app.py
```
Truy cập: `http://127.0.0.1:5000`
- Tài khoản Quản trị: `admin` / `Admin@123`
- Tài khoản Team Lead: `lead_tuan` / `Lead@123`
- Tài khoản Agent: `agent_lan` / `Agent@123` hoặc `agent_huy` / `Agent@123`

### Bước 5: Xuất báo cáo DOCX
```bash
python generate_report.py
```
File báo cáo `Bao_Cao_Thuc_Hanh_AI_Augmented_SDLC_De_Tai_10.docx` sẽ được tạo ngay trong thư mục gốc.
