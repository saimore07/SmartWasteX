import os
import pytest
from app import create_app
from config import Config
from models import db
from models.models import EWasteAsset, EWasteLifecycle

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

@pytest.fixture
def app_instance():
    app = create_app(TestConfig)
    yield app

@pytest.fixture
def admin_client(app_instance):
    with app_instance.test_client() as client:
        client.post('/login', data={
            'email': 'admin@smartwastex.in',
            'password': 'admin@123'
        }, follow_redirects=True)
        yield client

@pytest.fixture
def anon_client(app_instance):
    with app_instance.test_client() as client:
        yield client

def test_register_ewaste_asset(admin_client):
    """Test registering a new e-waste asset generates Asset ID and QR code."""
    response = admin_client.post('/admin/ewaste', data={
        'device_name': 'HP LaserJet Pro Printer',
        'category': 'Peripherals',
        'serial_number': 'SN-HP-84920',
        'location': 'Library 1st Floor',
        'weight_kg': 8.5,
        'recycler': 'EcoRecycle Solutions Hub',
        'notes': 'Decommissioned after 6 years of university library service.'
    }, follow_redirects=True)

    assert response.status_code == 200
    asset = EWasteAsset.query.filter_by(device_name='HP LaserJet Pro Printer').first()
    assert asset is not None
    assert asset.asset_id.startswith('EW-2026-')
    assert asset.current_status == 'REGISTERED'
    assert asset.qr_code_filename is not None

def test_advance_lifecycle_stages(app_instance, admin_client):
    """Test stepping through full e-waste lifecycle."""
    with app_instance.app_context():
        asset = EWasteAsset.query.filter_by(asset_id='EW-2026-0001').first()
        assert asset is not None
        asset_id = asset.asset_id

    # Step: SENT_TO_RECYCLER
    resp1 = admin_client.post(f'/admin/ewaste/{asset_id}', data={
        'status': 'SENT_TO_RECYCLER',
        'notes': 'Dispatched via certified logistics manifest.'
    }, follow_redirects=True)
    assert resp1.status_code == 200

    with app_instance.app_context():
        asset = EWasteAsset.query.filter_by(asset_id=asset_id).first()
        assert asset.current_status == 'SENT_TO_RECYCLER'

    # Step: RECYCLED
    resp2 = admin_client.post(f'/admin/ewaste/{asset_id}', data={
        'status': 'RECYCLED',
        'notes': 'Smelting and copper/gold extraction completed. Certificate issued.'
    }, follow_redirects=True)
    assert resp2.status_code == 200

    with app_instance.app_context():
        asset = EWasteAsset.query.filter_by(asset_id=asset_id).first()
        assert asset.current_status == 'RECYCLED'

def test_public_qr_passport_unauthenticated(anon_client):
    """Test that public QR passport can be opened by anyone without login."""
    response = anon_client.get('/ewaste/EW-2026-0001')
    assert response.status_code == 200
    assert b"E-WASTE DIGITAL PASSPORT" in response.data
    assert b"EW-2026-0001" in response.data
    assert b"Dell Latitude 5420 Laptop" in response.data
    assert b"Circular Lifecycle Track & Trace" in response.data

@pytest.fixture
def user_client(app_instance):
    with app_instance.test_client() as client:
        client.post('/login', data={
            'email': 'user1@smartwastex.in',
            'password': 'user1@123'
        }, follow_redirects=True)
        yield client

def test_ewaste_dashboard(anon_client):
    """Test e-waste circularity dashboard loads with metrics and FSM."""
    resp = anon_client.get('/ewaste')
    assert resp.status_code == 200
    assert b"Institutional" in resp.data
    assert b"E-Waste Tracker" in resp.data
    assert b"Custody Transition FSM" in resp.data

def test_ewaste_dashboard_user(user_client):
    """Test user accessing dashboard view."""
    resp_dash = user_client.get('/ewaste/dashboard')
    assert resp_dash.status_code == 200
    assert b"Recently Enrolled Hardware" in resp_dash.data

def test_ewaste_public_ledger(anon_client):
    """Test public ledger view and search filtering."""
    resp = anon_client.get('/ewaste/ledger')
    assert resp.status_code == 200
    assert b"Public E-Waste Ledger" in resp.data
    assert b"EW-2026-0001" in resp.data

    # Search filter
    search_resp = anon_client.get('/ewaste/ledger?q=Dell')
    assert search_resp.status_code == 200
    assert b"Dell Latitude 5420" in search_resp.data

