import json
from backend.mcp_server import process_mcp_message, MCP_TOOLS


def test_mcp_initialize() -> None:
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    resp = process_mcp_message(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "vietincare-mcp-server"
    assert "tools" in resp["result"]["capabilities"]


def test_mcp_tools_list() -> None:
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    resp = process_mcp_message(req)
    assert resp["id"] == 2
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "search_banking_knowledge" in tool_names
    assert "get_ticket_details" in tool_names
    assert "check_customer_profile" in tool_names


def test_mcp_tool_call_search_knowledge() -> None:
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_banking_knowledge",
            "arguments": {"query": "khóa thẻ iPay"}
        }
    }
    resp = process_mcp_message(req)
    assert resp["id"] == 3
    content = resp["result"]["content"]
    assert len(content) > 0
    data = json.loads(content[0]["text"])
    assert data["query"] == "khóa thẻ iPay"
    assert len(data["results"]) >= 1


def test_mcp_unknown_method() -> None:
    req = {
        "jsonrpc": "2.0",
        "id": 99,
        "method": "unknown/method",
        "params": {}
    }
    resp = process_mcp_message(req)
    assert "error" in resp
    assert resp["error"]["code"] == -32601

