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
