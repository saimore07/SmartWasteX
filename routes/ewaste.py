"""
SmartWasteX E-Waste Circularity & Custody Chain Blueprint
=========================================================
Provides complete institutional e-waste management:
- E-Waste Dashboard with circular metrics & FSM pipeline visual
- Public Ledger with search & status filters
- AI YOLOv8 Waste Classifier with visual bounding box annotations
- User E-Waste Drop-off intake with Green Credits rewards
- Institutional Asset Registration with automated QR passport generation
- Custody Transfer with Finite State Machine (FSM) enforcement
- Immutable Lifecycle Audit Trail
- Public Digital Passport scanned via mobile QR codes
"""

import os
import shutil
import uuid
from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, current_app, jsonify
)
from werkzeug.utils import secure_filename
from routes.auth import login_required, role_required
from models import db
from models.models import User, EWasteAsset, EWasteLifecycle, GreenCreditTransaction
from services.qr_service import qr_service
from services.classifier import classifier_service

ewaste_bp = Blueprint('ewaste', __name__)

# ── Finite State Machine (FSM) Transitions ───────────────────────────
ALLOWED_TRANSITIONS = {
    'PENDING_DROPOFF':     ['IN_USE', 'REGISTERED', 'DECOMMISSIONED', 'E_WASTE_STORAGE', 'COLLECTION_REQUESTED'],
    'IN_USE':              ['DECOMMISSIONED', 'E_WASTE_STORAGE', 'COLLECTION_REQUESTED'],
    'REGISTERED':          ['IN_USE', 'DECOMMISSIONED', 'E_WASTE_STORAGE', 'COLLECTION_REQUESTED'],
    'DECOMMISSIONED':      ['E_WASTE_STORAGE', 'COLLECTION_REQUESTED', 'COLLECTED'],
    'E_WASTE_STORAGE':     ['COLLECTION_REQUESTED', 'COLLECTED', 'SENT_TO_RECYCLER'],
    'COLLECTION_REQUESTED': ['COLLECTED', 'SENT_TO_RECYCLER', 'E_WASTE_STORAGE'],
    'COLLECTED':           ['SENT_TO_RECYCLER', 'RECYCLED'],
    'SENT_TO_RECYCLER':    ['RECYCLED'],
    'RECYCLED':            [],          # terminal state
}

LIFECYCLE_STAGES = [
    'REGISTERED',
    'IN_USE',
    'DECOMMISSIONED',
    'COLLECTION_REQUESTED',
    'COLLECTED',
    'SENT_TO_RECYCLER',
    'RECYCLED'
]

STATUS_COLORS = {
    'REGISTERED':          'primary',
    'IN_USE':              'info',
    'PENDING_DROPOFF':     'warning',
    'DECOMMISSIONED':      'secondary',
    'E_WASTE_STORAGE':     'danger',
    'COLLECTION_REQUESTED': 'danger',
    'COLLECTED':           'primary',
    'SENT_TO_RECYCLER':    'primary',
    'RECYCLED':            'success',
}


def _allowed_file(filename):
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'webp'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


# ── 1. E-Waste Dashboard ──────────────────────────────────────────────
@ewaste_bp.route('/ewaste')
@ewaste_bp.route('/ewaste/dashboard')
def dashboard():
    """Circularity overview dashboard with FSM pipeline and custody stats."""
    total = EWasteAsset.query.count()
    in_use = EWasteAsset.query.filter(EWasteAsset.current_status.in_(['IN_USE', 'REGISTERED'])).count()
    decom = EWasteAsset.query.filter_by(current_status='DECOMMISSIONED').count()
    storage = EWasteAsset.query.filter(
        EWasteAsset.current_status.in_(['E_WASTE_STORAGE', 'COLLECTION_REQUESTED', 'PENDING_DROPOFF'])
    ).count()
    collected = EWasteAsset.query.filter(
        EWasteAsset.current_status.in_(['COLLECTED', 'SENT_TO_RECYCLER'])
    ).count()
    recycled = EWasteAsset.query.filter_by(current_status='RECYCLED').count()

    recent_assets = EWasteAsset.query.order_by(EWasteAsset.created_at.desc()).limit(8).all()
    recent_logs = EWasteLifecycle.query.order_by(EWasteLifecycle.timestamp.desc()).limit(8).all()

    return render_template(
        'ewaste/dashboard.html',
        total=total,
        in_use=in_use,
        decom=decom,
        storage=storage,
        collected=collected,
        recycled=recycled,
        recent_assets=recent_assets,
        recent_logs=recent_logs,
        status_colors=STATUS_COLORS,
    )


