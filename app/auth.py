# This file will contain authentication routes and logic (login, logout, etc.)
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, db # Import User model and db
from .utils import login_required # Import login_required decorator

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: # If already logged in, redirect to appropriate dashboard
        user_role = session.get('user_role')
        if user_role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        elif user_role == 'leader':
            return redirect(url_for('leader.leader_dashboard'))
        else: # member user
            return redirect(url_for('member.member_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        error = None
        user = User.query.filter_by(username=username).first()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user.password_hash, password):
            error = 'Incorrect password.'

        if error is None:
            # Store user info in session
            session.clear()
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['username'] = user.username
            session['preferred_nav'] = user.preferred_nav

            # Store can_view_funds flag only for leaders
            if user.role == 'leader':
                session['user_can_view_funds'] = user.can_view_funds

            flash(f'Welcome back, {user.username}!', 'success')
            # Redirect to appropriate dashboard based on role
            if user.role == 'admin':
                return redirect(url_for('admin.admin_dashboard'))
            elif user.role == 'leader':
                return redirect(url_for('leader.leader_dashboard'))
            else: # member user
                return redirect(url_for('member.member_dashboard'))
        else:
            flash(error, 'danger')

    # For GET request or failed POST, render login form
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required # Make sure user is logged in to log out
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

# Add registration/user creation routes here later if needed (e.g., for admin/leader)
