# app/routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from flask_login import login_user, current_user, logout_user
from ..database.models import User
from .. import db # If you need to interact with db directly in more complex auth logic

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirect based on role if already authenticated
        if current_user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        elif current_user.role == 'leader':
            # Assuming you have/will have 'leader.leader_dashboard'
            return redirect(url_for('leader.leader_dashboard')) 
        elif current_user.role == 'member':
            # Assuming you have/will have 'member.member_dashboard'
            return redirect(url_for('member.member_dashboard'))
        else:
            return redirect(url_for('general.index')) # Fallback

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # remember = True if request.form.get('remember') else False # Add if you implement 'Remember Me'

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if user account is active
        if not user.status:  # Assuming 'status' is a boolean field in your User model
            flash('Your account is inactive. Please contact an administrator.', 'warning')
            return redirect(url_for('auth.login'))

        # Use Flask-Login's login_user function
        # login_user(user, remember=remember) # Uncomment and use if you implement 'Remember Me'
        login_user(user) # Simplified for now

        # Store user info in session (Flask-Login handles user_id in its own way)
        session['username'] = user.username
        # session['user_role'] = user.role # Not strictly needed by role_required now

        flash(f'Welcome back, {user.username}!', 'success')
        
        next_page = request.args.get('next')
        # Basic validation for next_page to prevent open redirect vulnerabilities
        # A more robust check might involve urlparse and checking netloc
        if next_page and (not next_page.startswith('/') and not next_page.startswith(request.host_url)):
            next_page = None

        # Redirect based on role, honoring next_page if valid and present
        if user.role == 'admin':
            return redirect(next_page or url_for('admin.admin_dashboard'))
        elif user.role == 'leader':
            return redirect(next_page or url_for('leader.leader_dashboard')) 
        elif user.role == 'member':
            return redirect(next_page or url_for('member.member_dashboard'))
        else:
            # Fallback if role is not recognized or no specific dashboard
            return redirect(next_page or url_for('general.index'))

    return render_template('auth/login.html', title='Login')

@auth_bp.route('/logout')
def logout():
    logout_user() # Use Flask-Login's logout_user
    # session.clear() # logout_user() is generally preferred as it cleans up Flask-Login specific session keys
    flash('You have been successfully logged out.', 'success')
    return redirect(url_for('general.index'))

# Placeholder for registration - you'll need to implement this
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # For now, just redirect to login or show a simple message
    flash('Registration is not yet implemented.', 'info')
    return redirect(url_for('auth.login'))
    # return render_template('auth/register.html', title='Register') 