# ── 2. Public Ledger ──────────────────────────────────────────────────
@ewaste_bp.route('/ewaste/ledger')
def public_ledger():
    """Transparent public ledger of all tracked assets with search and status filters."""
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = EWasteAsset.query
    if search_query:
        query = query.filter(
            (EWasteAsset.asset_id.ilike(f"%{search_query}%")) |
            (EWasteAsset.device_name.ilike(f"%{search_query}%")) |
            (EWasteAsset.serial_number.ilike(f"%{search_query}%")) |
            (EWasteAsset.location.ilike(f"%{search_query}%")) |
            (EWasteAsset.department.ilike(f"%{search_query}%"))
        )
    if status_filter:
        if status_filter == 'REGISTERED':
            query = query.filter(EWasteAsset.current_status.in_(['REGISTERED', 'IN_USE']))
        elif status_filter == 'COLLECTION_REQUESTED':
            query = query.filter(EWasteAsset.current_status.in_(['COLLECTION_REQUESTED', 'E_WASTE_STORAGE']))
        else:
            query = query.filter_by(current_status=status_filter)

    assets = query.order_by(EWasteAsset.created_at.desc()).all()

    return render_template(
        'ewaste/ledger.html',
        assets=assets,
        search_query=search_query,
        status_filter=status_filter,
        status_colors=STATUS_COLORS,
    )


# ── 3. AI YOLOv8 Waste Scanner ────────────────────────────────────────
@ewaste_bp.route('/ewaste/scan', methods=['GET', 'POST'])
def scan():
    """YOLOv8 deep learning vision scanner with bounding box annotations."""
    result = None
    image_url = None

    if request.method == 'POST':
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        sample_item = request.form.get('sample_item', '').strip()
        uploaded_file = request.files.get('waste_image')

        filepath = None
        rel_filename = None

        if sample_item:
            sample_candidates = [
                f"{sample_item}.jpg",
                f"{sample_item}_peel.jpg",
                f"plastic_{sample_item}.jpg",
                "battery.jpg" if 'laptop' in sample_item or 'battery' in sample_item else f"{sample_item}.jpg"
            ]
            sample_src = None
            for cand in sample_candidates:
                cand_path = os.path.join(upload_folder, 'samples', cand)
                if os.path.exists(cand_path):
                    sample_src = cand_path
                    break

            clean_name = f"scan_{sample_item}_{int(datetime.now().timestamp())}.jpg"
            dest_path = os.path.join(upload_folder, clean_name)
            if sample_src and os.path.exists(sample_src):
                shutil.copyfile(sample_src, dest_path)
            else:
                import cv2
                import numpy as np
                dummy = np.zeros((300, 300, 3), dtype=np.uint8)
                dummy[:] = (40, 140, 60) if sample_item == 'banana' else (200, 100, 30)
                cv2.imwrite(dest_path, dummy)
            filepath = dest_path
            rel_filename = clean_name
        elif uploaded_file and uploaded_file.filename:
            if not _allowed_file(uploaded_file.filename):
                flash("Unsupported image format. Please upload PNG, JPG, or WEBP.", "danger")
                return render_template('ewaste/scan.html')
            sec_name = secure_filename(uploaded_file.filename)
            unique_name = f"scan_{uuid.uuid4().hex[:8]}_{sec_name}"
            dest_path = os.path.join(upload_folder, unique_name)
            uploaded_file.save(dest_path)
            filepath = dest_path
            rel_filename = unique_name
        else:
            flash("Please upload an image file or click one of the demo samples.", "warning")
            return render_template('ewaste/scan.html')

        # Run YOLOv8 / CV analysis
        result = classifier_service.analyze(filepath, hint=sample_item)
        image_url = url_for('static', filename=f"uploads/{rel_filename}")

    return render_template('ewaste/scan.html', result=result, image_url=image_url)


