import os
import shutil
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from werkzeug.utils import secure_filename
from routes.auth import login_required, role_required
from models import db
from models.models import User, WasteScan, GreenCreditTransaction, Bin
from services.classifier import classifier
from services.iot_simulator import IoTSimulator

waste_bp = Blueprint('waste', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@waste_bp.route('/user/scan', methods=['GET', 'POST'])
@login_required
@role_required('user', 'admin')
def scan():
    if request.method == 'POST':
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)

        user_id = session['user_id']
        sample_item = request.form.get('sample_item', '').strip()
        user_hint = request.form.get('hint', '').strip()
        uploaded_file = request.files.get('waste_image')

        filename = None
        filepath = None

        # Check if user selected one of the rapid demo samples
        if sample_item:
            sample_source = os.path.join(upload_folder, 'samples', f"{sample_item}.jpg")
            clean_name = f"sample_{sample_item}_{int(datetime.now().timestamp())}.jpg"
            dest_path = os.path.join(upload_folder, clean_name)
            
            if os.path.exists(sample_source):
                shutil.copyfile(sample_source, dest_path)
            else:
                # Generate a dummy placeholder image with OpenCV if sample not found
                import cv2
                import numpy as np
                dummy = np.zeros((300, 300, 3), dtype=np.uint8)
                dummy[:] = (35, 120, 50) if 'banana' in sample_item else (140, 60, 20)
                cv2.imwrite(dest_path, dummy)

            filename = clean_name
            filepath = dest_path
            original_label = sample_item

        elif uploaded_file and uploaded_file.filename:
            if not allowed_file(uploaded_file.filename):
                flash('Unsupported image format. Allowed formats: PNG, JPG, JPEG, WEBP.', 'danger')
                return render_template('user/scan.html')

            sec_name = secure_filename(uploaded_file.filename)
            unique_name = f"upload_{int(datetime.now().timestamp())}_{sec_name}"
            dest_path = os.path.join(upload_folder, unique_name)
            uploaded_file.save(dest_path)

            filename = unique_name
            filepath = dest_path
            original_label = uploaded_file.filename
        else:
            flash('Please select an image file to upload or choose one of the demo samples.', 'warning')
            return render_template('user/scan.html')

        # Run AI Classification
        result = classifier.classify(filepath, original_filename=original_label, user_hint=user_hint)

        # Store in database
        scan_record = WasteScan(
            user_id=user_id,
            image_filename=filename,
            detected_item=result['detected_item'],
            category=result['category'],
            confidence=result['confidence'],
            recommendation=result['recommendation'],
            nearest_bin_id=result['nearest_bin_id'],
            credits_awarded=result['credits'],
            diverted_weight_kg=result['diverted_weight_kg'],
            status='SCANNED',
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(scan_record)
        db.session.commit()

        return redirect(url_for('waste.result', scan_id=scan_record.id))

    return render_template('user/scan.html')

@waste_bp.route('/user/waste/result/<int:scan_id>')
@login_required
@role_required('user', 'admin')
def result(scan_id):
    scan_record = db.get_or_404(WasteScan, scan_id)

    # Security check: User can only view their own scan records (unless admin)
    if scan_record.user_id != session['user_id'] and session.get('role') != 'admin':
        flash('Access denied: You can only view your own scan records.', 'danger')
        return redirect(url_for('user.dashboard'))

    nearest_bin = db.session.get(Bin, scan_record.nearest_bin_id) if scan_record.nearest_bin_id else None

    return render_template(
        'user/result.html',
        scan=scan_record,
        bin=nearest_bin
    )

@waste_bp.route('/user/waste/confirm/<int:scan_id>', methods=['POST'])
@login_required
@role_required('user', 'admin')
def confirm_disposal(scan_id):
    scan_record = db.get_or_404(WasteScan, scan_id)

    # Security check: User can only confirm their own scan disposals
    if scan_record.user_id != session['user_id'] and session.get('role') != 'admin':
        flash('Access denied: You cannot confirm another user\'s disposal.', 'danger')
        return redirect(url_for('user.dashboard'))

    user = db.session.get(User, session['user_id'])

    if scan_record.status == 'DISPOSED':
        flash('This item disposal has already been confirmed.', 'info')
        return redirect(url_for('waste.result', scan_id=scan_record.id))

    # Mark as disposed
    scan_record.status = 'DISPOSED'
    
    # Update user statistics
    user.green_credits += scan_record.credits_awarded
    user.items_recycled += 1
    user.waste_diverted_kg = round(user.waste_diverted_kg + scan_record.diverted_weight_kg, 2)

    # Record Green Credit Transaction
    transaction = GreenCreditTransaction(
        user_id=user.id,
        amount=scan_record.credits_awarded,
        action_type='WASTE_DISPOSAL',
        description=f"{scan_record.detected_item} properly segregated ({scan_record.category})",
        reference_id=f"SCAN-{scan_record.id}",
        created_at=datetime.now(timezone.utc)
    )
    db.session.add(transaction)

    # Slightly update the target smart bin telemetry to reflect realistic intake
    if scan_record.nearest_bin_id:
        bin_obj = db.session.get(Bin, scan_record.nearest_bin_id)
        if bin_obj:
            new_fill = min(100.0, bin_obj.fill_percentage + 0.8)
            IoTSimulator.update_bin_telemetry(bin_obj, new_fill)

    db.session.commit()

    flash(f"🎉 Disposal Confirmed! You earned +{scan_record.credits_awarded} Green Credits. Thank you for keeping our campus clean!", 'success')
    return redirect(url_for('waste.result', scan_id=scan_record.id))
