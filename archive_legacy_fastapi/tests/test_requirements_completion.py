"""Regression checks for the missing topic-10 workflows (database doubles)."""
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings


class DatabaseDouble:
    def __init__(self, role='Supervisor', status='Đang xử lý', agent=12):
        self.role, self.status, self.agent = role, status, agent
        self.executed = []
        self.reads = []
        self.customer = {'id': 5, 'userId': 8, 'name': 'Demo', 'email': 'demo@example.test', 'phone': None, 'isActive': True}

    def fetch_one(self, sql, args=()):
        self.reads.append((sql, args))
        if 'FROM AuthSession' in sql:
            return {'MaUser': 12, 'MaKH': 5, 'TenRole': self.role, 'HoTen': 'Demo', 'Email': 'demo@example.test'}
        if 'SELECT TrangThai FROM UserAccount' in sql:
            return {'TrangThai': 1}
        if 'SELECT MaUser FROM UserAccount' in sql:
            return {'MaUser': 8}
        if 'SELECT MaUser FROM Customer' in sql:
            return {'MaUser': 8}
        if 'FROM Customer c' in sql:
            return self.customer.copy()
        if 'FROM Ticket t WHERE' in sql:
            return {'id': 31, 'customerId': 5, 'agentId': self.agent, 'status': self.status, 'title': 'Old', 'content': 'Old text'}
        if 'FROM TicketCategory WHERE' in sql:
            return {'MaCategory': 1} if args[0] == 1 else None
        return None

    def fetch_all(self, sql, args=()):
        self.reads.append((sql, args))
        if 'FROM Customer c' in sql:
            return [self.customer.copy()]
        if 'FROM TicketAIAnalysis' in sql:
            return [{'id': 4, 'summary': 'Saved summary', 'status': 'Pending'}]
        return []

    def execute(self, sql, args=()):
        self.executed.append((sql, args))
        return 1

    @contextmanager
    def transaction(self):
        yield self


def client_for(db):
    settings = Settings.from_env({'APP_ORIGIN': 'http://localhost:3000'})
    client = TestClient(create_app(database=db, settings=settings))
    client.cookies.set('vietincare_session', 'b' * 64)
    client.headers.update({'Origin': settings.origin, 'X-Vietincare-Request': '1',
                           'Idempotency-Key': '12345678-1234-4234-8234-123456789abc'})
    return client


@pytest.mark.parametrize('role', ['Admin', 'Supervisor'])
def test_customer_contacts_and_history_are_available_to_managers(role):
    db = DatabaseDouble(role)
    with client_for(db) as client:
        assert client.get('/api/customers?query=Demo').json()['customers'][0]['id'] == 5
        assert client.get('/api/customers/5').json()['customer']['email'] == 'demo@example.test'
        result = client.patch('/api/customers/5', json={'fullName': 'Updated', 'email': 'new@example.test', 'phone': ''})
        assert result.status_code == 200
        assert any(sql.startswith('UPDATE Customer') for sql, _ in db.executed)
        assert any(sql.startswith('UPDATE UserAccount') for sql, _ in db.executed)
        assert any('CUSTOMER_UPDATE' in sql for sql, _ in db.executed)


@pytest.mark.parametrize('role', ['Customer', 'Agent'])
def test_customer_directory_denies_unprivileged_roles(role):
    db = DatabaseDouble(role)
    with client_for(db) as client:
        assert client.get('/api/customers').status_code == 403
        assert client.get('/api/customers/5').status_code == 403
        assert client.patch('/api/customers/5', json={'fullName': 'No'}).status_code == 403
    assert not db.executed


@pytest.mark.parametrize('payload', [{'role': 'Admin'}, {'password': 'not-allowed'}, {'email': 'invalid'}, {}])
def test_customer_editor_cannot_escalate_roles_or_accept_invalid_fields(payload):
    db = DatabaseDouble()
    with client_for(db) as client:
        assert client.patch('/api/customers/5', json=payload).status_code == 400
    assert not db.executed


@pytest.mark.parametrize('role', ['Agent', 'Supervisor'])
def test_ticket_edit_updates_content_category_and_audit(role):
    db = DatabaseDouble(role)
    with client_for(db) as client:
        response = client.post('/api/tickets/31/details', json={'title': ' New title ', 'content': 'New content', 'categoryId': 1})
    assert response.status_code == 200
    update = next(args for sql, args in db.executed if sql.startswith('UPDATE Ticket SET TieuDe'))
    assert update == ('New title', 'New content', 1, 31)
    assert any('TICKET_DETAILS' in args for _, args in db.executed)
    assert not any('INSERT INTO TicketReply' in sql for sql, _ in db.executed)


@pytest.mark.parametrize('role,status,agent,code', [
    ('Customer', 'Đang xử lý', 12, 403), ('Agent', 'Mới', 12, 403),
    ('Agent', 'Đang xử lý', 99, 403), ('Supervisor', 'Đã đóng', 12, 409),
])
def test_ticket_editor_checks_role_assignment_and_closed_state(role, status, agent, code):
    db = DatabaseDouble(role, status, agent)
    with client_for(db) as client:
        assert client.post('/api/tickets/31/details', json={'title': 'New', 'content': 'Text'}).status_code == code
    assert not db.executed


@pytest.mark.parametrize('value', ['2026-02-30', '2026-13-01', 'invalid'])
def test_ticket_filters_reject_nonexistent_calendar_dates(value):
    with client_for(DatabaseDouble()) as client:
        assert client.get('/api/tickets', params={'startDate': value}).status_code == 400


def test_saved_ai_analysis_visible_to_staff_but_not_customer():
    for role in ('Agent', 'Supervisor', 'Customer'):
        db = DatabaseDouble(role)
        with client_for(db) as client:
            result = client.get('/api/tickets/31')
            assert result.status_code == 200
            assert bool(result.json()['analyses']) == (role != 'Customer')
        assert not db.executed


def test_customer_search_uses_bound_parameters():
    db = DatabaseDouble()
    with client_for(db) as client:
        assert client.get('/api/customers', params={'query': "' OR 1=1 --"}).status_code == 200
    sql, args = next((sql, args) for sql, args in db.reads if 'FROM Customer c' in sql)
    assert 'OR 1=1' not in sql
    assert "%' OR 1=1 --%" in args
