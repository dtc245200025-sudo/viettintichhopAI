import pytest
from app import create_app
from services.auth_service import AuthService
from database.db import init_db

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_auth_success():
    init_db()
    user = AuthService.authenticate('admin', 'Admin@123')
    assert user is not None
    assert user['username'] == 'admin'
    assert user['role'] == 'admin'

def test_auth_failure():
    init_db()
    user = AuthService.authenticate('admin', 'WrongPass')
    assert user is None

def test_login_route_get(client):
    res = client.get('/login')
    assert res.status_code == 200
    assert b"ViettinCare Support" in res.data

