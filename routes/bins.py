from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from routes.auth import login_required, role_required
from models import db
from models.models import Bin, CollectionRequest
from services.iot_simulator import IoTSimulator

bins_bp = Blueprint('bins', __name__)

@bins_bp.route('/admin/bins')
@login_required
@role_required('admin')
def admin_bins():
    bins_list = Bin.query.order_by(Bin.id.asc()).all()
    # Check if any bin has an overflow or high fill
    overflow_bins = [b for b in bins_list if b.fill_percentage >= 100]
    high_bins = [b for b in bins_list if 85 <= b.fill_percentage < 100]

    return render_template(
        'admin/bins.html',
        bins=bins_list,
        overflow_bins=overflow_bins,
        high_bins=high_bins
    )

@bins_bp.route('/admin/bins/<bin_id>/action', methods=['POST'])
@login_required
@role_required('admin')
def bin_action(bin_id):
    action = request.form.get('action')
    bin_obj = db.get_or_404(Bin, bin_id)
    alert_info = None

    if action == 'plus_10':
        bin_obj, alert_info = IoTSimulator.simulate_delta(bin_id, 10.0)
        flash(f"Telemetry updated: {bin_id} fill increased by +10% to {bin_obj.fill_percentage}%", 'info')
    elif action == 'minus_10':
        bin_obj, alert_info = IoTSimulator.simulate_delta(bin_id, -10.0)
        flash(f"Telemetry updated: {bin_id} fill decreased by -10% to {bin_obj.fill_percentage}%", 'info')
    elif action == 'random':
        bin_obj, alert_info = IoTSimulator.simulate_random(bin_id)
        flash(f"Random telemetry generated for {bin_id}: {bin_obj.fill_percentage}% fill", 'info')
    elif action == 'empty':
        bin_obj, alert_info = IoTSimulator.empty_bin(bin_id)
        flash(f"Bin {bin_id} has been emptied! Telemetry reset to 0%.", 'success')
    elif action == 'overflow':
        bin_obj, alert_info = IoTSimulator.simulate_delta(bin_id, 100.0 - bin_obj.fill_percentage)
        flash(f"Bin {bin_id} pushed to 100% capacity! Overflow alert triggered.", 'danger')

    if alert_info and alert_info.get('triggered'):
        flash(alert_info['message'], 'danger' if alert_info['priority'] == 'URGENT' else 'warning')

    return redirect(url_for('bins.admin_bins'))

@bins_bp.route('/api/bins')
def api_bins():
    bins_list = Bin.query.order_by(Bin.id.asc()).all()
    return jsonify([b.to_dict() for b in bins_list])

@bins_bp.route('/api/iot/bin-update', methods=['POST'])
def api_iot_bin_update():
    """
    Public IoT Gateway Endpoint for External Hardware Sensor Telemetry.
    Receives JSON telemetry payloads from physical smart bins or simulator.
    """
    data = request.get_json(silent=True) or request.form
    if not data:
        return jsonify({'success': False, 'error': 'JSON payload required'}), 400

    raw_bin_id = str(data.get('bin_id', '')).strip().upper()
    if not raw_bin_id:
        return jsonify({'success': False, 'error': 'bin_id is required'}), 400

    # Match bin ID directly or try zero-padded variant (BIN-1 -> BIN-01, BIN-001 -> BIN-01)
    bin_obj = db.session.get(Bin, raw_bin_id)
    if not bin_obj and raw_bin_id.startswith('BIN-'):
        num_part = raw_bin_id.split('-')[-1]
        try:
            padded_id = f"BIN-{int(num_part):02d}"
            bin_obj = db.session.get(Bin, padded_id)
        except ValueError:
            pass

    if not bin_obj:
        return jsonify({'success': False, 'error': f"Bin '{raw_bin_id}' not found"}), 404

    action = data.get('action')
    if action == 'empty':
        bin_obj, alert_info = IoTSimulator.empty_bin(bin_obj.id)
        return jsonify({
            'success': True,
            'bin_id': bin_obj.id,
            'fill_level': bin_obj.fill_percentage,
            'status': bin_obj.status,
            'weight_kg': bin_obj.weight_kg,
            'temperature_c': bin_obj.temperature_c,
            'battery_level': bin_obj.battery_level,
            'action': 'emptied'
        })

    # Read fill level from payload (supports fill_level, fill_percentage, or fill)
    fill_val = data.get('fill_level')
    if fill_val is None:
        fill_val = data.get('fill_percentage', data.get('fill'))

    if fill_val is None:
        return jsonify({'success': False, 'error': 'fill_level is required'}), 400

    try:
        fill_val = float(fill_val)
        fill_val = max(0.0, min(100.0, fill_val))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'fill_level must be a numeric value'}), 400

    bin_obj, alert_info = IoTSimulator.update_bin_telemetry(bin_obj, fill_val)

    return jsonify({
        'success': True,
        'bin_id': bin_obj.id,
        'fill_level': bin_obj.fill_percentage,
        'status': bin_obj.status,
        'weight_kg': bin_obj.weight_kg,
        'temperature_c': bin_obj.temperature_c,
        'battery_level': bin_obj.battery_level,
        'alert': alert_info
    })

@bins_bp.route('/api/bins/<bin_id>/simulate', methods=['POST'])
@login_required
@role_required('admin')
def api_simulate_bin(bin_id):
    data = request.get_json(silent=True) or request.form
    action = data.get('action')

    bin_obj = db.session.get(Bin, bin_id)
    if not bin_obj:
        return jsonify({'success': False, 'error': f'Bin {bin_id} not found'}), 404

    alert_info = None
    if action == 'plus_10':
        bin_obj, alert_info = IoTSimulator.simulate_delta(bin_id, 10.0)
    elif action == 'minus_10':
        bin_obj, alert_info = IoTSimulator.simulate_delta(bin_id, -10.0)
    elif action == 'random':
        bin_obj, alert_info = IoTSimulator.simulate_random(bin_id)
    elif action == 'empty':
        bin_obj, alert_info = IoTSimulator.empty_bin(bin_id)
    elif action == 'set_fill':
        fill_val = float(data.get('fill', 50.0))
        bin_obj, alert_info = IoTSimulator.update_bin_telemetry(bin_obj, fill_val)
    else:
        return jsonify({'success': False, 'error': 'Invalid action'}), 400

    return jsonify({
        'success': True,
        'bin': bin_obj.to_dict(),
        'alert': alert_info
    })

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

@bins_bp.route('/admin/collections/<int:req_id>/status', methods=['POST'])
@login_required
@role_required('admin')
def update_collection_status(req_id):
    req_obj = db.get_or_404(CollectionRequest, req_id)
    new_status = request.form.get('status')
    
    if new_status in ['PENDING', 'ASSIGNED', 'COLLECTED', 'COMPLETED']:
        req_obj.status = new_status
        if new_status == 'COMPLETED':
            req_obj.resolved_at = datetime.now(timezone.utc)
            # When completed, automatically empty the corresponding bin
            bin_obj = db.session.get(Bin, req_obj.bin_id)
            if bin_obj:
                IoTSimulator.empty_bin(bin_obj.id)
        db.session.commit()
        flash(f"Collection Request {req_obj.request_code} marked as {new_status}.", 'success')
    else:
        flash("Invalid status transition.", 'danger')

    return redirect(url_for('bins.admin_collections'))
