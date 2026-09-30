from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from models import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)  # 'user' or 'admin'
    green_credits = db.Column(db.Integer, default=0, nullable=False)
    items_recycled = db.Column(db.Integer, default=0, nullable=False)
    waste_diverted_kg = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    scans = db.relationship('WasteScan', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    credit_transactions = db.relationship('GreenCreditTransaction', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'green_credits': self.green_credits,
            'items_recycled': self.items_recycled,
            'waste_diverted_kg': round(self.waste_diverted_kg, 2),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ''
        }


class WasteScan(db.Model):
    __tablename__ = 'waste_scans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    detected_item = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'Biodegradable', 'Dry Recyclable', 'Hazardous / E-Waste'
    confidence = db.Column(db.Float, nullable=False)     # Percentage, e.g. 94.0
    recommendation = db.Column(db.Text, nullable=False)
    nearest_bin_id = db.Column(db.String(50), nullable=True)
    credits_awarded = db.Column(db.Integer, default=10, nullable=False)
    diverted_weight_kg = db.Column(db.Float, default=0.2, nullable=False)
    status = db.Column(db.String(30), default='SCANNED')  # 'SCANNED', 'DISPOSED'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'image_filename': self.image_filename,
            'detected_item': self.detected_item,
            'category': self.category,
            'confidence': round(self.confidence, 1),
            'recommendation': self.recommendation,
            'nearest_bin_id': self.nearest_bin_id,
            'credits_awarded': self.credits_awarded,
            'diverted_weight_kg': self.diverted_weight_kg,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ''
        }


class GreenCreditTransaction(db.Model):
    __tablename__ = 'green_credit_transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # 'WASTE_DISPOSAL', 'EWASTE_CONTRIBUTION', 'BONUS'
    description = db.Column(db.String(255), nullable=False)
    reference_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'action_type': self.action_type,
            'description': self.description,
            'reference_id': self.reference_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ''
        }


class Bin(db.Model):
    __tablename__ = 'bins'

    id = db.Column(db.String(30), primary_key=True)  # e.g. 'BIN-01'
    name = db.Column(db.String(100), nullable=False)
    waste_type = db.Column(db.String(50), nullable=False)  # 'Dry Recyclable', 'Biodegradable', 'Hazardous / E-Waste'
    location = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False, default=12.9716)
    longitude = db.Column(db.Float, nullable=False, default=77.5946)
    fill_percentage = db.Column(db.Float, default=0.0, nullable=False)
    weight_kg = db.Column(db.Float, default=0.0, nullable=False)
    temperature_c = db.Column(db.Float, default=24.0, nullable=False)
    battery_level = db.Column(db.Float, default=100.0, nullable=False)
    status = db.Column(db.String(20), default='NORMAL', nullable=False)  # 'NORMAL', 'WARNING', 'HIGH', 'OVERFLOW'
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    estimated_fill_rate = db.Column(db.Float, default=3.5)  # % increase per hour

    # Relationships
    readings = db.relationship('BinReading', backref='bin', lazy='dynamic', cascade='all, delete-orphan')
    collection_requests = db.relationship('CollectionRequest', backref='bin', lazy='dynamic', cascade='all, delete-orphan')

    def calculate_status(self):
        if self.fill_percentage >= 100:
            return 'OVERFLOW'
        elif self.fill_percentage >= 85:
            return 'HIGH'
        elif self.fill_percentage >= 70:
            return 'WARNING'
        else:
            return 'NORMAL'

    def estimate_hours_to_full(self):
        if self.fill_percentage >= 100:
            return 0.0
        rate = max(self.estimated_fill_rate, 0.5)
        hours = (100.0 - self.fill_percentage) / rate
        return round(hours, 1)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'waste_type': self.waste_type,
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'fill_percentage': round(self.fill_percentage, 1),
            'weight_kg': round(self.weight_kg, 1),
            'temperature_c': round(self.temperature_c, 1),
            'battery_level': round(self.battery_level, 1),
            'status': self.status,
            'last_updated': self.last_updated.strftime('%Y-%m-%d %H:%M:%S') if self.last_updated else '',
            'estimated_fill_rate': self.estimated_fill_rate,
            'hours_to_full': self.estimate_hours_to_full()
        }


class BinReading(db.Model):
    __tablename__ = 'bin_readings'

    id = db.Column(db.Integer, primary_key=True)
    bin_id = db.Column(db.String(30), db.ForeignKey('bins.id'), nullable=False)
    fill_percentage = db.Column(db.Float, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    temperature_c = db.Column(db.Float, nullable=False)
    battery_level = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class EWasteAsset(db.Model):
    __tablename__ = 'ewaste_assets'

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g. 'EW-2026-0001'
    device_name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False)  # 'Laptop', 'Smartphone', 'Circuit Board', etc.
    serial_number = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=False)
    current_status = db.Column(db.String(50), default='REGISTERED', nullable=False)
    # Statuses: 'REGISTERED', 'DECOMMISSIONED', 'COLLECTION_REQUESTED', 'COLLECTED', 'SENT_TO_RECYCLER', 'RECYCLED'
    recycler = db.Column(db.String(150), default='EcoRecycle Solutions Hub')
    weight_kg = db.Column(db.Float, default=1.5)
    notes = db.Column(db.Text, nullable=True)
    qr_code_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    lifecycle_logs = db.relationship('EWasteLifecycle', backref='asset', lazy='dynamic', cascade='all, delete-orphan', order_by='EWasteLifecycle.timestamp.asc()')

    def to_dict(self):
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'device_name': self.device_name,
            'category': self.category,
            'serial_number': self.serial_number or 'N/A',
            'location': self.location,
            'current_status': self.current_status,
            'recycler': self.recycler,
            'weight_kg': self.weight_kg,
            'notes': self.notes or '',
            'qr_code_filename': self.qr_code_filename,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else ''
        }


class EWasteLifecycle(db.Model):
    __tablename__ = 'ewaste_lifecycle'

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('ewaste_assets.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    updated_by = db.Column(db.String(100), default='Admin')
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status,
            'notes': self.notes or '',
            'updated_by': self.updated_by,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else ''
        }


class CollectionRequest(db.Model):
    __tablename__ = 'collection_requests'

    id = db.Column(db.Integer, primary_key=True)
    request_code = db.Column(db.String(50), unique=True, nullable=False)  # e.g. 'CR-2026-8910'
    bin_id = db.Column(db.String(30), db.ForeignKey('bins.id'), nullable=False)
    waste_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    fill_level = db.Column(db.Float, nullable=False)
    priority = db.Column(db.String(20), default='HIGH', nullable=False)  # 'MEDIUM', 'HIGH', 'URGENT'
    status = db.Column(db.String(30), default='PENDING', nullable=False)  # 'PENDING', 'ASSIGNED', 'COLLECTED', 'COMPLETED'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'request_code': self.request_code,
            'bin_id': self.bin_id,
            'waste_type': self.waste_type,
            'location': self.location,
            'fill_level': round(self.fill_level, 1),
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
            'resolved_at': self.resolved_at.strftime('%Y-%m-%d %H:%M') if self.resolved_at else None
        }
