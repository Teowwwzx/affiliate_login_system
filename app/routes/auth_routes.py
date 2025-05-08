# app/routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import check_password_hash
from flask_login import login_user, logout_user, current_user
from ..database.models import User
from .. import db # If you need to interact with db directly in more complex auth logic
from urllib.parse import urlparse, urljoin

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def is_safe_url(target):
    """
    Checks if a URL is safe for redirection.
    Ensures that the target URL is on the same domain as the application.
    """
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    # Ensure the scheme is http or https and the network location (domain) matches.
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        current_app.logger.info(f"User '{current_user.username}' (Role: {current_user.role}) already authenticated, redirecting to their dashboard.")
        # If user is already logged in, ALWAYS redirect to their respective dashboard
        # Ignore any 'next' parameter in this specific scenario to break loops.
        if current_user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        elif current_user.role == 'leader':
            return redirect(url_for('leader.leader_dashboard'))
        elif current_user.role == 'member':
            return redirect(url_for('member.member_dashboard'))
        else:
            # Fallback if role is somehow not set or recognized
            current_app.logger.warning(f"Authenticated user '{current_user.username}' has unrecognized role '{current_user.role}', redirecting to general dashboard.")
            return redirect(url_for('general.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Please check your login details and try again.', 'error')
            current_app.logger.warning(f"Failed login attempt for email: {email}")
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        current_app.logger.info(f"User '{user.username}' (Role: {user.role}) logged in successfully.")
        
        next_page = request.args.get('next')
        
        if next_page and is_safe_url(next_page):
            current_app.logger.info(f"Redirecting to 'next' URL: {next_page}")
            return redirect(next_page)
        else:
            if next_page: # Log if next_page was present but unsafe
                current_app.logger.warning(f"'next' URL '{next_page}' was unsafe or invalid. Redirecting to role-based dashboard.")
            
            current_app.logger.info(f"No 'next' URL or unsafe, redirecting to role-based dashboard for user '{user.username}'.")
            if user.role == 'admin':
                return redirect(url_for('admin.admin_dashboard'))
            elif user.role == 'leader':
                return redirect(url_for('leader.leader_dashboard'))
            elif user.role == 'member':
                return redirect(url_for('member.member_dashboard'))
            else:
                current_app.logger.warning(f"User '{user.username}' has unrecognized role '{user.role}' post-login, redirecting to general dashboard.")
                return redirect(url_for('general.dashboard'))

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