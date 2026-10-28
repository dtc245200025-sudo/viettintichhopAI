# Tài liệu Tích hợp Model Context Protocol (MCP) — VietinCare AI

> **Tham chiếu phương pháp luận:** Phần XXV & XXVI — *1_Thuc_hanh_AI_Augmented_SDLC.docx*  
> **Module thực thi:** [backend/mcp_server.py](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/backend/mcp_server.py)  
> **Kiểm thử tự động:** [tests/test_mcp_server.py](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/tests/test_mcp_server.py)

---

## 1. Giới thiệu về Model Context Protocol (MCP)

**Model Context Protocol (MCP)** là một chuẩn giao tiếp mở (open standard) do Anthropic khởi xướng, cho phép các mô hình AI (LLM / Agent) kết nối và truy xuất ngữ cảnh an toàn từ các nguồn dữ liệu bên ngoài, cơ sở dữ liệu nội bộ và các công cụ phát triển phần mềm (IDE, Issue Tracker, Git Repository).

Trong kiến trúc của **VietinCare AI**, MCP đóng vai trò là cây cầu nối chuẩn hóa (Standardized Bridge) giúp AI Agent không chỉ trả lời theo tri thức tĩnh mà có thể:
1. Truy vấn trực tiếp các đoạn tri thức nghiệp vụ ngân hàng từ kho dữ liệu MySQL (`KnowledgeBase` & `KnowledgeChunk`).
2. Tra cứu chi tiết trạng thái ca hỗ trợ (Ticket Lifecycle, SLA).
3. Đánh giá hồ sơ rủi ro và lịch sử tương tác của khách hàng.

---

## 2. Kiến trúc Hệ thống MCP của VietinCare AI

```
+-------------------------------------------------------------+
|                     AI Agent Client                         |
|     (Gemini API / Antigravity Agent / Claude Client)        |
+-------------------------------------------------------------+
                              |
                     JSON-RPC 2.0 (stdio)
                              |
+-------------------------------------------------------------+
|             VietinCare MCP Server (mcp_server.py)           |
+-------------------------------------------------------------+
      |                       |                       |
      v                       v                       v
[search_banking_knowledge] [get_ticket_details]  [check_customer_profile]
      |                       |                       |
      +-----------------------+-----------------------+
                              |
            MySQL Database Layer (qlkhviettin)
```

---

## 3. Danh mục Công cụ (Tools Schema)

### 3.1. Tool: `search_banking_knowledge`
- **Mục đích:** Tra cứu ngữ nghĩa trong kho tri thức ngân hàng (biểu phí thẻ, quy định mở khóa thẻ, hướng dẫn đăng ký iPay).
- **Tham số đầu vào:**
  - `query` (*string, required*): Câu hỏi hoặc từ khóa cần tra cứu.
  - `category` (*string, optional*): Danh mục (`Tài khoản`, `Thẻ tín dụng`, `E-Banking`, `Tiết kiệm`).
  - `limit` (*integer, default 3*): Số đoạn trích tối đa trả về.
- **Dữ liệu đầu ra:** Danh sách các đoạn trích (chunks) kèm điểm tương đồng (Cosine Similarity).

### 3.2. Tool: `get_ticket_details`
- **Mục đích:** Cung cấp cho AI Agent thông tin chi tiết về ca hỗ trợ đang xử lý.
- **Tham số đầu vào:**
  - `ticket_id` (*integer, required*): Mã định danh Ticket.
- **Dữ liệu đầu ra:** Tiêu đề, mô tả, trạng thái vòng đời, mức độ ưu tiên, thời gian SLA còn lại và nhân viên phụ trách.

### 3.3. Tool: `check_customer_profile`
- **Mục đích:** Kiểm tra thông tin định danh và phân loại mức độ rủi ro trước khi AI đưa ra gợi ý giải pháp.
- **Tham số đầu vào:**
  - `customer_id` (*integer, required*): Mã khách hàng.
- **Dữ liệu đầu ra:** Phân hạng khách hàng (VIP/Standard), trạng thái KYC, lịch sử cảm xúc (Sentiment history).

---

## 4. Cấu hình MCP Client (Ví dụ cho Antigravity / Claude Desktop)

Để tích hợp `vietincare-mcp-server` vào môi trường AI Agent, cấu hình file `mcp_config.json` như sau:

```json
{
  "mcpServers": {
    "vietincare-ai": {
      "command": ".\\.venv-1\\Scripts\\python.exe",
      "args": ["backend/mcp_server.py"],
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}
```

---

## 5. Kết quả Kiểm thử & Nghiệm thu MCP

Module MCP Server đã được kiểm thử tự động tại [tests/test_mcp_server.py](file:///d:/OneDrive/Documents/3%20-%201/Tri%20tue%20nhan%20tao/viettintichhopAI/tests/test_mcp_server.py):
- `test_mcp_initialize`: Pass 100% (Giao thức JSON-RPC 2.0 bắt tay thành công).
- `test_mcp_tools_list`: Pass 100% (Khai báo đủ 3 Tools nghiệp vụ).
- `test_mcp_tool_call_search_knowledge`: Pass 100% (Trả về dữ liệu tri thức đúng cấu trúc JSON).
- `test_mcp_unknown_method`: Pass 100% (Xử lý lỗi -32601 chuẩn JSON-RPC).

