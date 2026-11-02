from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from routes.auth import login_required, role_required
from models import db
from models.models import Bin, CollectionRequest
from services.iot_service import IoTService

bins_bp = Blueprint('bins', __name__)

def check_iot_auth():
    """
    Validates API key authentication for IoT sensor ingestion endpoints.
    Allows:
    1. Authenticated admin session
    2. Header: X-API-Key: <key>
    3. Header: Authorization: Bearer <key> or ApiKey <key>
    4. Query parameter: ?api_key=<key>
    5. JSON body: {"api_key": "<key>"}
    """
    if session.get('role') == 'admin' or session.get('user_role') == 'admin':
        return True

    expected_key = current_app.config.get('IOT_API_KEY', 'smartwastex-iot-device-key-2026')

    api_key = request.headers.get('X-API-Key')
    if not api_key:
        auth_hdr = request.headers.get('Authorization', '')
        if auth_hdr.startswith('Bearer '):
            api_key = auth_hdr[7:].strip()
        elif auth_hdr.startswith('ApiKey '):
            api_key = auth_hdr[7:].strip()
    if not api_key:
        api_key = request.args.get('api_key')
    if not api_key and request.is_json:
        body = request.get_json(silent=True)
        if isinstance(body, dict):
            api_key = body.get('api_key')

    if api_key and api_key == expected_key:
        return True

    return False

@bins_bp.route('/admin/bins')
@login_required
@role_required('admin')
def admin_bins():
    bins_list = Bin.query.order_by(Bin.id.asc()).all()
    overflow_bins = [b for b in bins_list if b.fill_percentage >= 100]
    high_bins = [b for b in bins_list if 85 <= b.fill_percentage < 100]
    api_key = current_app.config.get('IOT_API_KEY', 'smartwastex-iot-device-key-2026')

    return render_template(
        'admin/bins.html',
        bins=bins_list,
        overflow_bins=overflow_bins,
        high_bins=high_bins,
        iot_api_key=api_key
    )

@bins_bp.route('/admin/bins/<bin_id>/action', methods=['POST'])
@login_required
@role_required('admin')
def bin_action(bin_id):
    action = request.form.get('action')
    bin_obj = db.get_or_404(Bin, bin_id)

    if action == 'empty':
        bin_obj, _ = IoTService.empty_bin(bin_id)
        flash(f"Bin {bin_id} marked as emptied by facilities staff. Telemetry reset to 0%.", 'success')
    else:
        flash("Unsupported bin action.", 'warning')

    return redirect(url_for('bins.admin_bins'))

@bins_bp.route('/api/bins')
def api_bins():
    bins_list = Bin.query.order_by(Bin.id.asc()).all()
    return jsonify([b.to_dict() for b in bins_list])

@bins_bp.route('/api/iot/bin-update', methods=['POST'])
@bins_bp.route('/api/iot/telemetry', methods=['POST'])
@bins_bp.route('/api/iot/sensors', methods=['POST'])
def api_iot_bin_update():
    """
    Authenticated IoT Gateway Endpoint for External Hardware Sensor Telemetry.
    Ingests real physical sensor readings (fill percentage, weight, temperature, battery level).
    """
    if not check_iot_auth():
        return jsonify({
            'success': False,
            'error': 'Unauthorized: Valid X-API-Key or Authorization header required'
        }), 401

    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict() if request.form else None

    if not data:
        return jsonify({'success': False, 'error': 'JSON payload required'}), 400

    is_valid, err_msg, parsed = IoTService.validate_payload(data)
    if not is_valid:
        return jsonify({'success': False, 'error': err_msg}), 400

    raw_bin_id = parsed.get('raw_bin_id')
    bin_obj = IoTService.resolve_bin(raw_bin_id)
    if not bin_obj:
        return jsonify({'success': False, 'error': f"Bin '{raw_bin_id}' not found"}), 404

    # Handle tare/empty action
    if parsed.get('action') == 'empty':
        bin_obj, _ = IoTService.empty_bin(bin_obj.id)
        return jsonify({
            'success': True,
            'bin_id': bin_obj.id,
            'fill_percentage': bin_obj.fill_percentage,
            'fill_level': bin_obj.fill_percentage,
            'status': bin_obj.status,
            'weight_kg': bin_obj.weight_kg,
            'temperature_c': bin_obj.temperature_c,
            'battery_level': bin_obj.battery_level,
            'last_updated': bin_obj.last_updated.isoformat() if bin_obj.last_updated else None,
            'action': 'emptied'
        }), 200

    # Process real physical sensor telemetry
    bin_obj, alert_info = IoTService.record_sensor_reading(
        bin_obj=bin_obj,
        fill_percentage=parsed['fill_percentage'],
        weight_kg=parsed['weight_kg'],
        temperature_c=parsed['temperature_c'],
        battery_level=parsed['battery_level']
    )

    return jsonify({
        'success': True,
        'bin_id': bin_obj.id,
        'fill_percentage': bin_obj.fill_percentage,
        'fill_level': bin_obj.fill_percentage,
        'status': bin_obj.status,
        'weight_kg': bin_obj.weight_kg,
        'temperature_c': bin_obj.temperature_c,
        'battery_level': bin_obj.battery_level,
        'last_updated': bin_obj.last_updated.isoformat() if bin_obj.last_updated else None,
        'alert': alert_info
    }), 200