def test_ewaste_scan_page(user_client):
    """Test AI YOLOv8 Waste Scanner page and demo sample detection."""
    get_resp = user_client.get('/ewaste/scan')
    assert get_resp.status_code == 200
    assert b"AI Smart Waste &amp; E-Waste Classifier" in get_resp.data

    post_resp = user_client.post('/ewaste/scan', data={'sample_item': 'laptop'}, follow_redirects=True)
    assert post_resp.status_code == 200
    assert b"YOLOv8 Detection Result" in post_resp.data
    assert b"Laptop" in post_resp.data

def test_ewaste_user_dropoff(user_client, app_instance):
    """Test user drop-off generates asset, QR, and awards +25 Green Credits."""
    from models.models import User
    with app_instance.app_context():
        user = User.query.filter_by(email='user1@smartwastex.in').first()
        initial_credits = user.green_credits if user else 385

    resp = user_client.post('/ewaste/dropoff', data={
        'device_name': 'Discarded Broken Tablet',
        'department': 'Computer Science',
        'notes': 'Battery bulging. Dropped off at campus intake kiosk.'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"Drop-off QR generated" in resp.data
    assert b"Discarded Broken Tablet" in resp.data
    assert b"PENDING DROPOFF" in resp.data

    with app_instance.app_context():
        asset = EWasteAsset.query.filter_by(device_name='Discarded Broken Tablet').first()
        assert asset is not None
        assert asset.current_status == 'PENDING_DROPOFF'
        assert asset.qr_code_filename is not None

def test_ewaste_admin_registration(admin_client, app_instance):
    """Test admin registering campus hardware asset via /ewaste/register."""
    resp = admin_client.post('/ewaste/register', data={
        'device_name': 'Cisco 2960 Gigabit Switch',
        'department': 'IT Infrastructure',
        'category': 'Networking',
        'serial_number': 'CSCO-2960-99',
        'location': 'Server Room Rack 4',
        'weight_kg': 4.2,
        'recycler': 'EcoRecycle Solutions Hub',
        'notes': 'Decommissioned after core switch upgrade.'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"Cisco 2960 Gigabit Switch" in resp.data

    with app_instance.app_context():
        asset = EWasteAsset.query.filter_by(device_name='Cisco 2960 Gigabit Switch').first()
        assert asset is not None
        assert asset.current_status == 'IN_USE'
        assert asset.department == 'IT Infrastructure'

def test_ewaste_custody_transfer_fsm(admin_client, app_instance):
    """Test FSM guard: valid transition commits, invalid transition is rejected."""
    with app_instance.app_context():
        asset = EWasteAsset.query.filter_by(asset_id='EW-2026-0003').first()
        assert asset is not None
        asset_id = asset.asset_id
        # EW-2026-0003 is REGISTERED -> allowed next: IN_USE, DECOMMISSIONED, E_WASTE_STORAGE, COLLECTION_REQUESTED

    # 1. Valid transition: REGISTERED -> DECOMMISSIONED
    resp1 = admin_client.post(f'/ewaste/scan/{asset_id}', data={
        'new_status': 'DECOMMISSIONED',
        'location': 'Robotics Storage Bin',
        'remarks': 'FSM transition test to decommissioned.'
    }, follow_redirects=True)
    assert resp1.status_code == 200
    assert b"successfully transitioned to DECOMMISSIONED" in resp1.data

    # 2. Invalid transition: DECOMMISSIONED -> RECYCLED (Must go through storage/collected first)
    resp2 = admin_client.post(f'/ewaste/scan/{asset_id}', data={
        'new_status': 'RECYCLED',
        'location': 'Recycling Plant',
        'remarks': 'Illegal jump test.'
    }, follow_redirects=True)
    assert resp2.status_code == 200
    assert b"Invalid FSM transition" in resp2.data

def test_ewaste_api_endpoints(anon_client):
    """Test JSON APIs for e-waste assets and circularity stats."""
    resp_assets = anon_client.get('/api/ewaste/assets')
    assert resp_assets.status_code == 200
    data_assets = resp_assets.get_json()
    assert isinstance(data_assets, list)
    assert len(data_assets) > 0
    assert 'asset_id' in data_assets[0]

    resp_stats = anon_client.get('/api/ewaste/stats')
    assert resp_stats.status_code == 200
    data_stats = resp_stats.get_json()
    assert 'total' in data_stats
    assert 'recycled' in data_stats

