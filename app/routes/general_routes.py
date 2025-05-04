from flask import Blueprint, render_template, request, flash, redirect, url_for, session, abort
from werkzeug.security import generate_password_hash
from ..utils import login_required
from ..models import User, db
from datetime import datetime

general_bp = Blueprint('general', __name__)

# Index Page (Public Landing Page)
@general_bp.route('/')
def index():
    # If user is already logged in, redirect them to their dashboard
    if 'user_id' in session:
        return redirect(url_for('general.dashboard'))
    current_year = datetime.utcnow().year
    return render_template('general/index.html', current_year=current_year)

@general_bp.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session.get('user_id'))
    if user is None:
        flash("User not found.", 'danger')
        session.clear()
        return redirect(url_for('auth.login'))
    
    # Redirect to appropriate dashboard based on user role
    if user.role == 'admin':
        return redirect(url_for('admin.admin_dashboard'))
    elif user.role == 'leader':
        return redirect(url_for('leader.leader_dashboard'))
    elif user.role == 'offline':
        return redirect(url_for('offline.offline_dashboard'))
    
    # If we somehow get here, it's an unexpected case
    flash("Unexpected user role. Please contact support.", 'danger')
    return redirect(url_for('auth.logout'))

@general_bp.route('/set_nav_view', methods=['POST'])
@login_required
def set_nav_view():
    view = request.form.get('view')
    if view in ['navbar', 'sidebar']:
        session['preferred_nav'] = view
        flash('Navigation view updated successfully.', 'success')
        return redirect(request.referrer or url_for('general.profile'))
    return redirect(request.referrer or url_for('general.profile'))

@general_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Handle navigation view update
        view = request.form.get('view')
        if view in ['navbar', 'sidebar']:
            session['preferred_nav'] = view
            flash('Navigation view updated successfully.', 'success')
        
        # Handle theme update
        theme = request.form.get('theme')
        if theme in ['light', 'dark']:
            session['theme'] = theme
            flash('Theme updated successfully.', 'success')

        # Redirect to the current page to apply changes
        return redirect(request.referrer or url_for('general.settings'))

    # Ensure theme is applied to the page
    theme = session.get('theme', 'light')
    return render_template('general/settings.html', theme=theme)

@general_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session.get('user_id'))
    if user is None:
        flash("User not found.", 'danger')
        session.clear()
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        error = None
        if username != user.username and User.query.filter_by(username=username).first():
            error = f"Username '{username}' is already taken."
        elif not username:
            error = 'Username is required.'

        if error is None:
            user.username = username
            if password:
                user.password_hash = generate_password_hash(password)

            db.session.commit()
            session['username'] = user.username
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('general.profile'))
        else:
            flash(error, 'danger')

    return render_template('profile.html', user=user)

@general_bp.context_processor
def inject_current_year():
    return dict(current_year=datetime.utcnow().year)
