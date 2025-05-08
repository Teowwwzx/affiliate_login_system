# app/routes/member_routes.py
from flask import Blueprint, render_template, session, flash, redirect, url_for, request
from functools import wraps
from app.database.models import User
from app import db
from werkzeug.security import check_password_hash, generate_password_hash

member_bp = Blueprint('member', __name__, url_prefix='/member')


# Decorator to ensure user is a member
def member_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'member':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('general.dashboard')) # Or auth.login if preferred for unauthorized
        return f(*args, **kwargs)
    return decorated_function

@member_bp.route('/dashboard')
@member_required # Or just login_required if no specific role check needed beyond being a member
def member_dashboard():
    # Add any data fetching specific to the member dashboard
    member_id = session.get('user_id')
    member = User.query.get(member_id)

    if not member:
        flash('Member details not found. Please log in again.', 'danger')
        return redirect(url_for('auth.login')) # Or a more appropriate page

    leader = None
    if member.leader_id:
        leader = User.query.get(member.leader_id)
    
    return render_template(
        'member/member_dashboard.html', 
        title="Member Dashboard",
        member=member,
        leader=leader
    )

@member_bp.route('/change-password', methods=['GET', 'POST'])
@member_required
def change_password():
    member_id = session.get('user_id')
    member = User.query.get(member_id)

    if not member:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')

        if not current_password or not new_password or not confirm_new_password:
            flash('All password fields are required.', 'warning')
            return redirect(url_for('member.change_password'))

        if not check_password_hash(member.password_hash, current_password):
            flash('Incorrect current password.', 'danger')
            return redirect(url_for('member.change_password'))
        
        if new_password != confirm_new_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('member.change_password'))
        
        if len(new_password) < 6: # Basic password length validation
             flash('New password must be at least 6 characters long.', 'warning')
             return redirect(url_for('member.change_password'))

        member.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('Your password has been updated successfully!', 'success')
        return redirect(url_for('member.member_dashboard'))

    return render_template('member/change_password.html', title="Change Password")

# Add other member-specific routes if any, e.g., viewing personal sales, profile details