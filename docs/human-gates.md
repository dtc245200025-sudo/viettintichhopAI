# Human Gates của VietinCare AI (AI-Augmented SDLC)

## Phạm vi bổ sung ngày 29/10/2026

Người dùng đã yêu cầu hoàn thiện/kiểm thử và chọn thêm chức năng tự động trong phiên làm việc. Các phê duyệt ngày 28/10 dưới đây là lịch sử, không phải bằng chứng nghiệm thu phần bổ sung, Gemini thật hoặc phát hành sản xuất. Kết quả mới ở `docs/reports/final-acceptance-20261029/summary.md`; không tự ghi nhận người dùng đã duyệt kết quả chưa xem.

Tài liệu này ghi nhận bằng chứng kiểm soát và phê duyệt của con người qua 3 trạm kiểm soát (Human Gates) bắt buộc theo chuẩn phương pháp luận AI-Augmented SDLC (Phần III, Phần V và Phần XXIX của tài liệu thực hành mẫu).

---

## Human Gate 1 – Requirements Review & Approval (Phần III)

- **Reviewer:** Người dùng / Giảng viên hướng dẫn môn AI-Augmented SDLC
- **Ngày phê duyệt:** 2026-10-28
- **Quyết định:** **APPROVED (ĐÃ PHÊ DUYỆT)**
- **Phạm vi thẩm định:** [docs/requirements.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/requirements.md), [docs/user-stories.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/user-stories.md), [docs/acceptance-criteria.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/acceptance-criteria.md), [docs/requirements-issues.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/requirements-issues.md).

### Bảng kiểm định tiêu chí Gate 1:
- [x] **Tính trung thực với đề tài gốc:** Yêu cầu phản ánh chuẩn xác Đề tài 10 (CSKH Ngân hàng VietinCare AI) theo [docs/requirements/source-topic-10.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/requirements/source-topic-10.md), không bị nhầm lẫn với bài toán quản lý laptop của bài thực hành mẫu.
- [x] **Tính kiểm thử và truy vết:** Toàn bộ 16 Use Case (UC001 - UC016), User Stories và Acceptance Criteria (AC-001 đến AC-015) có mã định danh rõ ràng, ánh xạ 1-1 với bộ kiểm thử tự động.
- [x] **Giải quyết các điểm mơ hồ (Ambiguities):** Quyết định rõ vòng đời Ticket gồm 4 trạng thái: `Mới` $\to$ `Đang xử lý` $\leftrightarrow$ `Chờ khách hàng` $\to$ `Đã đóng`; quyền phân công thuộc Supervisor; khách hàng không tự đóng ticket khi chưa giải quyết xong.
- [x] **Kiểm soát AI tự phát sinh:** Không có tính năng AI ngoài luồng; AI chỉ đóng vai trò hỗ trợ Agent (Smart Reply, Tóm tắt, Phân loại/Ưu tiên) và có bước Human-in-the-Loop duyệt trước khi phản hồi khách hàng.

---

## Human Gate 2 – Architecture and Database Review (Phần V)

- **Reviewer:** Người dùng / Giảng viên hướng dẫn môn AI-Augmented SDLC
- **Ngày phê duyệt:** 2026-10-28
- **Quyết định:** **APPROVED (ĐÃ PHÊ DUYỆT)**
- **Phạm vi thẩm định:** [docs/architecture.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/architecture.md), [docs/database-design.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/database-design.md), [docs/uml-design.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/uml-design.md), [SQLQuery1.sql](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/SQLQuery1.sql), [migrations/](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/migrations).

### Bảng kiểm định tiêu chí Gate 2:
- [x] **Kiến trúc phân tầng chuẩn Enterprise:** Sử dụng FastAPI async hiệu năng cao kết hợp với MySQL Community Server 8.0.46 (InnoDB, `utf8mb4`). Tách biệt rõ ràng các tầng: Presentation (UI song ngữ VI/EN), Controller/Routes, Business Service, Data Access Layer và AI RAG Pipeline.
- [x] **Toàn vẹn và Nhất quán CSDL:** Mô hình dữ liệu gồm 15 bảng quan hệ được thiết kế chuẩn hóa 3NF, bảo toàn dữ liệu bằng 9 migrations (33 bước thực thi) có checksum và kiểm soát phiên bản chặt chẽ.
- [x] **Khử khuẩn Dữ liệu Nhạy cảm (PII Sanitization):** Tích hợp tầng làm sạch dữ liệu PII trong `backend/ai.py` che chắn toàn bộ mật khẩu, số thẻ tín dụng, số tài khoản, email và số điện thoại trước khi gửi sang mô hình AI Gemini/OpenAI.
- [x] **Đáp ứng Yêu cầu Phi Chức năng (NFR):** Bảo mật đa lớp (CSP headers, Session cookie HttpOnly, Scrypt password hashing, OTP SMS, Role-Based Access Control cho 4 vai trò).

---

## Human Gate 3 – Implementation, Verification & Release Review (Phần XXIX)

- **Reviewer:** Người dùng / Giảng viên hướng dẫn môn AI-Augmented SDLC
- **Ngày phê duyệt:** 2026-10-28
- **Quyết định:** **APPROVED (ĐÃ PHÊ DUYỆT)**
- **Phạm vi thẩm định:** Toàn bộ mã nguồn [backend/](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/backend), [VI/](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/VI), [EN/](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/EN), [tests/](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/tests), [docs/test-report.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/test-report.md), [docs/code-review.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/code-review.md), [docs/security-review.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/security-review.md).

### Bảng kiểm định tiêu chí Gate 3:
- [x] **Chất lượng kiểm thử tự động:** Đạt 119/119 test cases pass ở các cấp độ Unit test, Security test, Domain logic, Migration và Regression test.
- [x] **Đạt chuẩn Code Quality & Static Analysis:** Tuân thủ PEP 8, 100% mã nguồn Python biên dịch thành công (`python -m compileall backend tests`), không có lỗi cú pháp trong 8 file JavaScript và 5 PowerShell launcher scripts.
- [x] **Không tồn đọng lỗi bảo mật nghiêm trọng:** Không có lỗi CRITICAL hoặc HIGH trong báo cáo Security Review; cơ chế PII Sanitization và chống SQL Injection hoạt động ổn định.
- [x] **Bằng chứng AI-Augmented SDLC đầy đủ:** Đã thiết lập đầy đủ 8 Skills chuyên môn trong `.agents/skills/`, tài liệu kết nối giao thức MCP ([docs/mcp-integration.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/mcp-integration.md)) và Báo cáo quá trình AI hỗ trợ ([docs/ai-augmented-sdlc.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/ai-augmented-sdlc.md)).
