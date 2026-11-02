import pytest
from app import create_app
from config import Config
from models import db
from models.models import Bin, BinReading, CollectionRequest

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    IOT_API_KEY = 'test-iot-secret-key'

@pytest.fixture
def app_instance():
    app = create_app(TestConfig)
    return app

@pytest.fixture
def admin_client(app_instance):
    with app_instance.test_client() as client:
        # Log in as demo admin
        client.post('/login', data={
            'email': 'admin@smartwastex.in',
            'password': 'admin@123'
        }, follow_redirects=True)
        yield client

@pytest.fixture
def public_client(app_instance):
    with app_instance.test_client() as client:
        yield client

def test_admin_bins_view(admin_client):
    """Test smart bins page lists all institutional receptacles."""
    response = admin_client.get('/admin/bins')
    assert response.status_code == 200
    assert b"BIN-01" in response.data
    assert b"BIN-02" in response.data
    assert b"BIN-03" in response.data
    assert b"BIN-04" in response.data

def test_sensor_ingestion_valid_payload(public_client, app_instance):
    """Test valid real hardware sensor payload ingestion with API key."""
    payload = {
        "bin_id": "BIN-01",
        "fill_percentage": 65.5,
        "weight": 14.2,
        "temperature": 28.3,
        "battery_level": 94.0
    }
    response = public_client.post(
        '/api/iot/bin-update',
        json=payload,
        headers={'X-API-Key': 'test-iot-secret-key'}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['bin_id'] == 'BIN-01'
    assert data['fill_percentage'] == 65.5
    assert data['weight_kg'] == 14.2
    assert data['temperature_c'] == 28.3
    assert data['battery_level'] == 94.0
    assert data['status'] == 'NORMAL'

    # Verify Bin database record updated
    with app_instance.app_context():
        bin_obj = db.session.get(Bin, 'BIN-01')
        assert bin_obj.fill_percentage == 65.5
        assert bin_obj.weight_kg == 14.2
        assert bin_obj.temperature_c == 28.3
        assert bin_obj.battery_level == 94.0
        assert bin_obj.status == 'NORMAL'

def test_all_four_bin_statuses(public_client):
    """Test calculation of all 4 bin statuses: NORMAL, WARNING, HIGH, OVERFLOW."""
    headers = {'X-API-Key': 'test-iot-secret-key'}

    # 1. NORMAL (< 70%)
    res_normal = public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_percentage': 55.0}, headers=headers)
    assert res_normal.status_code == 200
    assert res_normal.get_json()['status'] == 'NORMAL'

    # 2. WARNING (70% <= fill < 85%)
    res_warning = public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_percentage': 76.0}, headers=headers)
    assert res_warning.status_code == 200
    assert res_warning.get_json()['status'] == 'WARNING'

    # 3. HIGH (85% <= fill < 100%)
    res_high = public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_percentage': 88.0}, headers=headers)
    assert res_high.status_code == 200
    assert res_high.get_json()['status'] == 'HIGH'
    assert res_high.get_json()['alert']['priority'] == 'HIGH'

    # 4. OVERFLOW (>= 100%)
    res_overflow = public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_percentage': 100.0}, headers=headers)
    assert res_overflow.status_code == 200
    assert res_overflow.get_json()['status'] == 'OVERFLOW'
    assert res_overflow.get_json()['alert']['priority'] == 'URGENT'

def test_overflow_alert_creates_collection_request(public_client, app_instance):
    """Test ingesting 100% capacity triggers URGENT overflow and creates automated collection request."""
    response = public_client.post(
        '/api/iot/bin-update',
        json={'bin_id': 'BIN-04', 'fill_percentage': 100.0},
        headers={'X-API-Key': 'test-iot-secret-key'}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'OVERFLOW'
    assert data['alert']['priority'] == 'URGENT'

    # Check database collection request
    with app_instance.app_context():
        req = CollectionRequest.query.filter_by(bin_id='BIN-04', priority='URGENT').order_by(CollectionRequest.id.desc()).first()
        assert req is not None
        assert req.status in ['PENDING', 'ASSIGNED', 'SCHEDULED']
        assert req.fill_level == 100.0

def test_empty_bin_resets_and_resolves_tickets(public_client, app_instance):
    """Test emptying bin resets fill to 0% and completes active collection requests."""
    headers = {'X-API-Key': 'test-iot-secret-key'}

    # Set high fill to trigger collection ticket
    public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-04', 'fill_percentage': 95.0}, headers=headers)
    
    # Send empty action
    response = public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-04', 'action': 'empty'}, headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data['fill_percentage'] == 0.0
    assert data['status'] == 'NORMAL'

    # Verify collection tickets are marked COMPLETED
    with app_instance.app_context():
        completed_reqs = CollectionRequest.query.filter_by(bin_id='BIN-04', status='COMPLETED').all()
        assert len(completed_reqs) > 0

def test_sensor_ingestion_api_key_auth(public_client):
    """Test API key protection on sensor endpoint."""
    payload = {'bin_id': 'BIN-02', 'fill_percentage': 50.0}

    # 1. Reject without key when unauthenticated
    unauth_resp = public_client.post('/api/iot/bin-update', json=payload)
    assert unauth_resp.status_code == 401
    assert unauth_resp.get_json()['success'] is False

    # 2. Reject with wrong key
    wrong_key_resp = public_client.post(
        '/api/iot/bin-update',
        json=payload,
        headers={'X-API-Key': 'invalid-device-key'}
    )
    assert wrong_key_resp.status_code == 401

    # 3. Accept with valid X-API-Key
    valid_key_resp = public_client.post(
        '/api/iot/bin-update',
        json=payload,
        headers={'X-API-Key': 'test-iot-secret-key'}
    )
    assert valid_key_resp.status_code == 200

    # 4. Accept with Bearer token
    bearer_resp = public_client.post(
        '/api/iot/bin-update',
        json=payload,
        headers={'Authorization': 'Bearer test-iot-secret-key'}
    )
    assert bearer_resp.status_code == 200

def test_sensor_ingestion_invalid_payloads(public_client):
    """Test rejection of malformed or out-of-range sensor readings."""
    headers = {'X-API-Key': 'test-iot-secret-key'}

    # Missing payload
    res_empty = public_client.post('/api/iot/bin-update', headers=headers)
    assert res_empty.status_code == 400

    # Missing bin_id
    res_no_bin = public_client.post('/api/iot/bin-update', json={'fill_percentage': 50.0}, headers=headers)
    assert res_no_bin.status_code == 400
    assert "bin_id is required" in res_no_bin.get_json()['error']

    # Missing fill
    res_no_fill = public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01'}, headers=headers)
    assert res_no_fill.status_code == 400
    assert "fill_percentage is required" in res_no_fill.get_json()['error']

    # Non-numeric fill
    res_str_fill = public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_percentage': 'high'}, headers=headers)
    assert res_str_fill.status_code == 400
    assert "numeric value" in res_str_fill.get_json()['error']

    # Out-of-range fill (> 100)
    res_over_fill = public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_percentage': 105.0}, headers=headers)
    assert res_over_fill.status_code == 400
    assert "between 0.0 and 100.0" in res_over_fill.get_json()['error']

    # Out-of-range fill (< 0)
    res_neg_fill = public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_percentage': -10.0}, headers=headers)
    assert res_neg_fill.status_code == 400

    # Out-of-range weight
    res_weight = public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_percentage': 50.0, 'weight': 600.0}, headers=headers)
    assert res_weight.status_code == 400

    # Out-of-range temperature
    res_temp = public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_percentage': 50.0, 'temperature': 120.0}, headers=headers)
    assert res_temp.status_code == 400

    # Out-of-range battery
    res_batt = public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_percentage': 50.0, 'battery_level': 110.0}, headers=headers)
    assert res_batt.status_code == 400

def test_sensor_ingestion_unknown_bin_id(public_client):
    """Test graceful handling of unknown bin IDs."""
    response = public_client.post(
        '/api/iot/bin-update',
        json={'bin_id': 'BIN-999', 'fill_percentage': 45.0},
        headers={'X-API-Key': 'test-iot-secret-key'}
    )
    assert response.status_code == 404
    assert "not found" in response.get_json()['error']

def test_bin_reading_historical_telemetry(public_client, app_instance):
    """Test that incoming sensor readings create historical audit records in BinReading."""
    headers = {'X-API-Key': 'test-iot-secret-key'}
    with app_instance.app_context():
        initial_count = BinReading.query.filter_by(bin_id='BIN-03').count()

    # Ingest 3 distinct readings
    public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-03', 'fill_percentage': 40.0, 'weight': 6.0}, headers=headers)
    public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-03', 'fill_percentage': 60.0, 'weight': 10.0}, headers=headers)
    public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-03', 'fill_percentage': 82.0, 'weight': 15.0}, headers=headers)

    with app_instance.app_context():
        after_count = BinReading.query.filter_by(bin_id='BIN-03').count()
        assert after_count == initial_count + 3

        latest = BinReading.query.filter_by(bin_id='BIN-03').order_by(BinReading.id.desc()).first()
        assert latest.fill_percentage == 82.0
        assert latest.weight_kg == 15.0

def test_bin_id_normalization(public_client):
    """Test normalization of integer IDs and zero-padded string variants."""
    headers = {'X-API-Key': 'test-iot-secret-key'}

    # Test integer ID: 2 -> BIN-02
    res_int = public_client.post('/api/iot/bin-update', json={'bin_id': 2, 'fill_percentage': 72.0}, headers=headers)
    assert res_int.status_code == 200
    assert res_int.get_json()['bin_id'] == 'BIN-02'

    # Test padded variant: BIN-002 -> BIN-02
    res_padded = public_client.post('/api/iot/bin-update', json={'bin_id': 'BIN-002', 'fill_percentage': 74.0}, headers=headers)
    assert res_padded.status_code == 200
    assert res_padded.get_json()['bin_id'] == 'BIN-02'
