import os
from datetime import datetime, timezone, timedelta
from flask import Flask, redirect, url_for, session, render_template
from config import Config
from models import db
from models.models import User, Bin, BinReading, EWasteAsset, EWasteLifecycle, CollectionRequest, WasteScan, GreenCreditTransaction
from services.qr_service import qr_service

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure required directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'samples'), exist_ok=True)
    os.makedirs(app.config['QR_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.user import user_bp
    from routes.waste import waste_bp
    from routes.bins import bins_bp
    from routes.ewaste import ewaste_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(waste_bp)
    app.register_blueprint(bins_bp)
    app.register_blueprint(ewaste_bp)
    app.register_blueprint(admin_bp)

    @app.route('/')
    def index():
        from services.impact_service import ImpactService
        metrics = ImpactService.get_admin_dashboard_metrics()
        bins_sample = Bin.query.order_by(Bin.id.asc()).all()
        return render_template('home.html', metrics=metrics, bins=bins_sample)

    @app.route('/health')
    def health():
        return {'status': 'ok'}

    # Custom Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    @app.errorhandler(413)
    def file_too_large(e):
        return render_template('404.html', message="Uploaded file exceeds the maximum 16MB limit."), 413

    # Seed Database on initial setup
    with app.app_context():
        init_and_seed_db(app)

    return app

def init_and_seed_db(app):
    db.create_all()

    demo_user_email = os.environ.get('DEMO_USER_EMAIL', 'user1@smartwastex.in')
    demo_user_password = os.environ.get('DEMO_USER_PASSWORD', 'user1@123')
    demo_admin_email = os.environ.get('DEMO_ADMIN_EMAIL', 'admin@smartwastex.in')
    demo_admin_password = os.environ.get('DEMO_ADMIN_PASSWORD', 'admin@123')

    # 1. Seed Demo User
    user1 = User.query.filter_by(email=demo_user_email).first()
    if not user1:
        user1 = User(
            email=demo_user_email,
            name='Rahul Sharma',
            role='user',
            green_credits=385,
            items_recycled=24,
            waste_diverted_kg=18.4,
            created_at=datetime.now(timezone.utc) - timedelta(days=15)
        )
        user1.set_password(demo_user_password)
        db.session.add(user1)

    # 2. Seed Demo Admin
    admin_user = User.query.filter_by(email=demo_admin_email).first()
    if not admin_user:
        admin_user = User(
            email=demo_admin_email,
            name='Dr. Ananya Rao',
            role='admin',
            green_credits=120,
            items_recycled=12,
            waste_diverted_kg=14.2,
            created_at=datetime.now(timezone.utc) - timedelta(days=30)
        )
        admin_user.set_password(demo_admin_password)
        db.session.add(admin_user)

    # 3. Seed Campus Champions for realistic Leaderboard
    extra_users = [
        ('sai@smartwastex.in', 'Sai K.', 420, 28, 22.5),
        ('priya@smartwastex.in', 'Priya M.', 340, 21, 15.8),
        ('aditya@smartwastex.in', 'Aditya V.', 290, 18, 12.3),
        ('sneha@smartwastex.in', 'Sneha Patel', 245, 16, 11.0),
        ('karan@smartwastex.in', 'Karan Mehta', 190, 12, 8.4)
    ]
    for email, name, credits, items, diverted in extra_users:
        if not User.query.filter_by(email=email).first():
            u = User(
                email=email,
                name=name,
                role='user',
                green_credits=credits,
                items_recycled=items,
                waste_diverted_kg=diverted,
                created_at=datetime.now(timezone.utc) - timedelta(days=20)
            )
            u.set_password('demo@123')
            db.session.add(u)

    # 4. Seed Smart Bins
    bins_data = [
        {
            'id': 'BIN-01',
            'name': 'Main Building Recyclable',
            'waste_type': 'Dry Recyclable',
            'location': 'Main Building',
            'latitude': 12.9716,
            'longitude': 77.5946,
            'fill': 42.0,
            'weight': 8.4,
            'temp': 28.0,
            'battery': 92.0,
            'status': 'NORMAL'
        },
        {
            'id': 'BIN-02',
            'name': 'Cafeteria Compost Hub',
            'waste_type': 'Biodegradable',
            'location': 'Cafeteria',
            'latitude': 12.9722,
            'longitude': 77.5955,
            'fill': 61.0,
            'weight': 17.1,
            'temp': 29.5,
            'battery': 88.0,
            'status': 'NORMAL'
        },
        {
            'id': 'BIN-03',
            'name': 'Library Paper & Plastic',
            'waste_type': 'Dry Recyclable',
            'location': 'Library',
            'latitude': 12.9710,
            'longitude': 77.5938,
            'fill': 78.0,
            'weight': 15.6,
            'temp': 27.2,
            'battery': 95.0,
            'status': 'WARNING'
        },
        {
            'id': 'BIN-04',
            'name': 'Engineering E-Waste Depot',
            'waste_type': 'Hazardous / E-Waste',
            'location': 'Engineering Block',
            'latitude': 12.9730,
            'longitude': 77.5962,
            'fill': 94.0,
            'weight': 18.4,
            'temp': 31.0,
            'battery': 74.0,
            'status': 'HIGH'
        }
    ]

    for b in bins_data:
        existing_bin = db.session.get(Bin, b['id'])
        if not existing_bin:
            new_bin = Bin(
                id=b['id'],
                name=b['name'],
                waste_type=b['waste_type'],
                location=b['location'],
                latitude=b['latitude'],
                longitude=b['longitude'],
                fill_percentage=b['fill'],
                weight_kg=b['weight'],
                temperature_c=b['temp'],
                battery_level=b['battery'],
                status=b['status'],
                last_updated=datetime.now(timezone.utc)
            )
            db.session.add(new_bin)
            # Add initial telemetry reading
            reading = BinReading(
                bin_id=b['id'],
                fill_percentage=b['fill'],
                weight_kg=b['weight'],
                temperature_c=b['temp'],
                battery_level=b['battery'],
                timestamp=datetime.now(timezone.utc)
            )
            db.session.add(reading)

    # 5. Seed Initial E-Waste Assets
    ewaste_assets = [
        {
            'asset_id': 'EW-2026-0001',
            'device_name': 'Dell Latitude 5420 Laptop',
            'category': 'Computing',
            'serial_number': 'DELL-LT-9482',
            'location': 'CS Lab 2',
            'status': 'COLLECTED',
            'recycler': 'EcoRecycle Solutions Hub',
            'weight_kg': 2.1,
            'notes': 'Battery retired at 62% health. RAM and SSD sanitized and reclaimed for hardware lab.',
            'history': [
                ('REGISTERED', 'Asset flagged for end-of-life audit by Dept IT staff.', -10),
                ('DECOMMISSIONED', 'Hard drive shredded to NIST 800-88 compliance standards.', -8),
                ('COLLECTION_REQUESTED', 'Handover ticket logged for campus logistics depot.', -5),
                ('COLLECTED', 'Collected by campus facilities logistics team for R2 recycler dispatch.', -2)
            ]
        },
        {
            'asset_id': 'EW-2026-0002',
            'device_name': 'Old Smartphone (Samsung Galaxy S9)',
            'category': 'Mobile',
            'serial_number': 'SAMS-GAL-3310',
            'location': 'Admin Office',
            'status': 'DECOMMISSIONED',
            'recycler': 'EcoRecycle Solutions Hub',
            'weight_kg': 0.18,
            'notes': 'Swollen lithium-ion cell safely neutralised in fire-retardant storage bin.',
            'history': [
                ('REGISTERED', 'Dropped at admin reception e-waste intake bin.', -4),
                ('DECOMMISSIONED', 'Inspected for hazardous electrolyte leak. Battery isolated.', -2)
            ]
        },
        {
            'asset_id': 'EW-2026-0003',
            'device_name': 'Microcontroller Circuit Board & PCB Spares',
            'category': 'Component',
            'serial_number': 'PCB-ROBOTICS-88',
            'location': 'Robotics Lab',
            'status': 'REGISTERED',
            'recycler': 'EcoRecycle Solutions Hub',
            'weight_kg': 0.45,
            'notes': 'Scrap FR-4 boards containing copper, gold plating traces, and lead-free solder.',
            'history': [
                ('REGISTERED', 'Enrolled into institutional e-waste circularity inventory.', -1)
            ]
        }
    ]

    qr_folder = app.config['QR_FOLDER']
    for asset_dict in ewaste_assets:
        if not EWasteAsset.query.filter_by(asset_id=asset_dict['asset_id']).first():
            qr_file = qr_service.generate_asset_qr(asset_dict['asset_id'], output_dir=qr_folder)
            asset = EWasteAsset(
                asset_id=asset_dict['asset_id'],
                device_name=asset_dict['device_name'],
                category=asset_dict['category'],
                serial_number=asset_dict['serial_number'],
                location=asset_dict['location'],
                current_status=asset_dict['status'],
                recycler=asset_dict['recycler'],
                weight_kg=asset_dict['weight_kg'],
                notes=asset_dict['notes'],
                qr_code_filename=qr_file,
                created_at=datetime.now(timezone.utc) - timedelta(days=12)
            )
            db.session.add(asset)
            db.session.flush()

            for status, note, days_offset in asset_dict['history']:
                log = EWasteLifecycle(
                    asset_id=asset.id,
                    status=status,
                    notes=note,
                    updated_by='Admin IT Staff',
                    timestamp=datetime.now(timezone.utc) + timedelta(days=days_offset)
                )
                db.session.add(log)

    # 6. Seed Collection Requests (BIN-04 is HIGH / 94%)
    if not CollectionRequest.query.filter_by(bin_id='BIN-04').first():
        col_req = CollectionRequest(
            request_code='CR-04-9401',
            bin_id='BIN-04',
            waste_type='Hazardous / E-Waste',
            location='Engineering Block',
            fill_level=94.0,
            priority='HIGH',
            status='PENDING',
            created_at=datetime.now(timezone.utc) - timedelta(hours=3)
        )
        db.session.add(col_req)

    # 7. Seed Initial Activity History for user1
    db.session.flush()
    if user1 and user1.credit_transactions.count() == 0:
        initial_history = [
            (25, 'WASTE_DISPOSAL', 'Battery correctly disposed at Engineering Block', timedelta(hours=4)),
            (10, 'WASTE_DISPOSAL', 'Plastic bottle recycled at Main Building', timedelta(days=1)),
            (10, 'WASTE_DISPOSAL', 'Newspaper deposited at Library', timedelta(days=2)),
            (5, 'WASTE_DISPOSAL', 'Compostable food packaging deposited at Cafeteria', timedelta(days=3)),
            (50, 'EWASTE_CONTRIBUTION', 'Institutional IT keyboard enrolled into E-Waste Tracker', timedelta(days=5))
        ]
        for amt, action_type, desc, offset in initial_history:
            txn = GreenCreditTransaction(
                user_id=user1.id,
                amount=amt,
                action_type=action_type,
                description=desc,
                reference_id='SEED',
                created_at=datetime.now(timezone.utc) - offset
            )
            db.session.add(txn)

    db.session.commit()

# Create application instance for gunicorn or flask run
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '1').lower() in ('true', '1', 't')
    app.run(host='0.0.0.0', port=port, debug=debug)
