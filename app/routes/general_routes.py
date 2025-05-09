from ..database import db
from datetime import datetime
from ..database.models import User
from ..utils import login_required
from werkzeug.security import generate_password_hash
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user

general_bp = Blueprint('general', __name__)

# Index Page (Public Landing Page)
@general_bp.route('/')
def index():
    # If user is already logged in, redirect them to their dashboard
    if current_user.is_authenticated:
        # flash("You are already logged in.", 'info') # Optional: inform user
        if current_user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        elif current_user.role == 'leader':
            return redirect(url_for('leader.leader_dashboard'))
        elif current_user.role == 'member':
            return redirect(url_for('member.member_dashboard'))
        else:
            # Fallback if role is not defined or unexpected for an authenticated user
            return redirect(url_for('auth.logout')) # Or some generic authenticated page
    
    return render_template('index.html')

@general_bp.route('/dashboard')
@login_required
def dashboard():
    # Redirect to appropriate dashboard based on user role
    if current_user.role == 'admin':
        return redirect(url_for('admin.admin_dashboard'))
    elif current_user.role == 'leader':
        return redirect(url_for('leader.leader_dashboard'))
    elif current_user.role == 'member':
        return redirect(url_for('member.member_dashboard'))
    
    # If we somehow get here, it's an unexpected case
    flash("Unexpected user role. Please contact support.", 'danger')
    return redirect(url_for('auth.logout'))

@general_bp.context_processor
def inject_current_year():
    return dict(current_year=datetime.utcnow().year)
