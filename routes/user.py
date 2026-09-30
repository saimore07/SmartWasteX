from flask import Blueprint, render_template, session
from routes.auth import login_required, role_required
from models import db
from models.models import User, WasteScan, GreenCreditTransaction
from services.impact_service import ImpactService

user_bp = Blueprint('user', __name__)

@user_bp.route('/user/dashboard')
@login_required
@role_required('user', 'admin')
def dashboard():
    user = db.session.get(User, session['user_id'])
    
    # Calculate leaderboard rank
    higher_users = User.query.filter(User.green_credits > user.green_credits).count()
    rank = higher_users + 1

    # Recent activity: latest 5 credit transactions or scans
    recent_transactions = GreenCreditTransaction.query.filter_by(user_id=user.id)\
        .order_by(GreenCreditTransaction.created_at.desc()).limit(5).all()

    sustainability_score = ImpactService.get_campus_sustainability_score()

    return render_template(
        'user/dashboard.html',
        user=user,
        rank=rank,
        recent_transactions=recent_transactions,
        sustainability_score=sustainability_score
    )

@user_bp.route('/user/history')
@login_required
@role_required('user', 'admin')
def history():
    user = db.session.get(User, session['user_id'])
    scans = WasteScan.query.filter_by(user_id=user.id)\
        .order_by(WasteScan.created_at.desc()).all()
    transactions = GreenCreditTransaction.query.filter_by(user_id=user.id)\
        .order_by(GreenCreditTransaction.created_at.desc()).all()

    return render_template(
        'user/history.html',
        user=user,
        scans=scans,
        transactions=transactions
    )

@user_bp.route('/user/leaderboard')
@login_required
@role_required('user', 'admin')
def leaderboard():
    current_user = db.session.get(User, session['user_id'])
    
    # Query all users ordered by green credits
    champions = User.query.filter_by(role='user').order_by(User.green_credits.desc()).limit(20).all()

    # Determine rank of current user
    higher_users = User.query.filter(User.green_credits > current_user.green_credits).count()
    current_rank = higher_users + 1

    return render_template(
        'user/leaderboard.html',
        current_user=current_user,
        current_rank=current_rank,
        champions=champions
    )

@user_bp.route('/user/impact')
@login_required
@role_required('user', 'admin')
def impact():
    user_impact = ImpactService.get_user_impact(session['user_id'])
    current_user = db.session.get(User, session['user_id'])
    campus_metrics = ImpactService.get_admin_dashboard_metrics()

    return render_template(
        'user/impact.html',
        user=current_user,
        impact=user_impact,
        campus=campus_metrics
    )
