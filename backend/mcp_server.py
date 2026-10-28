"""
VietinCare AI - Model Context Protocol (MCP) Server
Cung cấp các Tool chuẩn MCP (Model Context Protocol - JSON-RPC 2.0)
giúp AI Agent truy xuất ngữ cảnh tri thức ngân hàng và thông tin Ticket.
Tuân thủ Phần XXV & XXVI của tài liệu AI-Augmented SDLC.
"""

from __future__ import annotations

import json
import sys
from typing import Any

MCP_SERVER_NAME = "vietincare-mcp-server"
MCP_SERVER_VERSION = "1.0.0"

# Danh sách công cụ (Tools) được khai báo theo chuẩn MCP
MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_banking_knowledge",
        "description": "Truy xuất cơ sở tri thức ngân hàng VietinCare (FAQ, quy định biểu phí, chính sách thẻ, chuyển tiền)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Từ khóa hoặc câu hỏi cần tra cứu ngữ nghĩa",
                },
                "category": {
                    "type": "string",
                    "description": "Danh mục nghiệp vụ (Tài khoản, Thẻ tín dụng, E-Banking, Tiết kiệm)",
                    "enum": ["Tài khoản", "Thẻ tín dụng", "E-Banking", "Tiết kiệm", "Khác"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Số lượng đoạn trích tối đa trả về (mặc định 3)",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_ticket_details",
        "description": "Lấy chi tiết yêu cầu hỗ trợ (Ticket), lịch sử trao đổi và trạng thái SLA",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "Mã số định danh của Ticket (MaTicket)",
                },
            },
            "required": ["ticket_id"],
        },
    },
    {
        "name": "check_customer_profile",
        "description": "Tra cứu hồ sơ khách hàng, phân hạng rủi ro và lịch sử các ca hỗ trợ gần nhất",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "integer",
                    "description": "Mã khách hàng (MaKH)",
                },
            },
            "required": ["customer_id"],
        },
    },
]


def handle_tool_call(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Xử lý thực thi tool call và trả lời theo format nội dung của MCP"""
    if tool_name == "search_banking_knowledge":
        query = arguments.get("query", "")
        category = arguments.get("category", "Tất cả")
        # Giả lập kết quả trích xuất từ KnowledgeBase và KnowledgeChunk
        mock_chunks = [
            {
                "title": "Hướng dẫn khóa thẻ khẩn cấp qua iPay",
                "category": "Thẻ tín dụng",
                "content": "Khách hàng có thể khóa thẻ tức thì trên ứng dụng VietinBank iPay mục Dịch vụ thẻ -> Khóa thẻ, hoặc gọi tổng đài 1900 558 868 nhánh 1.",
                "relevance_score": 0.95,
            },
            {
                "title": "Biểu phí duy trì dịch vụ iPay Mobile",
                "category": "E-Banking",
                "content": "VietinBank miễn phí duy trì và chuyển khoản trọn đời trên VietinBank iPay Mobile từ ngày 01/01/2023.",
                "relevance_score": 0.88,
            },
        ]
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"query": query, "category": category, "results": mock_chunks},
                        ensure_ascii=False,
                        indent=2,
                    ),
                }
            ]
        }

    elif tool_name == "get_ticket_details":
        ticket_id = arguments.get("ticket_id")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "ticketId": ticket_id,
                            "title": "Yêu cầu tra soát giao dịch thẻ ATM lỗi trừ tiền",
                            "status": "Đang xử lý",
                            "priority": "Cao",
                            "slaRemainingHours": 4.5,
                            "category": "Thẻ tín dụng",
                            "assignedAgent": "Lưu Thùy Linh",
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                }
            ]
        }

    elif tool_name == "check_customer_profile":
        customer_id = arguments.get("customer_id")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "customerId": customer_id,
                            "tier": "VIP Gold",
                            "kycStatus": "VERIFIED",
                            "sentimentHistory": ["Trung tính", "Tích cực"],
                            "totalTickets": 3,
                            "resolvedTickets": 2,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                }
            ]
        }

    return {
        "isError": True,
        "content": [{"type": "text", "text": f"Tool '{tool_name}' không tồn tại trong hệ thống."}],
    }


def process_mcp_message(message: dict[str, Any]) -> dict[str, Any] | None:
    """Xử lý một thông điệp JSON-RPC 2.0 gửi đến MCP Server"""
    msg_id = message.get("id")
    method = message.get("method")
    params = message.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": MCP_SERVER_NAME,
                    "version": MCP_SERVER_VERSION,
                },
                "capabilities": {
                    "tools": {"listChanged": False},
                },
            },
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": MCP_TOOLS,
            },
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = handle_tool_call(tool_name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result,
        }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {
            "code": -32601,
            "message": f"Method '{method}' not found",
        },
    }


def run_stdio_server() -> None:
    """Vận hành server qua chuẩn Standard I/O (stdin/stdout)"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = process_mcp_message(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_server()

