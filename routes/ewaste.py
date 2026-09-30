import os
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from routes.auth import login_required, role_required
from models import db
from models.models import EWasteAsset, EWasteLifecycle
from services.qr_service import qr_service

ewaste_bp = Blueprint('ewaste', __name__)

LIFECYCLE_STAGES = [
    'REGISTERED',
    'DECOMMISSIONED',
    'COLLECTION_REQUESTED',
    'COLLECTED',
    'SENT_TO_RECYCLER',
    'RECYCLED'
]

@ewaste_bp.route('/admin/ewaste', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_ewaste():
    if request.method == 'POST':
        device_name = request.form.get('device_name', '').strip()
        category = request.form.get('category', 'Computing').strip()
        serial_number = request.form.get('serial_number', '').strip()
        location = request.form.get('location', '').strip()
        recycler = request.form.get('recycler', 'EcoRecycle Solutions Hub').strip()
        weight_kg = float(request.form.get('weight_kg', 1.5))
        notes = request.form.get('notes', '').strip()

        if not device_name or not location:
            flash('Device Name and Campus Location are required fields.', 'danger')
            return redirect(url_for('ewaste.admin_ewaste'))

        # Generate unique sequential asset ID
        total_assets = EWasteAsset.query.count()
        asset_id = f"EW-2026-{(total_assets + 1):04d}"

        # Generate QR code
        qr_folder = current_app.config['QR_FOLDER']
        qr_filename = qr_service.generate_asset_qr(asset_id, output_dir=qr_folder)

        # Create Asset Record
        new_asset = EWasteAsset(
            asset_id=asset_id,
            device_name=device_name,
            category=category,
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

        # Add Initial Lifecycle Step
        lifecycle_entry = EWasteLifecycle(
            asset_id=new_asset.id,
            status='REGISTERED',
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

@ewaste_bp.route('/admin/ewaste/<asset_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_ewaste_detail(asset_id):
    asset = EWasteAsset.query.filter_by(asset_id=asset_id).first_or_404()

    if request.method == 'POST':
        new_status = request.form.get('status')
        status_notes = request.form.get('notes', '').strip()

        if new_status in LIFECYCLE_STAGES:
            asset.current_status = new_status
            asset.updated_at = datetime.now(timezone.utc)

            # Record Lifecycle Event
            lifecycle_log = EWasteLifecycle(
                asset_id=asset.id,
                status=new_status,
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
    logged_statuses = [log.status for log in logs]

    return render_template(
        'admin/ewaste_detail.html',
        asset=asset,
        logs=logs,
        stages=LIFECYCLE_STAGES,
        logged_statuses=logged_statuses
    )

@ewaste_bp.route('/ewaste/<asset_id>')
def public_ewaste_passport(asset_id):
    """
    Publicly accessible Read-Only Digital Passport Page.
    Scanned via mobile QR code on the physical hardware item.
    """
    asset = EWasteAsset.query.filter_by(asset_id=asset_id).first_or_404()
    logs = asset.lifecycle_logs.order_by(EWasteLifecycle.timestamp.asc()).all()
    logged_statuses = [log.status for log in logs]

    # Map status to friendly stage information
    stage_index = LIFECYCLE_STAGES.index(asset.current_status) if asset.current_status in LIFECYCLE_STAGES else 0

    return render_template(
        'ewaste_public.html',
        asset=asset,
        logs=logs,
        stages=LIFECYCLE_STAGES,
        logged_statuses=logged_statuses,
        current_stage_idx=stage_index
    )
