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
    
    # Upload and static assets
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(str(basedir), 'static', 'uploads'))
    QR_FOLDER = os.environ.get('QR_FOLDER', os.path.join(str(basedir), 'static', 'qr_codes'))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp'}
    
    # IoT Simulation defaults
    SIMULATION_INTERVAL_SEC = int(os.environ.get('SIMULATION_INTERVAL_SEC', 30))
