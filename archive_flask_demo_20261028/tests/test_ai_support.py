import pytest
from app import create_app
from services.ai_support_service import AISupportService
from services.ticket_service import TicketService
from database.db import init_db

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_pii_sanitization():
    raw_text = "Mật khẩu của tôi là Pass@123456 và số thẻ là 4532-1111-2222-3333, liên hệ 0912345678"
    sanitized = AISupportService.sanitize_pii(raw_text)

    assert "Pass@123456" not in sanitized
    assert "[MASKED_PASSWORD]" in sanitized
    assert "4532-1111-2222-3333" not in sanitized
    assert "[MASKED_CREDIT_CARD]" in sanitized
    assert "0912345678" not in sanitized
    assert "[MASKED_PHONE]" in sanitized

def test_ai_ticket_classification():
    title = "Không thể đăng nhập sau khi đổi mật khẩu"
    desc = "Bị khóa tài khoản do nhập sai mật khẩu nhiều lần"
    res = AISupportService.classify_ticket(title, desc)

    assert res['category'] == "Tài khoản & Đăng nhập"
    assert res['suggested_priority'] in ["High", "Medium"]
    assert "đổi mật khẩu" in res['keywords'] or "reset" in res['keywords']

def test_faq_retrieval():
    init_db()
    intent = {
        "category": "Tài khoản & Đăng nhập",
        "keywords": ["đổi mật khẩu", "reset", "email"]
    }
    faqs = AISupportService.retrieve_faqs(intent)
    assert len(faqs) > 0
    assert any("email" in f['question'].lower() or "mật khẩu" in f['question'].lower() for f in faqs)

def test_ai_suggest_response_fallback_and_guardrail():
    init_db()
    ticket = TicketService.get_ticket_by_id(1)
    comments = TicketService.get_comments(1)

    result = AISupportService.suggest_response(ticket, comments)
    assert "draft_response" in result
    assert len(result["draft_response"]) > 20
    # Guardrail check: Response should be polite
    assert "Kính chào" in result["draft_response"] or "ViettinCare" in result["draft_response"]

def test_ai_summarize_history():
    init_db()
    ticket = TicketService.get_ticket_by_id(1)
    comments = TicketService.get_comments(1)

    result = AISupportService.summarize_history(ticket, comments)
    assert "summary" in result
    assert len(result["summary"]) > 10
    assert "•" in result["summary"] or "-" in result["summary"]


