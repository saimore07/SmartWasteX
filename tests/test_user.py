"""
SmartWasteX — User Module & Dashboard Tests
===========================================
Validates user dashboard, activity history, campus leaderboard,
and environmental impact calculations.
"""

import pytest
from app import create_app
from config import Config
from models import db
from models.models import User, WasteScan, GreenCreditTransaction


class TestUserConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


@pytest.fixture
def client():
    app = create_app(TestUserConfig)
    with app.test_client() as client:
        # Authenticate as demo user
        client.post('/login', data={
            'email': 'user1@smartwastex.in',
            'password': 'user1@123'
        }, follow_redirects=True)
        yield client


@pytest.fixture
def unauth_client():
    app = create_app(TestUserConfig)
    with app.test_client() as client:
        yield client


def test_user_dashboard_authenticated(client):
    """Test user dashboard loads with rank, credits, and sustainability score."""
    response = client.get('/user/dashboard')
    assert response.status_code == 200
    assert b"Rahul Sharma" in response.data
    assert b"Campus Sustainability Index" in response.data
    assert b"Scan Waste" in response.data


def test_user_dashboard_unauthenticated_redirect(unauth_client):
    """Test unauthenticated user is redirected to login."""
    response = client = unauth_client.get('/user/dashboard')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_user_history_page(client):
    """Test user history displays transactions and waste scans."""
    response = client.get('/user/history')
    assert response.status_code == 200
    assert b"Personal Waste &amp; Credits Ledger" in response.data or b"Personal Waste & Credits Ledger" in response.data
    assert b"Cumulative Mass Diverted" in response.data


def test_user_leaderboard_page(client):
    """Test campus leaderboard loads champions and highlights current user."""
    response = client.get('/user/leaderboard')
    assert response.status_code == 200
    assert b"Campus Green Champions" in response.data
    assert b"Rahul Sharma" in response.data
    assert b"Real-Time Campus Standings" in response.data


def test_user_impact_page(client):
    """Test personal environmental impact metrics and equivalents."""
    response = client.get('/user/impact')
    assert response.status_code == 200
    assert b"Your Environmental Impact" in response.data
    assert b"Carbon Emissions Avoided" in response.data
    assert b"SDG 11 Climate Metrics" in response.data


def test_user_cannot_access_admin_dashboard(client):
    """Test standard user is blocked from admin dashboard."""
    response = client.get('/admin/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b"Access denied" in response.data
