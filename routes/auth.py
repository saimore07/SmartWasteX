import re
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db
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

    # Support pre-filled email from query params (e.g. after signup)
    default_email = request.args.get('email', '')

    if request.method == 'POST':
        login_input = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not login_input or not password:
            flash('Both username/email and password are required.', 'danger')
            return render_template('login.html', email=login_input)

        user = User.query.filter(
            (User.email == login_input) | (User.email == f"{login_input}@smartwastex.in")
        ).first()

        if not user or not user.check_password(password):
            flash('Invalid email or password. Please check your credentials.', 'danger')
            return render_template('login.html', email=login_input)

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

    return render_template('login.html', email=default_email)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('name', '').strip()
        raw_email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        # Validation
        if not full_name or not raw_email or not password or not confirm_password:
            flash('All fields are required. Please fill in your complete details.', 'danger')
            return render_template('signup.html', name=full_name, email=raw_email)

        if len(full_name) < 2:
            flash('Please enter a valid full name.', 'danger')
            return render_template('signup.html', name=full_name, email=raw_email)

        # Email or username format check
        if '@' in raw_email:
            email_pattern = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
            if not re.match(email_pattern, raw_email):
                flash('Please enter a valid email address (e.g., student@university.edu).', 'danger')
                return render_template('signup.html', name=full_name, email=raw_email)
            canonical_email = raw_email
        else:
            if not re.match(r'^[a-z0-9._-]+$', raw_email):
                flash('Username can only contain letters, numbers, dots, and underscores.', 'danger')
                return render_template('signup.html', name=full_name, email=raw_email)
            canonical_email = f"{raw_email}@smartwastex.in"

        if password != confirm_password:
            flash('Passwords do not match. Please re-enter matching passwords.', 'danger')
            return render_template('signup.html', name=full_name, email=raw_email)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('signup.html', name=full_name, email=raw_email)

        # Check for existing user (case-insensitive)
        existing_user = User.query.filter(
            (User.email == canonical_email) | (User.email == raw_email)
        ).first()

        if existing_user:
            flash('An account with that username or email already exists. Please log in.', 'warning')
            return redirect(url_for('auth.login', email=raw_email))

        # Create new user - always role 'user' for safety
        new_user = User(
            name=full_name,
            email=canonical_email,
            role='user',
            green_credits=0,
            items_recycled=0,
            waste_diverted_kg=0.0
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Your account has been successfully created! Please log in below.', 'success')
        return redirect(url_for('auth.login', email=raw_email))

    return render_template('signup.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been safely logged out.', 'info')
    return redirect(url_for('auth.login'))