# ── 4. User E-Waste Drop-off Intake ───────────────────────────────────
@ewaste_bp.route('/ewaste/dropoff', methods=['GET', 'POST'])
@ewaste_bp.route('/ewaste/initiate_dropoff', methods=['POST'])
def dropoff():
    """User-initiated e-waste drop-off ticket with Green Credit incentives."""
    if 'user_id' not in session:
        flash("Please log in to generate an official e-waste drop-off passport and earn Green Credits.", "warning")
        return redirect(url_for('auth.login', next=url_for('ewaste.dropoff')))

    if request.method == 'POST':
        device_name = request.form.get('device_name', 'Electronic Equipment').strip()
        department = request.form.get('department', '').strip() or f"User Drop-off: {session.get('name', 'Campus Member')}"
        notes = request.form.get('notes', '').strip()

        # Generate unique sequential asset ID (EW-2026-XXXX)
        year = datetime.now(timezone.utc).year
        total = EWasteAsset.query.count()
        asset_id = f"EW-{year}-{(total + 1):04d}"

        # Generate QR code
        qr_folder = current_app.config['QR_FOLDER']
        qr_filename = qr_service.generate_asset_qr(asset_id, output_dir=qr_folder)

        new_asset = EWasteAsset(
            asset_id=asset_id,
            device_name=device_name,
            category='Hazardous / E-Waste',
            department=department,
            serial_number=f"TICKET-{asset_id}",
            location='Pending Drop-off (Campus Kiosk)',
            current_status='PENDING_DROPOFF',
            recycler='EcoRecycle Solutions Hub',
            weight_kg=1.5,
            notes=notes or 'User-initiated campus drop-off ticket.',
            qr_code_filename=qr_filename,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(new_asset)
        db.session.flush()

        # Initial lifecycle audit log
        init_log = EWasteLifecycle(
            asset_id=new_asset.id,
            old_status=None,
            new_status='PENDING_DROPOFF',
            location='Pending Drop-off (Campus Kiosk)',
            updated_by=session.get('name', 'User'),
            notes=f"User drop-off ticket generated: {notes}" if notes else "Intake ticket generated.",
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(init_log)

        # Award Green Credits (+25) to user
        user = db.session.get(User, session['user_id'])
        if user:
            user.green_credits += 25
            user.items_recycled += 1
            user.waste_diverted_kg += 1.5
            txn = GreenCreditTransaction(
                user_id=user.id,
                amount=25,
                action_type='EWASTE_CONTRIBUTION',
                description=f"Enrolled {device_name} ({asset_id}) for institutional e-waste circularity",
                reference_id=asset_id,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(txn)

        db.session.commit()
        flash(f"Drop-off QR generated! Asset {asset_id} enrolled. +25 Green Credits awarded!", "success")
        return redirect(url_for('ewaste.asset_detail', asset_id=asset_id))

    return render_template('ewaste/dropoff.html')


# ── 5. Institutional Asset Registration (Admin) ───────────────────────
@ewaste_bp.route('/ewaste/register', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def register_asset():
    """Admin registration for campus hardware assets."""
    if request.method == 'POST':
        device_name = request.form.get('device_name', '').strip()
        department = request.form.get('department', '').strip() or 'IT Infrastructure'
        category = request.form.get('category', 'Computing').strip()
        serial_number = request.form.get('serial_number', '').strip()
        location = request.form.get('location', '').strip()
        recycler = request.form.get('recycler', 'EcoRecycle Solutions Hub').strip()
        notes = request.form.get('notes', '').strip()

        try:
            weight_kg = float(request.form.get('weight_kg', 1.5))
        except ValueError:
            weight_kg = 1.5

        if not device_name or not location:
            flash("Device name and location are required fields.", "warning")
            return redirect(url_for('ewaste.register_asset'))

        # Generate unique sequential ID
        year = datetime.now(timezone.utc).year
        total = EWasteAsset.query.count()
        asset_id = f"EW-{year}-{(total + 1):04d}"

        # Generate QR code
        qr_folder = current_app.config['QR_FOLDER']
        qr_filename = qr_service.generate_asset_qr(asset_id, output_dir=qr_folder)

        new_asset = EWasteAsset(
            asset_id=asset_id,
            device_name=device_name,
            category=category,
            department=department,
            serial_number=serial_number or f"SN-{asset_id}",
            location=location,
            current_status='IN_USE',
            recycler=recycler,
            weight_kg=weight_kg,
            notes=notes,
            qr_code_filename=qr_filename,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(new_asset)
        db.session.flush()

        init_log = EWasteLifecycle(
            asset_id=new_asset.id,
            old_status=None,
            new_status='IN_USE',
            location=location,
            updated_by=session.get('name', 'Admin Staff'),
            notes=f"Institutional asset enrolled: {notes}" if notes else "Initial asset registration.",
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(init_log)
        db.session.commit()

        flash(f"Asset {asset_id} ({device_name}) registered successfully with Digital Passport QR!", "success")
        return redirect(url_for('ewaste.asset_detail', asset_id=asset_id))

    return render_template('ewaste/register.html')


# ── 6. Asset Detail Page ──────────────────────────────────────────────
@ewaste_bp.route('/ewaste/asset/<asset_id>')
def asset_detail(asset_id):
    """Full asset profile, QR code view, FSM progress visual, and audit timeline."""
    asset = EWasteAsset.query.filter_by(asset_id=asset_id).first_or_404()
    logs = asset.lifecycle_logs.order_by(EWasteLifecycle.timestamp.asc()).all()
    valid_next_states = ALLOWED_TRANSITIONS.get(asset.current_status, [])

    return render_template(
        'ewaste/asset_detail.html',
        asset=asset,
        logs=logs,
        allowed_next_states=valid_next_states,
        status_colors=STATUS_COLORS,
    )


# ── 7. QR Scan & Authorized Custody Transfer Form (FSM Guarded) ────────
@ewaste_bp.route('/ewaste/scan/<asset_id>', methods=['GET', 'POST'])
def handle_qr_scan(asset_id):
    """
    Public QR scan endpoint.
    If viewed by an Admin, displays the Authorized Custody Transfer form with FSM transitions.
    If viewed by public/guest, displays the digital passport with audit trail.
    """
    asset = EWasteAsset.query.filter_by(asset_id=asset_id).first_or_404()
    valid_next_states = ALLOWED_TRANSITIONS.get(asset.current_status, [])

    if request.method == 'POST':
        if session.get('role') != 'admin':
            flash("Unauthorized. Only authenticated campus admins can commit custody transfers.", "danger")
            return redirect(url_for('ewaste.handle_qr_scan', asset_id=asset.asset_id))

        new_status = request.form.get('new_status')
        new_location = request.form.get('location', '').strip() or asset.location
        remarks = request.form.get('remarks', '').strip()
        actor = session.get('name', 'Campus Admin')

        if new_status not in valid_next_states:
            flash(
                f"Invalid FSM transition: {asset.current_status} → {new_status}. "
                f"Allowed next states: {', '.join(valid_next_states) or 'none (terminal state)'}.",
                "danger"
            )
            return redirect(url_for('ewaste.handle_qr_scan', asset_id=asset.asset_id))

        # Log immutable audit entry
        old_status = asset.current_status
        audit_entry = EWasteLifecycle(
            asset_id=asset.id,
            old_status=old_status,
            new_status=new_status,
            location=new_location,
            updated_by=actor,
            notes=remarks or f"Custody transferred from {old_status} to {new_status}",
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(audit_entry)

        # Mutate master record
        asset.current_status = new_status
        asset.location = new_location
        asset.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        flash(f"Asset {asset.asset_id} successfully transitioned to {new_status.replace('_', ' ')}.", "success")
        return redirect(url_for('ewaste.asset_detail', asset_id=asset.asset_id))

    return redirect(url_for('ewaste.asset_detail', asset_id=asset.asset_id))


# ── 8. Public Read-Only Digital Passport ───────────────────────────────
@ewaste_bp.route('/ewaste/<asset_id>')
def public_ewaste_passport(asset_id):
    """
    Publicly accessible Read-Only Digital Passport Page.
    Scanned via mobile QR code on the physical hardware item.
    """
    asset = EWasteAsset.query.filter_by(asset_id=asset_id).first_or_404()
    logs = asset.lifecycle_logs.order_by(EWasteLifecycle.timestamp.asc()).all()
    logged_statuses = [log.display_status for log in logs]
    stage_index = LIFECYCLE_STAGES.index(asset.current_status) if asset.current_status in LIFECYCLE_STAGES else 0

    return render_template(
        'ewaste_public.html',
        asset=asset,
        logs=logs,
        stages=LIFECYCLE_STAGES,
        logged_statuses=logged_statuses,
        current_stage_idx=stage_index
    )


# ── 9. Admin E-Waste View (Backward Compatible) ────────────────────────
@ewaste_bp.route('/admin/ewaste', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_ewaste():
    """Preserves existing SmartWasteX admin page with full compatibility."""
    if request.method == 'POST':
        device_name = request.form.get('device_name', '').strip()
        category = request.form.get('category', 'Computing').strip()
        serial_number = request.form.get('serial_number', '').strip()
        location = request.form.get('location', '').strip()
        recycler = request.form.get('recycler', 'EcoRecycle Solutions Hub').strip()
        try:
            weight_kg = float(request.form.get('weight_kg', 1.5))
        except ValueError:
            weight_kg = 1.5
        notes = request.form.get('notes', '').strip()

        if not device_name or not location:
            flash('Device Name and Campus Location are required fields.', 'danger')
            return redirect(url_for('ewaste.admin_ewaste'))

        total_assets = EWasteAsset.query.count()
        asset_id = f"EW-2026-{(total_assets + 1):04d}"

        qr_folder = current_app.config['QR_FOLDER']
        qr_filename = qr_service.generate_asset_qr(asset_id, output_dir=qr_folder)

        new_asset = EWasteAsset(
            asset_id=asset_id,
            device_name=device_name,
            category=category,
            department='Institutional / IT',
            serial_number=serial_number or f"SN-{asset_id}",
            location=location,
            current_status='REGISTERED',
            recycler=recycler,
            weight_kg=weight_kg,
            notes=notes,
            qr_code_filename=qr_filename,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(new_asset)
        db.session.flush()

        lifecycle_entry = EWasteLifecycle(
            asset_id=new_asset.id,
            status='REGISTERED',
            new_status='REGISTERED',
            location=location,
            notes=f"Asset enrolled into campus e-waste stream: {notes}" if notes else "Asset initial registration.",
            updated_by=session.get('name', 'Admin'),
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(lifecycle_entry)
        db.session.commit()

        flash(f"E-Waste Asset {asset_id} ({device_name}) successfully registered with Digital Passport QR!", 'success')
        return redirect(url_for('ewaste.admin_ewaste_detail', asset_id=asset_id))

    assets = EWasteAsset.query.order_by(EWasteAsset.created_at.desc()).all()
    return render_template('admin/ewaste.html', assets=assets, stages=LIFECYCLE_STAGES)


# ── 10. Admin Asset Detail Lifecycle Advancement (Backward Compatible) ─
@ewaste_bp.route('/admin/ewaste/<asset_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_ewaste_detail(asset_id):
    """Preserves existing SmartWasteX admin asset detail route."""
    asset = EWasteAsset.query.filter_by(asset_id=asset_id).first_or_404()

    if request.method == 'POST':
        new_status = request.form.get('status')
        status_notes = request.form.get('notes', '').strip()

        if new_status in LIFECYCLE_STAGES:
            old_status = asset.current_status
            asset.current_status = new_status
            asset.updated_at = datetime.now(timezone.utc)

            lifecycle_log = EWasteLifecycle(
                asset_id=asset.id,
                old_status=old_status,
                status=new_status,
                new_status=new_status,
                location=asset.location,
                notes=status_notes or f"Status advanced to {new_status}",
                updated_by=session.get('name', 'Admin'),
                timestamp=datetime.now(timezone.utc)
            )
            db.session.add(lifecycle_log)
            db.session.commit()
            flash(f"Asset {asset_id} lifecycle updated to {new_status}!", 'success')
        else:
            flash('Invalid lifecycle stage selected.', 'danger')

        return redirect(url_for('ewaste.admin_ewaste_detail', asset_id=asset.asset_id))

    logs = asset.lifecycle_logs.order_by(EWasteLifecycle.timestamp.asc()).all()
    logged_statuses = [log.display_status for log in logs]

    return render_template(
        'admin/ewaste_detail.html',
        asset=asset,
        logs=logs,
        stages=LIFECYCLE_STAGES,
        logged_statuses=logged_statuses
    )


# ── 11. Clean JSON APIs ────────────────────────────────────────────────
@ewaste_bp.route('/api/ewaste/assets')
def api_ewaste_assets():
    """Returns JSON list of all tracked e-waste assets."""
    assets = EWasteAsset.query.order_by(EWasteAsset.created_at.desc()).all()
    return jsonify([a.to_dict() for a in assets])


@ewaste_bp.route('/api/ewaste/stats')
def api_ewaste_stats():
    """Returns JSON summary metrics for external dashboard widgets."""
    return jsonify({
        'total': EWasteAsset.query.count(),
        'in_use': EWasteAsset.query.filter(EWasteAsset.current_status.in_(['IN_USE', 'REGISTERED'])).count(),
        'decommissioned': EWasteAsset.query.filter_by(current_status='DECOMMISSIONED').count(),
        'storage': EWasteAsset.query.filter(
            EWasteAsset.current_status.in_(['E_WASTE_STORAGE', 'COLLECTION_REQUESTED', 'PENDING_DROPOFF'])
        ).count(),
        'collected': EWasteAsset.query.filter(
            EWasteAsset.current_status.in_(['COLLECTED', 'SENT_TO_RECYCLER'])
        ).count(),
        'recycled': EWasteAsset.query.filter_by(current_status='RECYCLED').count(),
    })
