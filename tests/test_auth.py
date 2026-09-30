import pytest
from app import create_app
from config import Config
from models import db
from models.models import User

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as client:
        yield client

def test_demo_user_login(client):
    """Verify demo user can log in with correct credentials and redirects to user dashboard."""
    response = client.post('/login', data={
        'email': 'user1@smartwastex.in',
        'password': 'user1@123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back, Rahul" in response.data or b"Dashboard" in response.data

def test_demo_admin_login(client):
    """Verify demo admin can log in with correct credentials and redirects to admin dashboard."""
    response = client.post('/login', data={
        'email': 'admin@smartwastex.in',
        'password': 'admin@123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Campus Sustainability Command Center" in response.data

def test_invalid_login(client):
    """Verify invalid password fails with error message."""
    response = client.post('/login', data={
        'email': 'user1@smartwastex.in',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data

def test_role_protection_user_cannot_access_admin(client):
    """Verify normal user cannot access admin routes."""
    # Login as user
    client.post('/login', data={
        'email': 'user1@smartwastex.in',
        'password': 'user1@123'
    }, follow_redirects=True)

    # Attempt to access admin dashboard
    response = client.get('/admin/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b"Access denied" in response.data
    # Confirms redirected back to user dashboard
    assert b"Welcome back" in response.data or b"Scan New Waste" in response.data

def test_logout(client):
    """Verify user can safely log out."""
    client.post('/login', data={
        'email': 'user1@smartwastex.in',
        'password': 'user1@123'
    }, follow_redirects=True)

    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"logged out" in response.data

def test_health_check(client):
    """Verify /health endpoint returns 200 with status ok."""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json() == {'status': 'ok'}

def test_public_homepage(client):
    """Verify public homepage loads at root / with expected content."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"SmartWaste" in response.data
    assert b"cleaner campuses and smarter cities" in response.data
    assert b"Login" in response.data
    assert b"Explore SmartWasteX" in response.data

def test_login_with_username_prefix(client):
    """Verify user can log in with username prefix without domain."""
    response = client.post('/login', data={
        'email': 'user1',
        'password': 'user1@123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back, Rahul" in response.data
