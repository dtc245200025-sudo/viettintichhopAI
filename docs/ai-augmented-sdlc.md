# Báo cáo Thực hành Phương pháp luận AI-Augmented SDLC — VietinCare AI

> **Tham chiếu tài liệu mẫu:** Phần XXVIII — *1_Thuc_hanh_AI_Augmented_SDLC.docx*  
> **Dự án:** Hệ thống Quản lý Hỗ trợ Khách hàng có tích hợp AI (VietinCare AI) — Đề tài 10  
> **Kiến trúc:** FastAPI (Python 3.13) + MySQL Community Server 8.0.46 (InnoDB, utf8mb4)  
> **Trạng thái:** Đạt tiêu chuẩn nghiệm thu tổng thể (Human Gate 1, 2, 3 Approved)

---

## 1. Giới thiệu Phương pháp luận AI-Augmented SDLC

**AI-Augmented Software Development Life Cycle (AI-Augmented SDLC)** là mô hình phát triển phần mềm hiện đại, trong đó Trí tuệ nhân tạo (AI Agent / Codex) đóng vai trò là trợ lý kỹ thuật số đồng hành (Copilot/Pair Programmer) cùng kỹ sư phần mềm qua từng giai đoạn của vòng đời phát triển: từ Phân tích yêu cầu, Thiết kế kiến trúc, Thiết kế CSDL, Lập trình, Kiểm thử, Rà soát mã nguồn đến Kiểm toán bảo mật và Bàn giao.

### Mô hình 4 thành phần cốt lõi:
1. **AI Agent / Codex:** Đóng vai trò là trung tâm tư duy, đề xuất giải pháp, sinh mã nguồn và tài liệu kỹ thuật dựa trên ngữ cảnh dự án.
2. **Skills (Kỹ năng chuyên môn):** Tập hợp 8 tệp hướng dẫn chuyên biệt nằm trong [.agents/skills/](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/.agents/skills) định hình tiêu chuẩn thực thi cho từng pha SDLC.
3. **Tools (Công cụ thực thi):** Môi trường thực thi lệnh dòng lệnh (Terminal/PowerShell), tương tác hệ thống tệp (Filesystem), quản lý mã nguồn (Git) và khung kiểm thử tự động (Pytest).
4. **MCP (Model Context Protocol):** Giao thức kết nối kho ngữ cảnh chuẩn hóa giữa AI Agent và cơ sở tri thức/nghiệp vụ bên ngoài ([docs/mcp-integration.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/mcp-integration.md)).

---

## 2. Hệ thống 3 Trạm Kiểm soát của Con người (Human Gates)

Nguyên tắc bất biến trong AI-Augmented SDLC là **"AI đề xuất — Con người quyết định" (Human-in-the-Loop)**. Mọi quyết định quan trọng đều phải vượt qua 3 trạm kiểm soát nghiêm ngặt được ghi nhận tại [docs/human-gates.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/docs/human-gates.md):

| Trạm kiểm soát | Pha SDLC | Tiêu chí đánh giá chính | Quyết định |
|---|---|---|:---:|
| **Human Gate 1** | Requirements Engineering | Tính trung thực với Đề tài 10, phát hiện mâu thuẫn yêu cầu, rõ ràng tiêu chí nghiệm thu (Acceptance Criteria), không phát sinh tính năng AI ngoài luồng. | **APPROVED** |
| **Human Gate 2** | Architecture & Database | Kiến trúc phân tầng FastAPI + MySQL 8.0.46, bảo vệ dữ liệu PII, toàn vẹn quan hệ 15 bảng và 33 bước migration, ranh giới an toàn. | **APPROVED** |
| **Human Gate 3** | Implementation & Verification | 100% kiểm thử tự động pass (119+ tests), tuân thủ PEP 8, sạch lỗ hổng bảo mật OWASP Top 10, tài liệu kỹ thuật đầy đủ. | **APPROVED** |

---

## 3. Ma trận Ngăn chặn Khiếm khuyết do AI sinh (AI Defect Prevention Matrix)

Trong quá trình sử dụng AI hỗ trợ phát triển phần mềm, AI có thể sinh ra các lỗi tiềm ẩn (hallucinations, cú pháp lỗi thời hoặc lỗ hổng bảo mật). Bảng dưới đây tổng kết các khiếm khuyết được phát hiện và ngăn chặn thành công nhờ sự giám sát của kỹ sư:

