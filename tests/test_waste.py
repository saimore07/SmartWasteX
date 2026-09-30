import pytest
from app import create_app
from config import Config
from models import db
from models.models import User, WasteScan, GreenCreditTransaction

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as client:
        # Log in as demo user
        client.post('/login', data={
            'email': 'user1@smartwastex.in',
            'password': 'user1@123'
        }, follow_redirects=True)
        yield client

def test_waste_scan_battery(client):
    """Test AI classification of hazardous/e-waste battery."""
    response = client.post('/user/scan', data={
        'sample_item': 'battery'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"AI Waste Analysis" in response.data
    assert b"Battery" in response.data
    assert b"Hazardous / E-Waste" in response.data
    assert b"+25" in response.data

def test_waste_scan_banana_peel(client):
    """Test AI classification of biodegradable banana peel."""
    response = client.post('/user/scan', data={
        'sample_item': 'banana_peel'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Banana Peel" in response.data
    assert b"Biodegradable" in response.data
    assert b"+5" in response.data

def test_confirm_disposal_awards_credits(client):
    """Test that confirming disposal increases Green Credits and logs transaction."""
    # 1. First trigger scan
    client.post('/user/scan', data={'sample_item': 'battery'}, follow_redirects=True)
    scan = WasteScan.query.filter_by(detected_item='Lithium Battery').order_by(WasteScan.id.desc()).first()
    assert scan is not None

    initial_user = User.query.filter_by(email='user1@smartwastex.in').first()
    initial_credits = initial_user.green_credits

    # 2. Confirm disposal
    confirm_resp = client.post(f'/user/waste/confirm/{scan.id}', follow_redirects=True)
    assert confirm_resp.status_code == 200
    assert b"Disposal Confirmed" in confirm_resp.data

    # 3. Check DB points updated
    updated_user = User.query.filter_by(email='user1@smartwastex.in').first()
    assert updated_user.green_credits == initial_credits + scan.credits_awarded

    # 4. Check transaction logged
    txn = GreenCreditTransaction.query.filter_by(reference_id=f"SCAN-{scan.id}").first()
    assert txn is not None
    assert txn.amount == scan.credits_awarded

def test_leaderboard_page(client):
    """Test leaderboard displays campus champions and highlights current user."""
    response = client.get('/user/leaderboard')
    assert response.status_code == 200
    assert b"Campus Green Champions" in response.data
    assert b"Rahul Sharma" in response.data
    assert b"Real-Time Campus Standings" in response.data
