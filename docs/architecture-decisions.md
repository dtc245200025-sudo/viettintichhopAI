# Bản ghi quyết định kiến trúc (Architectural Decision Records - ADR) - Đề tài 10

## ADR-001: Lựa chọn Framework Backend (Python FastAPI)
- **Bối cảnh**: Project trước đã triển khai API, session, RBAC, chat/RAG, ticket, admin và báo cáo bằng FastAPI với bộ test rộng hơn bản demo Flask.
- **Quyết định**: Khôi phục FastAPI tại `backend/` làm backend duy nhất; bản Flask rút gọn được lưu tại `archive_flask_demo_20261028/`.
- **Hệ quả**: Giữ được các REST path và giao diện VI/EN trước đây; mọi tài liệu, test và launcher phải tham chiếu FastAPI.

## ADR-002: Áp dụng mô hình Human-in-the-Loop cho phản hồi AI
- **Bối cảnh**: Mô hình ngôn ngữ lớn (LLM) có nguy cơ bịa đặt (hallucination), có thể đưa ra lời khuyên sai quy trình hoặc cam kết bồi thường ngoài thẩm quyền làm thiệt hại cho doanh nghiệp.
- **Quyết định**: Tuyệt đối không cho phép AI tự động gửi tin nhắn trực tiếp tới khách hàng. AI chỉ sinh ra bản nháp (Draft Response). Nhân viên hỗ trợ phải xem trước, chỉnh sửa (nếu cần) và bấm nút xác nhận duyệt mới được lưu vào hệ thống và gửi cho khách.
- **Hệ quả**: Giảm rủi ro nội dung AI được gửi sai; vẫn cần phân quyền, kiểm thử và trách nhiệm của người duyệt.

## ADR-003: Kiến trúc RAG tối giản cho cơ sở tri thức FAQ
- **Bối cảnh**: Cần cung cấp cho AI các chính sách chính thức của doanh nghiệp để câu trả lời luôn bám sát nghiệp vụ.
- **Quyết định**: Triển khai tầng `FAQ Retriever` dựa trên trích xuất từ khóa phân loại và truy vấn tham số hóa (Parameterized SQL) lọc theo chuyên mục và từ khóa liên quan, đưa vào Context Builder trước khi gửi prompt cho Gemini API.
- **Hệ quả**: Chi phí vận hành thấp, không phụ thuộc vào hạ tầng vector database cồng kềnh, tốc độ truy xuất dưới 50ms.

## ADR-004: Bảo mật thông tin cá nhân khách hàng (PII Masking)
- **Bối cảnh**: Khách hàng thường gửi thông tin nhạy cảm (số thẻ, mật khẩu tạm thời, số điện thoại) trong mô tả ticket. Gửi trực tiếp dữ liệu này ra API công cộng vi phạm nguyên tắc bảo mật.
- **Quyết định**: Thiết kế module `sanitizer` chạy cục bộ trên máy chủ trước khi xây dựng ngữ cảnh AI, tự động thay thế các mẫu nhạy cảm bằng nhãn mask `[MASKED_INFO]`.
- **Hệ quả**: Giảm lượng dữ liệu nhạy cảm gửi ra ngoài; vẫn cần data minimization và kiểm thử PII đầy đủ.

## ADR-005: Hệ quản trị cơ sở dữ liệu duy nhất
- **Quyết định**: Chỉ dùng MySQL Community Server 8.0.46, InnoDB, utf8mb4. `SQLQuery1.sql` là script khởi tạo; database có dữ liệu dùng migration riêng.
- **Hệ quả**: Backend FastAPI dùng trực tiếp MySQL, không có fallback SQLite. MySQL integration vẫn phải chạy trong database kiểm thử cách ly.

