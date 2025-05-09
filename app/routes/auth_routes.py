# app/routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from flask_login import login_user, logout_user, current_user, login_required
from ..database.models import User
from .. import db # If you need to interact with db directly in more complex auth logic

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:  # Check if already logged in
        if current_user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        elif current_user.role == 'leader':
            return redirect(url_for('leader.leader_dashboard'))
        elif current_user.role == 'member':
            return redirect(url_for('member.member_dashboard'))
        else:
            return redirect(url_for('general.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if user account is active
        if not user.status:
            flash('Your account is inactive. Please contact an administrator.', 'warning')
            return redirect(url_for('auth.login'))

        # Use Flask-Login's login_user function
        login_user(user)

        # Store user info in session for convenience (Flask-Login handles user_id)
        session['username'] = user.username
        session['user_role'] = user.role

        flash(f'Welcome back, {user.username}!', 'success')
        
        # Handle the next parameter if it exists
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):  # Ensure it's a relative URL
            return redirect(next_page)
        
        # Redirect to appropriate dashboard based on role
        if user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        elif user.role == 'leader':
            return redirect(url_for('leader.leader_dashboard'))
        elif user.role == 'member':
            return redirect(url_for('member.member_dashboard'))
        else:
            flash('Login successful, but role dashboard not found.', 'warning')
            return redirect(url_for('general.index'))

    return render_template('auth/login.html', title='Login')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()  # Use Flask-Login's logout_user function
    session.clear()  # Clear any custom session data
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('general.index'))

# Placeholder for registration - you'll need to implement this
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # For now, just redirect to login or show a simple message
    flash('Registration is not yet implemented.', 'info')
    return redirect(url_for('auth.login'))
    # return render_template('auth/register.html', title='Register') 