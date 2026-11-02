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

def test_waste_scan_corrupted_image(client):
    """Test that uploading a corrupted/broken image returns 400 and does not crash."""
    import io
    data = {
        'waste_image': (io.BytesIO(b"Not an actual image byte stream"), 'corrupt.jpg')
    }
    response = client.post('/user/scan', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert b"Unable to process this image" in response.data

def test_waste_scan_unsupported_format(client):
    """Test that uploading an unsupported format returns 400."""
    import io
    data = {
        'waste_image': (io.BytesIO(b"print('hello')"), 'script.py')
    }
    response = client.post('/user/scan', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert b"Unsupported image format" in response.data

def test_waste_scan_oversized_image(client):
    """Test that uploading an image > 5 MB triggers 413 Request Entity Too Large."""
    import io
    oversized_data = b"0" * (6 * 1024 * 1024) # 6 MB
    data = {
        'waste_image': (io.BytesIO(oversized_data), 'huge.jpg')
    }
    response = client.post('/user/scan', data=data, content_type='multipart/form-data')
    assert response.status_code == 413
    assert b"smaller than 5 MB" in response.data

def test_waste_scan_valid_uploaded_image(client):
    """Test that uploading a valid generated image succeeds and creates a scan record."""
    import io
    from PIL import Image
    # Create a small valid test image in memory
    img_byte_arr = io.BytesIO()
    img = Image.new('RGB', (200, 200), color=(50, 150, 70))
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)

    data = {
        'waste_image': (img_byte_arr, 'test_scan.jpg')
    }
    response = client.post('/user/scan', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b"AI Waste Analysis" in response.data
    assert b"Nearest Smart Receptacle" in response.data

def test_waste_scan_service_busy_lock(client):
    """Test that when inference lock is busy, service gracefully returns 503 without crashing."""
    from services.classifier import classifier
    original_timeout = classifier.lock_timeout
    try:
        # Acquire lock to simulate concurrent inference in progress
        classifier.lock_timeout = 0.2
        classifier._inference_lock.acquire()

        import io
        from PIL import Image
        img_byte_arr = io.BytesIO()
        img = Image.new('RGB', (100, 100), color=(100, 100, 100))
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)

        data = {
            'waste_image': (img_byte_arr, 'busy_test.jpg')
        }
        response = client.post('/user/scan', data=data, content_type='multipart/form-data')
        assert response.status_code == 503
        assert b"scanning service is currently busy" in response.data
    finally:
        if classifier._inference_lock.locked():
            classifier._inference_lock.release()
        classifier.lock_timeout = original_timeout

def test_validate_and_preprocess_image_resizes_large_dimensions(tmp_path):
    """Test that validate_and_preprocess_image downscales large images to max 1280px."""
    from services.classifier import validate_and_preprocess_image
    from PIL import Image
    test_img_path = str(tmp_path / "huge_resolution.jpg")
    img = Image.new('RGB', (2400, 1800), color=(80, 160, 240))
    img.save(test_img_path, format='JPEG')

    processed_np = validate_and_preprocess_image(test_img_path, max_dim=1280)
    h, w = processed_np.shape[:2]
    assert max(h, w) <= 1280
    assert w == 1280 or h == 1280