@bins_bp.route('/admin/collections')
@login_required
@role_required('admin')
def admin_collections():
    status_filter = request.args.get('status')
    query = CollectionRequest.query.order_by(
        db.case(
            (CollectionRequest.status == 'PENDING', 1),
            (CollectionRequest.status == 'ASSIGNED', 2),
            (CollectionRequest.status == 'COLLECTED', 3),
            else_=4
        ),
        CollectionRequest.created_at.desc()
    )

    if status_filter:
        query = query.filter_by(status=status_filter)

    requests = query.all()
    pending_count = CollectionRequest.query.filter_by(status='PENDING').count()

    return render_template(
        'admin/collection.html',
        requests=requests,
        pending_count=pending_count,
        current_filter=status_filter
    )

@bins_bp.route('/admin/collections/<int:req_id>/schedule', methods=['POST'])
@login_required
@role_required('admin')
def schedule_collection(req_id):
    req_obj = db.get_or_404(CollectionRequest, req_id)
    pickup_date = request.form.get('pickup_date', '').strip()
    pickup_time = request.form.get('pickup_time', '').strip()

    if not pickup_date:
        pickup_date = datetime.now().strftime('%Y-%m-%d')
    if not pickup_time:
        pickup_time = datetime.now().strftime('%H:%M')

    req_obj.status = 'SCHEDULED'
    req_obj.scheduled_date = pickup_date
    req_obj.scheduled_time = pickup_time
    db.session.commit()

    flash(f"Waste pickup for {req_obj.bin_id} scheduled for {pickup_date} at {pickup_time}.", 'success')
    next_url = request.form.get('next_url')
    if next_url:
        return redirect(next_url)
    return redirect(url_for('admin.dashboard'))

@bins_bp.route('/admin/collections/<int:req_id>/status', methods=['POST'])
@login_required
@role_required('admin')
def update_collection_status(req_id):
    req_obj = db.get_or_404(CollectionRequest, req_id)
    new_status = request.form.get('status')
    
    if new_status in ['PENDING', 'SCHEDULED', 'ASSIGNED', 'COLLECTED', 'COMPLETED']:
        req_obj.status = new_status
        if new_status == 'COMPLETED':
            req_obj.resolved_at = datetime.now(timezone.utc)
            # When completed, automatically reset the serviced bin to empty
            bin_obj = db.session.get(Bin, req_obj.bin_id)
            if bin_obj:
                IoTService.empty_bin(bin_obj.id)
        db.session.commit()
        flash(f"Collection Request {req_obj.request_code} marked as {new_status}.", 'success')
    else:
        flash("Invalid status transition.", 'danger')

    next_url = request.form.get('next_url')
    if next_url:
        return redirect(next_url)
    return redirect(url_for('bins.admin_collections'))
