import os
import re
import json
import time
from database.db import get_db

# Thử import google.generativeai nếu có API key
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class AISupportService:
    @staticmethod
    def sanitize_pii(text: str) -> str:
        """
        Khử định danh PII (Personal Identifiable Information) trước khi gửi sang LLM.
        """
        if not text:
            return ""
        # Che mật khẩu (dạng Pass@..., password=..., mật khẩu của tôi là XYZ)
        text = re.sub(r'(?i)(password|mat khau|mật khẩu)[\s:=]+(?:của tôi là|là)?\s*([^\s,]+)', r'\1: [MASKED_PASSWORD]', text)
        text = re.sub(r'(?i)(Pass@\w+)', '[MASKED_PASSWORD]', text)
        # Che số thẻ tín dụng hoặc số tài khoản ngân hàng (10-16 chữ số)
        text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[MASKED_CREDIT_CARD]', text)
        # Che số điện thoại VN (10 chữ số bắt đầu bằng 03, 05, 07, 08, 09)
        text = re.sub(r'\b(0[3|5|7|8|9]\d{8})\b', '[MASKED_PHONE]', text)
        text = re.sub(r'\b\d{9,16}\b', '[MASKED_ACCOUNT_NO]', text)
        return text

    @staticmethod
    def analyze_ticket(title: str, description: str) -> dict:
        """
        Ticket Analyzer: Trích xuất Intermediate Representation JSON.
        """
        clean_text = AISupportService.sanitize_pii(f"{title} {description}").lower()

        # Quy tắc xác định danh mục và mức độ khẩn cấp
        category = "Tư vấn & Hướng dẫn sử dụng"
        priority = "Medium"
        keywords = []

        if any(w in clean_text for w in ["mật khẩu", "đăng nhập", "login", "reset", "otp", "kích hoạt"]):
            category = "Tài khoản & Đăng nhập"
            keywords.extend(["đổi mật khẩu", "reset", "email", "otp"])
            priority = "High" if "gấp" in clean_text or "không vào được" in clean_text else "Medium"

        elif any(w in clean_text for w in ["tiền", "thanh toán", "trừ tiền", "hoàn tiền", "hóa đơn", "banking", "qr"]):
            category = "Thanh toán & Hóa đơn"
            keywords.extend(["thanh toán", "trừ tiền", "ngân hàng", "giao dịch"])
            priority = "Urgent" if "hai lần" in clean_text or "bị trừ" in clean_text else "High"

        elif any(w in clean_text for w in ["lỗi 500", "crash", "sập", "trắng xóa", "màn hình trắng", "chết web"]):
            category = "Lỗi kỹ thuật & Phần mềm"
            keywords.extend(["lỗi kỹ thuật", "hệ thống", "crash"])
            priority = "Urgent"

        elif any(w in clean_text for w in ["nâng cấp", "vip", "bảng giá", "hợp đồng"]):
            category = "Tư vấn & Hướng dẫn sử dụng"
            keywords.extend(["nâng cấp", "gói dịch vụ", "vip"])
            priority = "Medium"

        return {
            "category": category,
            "suggested_priority": priority,
            "keywords": keywords,
            "sanitized_summary": clean_text[:200]
        }

    @staticmethod
    def retrieve_faqs(intent: dict) -> list:
        """
        FAQ Retriever: Truy xuất các bài viết cơ sở tri thức tương ứng.
        """
        conn = get_db()
        cursor = conn.cursor()
        category = intent.get("category", "")
        keywords = intent.get("keywords", [])

        query = "SELECT * FROM faqs WHERE category = ?"
        params = [category]

        cursor.execute(query, params)
        faqs = [dict(row) for row in cursor.fetchall()]

        # Nếu không có FAQ khớp danh mục, tìm theo từ khóa
        if not faqs and keywords:
            kw_conditions = " OR ".join(["keywords LIKE ?" for _ in keywords])
            query = f"SELECT * FROM faqs WHERE {kw_conditions} LIMIT 3"
            params = [f"%{k}%" for k in keywords]
            cursor.execute(query, params)
            faqs = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return faqs

    @staticmethod
    def build_context(ticket: dict, comments: list, faqs: list) -> str:
        """
        Context Builder: Xây dựng ngữ cảnh gọn gàng, bảo mật cho AI.
        """
        ticket_title = AISupportService.sanitize_pii(ticket.get("title", ""))
        ticket_desc = AISupportService.sanitize_pii(ticket.get("description", ""))

        context_lines = [
            f"[THÔNG TIN TICKET]",
            f"Mã: {ticket.get('ticket_number')} | Tiêu đề: {ticket_title}",
            f"Mô tả sự cố: {ticket_desc}",
            f"Danh mục: {ticket.get('category')} | Mức ưu tiên: {ticket.get('priority')}",
            "",
            "[LỊCH SỬ TRAO ĐỔI GẦN ĐÂY]"
        ]

        if comments:
            for c in comments[-4:]: # Chỉ lấy 4 trao đổi gần nhất để tiết kiệm token
                sanitized_c = AISupportService.sanitize_pii(c.get("content", ""))
                context_lines.append(f"- {c.get('author_role', 'user')} ({c.get('author_name', '')}): {sanitized_c}")
        else:
            context_lines.append("(Chưa có trao đổi nào)")

        context_lines.append("\n[CƠ SỞ TRI THỨC VÀ CHÍNH SÁCH DOANH NGHIỆP]")
        if faqs:
            for faq in faqs:
                context_lines.append(f"Vấn đề: {faq.get('question')}\nGiải pháp chuẩn: {faq.get('answer')}\n")
        else:
            context_lines.append("Không có tài liệu FAQ khớp trực tiếp. Cần kiểm tra kỹ thông tin trước khi phản hồi.")

        return "\n".join(context_lines)

    @staticmethod
    def generate_with_gemini(system_instruction: str, user_prompt: str) -> str:
        """
        Gọi Google Gemini API nếu có API KEY; nếu không có hoặc lỗi, fallback qua rule-based generator.
        """
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if HAS_GENAI and api_key and api_key != "your_gemini_api_key_here":
            try:
                genai.configure(api_key=api_key)
                # Dùng model gemini-1.5-flash / gemini-pro
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=system_instruction
                )
                response = model.generate_content(user_prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[AISupportService] Lỗi kết nối Gemini API: {e}. Đang chuyển sang Fallback Engine.")

        return None

    @staticmethod
    def suggest_response(ticket: dict, comments: list) -> dict:
        """
        Gợi ý câu trả lời nháp (Draft Response Suggester) tuân thủ Human-in-the-Loop.
        """
        start_time = time.time()
        intent = AISupportService.analyze_ticket(ticket.get("title", ""), ticket.get("description", ""))
        faqs = AISupportService.retrieve_faqs(intent)
        context = AISupportService.build_context(ticket, comments, faqs)

        system_instruction = (
            "Bạn là Trợ lý AI hỗ trợ nhân viên chăm sóc khách hàng ViettinCare. "
            "Nhiệm vụ của bạn là SOẠN THẢO CÂU TRẢ LỜI NHÁP để nhân viên hỗ trợ duyệt trước khi gửi cho khách hàng.\n"
            "QUY TẮC BẮT BUỘC:\n"
            "1. Chỉ sử dụng thông tin trong phần [CƠ SỞ TRI THỨC VÀ CHÍNH SÁCH DOANH NGHIỆP].\n"
            "2. Xưng hô lịch sự, thân thiện: 'Dạ ViettinCare chào Quý khách...'\n"
            "3. TUYỆT ĐỐI KHÔNG cam kết hoàn tiền mặt ngay lập tức hoặc vi phạm chính sách nếu chưa có phê duyệt kế toán.\n"
            "4. Nếu thông tin chưa đủ, lịch sự yêu cầu khách hàng cung cấp thêm chi tiết (mã giao dịch, ảnh chụp màn hình).\n"
            "5. Không bịa đặt chính sách."
        )

        user_prompt = f"Dựa vào thông tin ngữ cảnh sau đây:\n\n{context}\n\nHãy soạn thảo một câu trả lời mẫu ngắn gọn, chuyên nghiệp và đầy đủ hướng dẫn giải quyết."

        raw_output = AISupportService.generate_with_gemini(system_instruction, user_prompt)

        # Fallback Engine chất lượng cao nếu chưa cấu hình API Key
        if not raw_output:
            faq_solution = faqs[0]['answer'] if faqs else "Nhân viên hỗ trợ đang tiến hành kiểm tra trên hệ thống trung tâm."
            raw_output = (
                f"Kính chào Quý khách {ticket.get('customer_name', '')},\n\n"
                f"Bộ phận Hỗ trợ Kỹ thuật ViettinCare đã tiếp nhận yêu cầu về sự cố: '{ticket.get('title')}'.\n\n"
                f"Dựa trên quy trình hỗ trợ tiêu chuẩn:\n"
                f"{faq_solution}\n\n"
                f"Nếu Quý khách cần hỗ trợ thêm hoặc sự cố vẫn tiếp diễn, vui lòng phản hồi trực tiếp tại ticket này để chúng tôi ưu tiên xử lý.\n\n"
                f"Trân trọng cảm ơn,\n"
                f"Đội ngũ Hỗ trợ ViettinCare"
            )

        latency_ms = int((time.time() - start_time) * 1000)

        # Ghi log kiểm toán AI
        AISupportService.log_ai_action(
            ticket_id=ticket.get("id"),
            action_type="suggest_response",
            input_context=context,
            raw_ai_output=raw_output,
            latency_ms=latency_ms
        )

        return {
            "draft_response": raw_output,
            "intent": intent,
            "matched_faqs": len(faqs),
            "latency_ms": latency_ms
        }

    @staticmethod
    def summarize_history(ticket: dict, comments: list) -> dict:
        """
        AI Tóm tắt chuỗi trao đổi dài thành các gạch đầu dòng cho nhân viên tiếp nhận ca.
        """
        start_time = time.time()
        context = AISupportService.build_context(ticket, comments, [])

        system_instruction = (
            "Bạn là trợ lý tóm tắt ticket cho nhân viên trực ca tiếp theo. "
            "Tóm tắt chuỗi hội thoại thành 3 ý chính:\n"
            "1. Vấn đề ban đầu của khách hàng\n"
            "2. Các bước/giải pháp đã thực hiện\n"
            "3. Hiện trạng và hành động cần tiếp tục xử lý"
        )
        user_prompt = f"Ngữ cảnh trao đổi:\n\n{context}\n\nHãy tóm tắt ngắn gọn dưới dạng 3 gạch đầu dòng."

        raw_output = AISupportService.generate_with_gemini(system_instruction, user_prompt)

        if not raw_output:
            raw_output = (
                f"• Khách hàng báo cáo sự cố: {ticket.get('title')}.\n"
                f"• Nhân viên tiếp nhận đã phản hồi hướng dẫn xử lý và chờ thông tin đối soát.\n"
                f"• Trạng thái hiện tại: {ticket.get('status')}. Cần tiếp tục theo dõi xác nhận từ khách hàng."
            )

        latency_ms = int((time.time() - start_time) * 1000)

        AISupportService.log_ai_action(
            ticket_id=ticket.get("id"),
            action_type="summarize",
            input_context=context,
            raw_ai_output=raw_output,
            latency_ms=latency_ms
        )

        return {
            "summary": raw_output,
            "latency_ms": latency_ms
        }

    @staticmethod
    def classify_ticket(title: str, description: str) -> dict:
        """
        AI Phân loại danh mục và mức ưu tiên gợi ý.
        """
        start_time = time.time()
        intent = AISupportService.analyze_ticket(title, description)
        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "category": intent["category"],
            "suggested_priority": intent["suggested_priority"],
            "keywords": intent["keywords"],
            "latency_ms": latency_ms
        }

    @staticmethod
    def log_ai_action(ticket_id, action_type, input_context, raw_ai_output, approved_output=None, is_approved=False, agent_id=None, latency_ms=0):
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_logs (ticket_id, action_type, input_context, raw_ai_output, approved_output, is_approved, agent_id, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ticket_id, action_type, input_context, raw_ai_output, approved_output, 1 if is_approved else 0, agent_id, latency_ms))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[AISupportService] Không thể ghi ai_logs: {e}")