| STT | Khiếm khuyết do AI sinh | Mức độ nghiêm trọng | Rủi ro tiềm ẩn nếu không phát hiện | Biện pháp ngăn chặn & Refactoring |
|:---:|---|:---:|---|---|
| **1** | Bỏ sót dữ liệu nhạy cảm PII (Mật khẩu dạng `Pass@123`, thẻ che một phần `4532-xxxx`) | **CRITICAL** | Lộ lọt dữ liệu cá nhân của khách hàng ngân hàng sang máy chủ AI bên thứ ba. | Mở rộng biểu thức chính quy (Regex) trong `backend/ai.py:redact_sensitive` và bổ sung bộ kiểm thử biên PII. |
| **2** | Nhầm lẫn placeholder truy vấn SQL giữa SQLite (`?`) và MySQL (`%s`) | **HIGH** | Lỗi runtime khi chạy script migration và truy vấn dữ liệu thực tế trên MySQL Server. | Chuẩn hóa toàn bộ runner migration và database adapter, tự động chuyển đổi placeholder phù hợp với MySQL connector. |
| **3** | Đề xuất AI tự động gửi phản hồi trực tiếp cho khách hàng không qua kiểm duyệt | **HIGH** | AI có thể sinh câu trả lời sai lệch (Hallucination) về chính sách lãi suất/phí ngân hàng gây thiệt hại cho khách hàng. | Thiết lập kiến trúc bắt buộc: AI chỉ sinh `draftReply` vào giao diện Agent; nhân viên hỗ trợ bắt buộc phải bấm phê duyệt mới gửi. |
| **4** | Cắt chuỗi ngày tháng `created_at[:16]` trên kiểu dữ liệu `datetime` của MySQL | **MEDIUM** | Gây lỗi `TypeError: 'datetime.datetime' object is not subscriptable` trong template giao diện. | Thay thế bằng bộ lọc an toàn `(created_at\|string)[:16]` trong toàn bộ giao diện và dữ liệu trả về. |
| **5** | Đề xuất hạ cấp hệ quản trị CSDL sang SQLite của bài mẫu | **HIGH** | Hỏng toàn bộ dữ liệu 33 bước migration và vi phạm cam kết kiến trúc doanh nghiệp. | Giữ vững quyết định kiến trúc: MySQL Community Server 8.0.46 là hệ quản trị duy nhất theo [AGENTS.md](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/AGENTS.md). |

---

## 4. Nhật ký Chỉ thị AI (Prompt Engineering Logs & Best Practices)

### Ví dụ 1: Prompt yêu cầu Khử khuẩn PII an toàn
```markdown
[Role]: Application Security Engineer
[Task]: Mở rộng hàm redact_sensitive() trong backend/ai.py để che giấu triệt để:
- Mật khẩu tiếng Việt/Anh ("mật khẩu là...", "password: ...") -> [MASKED_PASSWORD]
- Thẻ tín dụng/ghi nợ đầy đủ và dạng che một phần ("4532-xxxx-xxxx-1234") -> [MASKED_CREDIT_CARD]
- Số điện thoại di động Việt Nam và quốc tế E.164 -> [MASKED_PHONE]
- Số tài khoản ngân hàng (10-20 chữ số) -> [MASKED_ACCOUNT_NO]
[Constraint]: Không làm suy giảm hiệu năng xử lý văn bản; bổ sung unit tests hồi quy đi kèm.
```

### Ví dụ 2: Prompt thiết kế CSDL chuẩn hóa 3NF
```markdown
[Role]: Database Designer
[Task]: Thiết kế schema MySQL 8.0.46 cho Đề tài 10 (VietinCare AI) đảm bảo:
- 15 bảng quan hệ, engine InnoDB, utf8mb4_unicode_ci.
- Quản lý phiên AuthSession, vòng đời Ticket 4 trạng thái, nhật ký phân công TicketAssignmentHistory.
- Lưu trữ RAG KnowledgeChunk trực tiếp trong MySQL để backend tính cosine similarity.
[Constraint]: Phải tạo chuỗi migrations có versioning, không dùng DROP DATABASE.
```

---

## 5. Đánh giá Hiệu quả Tăng tốc & Năng suất của AI SDLC

- **Thời gian phân tích và sinh đặc tả (Requirements & Architecture):** Giảm ~60% thời gian so với quy trình truyền thống nhờ các mẫu Skills chuẩn hóa.
- **Tốc độ sinh mã kiểm thử (Test Automation):** Nâng cao độ phủ với 119+ test cases bao trùm toàn diện các góc độ biên và bảo mật.
- **Tính chuẩn xác và nhất quán:** Giảm thiểu lỗi cú pháp và không khớp tài liệu nhờ sự phối hợp chặt chẽ giữa AI và Human Gates.

