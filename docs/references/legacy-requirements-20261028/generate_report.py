import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import os

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)

def create_full_report_docx(output_path):
    doc = docx.Document()

    # Set margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title1 = p_title.add_run("XÂY DỰNG HỆ THỐNG\nQUẢN LÝ HỖ TRỢ KHÁCH HÀNG BẰNG AI-AUGMENTED SDLC\n")
    run_title1.font.size = Pt(20)
    run_title1.font.bold = True
    run_title1.font.color.rgb = RGBColor(15, 23, 42)

    run_sub = p_title.add_run("(Áp dụng cho Đề tài 10: Hệ thống Quản lý Hỗ trợ Khách hàng có tích hợp AI)\n")
    run_sub.font.size = Pt(13)
    run_sub.font.italic = True
    run_sub.font.color.rgb = RGBColor(71, 85, 105)

    # A. TIÊU CHÍ ĐÁNH GIÁ
    h_a = doc.add_heading("A. TIÊU CHÍ ĐÁNH GIÁ BÀI THỰC HÀNH", level=1)
    p_a = doc.add_paragraph(
        "Điểm cốt lõi của bài thực hành này là không dùng Codex như một công cụ sinh code đơn thuần, "
        "mà tổ chức Codex thành một AI Agent thực hiện các quy trình SDLC có kiểm soát bằng Skills, Tools và MCP, "
        "với các điểm kiểm soát của con người (Human Gate). Cách tiếp cận này hoàn toàn phù hợp với định hướng hiện tại "
        "về AI-Augmented SDLC: hiểu codebase, xây dựng tính năng, kiểm thử, review và tự động hóa các workflow lặp lại; "
        "đồng thời lưu trữ các workflow thành Skills chuẩn hóa.\n"
        "Đánh giá năng lực sử dụng AI trong SDLC, thay vì chỉ đánh giá 'AI đã viết được bao nhiêu code'."
    )

    table_score = doc.add_table(rows=1, cols=2)
    table_score.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table_score.rows[0].cells
    hdr[0].text = "Nội dung"
    hdr[1].text = "Điểm"
    set_cell_background(hdr[0], "0F172A")
    set_cell_background(hdr[1], "0F172A")
    hdr[0].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
    hdr[1].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
    hdr[0].paragraphs[0].runs[0].font.bold = True
    hdr[1].paragraphs[0].runs[0].font.bold = True

    scores = [
        ("Phân tích yêu cầu (Customer Requirements & Ambiguities)", "1.0"),
        ("Xây dựng Requirements Skill", "1.0"),
        ("Thiết kế kiến trúc", "1.0"),
        ("Database Skill + CSDL (Schema & ERD)", "1.0"),
        ("Coding Skill + implementation", "1.5"),
        ("Testing Skill + test evidence", "1.5"),
        ("Review + Security Skill (PII Masking, OWASP)", "1.0"),
        ("Documentation Skill", "0.5"),
        ("Sử dụng Tools/MCP", "0.5"),
        ("Human verification + báo cáo quá trình AI (Human Gate)", "1.0"),
        ("Tổng", "10.0")
    ]

    for item, sc in scores:
        row = table_score.add_row().cells
        row[0].text = item
        row[1].text = sc
        if item == "Tổng":
            set_cell_background(row[0], "F1F5F9")
            set_cell_background(row[1], "F1F5F9")
            row[0].paragraphs[0].runs[0].font.bold = True
            row[1].paragraphs[0].runs[0].font.bold = True

    doc.add_paragraph("\nSinh viên phải nộp đầy đủ cả 9 thành phần:")
    p_sub = doc.add_paragraph()
    deliverables = [
        "1. SKILL.md (Tất cả các file Skill trong .agents/skills/)",
        "2. Prompt/task đã giao cho Codex",
        "3. Artifact Codex tạo ra (các file trong docs/)",
        "4. Kết quả kiểm thử (Test plan, test report, bằng chứng pytest)",
        "5. Review report (Code review report)",
        "6. Security report (Báo cáo bảo mật PII & OWASP)",
        "7. Các lỗi AI phát hiện được & Hallucination đã ngăn chặn",
        "8. Những chỉnh sửa do con người thực hiện (Human Gate)",
        "9. Git history (Toàn bộ commit log)"
    ]
    for d in deliverables:
        p_sub.add_run(d + "\n")

    # B. MÔ HÌNH TỔNG QUÁT
    doc.add_heading("B. MÔ HÌNH TỔNG QUÁT VÒNG ĐỜI PHÁT TRIỂN PHẦN MỀM ĐƯỢC TĂNG CƯỜNG BẰNG TRÍ TUỆ NHÂN TẠO AI", level=1)
    doc.add_paragraph(
        "Mô hình AI-Augmented SDLC kết hợp chặt chẽ 3 trụ cột: Con người (Human) đóng vai trò giám sát và ra quyết định tối cao; "
        "AI/LLM đóng vai trò trợ lý chuyên môn thực hiện các tác vụ kỹ thuật theo tiêu chuẩn; và Công cụ (Tools/MCP) "
        "cung cấp môi trường thực thi, kiểm thử và tích hợp dữ liệu."
    )
    p_box = doc.add_paragraph()
    p_box.add_run(
        "AI-Augmented SDLC Architecture:\n"
        "  [Con người] <=======> [AI / LLM Agent] <=======> [Công cụ (Tools / MCP)]\n"
        "                               │\n"
        "                               ▼\n"
        "                     [Phát triển phần mềm]\n"
        "                               │\n"
        "   ┌──────────────┬────────────┼─────────────┬─────────────┐\n"
        "   ▼              ▼            ▼             ▼             ▼\n"
        "Requirements    Design       Coding       Testing      Deployment\n"
        "   └──────────────┴────────────┼─────────────┴─────────────┘\n"
        "                               ▼\n"
        "                         [Maintenance]\n"
    )

    doc.add_paragraph(
        "Khi sử dụng Codex làm AI Agent điều phối quy trình, mô hình tương tác được chuẩn hóa:\n"
        "  Codex Agent điều phối:\n"
        "  - Skills: Quy trình chuẩn, Coding rules, Testing rules, Review checklists\n"
        "  - Context: Source code, Database Schema, Customer Requirements, Documentation\n"
        "  - Tools: Terminal, Git, Python Test Runner, File System\n"
        "  - MCP: Kết nối dịch vụ bên ngoài, Issue Tracker\n"
        "  ===> Tạo ra dự án phần mềm ViettinCare chất lượng cao."
    )

    # C. HỆ THỐNG QUẢN LÝ HỖ TRỢ KHÁCH HÀNG BẰNG AI-AUGMENTED SDLC VỚI CODEX
    doc.add_heading("C. HỆ THỐNG QUẢN LÝ HỖ TRỢ KHÁCH HÀNG BẰNG AI-AUGMENTED SDLC VỚI CODEX", level=1)

    # 1. Mục tiêu
    doc.add_heading("1. Mục tiêu", level=2)
    goals = [
        "Phân tích yêu cầu phần mềm quản lý ticket hỗ trợ khách hàng với sự trợ giúp của AI.",
        "Xây dựng và sử dụng Skill cho từng hoạt động SDLC (requirements, architecture, database, coding, testing, review, security).",
        "Sử dụng Codex như một AI Agent có kiểm soát thay vì chỉ sinh mã nguồn tự do.",
        "Phân biệt rõ ràng vai trò của Skill, Tool và MCP trong hệ thống.",
        "Sử dụng Codex xuyên suốt các giai đoạn: Requirements Engineering, Architecture Design, Database Design, Implementation, Testing, Code Review, Security Review, Documentation.",
        "Tích hợp các tính năng AI hỗ trợ khách hàng: AI phân loại ticket & mức ưu tiên, gợi ý câu trả lời nháp từ cơ sở tri thức FAQ (RAG), tóm tắt chuỗi trao đổi dài.",
        "Thiết lập cơ chế kiểm chứng độc lập kết quả do AI tạo ra và Human Gate bắt buộc con người phê duyệt trước khi gửi phản hồi.",
        "Khử định danh dữ liệu nhạy cảm (PII Masking) trước khi truyền sang LLM bên ngoài.",
        "Kiểm soát phòng chống hallucination: AI không được tự ý cam kết bồi thường hay bịa đặt chính sách.",
        "Quản lý Skill cùng với mã nguồn bằng Git."
    ]
    p_g = doc.add_paragraph()
    for g in goals:
        p_g.add_run(f"• {g}\n")

    # PHẦN I. XÁC ĐỊNH BÀI TOÁN
    doc.add_heading("PHẦN I. XÁC ĐỊNH BÀI TOÁN", level=2)
    doc.add_heading("Bước 1. Xác định bài toán", level=3)
    doc.add_paragraph(
        "Ta xây dựng: Hệ thống quản lý hỗ trợ khách hàng có tích hợp AI (ViettinCare).\n"
        "Hệ thống giải quyết bài toán tiếp nhận yêu cầu hỗ trợ, theo dõi trạng thái ticket, phân công nhân viên xử lý "
        "và tóm tắt lịch sử trao đổi. Tích hợp AI phân loại sự cố, gợi ý câu trả lời nháp từ FAQ và tóm tắt hội thoại.\n\n"
        "Hệ thống có các nhóm người dùng chính:\n"
        "1. Quản trị viên (Admin): Toàn quyền cấu hình, quản lý tài khoản nhân viên, quản lý cơ sở tri thức FAQ.\n"
        "2. Quản lý nhóm (Team Lead): Phân công ticket cho nhân viên, theo dõi tiến độ xử lý và xem báo cáo SLA, hiệu suất.\n"
        "3. Nhân viên hỗ trợ (Support Agent): Xem ticket được giao, cập nhật trạng thái (Mới, Đang xử lý, Chờ khách, Đã đóng), trao đổi với khách, sử dụng Trợ lý AI và phê duyệt câu trả lời nháp.\n"
        "4. Khách hàng (Customer): Gửi yêu cầu hỗ trợ, theo dõi tiến độ và trao đổi phản hồi."
    )

    # PHẦN II. CHUẨN BỊ MÔI TRƯỜNG
    doc.add_heading("PHẦN II. CHUẨN BỊ MÔI TRƯỜNG", level=2)
    doc.add_heading("Bước 2. Tạo project", level=3)
    doc.add_paragraph(
        "Mở Terminal tại thư mục làm việc:\n"
        "Tạo thư mục: ViettinCare\n"
        "Khởi tạo Git: git init\n"
        "Tạo môi trường ảo Python: python -m venv venv\n"
        "Kích hoạt môi trường: venv\\Scripts\\activate\n"
        "Cài các thư viện: pip install flask werkzeug python-dotenv pytest google-generativeai\n"
        "Lưu dependencies: pip freeze > requirements.txt"
    )

    # PHẦN III. TẠO CẤU TRÚC AI-AUGMENTED SDLC
    doc.add_heading("PHẦN III. TẠO CẤU TRÚC AI-AUGMENTED SDLC", level=2)
    doc.add_heading("Bước 3. Tạo cấu trúc thư mục (Dùng Codex để tạo)", level=3)
    doc.add_paragraph(
        "Cấu trúc thư mục dự án ViettinCare:\n"
        "ViettinCare/\n"
        "├── .git/\n"
        "├── .agents/\n"
        "│    └── skills/\n"
        "├── docs/\n"
        "├── backend/\n"
        "├── migrations/\n"
        "├── VI/\n"
        "├── EN/\n"
        "├── tests/\n"
        "├── requirements.txt\n"
        "└── .gitignore\n"
        "Đây là lúc bắt đầu đưa AI-Augmented SDLC vào project."
    )

    # PHẦN IV. XÂY DỰNG REQUIREMENTS SKILL
    doc.add_heading("PHẦN IV. XÂY DỰNG REQUIREMENTS SKILL", level=2)
    doc.add_heading("Bước 4. Tạo Skill phân tích yêu cầu", level=3)
    doc.add_paragraph(
        "Tạo thư mục: .agents/skills/requirements-analysis/\n"
        "Tạo file: .agents/skills/requirements-analysis/SKILL.md\n"
        "Quy định nghiêm ngặt: Input -> Process (10 bước chuẩn hóa từ Identify stakeholders đến Traceability) -> Rules (Không viết code, không bịa quy tắc, tách bạch giả định) -> Outputs -> Verification."
    )

    # PHẦN V. CUNG CẤP YÊU CẦU CHO CODEX
    doc.add_heading("PHẦN V. CUNG CẤP YÊU CẦU CHO CODEX", level=2)
    doc.add_heading("Bước 5. Tạo yêu cầu của khách hàng", level=3)
    doc.add_paragraph(
        "Tạo file: docs/customer-requirement.md\n"
        "Nội dung mô tả bài toán tiếp nhận yêu cầu hỗ trợ, khách hàng, nhân viên xử lý, trạng thái ticket và lịch sử trao đổi. "
        "Yêu cầu AI phân loại ticket, gợi ý phản hồi đối chiếu FAQ và tóm tắt lịch sử hỗ trợ, kèm cơ chế nhân viên duyệt câu trả lời."
    )

    # PHẦN VI. YÊU CẦU CODEX SỬ DỤNG SKILL
    doc.add_heading("PHẦN VI. YÊU CẦU CODEX SỬ DỤNG SKILL", level=2)
    doc.add_heading("Bước 6. Chạy Codex", level=3)
    doc.add_paragraph(
        "Prompt giao nhiệm vụ cho Codex:\n"
        "  'Hãy thực hiện Requirements Engineering cho project này.\n"
        "   Sử dụng requirements-analysis skill.\n"
        "   Đọc: docs/customer-requirement.md\n"
        "   Thực hiện đúng quy trình được quy định trong skill.\n"
        "   Không viết source code.\n"
        "   Tạo: docs/requirements.md, docs/user-stories.md, docs/acceptance-criteria.md, docs/requirements-issues.md.\n"
        "   Sau khi hoàn thành, giải thích: Skill đã dùng, Artifacts đã tạo, Requirements chưa rõ, Giả định đã dùng.'"
    )

    # PHẦN VII. KIỂM CHỨNG KẾT QUẢ
    doc.add_heading("PHẦN VII. KIỂM CHỨNG KẾT QUẢ", level=2)
    doc.add_heading("Bước 7. Không chấp nhận ngay kết quả của AI", level=3)
    doc.add_paragraph(
        "Sinh viên mở docs/requirements.md và kiểm tra:\n"
        "- FR-001: Người dùng có thể đăng nhập và phân quyền RBAC.\n"
        "- FR-002: Quản lý thông tin khách hàng.\n"
        "- FR-003: Tạo và theo dõi vòng đời ticket (Mới, Đang xử lý, Chờ khách, Đã đóng).\n"
        "- FR-004: Phân công ticket cho nhân viên.\n"
        "- FR-005: Trao đổi comment và file đính kèm ở mức mô tả.\n"
        "- FR-006: Tìm kiếm và lọc ticket.\n"
        "- FR-007: Thống kê số ticket, thời gian xử lý, nhóm vấn đề.\n"
        "- FR-008: AI phân loại ticket và gợi ý mức ưu tiên.\n"
        "- FR-009: AI gợi ý câu trả lời nháp đối chiếu FAQ.\n"
        "- FR-010: Cơ chế con người phê duyệt câu trả lời AI (Human-in-the-Loop).\n"
        "- FR-011: AI tóm tắt lịch sử trao đổi dài.\n\n"
        "Kiểm tra AI Hallucination: Codex ban đầu đề xuất tự động hoàn tiền vào tài khoản ngân hàng và tự động gọi điện qua VoIP. "
        "Con người đã phát hiện và loại bỏ các yêu cầu bịa đặt này."
    )

    # PHẦN VIII. HUMAN GATE 1
    doc.add_heading("PHẦN VIII. HUMAN GATE 1", level=2)
    doc.add_paragraph(
        "Không được: Requirements -> Codex -> Architecture\n"
        "Mà phải: Requirements -> Codex -> Human Verification -> [CHỜ PHÊ DUYỆT] -> Architecture\n\n"
        "Requirements Review:\n"
        "Reviewer: Student / Lead QA\n"
        "Status: CHỜ CON NGƯỜI PHÊ DUYỆT\n"
        "Checked:\n"
        "[ ] Functional requirements (FR-001 -> FR-011)\n"
        "[ ] Non-functional requirements (NFR-001 -> NFR-006: PII Masking, Security)\n"
        "[ ] User stories (US-001 -> US-011)\n"
        "[ ] Acceptance criteria (AC-001 -> AC-009)\n"
        "[ ] Ambiguities & requirement invention reviewed\n"
        "Chưa được phê duyệt để chuyển sang Architecture Design."
    )

    # PHẦN IX. XÂY DỰNG ARCHITECTURE SKILL
    doc.add_heading("PHẦN IX. XÂY DỰNG ARCHITECTURE SKILL", level=2)
    doc.add_heading("Bước 8. Tạo Skill", level=3)
    doc.add_paragraph(
        "Tạo: .agents/skills/architecture-design/SKILL.md\n"
        "Quy định quy trình 10 bước: Style -> Components -> Responsibilities -> Dependencies -> Communication -> Data flow -> External systems -> Security boundaries -> ADR -> Traceability."
    )

    # PHẦN X. SỬ DỤNG ARCHITECTURE SKILL
    doc.add_heading("PHẦN X. SỬ DỤNG ARCHITECTURE SKILL", level=2)
    doc.add_heading("Bước 9. Yêu cầu Codex", level=3)
    doc.add_paragraph(
        "Codex thiết kế kiến trúc phân tầng kết hợp Service-Oriented AI Pipeline:\n"
        "  Web Browser (Support UI & AI Assistant Panel)\n"
        "       │\n"
        "       ▼\n"
        "  FastAPI Application (Session Auth & RBAC)\n"
        "       │\n"
        "  ┌────┴──────────────────────────┬────────────────────────┐\n"
        "  ▼                               ▼                        ▼\n"
        "Auth Service / Customer Service  Ticket Service    AI Support Service\n"
        "  │                               │                        │\n"
        "  ▼                               │              ┌─────────┴─────────┐\n"
        "Database (MySQL 8.0.46) <────────┘              ▼                   ▼\n"
        "                                           FAQ Retriever      Context Builder\n"
        "                                                 │                   │\n"
        "                                                 └─────────┬─────────┘\n"
        "                                                           ▼\n"
        "                                                    Gemini LLM API"
    )

    # PHẦN XI. HUMAN GATE 2
    doc.add_heading("PHẦN XI. HUMAN GATE 2", level=2)
    doc.add_paragraph(
        "Sinh viên kiểm tra Traceability giữa Yêu cầu và Thành phần kiến trúc:\n"
        "- FR-003 Create/Update Ticket -> Ticket Service -> MySQL 8.0.46\n"
        "- FR-008 AI Classification -> Ticket Analyzer -> AI Support Service\n"
        "- FR-009 AI Suggest Response -> FAQ Retriever -> Context Builder -> Gemini API\n"
        "- FR-010 Human Gate Approval -> Ticket Controller -> Approve API -> Ticket Comments DB\n"
        "Bảng ánh xạ đã được tạo để người duyệt kiểm tra. Trạng thái Human Gate 2: CHỜ CON NGƯỜI PHÊ DUYỆT."
    )

    # PHẦN XII. DATABASE SKILL
    doc.add_heading("PHẦN XII. DATABASE SKILL", level=2)
    doc.add_heading("Bước 10. Tạo Skill", level=3)
    doc.add_paragraph(
        "Tạo: .agents/skills/database-design/SKILL.md\n"
        "Quy định: Requirements -> Entities -> Relationships -> Normalization -> PK/FK -> Constraints -> Indexes -> SQL Schema -> Verification.\n\n"
        "Thực thể chính:\n"
        "- users (id, username, email, password_hash, full_name, role)\n"
        "- customers (id, full_name, email, phone, company, tier)\n"
        "- tickets (id, ticket_number, customer_id, title, description, category, priority, status, assigned_to)\n"
        "- ticket_comments (id, ticket_id, user_id, author_role, author_name, content, is_internal)\n"
        "- faqs (id, category, question, answer, keywords)\n"
        "- ai_logs (id, ticket_id, action_type, input_context, raw_ai_output, approved_output, is_approved, agent_id, latency_ms)"
    )

    # PHẦN XIII. YÊU CẦU CODEX THIẾT KẾ DATABASE
    doc.add_heading("PHẦN XIII. YÊU CẦU CODEX THIẾT KẾ DATABASE", level=2)
    doc.add_heading("Bước 11", level=3)
    doc.add_paragraph("Codex tạo docs/database-design.md và database/schema.sql với đầy đủ ràng buộc toàn vẹn và chỉ mục tối ưu.")

    # PHẦN XIV. KIỂM TRA DATABASE
    doc.add_heading("PHẦN XIV. KIỂM TRA DATABASE", level=2)
    doc.add_paragraph(
        "Sinh viên kiểm tra:\n"
        "Ticket -> customer_id, title, description, category, priority, status, assigned_to, timestamps.\n"
        "Đồng thời kiểm tra: PRIMARY KEY, FOREIGN KEY, NOT NULL, UNIQUE, CHECK constraints (status in 'New', 'In Progress', 'Waiting Customer', 'Closed'), INDEX trên status, priority, customer_id, assigned_to."
    )

    # PHẦN XV. IMPLEMENTATION SKILL
    doc.add_heading("PHẦN XV. IMPLEMENTATION SKILL", level=2)
    doc.add_heading("Bước 12. Tạo Skill", level=3)
    doc.add_paragraph(
        "Tạo: .agents/skills/implementation/SKILL.md\n"
        "Quy trình: Read Specification -> Understand Architecture -> Understand Database -> Implement -> Run Linter -> Run Tests -> Review Diff."
    )

    # PHẦN XVI. BẮT ĐẦU LẬP TRÌNH
    doc.add_heading("PHẦN XVI. BẮT ĐẦU LẬP TRÌNH", level=2)
    doc.add_heading("Bước 13. Yêu cầu Codex", level=3)
    doc.add_paragraph(
        "Triển khai Core System trước:\n"
        "1. Database connection & DAO (database/db.py)\n"
        "2. Customer API và RBAC (backend/customers.py)\n"
        "3. Ticket lifecycle, assignment và AI review (backend/tickets.py)\n"
        "4. Search & Filter tickets theo status, priority, search term\n"
        "5. Dashboard SLA analytics thống kê số lượng và tỷ lệ ticket\n"
        "Chưa triển khai các chức năng AI ở bước này."
    )

    # PHẦN XVII. TESTING SKILL
    doc.add_heading("PHẦN XVII. TESTING SKILL", level=2)
    doc.add_heading("Bước 14. Tạo Testing Skill", level=3)
    doc.add_paragraph(
        "Tạo: .agents/skills/testing/SKILL.md\n"
        "Quy định: Requirements -> Test Scenario -> Test Case -> Automated Test -> Execution -> Result -> Defect."
    )

    # PHẦN XVIII. KIỂM THỬ
    doc.add_heading("PHẦN XVIII. KIỂM THỬ", level=2)
    doc.add_heading("Bước 15. Yêu cầu Codex", level=3)
    doc.add_paragraph(
        "Thực hiện kiểm thử bằng Pytest. Tạo tests/test_auth.py, tests/test_tickets.py, tests/test_ai_support.py.\n"
        "Sau khi khôi phục FastAPI, kết quả thực thi ngày 2026-10-28 đạt 110 test, 1 MySQL integration skip; compileall và cú pháp JavaScript đạt. Chưa kiểm thử browser, SMS hoặc provider AI thật. Tạo docs/test-plan.md và docs/test-report.md."
    )

    # PHẦN XIX. CODE REVIEW SKILL
    doc.add_heading("PHẦN XIX. CODE REVIEW SKILL", level=2)
    doc.add_heading("Bước 16. Tạo Skill", level=3)
    doc.add_paragraph(
        "Tạo: .agents/skills/code-review/SKILL.md\n"
        "Tiêu chí: Correctness, Requirements Compliance, Architecture Compliance, Maintainability, Security, Performance, Testing."
    )

    # PHẦN XX. REVIEW CODE
    doc.add_heading("PHẦN XX. REVIEW CODE", level=2)
    doc.add_heading("Bước 17", level=3)
    doc.add_paragraph(
        "Đánh giá mã nguồn và lập docs/code-review.md. Phát hiện lỗi regex PII và thiếu kiểm tra rỗng tại API duyệt phản hồi; "
        "đã xử lý một số lỗi trước đây; review hiện hành vẫn ghi nhận các phát hiện CRITICAL/HIGH về secret, authentication, RBAC và cấu hình database chưa xử lý."
    )

    # PHẦN XXI. SECURITY SKILL
    doc.add_heading("PHẦN XXI. SECURITY SKILL", level=2)
    doc.add_heading("Bước 18. Tạo Skill", level=3)
    doc.add_paragraph(
        "Tạo: .agents/skills/security-review/SKILL.md\n"
        "Checklist: SQL Injection, XSS, CSRF, Authentication, Authorization, Secrets, Input Validation, PII Masking, AI Hallucination Guardrails."
    )

    # PHẦN XXII. SECURITY REVIEW
    doc.add_heading("PHẦN XXII. SECURITY REVIEW", level=2)
    doc.add_heading("Bước 19", level=3)
    doc.add_paragraph(
        "Thực hiện review bảo mật và lập docs/security-review.md. Truy vấn đã đọc dùng tham số hóa và mật khẩu được băm, "
        "nhưng CSRF, RBAC, secret mặc định, MySQL thật, PII đối kháng và provider AI thật vẫn chưa đạt hoặc chưa kiểm chứng."
    )

    # PHẦN XXIII. TRỢ LÝ AI HỖ TRỢ KHÁCH HÀNG (TƯƠNG ỨNG PHẦN CHATBOT AI TRONG MẪU)
    doc.add_heading("PHẦN XXIII. TRỢ LÝ AI HỖ TRỢ KHÁCH HÀNG (AI SUPPORT ASSISTANT)", level=2)
    doc.add_paragraph(
        "Sau khi core system ổn định, ta mới triển khai trợ lý AI hỗ trợ khách hàng.\n"
        "Kiến trúc:\n"
        "Customer / Support Agent\n"
        "   │\n"
        "   ▼\n"
        "Support UI Workspace\n"
        "   │\n"
        "   ▼\n"
        "FastAPI (/api/...)\n"
        "   │\n"
        "   ▼\n"
        "AI Support Service (RAG)\n"
        "   │\n"
        "   ├── 1. PII Sanitization (Khử định danh mật khẩu, thẻ, SĐT)\n"
        "   ├── 2. Ticket & Question Analyzer (Trích xuất intent JSON)\n"
        "   ├── 3. FAQ Knowledge Retriever (Tra cứu chính sách/FAQ chuẩn)\n"
        "   ├── 4. Context Builder (Xây dựng ngữ cảnh gọn)\n"
        "   └── 5. Prompt Builder (Áp đặt quy tắc không bịa đặt, chỉ tạo bản nháp)\n"
        "   │\n"
        "   ▼\n"
        "Gemini API / LLM Engine\n"
        "   │\n"
        "   ▼\n"
        "AI Draft Response\n"
        "   │\n"
        "   ▼\n"
        "[HUMAN GATE] Nhân viên hỗ trợ kiểm tra, chỉnh sửa và bấm Duyệt gửi khách"
    )

    sub_steps_ai = [
        ("1. Xác định yêu cầu AI hỗ trợ", "Tạo docs/ai-support-requirements.md xác định AI phân loại sự cố, gợi ý câu trả lời nháp, tóm tắt lịch sử trao đổi dài và cơ chế con người duyệt."),
        ("2. Sử dụng Requirements Skill", "Phân tích yêu cầu AI hỗ trợ, tạo các user stories và acceptance criteria tương ứng."),
        ("3. Xác định User Story & Acceptance Criteria", "Xác định AC-AI-001 (gợi ý trả lời), AC-AI-002 (tóm tắt), AC-AI-003 (phân loại), AC-AI-004 (Human Gate review)."),
        ("Human Gate", "Kiểm tra functional requirements, user stories, acceptance criteria, hallucination policy và PII privacy."),
        ("4. Thiết kế kiến trúc Trợ lý AI", "Thiết kế các module: Ticket Controller, Ticket Analyzer, FAQ Retriever, Context Builder, Prompt Builder, Gemini Service, Human Gate Handler."),
        ("5. Thiết kế Ticket Context Analyzer", "Tạo intermediate representation JSON (category, suggested_priority, keywords, sanitized_summary). Tạo Skill ticket-analysis."),
        ("6. FAQ Knowledge Retrieval", "Truy xuất bài viết FAQ bằng SQL tham số hóa dựa trên category và keywords. Tạo Skill faq-retrieval."),
        ("7. Implement Retrieval", "Triển khai hàm retrieve_faqs(intent) an toàn, không SQL injection."),
        ("8. Context Builder", "Xây dựng ngữ cảnh cô đọng, lọc PII. Tạo Skill context-builder."),
        ("9. Prompt Builder", "Thiết lập system prompt: 'Bạn là trợ lý chăm sóc khách hàng. Chỉ tạo câu trả lời nháp cho nhân viên duyệt. Không hứa hoàn tiền nếu dữ liệu không cung cấp.' Tạo Skill ai-prompt."),
        ("10. AI Provider", "Triển khai backend/ai.py hỗ trợ Gemini/OpenAI, timeout, structured output, embedding và lỗi an toàn."),
        ("11. Kết hợp thành AI Support Service", "Tích hợp toàn bộ pipeline: Ticket -> Sanitize -> Analyze -> Retrieve FAQ -> Context -> Prompt -> Gemini -> Draft -> Human Approval."),
        ("12. Tạo FastAPI", "Triển khai API auth, customer, ticket, chat, knowledge, admin, reports và AI review trong backend/."),
        ("13. Xây dựng giao diện Hỗ trợ & Trợ lý AI", "Thiết kế giao diện 2 cột hiện đại: Cột trái quản lý ticket và luồng bình luận; Cột phải là Trợ lý AI với các tab Gợi ý nháp, Tóm tắt, Phân loại và Nút Phê duyệt của con người."),
        ("14. Chạy thử toàn bộ hệ thống", "Khởi chạy hệ thống trên máy chủ cục bộ, kiểm tra toàn bộ luồng từ tạo ticket, AI gợi ý đến nhân viên duyệt gửi.")
    ]

    for title, desc in sub_steps_ai:
        doc.add_heading(title, level=3)
        doc.add_paragraph(desc)

    # PHẦN XXIV. MCP
    doc.add_heading("PHẦN XXIV. MCP", level=2)
    doc.add_paragraph(
        "Khi hệ thống kết nối với GitHub Issues, hệ thống Helpdesk bên ngoài hoặc Webhook của bên thứ ba, "
        "MCP (Model Context Protocol) mới ở mức thiết kế dự kiến, chưa được cấu hình hoặc kiểm thử trong project:\n"
        "External Issue/Ticket -> MCP Server -> Codex Agent -> Phân tích -> Đề xuất bản vá -> Testing -> Human Approval."
    )

    # PHẦN XXV. DOCUMENTATION SKILL
    doc.add_heading("PHẦN XXV. DOCUMENTATION SKILL", level=2)
    doc.add_heading("Bước 20", level=3)
    doc.add_paragraph(
        "Tạo: .agents/skills/documentation/SKILL.md\n"
        "Đọc toàn bộ project và đồng bộ hóa tài liệu: README.md, docs/api.md, docs/architecture.md, "
        "docs/database-design.md, docs/deployment.md, docs/user-guide.md. Mọi kết luận phải kèm phạm vi và bằng chứng kiểm tra."
    )

    # PHẦN XXVI. KẾT QUẢ CUỐI CÙNG
    doc.add_heading("PHẦN XXVI. KẾT QUẢ CUỐI CÙNG", level=2)
    doc.add_paragraph(
        "Project đã có cấu trúc mã nguồn, schema, tài liệu đặc tả và 8 Skills quy trình. Chưa thể tuyên bố hoàn thành toàn bộ vì Human Gates, MySQL integration, trình duyệt, provider AI thật và các phát hiện bảo mật vẫn đang mở."
    )

    # PHẦN XXVII. TOÀN BỘ QUY TRÌNH DƯỚI DẠNG AI-AUGMENTED SDLC
    doc.add_heading("PHẦN XXVII. TOÀN BỘ QUY TRÌNH DƯỚI DẠNG AI-AUGMENTED SDLC", level=2)
    doc.add_paragraph(
        "Toàn bộ quy trình phát triển Đề tài 10 thể hiện sự phối hợp nhịp nhàng giữa Codex, Skills, Tools, MCP và Human Gates:\n"
        "Customer Requirement -> CODEX Agent (điều phối qua Skills) -> Requirements -> [HUMAN GATE 1] -> Architecture -> [HUMAN GATE 2] -> Database -> [HUMAN GATE 3] -> Source Code -> Tests (Pytest) -> Test Results -> Review Report -> Security Report -> Documentation -> [HUMAN QA] -> RELEASE.\n"
        "Trong đó, Tools đã dùng gồm Terminal, File System, Python và Pytest. MCP với GitHub/External APIs mới là thiết kế dự kiến."
    )

    # PHẦN XXVIII. VAI TRÒ CỦA 4 THÀNH PHẦN
    doc.add_page_break()
    doc.add_heading("PHẦN XXVIII. VAI TRÒ CỦA 4 THÀNH PHẦN", level=2)
    table_roles = doc.add_table(rows=1, cols=2)
    table_roles.alignment = WD_TABLE_ALIGNMENT.CENTER
    hr = table_roles.rows[0].cells
    hr[0].text = "Thành phần"
    hr[1].text = "Vai trò"
    set_cell_background(hr[0], "0F172A")
    set_cell_background(hr[1], "0F172A")
    hr[0].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
    hr[1].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
    hr[0].paragraphs[0].runs[0].font.bold = True
    hr[1].paragraphs[0].runs[0].font.bold = True

    roles_data = [
        ("Codex", "AI Agent điều phối và thực hiện các tác vụ phát triển phần mềm trong SDLC"),
        ("Skill", "Tri thức thủ tục, quy trình và tiêu chuẩn chuyên môn quy định cách thực hiện một loại tác vụ cụ thể"),
        ("Tool", "Cơ chế cho phép Codex thực hiện thao tác cụ thể trên môi trường làm việc (Terminal, Git, Pytest, File System)"),
        ("MCP", "Cơ chế kết nối dự kiến với hệ thống bên ngoài; project chưa cấu hình MCP cho GitHub hoặc Ticket Webhook")
    ]
    for comp, desc in roles_data:
        r = table_roles.add_row().cells
        r[0].text = comp
        r[1].text = desc

    # PHẦN XXIX. QUẢN LÝ VERSION CỦA SKILL
    doc.add_heading("PHẦN XXIX. QUẢN LÝ VERSION CỦA SKILL", level=2)
    doc.add_paragraph(
        "Mẫu minh họa cách Skill có thể được nâng cấp theo thời gian; project hiện chưa có các thư mục phiên bản dưới đây:\n"
        "requirements-analysis/\n"
        "├── v1/SKILL.md (Phân tích cơ bản)\n"
        "├── v2/SKILL.md (Bổ sung phát hiện AI Hallucination)\n"
        "└── v3/SKILL.md (Tích hợp quy chuẩn PII Masking & Human Gate)"
    )

    # PHẦN XXX. MỘT LƯU Ý QUAN TRỌNG VỀ LƯU TRỮ SKILL
    doc.add_heading("PHẦN XXX. MỘT LƯU Ý QUAN TRỌNG VỀ LƯU TRỮ SKILL", level=2)
    doc.add_paragraph(
        "Cần phân biệt rõ hai cấp độ lưu trữ Skill:\n"
        "1. Cấp Project: Skill được quản lý cùng repository tại `.agents/skills/` nhằm phục vụ workflow cụ thể của dự án ViettinCare và đồng bộ hóa qua Git.\n"
        "2. Cấp Nền tảng: Sử dụng Skills API của nền tảng AI để tái sử dụng các Skill dùng chung cho nhiều dự án khác nhau trong doanh nghiệp.\n"
        "Do đó, trong bài thực hành này, dự án bắt đầu với lưu trữ chuẩn mực tại: Project -> `.agents/skills/`."
    )

    doc.save(output_path)
    print("DOCX created successfully at:", output_path)

if __name__ == '__main__':
    report_dir = os.path.join(os.path.dirname(__file__), "docs", "reports")
    os.makedirs(report_dir, exist_ok=True)
    out = os.path.join(report_dir, "Bao_Cao_Thuc_Hanh_AI_Augmented_SDLC_De_Tai_10.docx")
    create_full_report_docx(out)

