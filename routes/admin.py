import json
from flask import Blueprint, render_template
from routes.auth import login_required, role_required
from models import db
from models.models import Bin, CollectionRequest, EWasteAsset, WasteScan
from services.impact_service import ImpactService

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/dashboard')
@login_required
@role_required('admin')
def dashboard():
    metrics = ImpactService.get_admin_dashboard_metrics()
    chart_data = ImpactService.get_chart_data()

    # Active pickup alerts for full bins (100% capacity) and urgent collection requests
    pickup_alerts = CollectionRequest.query.filter(
        CollectionRequest.status.in_(['PENDING', 'SCHEDULED', 'ASSIGNED']),
        (CollectionRequest.fill_level >= 100) | (CollectionRequest.priority == 'URGENT')
    ).order_by(
        db.case((CollectionRequest.status == 'PENDING', 1), (CollectionRequest.status == 'SCHEDULED', 2), else_=3),
        CollectionRequest.created_at.desc()
    ).all()

    # Query recent alerts / urgent collection requests
    urgent_requests = CollectionRequest.query.filter(
        CollectionRequest.status.in_(['PENDING', 'SCHEDULED', 'ASSIGNED'])
    ).order_by(
        db.case((CollectionRequest.priority == 'URGENT', 1), else_=2),
        CollectionRequest.created_at.desc()
    ).limit(5).all()

    bins_list = Bin.query.order_by(Bin.id.asc()).all()
    recent_scans = WasteScan.query.order_by(WasteScan.created_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        metrics=metrics,
        chart_data=chart_data,
        chart_data_json=json.dumps(chart_data),
        urgent_requests=urgent_requests,
        pickup_alerts=pickup_alerts,
        bins=bins_list,
        recent_scans=recent_scans
    )


@admin_bp.route('/admin/analytics')
@login_required
@role_required('admin')
def analytics():
    metrics = ImpactService.get_admin_dashboard_metrics()
    chart_data = ImpactService.get_chart_data()
    bins_list = Bin.query.order_by(Bin.id.asc()).all()
    bins_json = json.dumps([b.to_dict() for b in bins_list])

    total_scans = WasteScan.query.count()
    total_ewaste = EWasteAsset.query.count()

    return render_template(
        'admin/analytics.html',
        metrics=metrics,
        chart_data_json=json.dumps(chart_data),
        bins_json=bins_json,
        bins=bins_list,
        total_scans=total_scans,
        total_ewaste=total_ewaste
    )

