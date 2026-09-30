import pytest
from app import create_app
from config import Config
from models import db
from models.models import Bin, CollectionRequest

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

@pytest.fixture
def admin_client():
    app = create_app(TestConfig)
    with app.test_client() as client:
        # Log in as demo admin
        client.post('/login', data={
            'email': 'admin@smartwastex.in',
            'password': 'admin@123'
        }, follow_redirects=True)
        yield client

def test_admin_bins_view(admin_client):
    """Test smart bins page lists all 4 receptacles."""
    response = admin_client.get('/admin/bins')
    assert response.status_code == 200
    assert b"BIN-01" in response.data
    assert b"BIN-02" in response.data
    assert b"BIN-03" in response.data
    assert b"BIN-04" in response.data

def test_bin_simulate_delta(admin_client):
    """Test simulating +10% fill on a bin."""
    bin_obj = db.session.get(Bin, 'BIN-01')
    initial_fill = bin_obj.fill_percentage

    response = admin_client.post('/api/bins/BIN-01/simulate', json={
        'action': 'plus_10'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['bin']['fill_percentage'] == initial_fill + 10.0

def test_overflow_alert_creates_collection_request(admin_client):
    """Test pushing bin to 100% capacity triggers URGENT overflow and creates collection ticket."""
    response = admin_client.post('/api/bins/BIN-04/simulate', json={
        'action': 'set_fill',
        'fill': 100.0
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['bin']['status'] == 'OVERFLOW'
    assert data['alert']['priority'] == 'URGENT'

    # Check database collection request
    req = CollectionRequest.query.filter_by(bin_id='BIN-04', priority='URGENT').first()
    assert req is not None
    assert req.status in ['PENDING', 'ASSIGNED']

def test_empty_bin_resets_and_resolves_tickets(admin_client):
    """Test emptying bin resets fill to 0% and completes pending tickets."""
    # Ensure bin has high fill
    admin_client.post('/api/bins/BIN-04/simulate', json={'action': 'set_fill', 'fill': 95.0})
    
    # Empty bin
    response = admin_client.post('/api/bins/BIN-04/simulate', json={'action': 'empty'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['bin']['fill_percentage'] == 0.0
    assert data['bin']['status'] == 'NORMAL'

    # Check ticket is completed
    completed_reqs = CollectionRequest.query.filter_by(bin_id='BIN-04', status='COMPLETED').all()
    assert len(completed_reqs) > 0

def test_iot_bin_update_api(admin_client):
    """Test public IoT gateway endpoint for external hardware sensor simulator."""
    # Test setting fill level
    response = admin_client.post('/api/iot/bin-update', json={
        'bin_id': 'BIN-02',
        'fill_level': 75.5
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['bin_id'] == 'BIN-02'
    assert data['fill_level'] == 75.5
    assert data['status'] == 'WARNING'

    # Test padded bin ID resolution (e.g. BIN-002 -> BIN-02)
    response_padded = admin_client.post('/api/iot/bin-update', json={
        'bin_id': 'BIN-002',
        'fill_level': 88.0
    })
    assert response_padded.status_code == 200
    assert response_padded.get_json()['status'] == 'HIGH'

    # Test empty action
    empty_resp = admin_client.post('/api/iot/bin-update', json={
        'bin_id': 'BIN-02',
        'action': 'empty'
    })
    assert empty_resp.status_code == 200
    assert empty_resp.get_json()['fill_level'] == 0.0
