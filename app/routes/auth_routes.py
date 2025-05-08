# app/routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from flask_login import login_user
from ..database.models import User
from .. import db # If you need to interact with db directly in more complex auth logic

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
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
        # session['user_id'] = user.id # Flask-Login handles this via current_user
        session['username'] = user.username
        session['user_role'] = user.role 
        # session['theme'] = user.theme_preference if hasattr(user, 'theme_preference') and user.theme_preference else 'light'

        flash(f'Welcome back, {user.username}!', 'success')
        return redirect(url_for('general.dashboard'))

    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('general.dashboard'))
        
    return render_template('auth/login.html', title='Login')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been successfully logged out.', 'success')
    return redirect(url_for('general.index'))

# Placeholder for registration - you'll need to implement this
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # For now, just redirect to login or show a simple message
    flash('Registration is not yet implemented.', 'info')
    return redirect(url_for('auth.login'))
    # return render_template('auth/register.html', title='Register') 