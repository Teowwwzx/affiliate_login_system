from ..database import db
from datetime import datetime
from ..database.models import User
from ..utils import login_required
from werkzeug.security import generate_password_hash
from flask import Blueprint, render_template, request, flash, redirect, url_for, session

general_bp = Blueprint('general', __name__)

# Index Page (Public Landing Page)
@general_bp.route('/')
def index():
    # If user is already logged in, redirect them to their dashboard
    if 'user_id' in session:
        return redirect(url_for('general.dashboard'))
    return render_template('index.html')

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
    elif user.role == 'member':
        return redirect(url_for('member.member_dashboard'))
    
    # If we somehow get here, it's an unexpected case
    flash("Unexpected user role. Please contact support.", 'danger')
    return redirect(url_for('auth.logout'))

@general_bp.context_processor
def inject_current_year():
    return dict(current_year=datetime.utcnow().year)
