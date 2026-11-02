import os
from pathlib import Path

basedir = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smartwastex-hackathon-sdg11-secret-2026')
    
    # Database URL: defaults to local SQLite; supports Render PostgreSQL if configured
    _db_url = os.environ.get('DATABASE_URL')
    if _db_url and _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
        
    SQLALCHEMY_DATABASE_URI = _db_url or f"sqlite:///{os.path.join(str(basedir), 'instance', 'smartwastex.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security: Session cookie hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Upload and static assets
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(str(basedir), 'static', 'uploads'))
    QR_FOLDER = os.environ.get('QR_FOLDER', os.path.join(str(basedir), 'static', 'qr_codes'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 5 * 1024 * 1024))  # 5 MB max upload for 512MB RAM stability
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp'}
    MAX_IMAGE_DIMENSION = int(os.environ.get('MAX_IMAGE_DIMENSION', 1280))  # Max width/height in px before preprocessing
    
    # AI Scanning & Concurrency Limits
    YOLO_IMGSZ = int(os.environ.get('YOLO_IMGSZ', 416))  # 416x416 inference image size
    INFERENCE_LOCK_TIMEOUT = float(os.environ.get('INFERENCE_LOCK_TIMEOUT', 15.0))  # Max lock wait time in seconds

    # IoT Hardware Gateway Security
    IOT_API_KEY = os.environ.get('IOT_API_KEY', 'smartwastex-iot-device-key-2026')
