from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.models import User

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash('Access denied: You do not have permission to view that resource.', 'danger')
                if user_role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                return redirect(url_for('user.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Both email and password are required.', 'danger')
            return render_template('login.html', email=email)

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid email or password. Please check your credentials.', 'danger')
            return render_template('login.html', email=email)

        # Store session
        session['user_id'] = user.id
        session['email'] = user.email
        session['name'] = user.name
        session['role'] = user.role

        flash(f"Welcome back, {user.name}!", 'success')

        next_url = request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)

        if user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been safely logged out.', 'info')
    return redirect(url_for('auth.login'))
