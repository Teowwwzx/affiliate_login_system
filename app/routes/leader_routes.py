# app/routes/leader_routes.py
from flask import Blueprint, render_template, session, flash, redirect, url_for, request
from functools import wraps
from app.database.models import User, Fund
from app import db
from sqlalchemy import func
from werkzeug.security import generate_password_hash

leader_bp = Blueprint("leader", __name__, url_prefix="/leader")


# Decorator to ensure user is a leader
def leader_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'leader':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('general.dashboard')) # Or auth.login if preferred for unauthorized
        return f(*args, **kwargs)
    return decorated_function


@leader_bp.route("/dashboard")
@leader_required
def leader_dashboard():
    leader_id = session.get('user_id')
    leader = User.query.get(leader_id)

    if not leader:
        flash('Leader information not found. Please log in again.', 'danger')
        return redirect(url_for('auth.login'))

    members = User.query.filter_by(leader_id=leader_id).order_by(User.username).all()

    # Calculate prize pools (assuming global as per admin dashboard logic)
    # Using FUND_TYPES defined in admin_routes or directly as strings if consistent
    dynamic_prize_pool_total = db.session.query(func.sum(Fund.amount)).filter(Fund.fund_type == 'dynamic_prize_pool').scalar() or 0.0
    static_prize_pool_total = db.session.query(func.sum(Fund.amount)).filter(Fund.fund_type == 'static_prize_pool').scalar() or 0.0
    
    return render_template(
        'leader/leader_dashboard.html',
        title="Leader Dashboard",
        leader=leader,
        members=members,
        dynamic_prize_pool_total=dynamic_prize_pool_total,
        static_prize_pool_total=static_prize_pool_total
    )


# Example: Route for a leader to manage their team
@leader_bp.route("/manage-team")
@leader_required
def manage_team():
    flash("Team management page is under construction.", "info")
    # Logic for managing team members
    # return render_template('leader/manage_team.html', title="Manage Team")
    return redirect(url_for("leader.leader_dashboard"))


# Example: Route for a leader to view sales related to them
@leader_bp.route("/my-sales")
@leader_required
def my_sales():
    flash("Sales records page is under construction.", "info")
    # Logic for viewing sales records
    # return render_template('leader/my_sales.html', title="My Sales Records")
    return redirect(url_for("leader.leader_dashboard"))


@leader_bp.route('/member/add', methods=['GET', 'POST'])
@leader_required
def create_member():
    leader_id = session.get('user_id')
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('All fields (username, email, password) are required.', 'danger')
            return redirect(url_for('leader.create_member'))

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('leader.create_member'))

        new_member = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role='member',  # Automatically assign 'member' role
            status=True,  # Default to 'active'
            leader_id=leader_id  # Assign to the current leader
        )
        db.session.add(new_member)
        db.session.commit()
        flash(f'Member {username} created successfully!', 'success')
        return redirect(url_for('leader.leader_dashboard'))

    return render_template('leader/create_edit_member.html', title="Add New Member", form_action=url_for('leader.create_member'))


@leader_bp.route('/member/<int:user_id>/edit', methods=['GET', 'POST'])
@leader_required
def edit_member(user_id):
    member_to_edit = User.query.get_or_404(user_id)
    current_leader_id = session.get('user_id')

    # Ensure leader can only edit their own members and not other leaders or admins
    if member_to_edit.leader_id != current_leader_id or member_to_edit.role != 'member':
        flash('You do not have permission to edit this user or this user is not your member.', 'danger')
        return redirect(url_for('leader.leader_dashboard'))

    if request.method == 'POST':
        new_username = request.form.get('username')
        new_email = request.form.get('email')
        new_status = request.form.get('status') == "true"  # Get status, default to active

        # Check for username/email conflicts excluding the current user
        username_conflict = User.query.filter(User.username == new_username, User.id != user_id).first()
        email_conflict = User.query.filter(User.email == new_email, User.id != user_id).first()

        if username_conflict:
            flash('That username is already taken by another user.', 'danger')
        elif email_conflict:
            flash('That email address is already taken by another user.', 'danger')
        else:
            member_to_edit.username = new_username
            member_to_edit.email = new_email
            member_to_edit.status = new_status

            db.session.commit()
            flash(f'Member {member_to_edit.username} updated successfully!', 'success')
            return redirect(url_for('leader.leader_dashboard'))

    # For GET request, pre-fill the form
    return render_template('leader/create_edit_member.html',
                           title=f"Edit Member: {member_to_edit.username}",
                           user=member_to_edit,
                           form_action=url_for('leader.edit_member', user_id=user_id))


@leader_bp.route('/member/<int:user_id>/delete', methods=['POST'])  # POST only for deletion
@leader_required
def delete_member(user_id):
    member_to_delete = User.query.get_or_404(user_id)
    current_leader_id = session.get('user_id')

    if member_to_delete.leader_id != current_leader_id or member_to_delete.role != 'member':
        flash('You do not have permission to delete this user or this user is not your member.', 'danger')
        return redirect(url_for('leader.leader_dashboard'))

    # Option 2: Actual Delete (use with caution)
    db.session.delete(member_to_delete)
    flash(f'Member {member_to_delete.username} has been deleted.', 'success')

    db.session.commit()
    return redirect(url_for('leader.leader_dashboard'))
