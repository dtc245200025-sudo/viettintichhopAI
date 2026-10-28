import pytest
from app import create_app
from database.db import init_db

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_unauthenticated_redirects(client):
    assert client.get('/dashboard').status_code == 302
    assert client.get('/tickets').status_code == 302
    assert client.get('/customers/').status_code == 302

def test_login_and_authenticated_routes(client):
    init_db()
    # 1. Login
    res = client.post('/login', data={'username': 'admin', 'password': 'Admin@123'}, follow_redirects=True)
    assert res.status_code == 200

    # 2. Dashboard
    res = client.get('/dashboard')
    assert res.status_code == 200
    assert b"stat-card" in res.data

    # 3. Tickets list
    res = client.get('/tickets')
    assert res.status_code == 200
    assert b"TCK-1001" in res.data

    # 4. Ticket Detail
    res = client.get('/tickets/1')
    assert res.status_code == 200
    assert b"TCK-1001" in res.data

    # 5. Customers list
    res = client.get('/customers/')
    assert res.status_code == 200
    assert b"hoang.pm@gmail.com" in res.data

    # 6. AI Classify API
    res = client.post('/api/ai/classify', json={'title': 'Không đổi được mật khẩu', 'description': 'Quên pass'})
    assert res.status_code == 200
    assert res.json['category'] == "Tài khoản & Đăng nhập"

    # 7. AI Suggest API (RAG Draft)
    res = client.post('/api/ai/suggest', json={'ticket_id': 1})
    assert res.status_code == 200
    assert 'draft_response' in res.json

    # 8. AI Summarize API
    res = client.post('/api/ai/summarize', json={'ticket_id': 1})
    assert res.status_code == 200
    assert 'summary' in res.json

    # 9. AI Human Gate (Approve & Send)
    res = client.post('/api/ai/approve-and-send', json={
        'ticket_id': 1,
        'content': 'Dạ ViettinCare đã kiểm tra và hỗ trợ giải quyết sự cố cho Quý khách.'
    })
    assert res.status_code == 200
    assert res.json['success'] is True

    # 10. Logout
    res = client.get('/logout', follow_redirects=True)
    assert res.status_code == 200

