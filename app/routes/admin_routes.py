# app/routes/admin_routes.py
from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    flash,
    current_app,
)
from ..utils import login_required, role_required  # Assuming you have these decorators
from flask import request
from ..database import db
from ..database.models import User, Fund  # Add Fund import
from sqlalchemy import func  # Import func for sum
from werkzeug.security import (
    generate_password_hash,
)  # Add this import at the top of the file
from flask_login import current_user

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

FUND_TYPES = {
    "dynamic_prize_pool": "Dynamic Prize Pool",
    "static_prize_pool": "Static Prize Pool",
    "general": "General/Operational",
}


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    username = session.get('username', 'Admin') # Default to 'Admin' if username not in session
    total_users = User.query.count()
    active_users = User.query.filter_by(status=True).count()

    # Count users who are leaders (have members reporting to them)
    # We query for distinct user IDs that appear as a leader_id in the User table.
    # Or, more directly, count users who have associated members.
    count_leaders = User.query.filter_by(
        role="leader"
    ).count()  # CORRECTED: Count all users with 'leader' role

    # Count users who are members (report to a leader)
    count_members_under_leader = User.query.filter(User.leader_id.isnot(None)).count()

    # Calculate sum of fund amounts. If no entries, default to 0.0
    dynamic_pool_total_query = (
        db.session.query(func.sum(Fund.amount))
        .filter(Fund.fund_type == "dynamic_prize_pool")
        .scalar()
    )
    dynamic_prize_pool_total = (
        dynamic_pool_total_query if dynamic_pool_total_query is not None else 0.0
    )

    static_pool_total_query = (
        db.session.query(func.sum(Fund.amount))
        .filter(Fund.fund_type == "static_prize_pool")
        .scalar()
    )
    static_prize_pool_total = (
        static_pool_total_query if static_pool_total_query is not None else 0.0
    )

    leaders_with_member_count = []
    all_users_who_are_leaders = User.query.filter_by(role="leader").all()

    for leader_user in all_users_who_are_leaders:
        member_count = len(leader_user.members)  # Get count of members for this leader
        leaders_with_member_count.append(
            {
                "username": leader_user.username,
                "member_count": member_count,
                "id": leader_user.id,  # useful for any links if needed
            }
        )

    sorted_leaders_by_member_count = sorted(
        leaders_with_member_count, key=lambda x: x["member_count"], reverse=True
    )

    stats = {
        "total_users": total_users,
        "active_users": active_users,
        "count_leaders": count_leaders,
        "count_members_under_leader": count_members_under_leader,
        "dynamic_prize_pool_total": dynamic_prize_pool_total,
        "static_prize_pool_total": static_prize_pool_total,
        "leaders_for_sales_calc": sorted_leaders_by_member_count[:5],  # Limit to top 5
        "total_leader_count_for_view_all": len(
            sorted_leaders_by_member_count
        ),  # For 'View All' link logic
        "current_value_price": 5000,
    }
    return render_template(
        "admin/admin_dashboard.html", title="Admin Dashboard", stats=stats
    )


@admin_bp.route("/users")
@login_required
@role_required("admin")
def list_users():
    page = request.args.get("page", 1, type=int)
    per_page = 10  # Or get from config

    # Get filter parameters from request arguments
    filter_role = request.args.get("role", None)
    filter_status_str = request.args.get("status", None)
    filter_leader_id = request.args.get("leader_id_filter", None)  # New filter

    # Build the base query
    query = User.query

    # Apply filters if they are provided
    if (
        filter_role
    ):  # An empty string for role (from 'All Roles') will evaluate to False here, which is correct.
        query = query.filter(User.role == filter_role)

    # Correctly handle status filter: only filter if 'true' or 'false' is explicitly passed.
    if filter_status_str and filter_status_str in ("true", "false"):
        filter_status = filter_status_str.lower() == "true"
        query = query.filter(User.status == filter_status)

    if (
        filter_leader_id
    ):  # An empty string for leader_id_filter (from 'All Leaders / Unassigned') will evaluate to False here.
        if filter_leader_id == "0":  # Check for 'Unassigned Members' filter
            query = query.filter(User.leader_id.is_(None))
        else:
            try:
                leader_id_int = int(filter_leader_id)
                query = query.filter(User.leader_id == leader_id_int)
            except ValueError:
                flash(
                    "Invalid Leader ID provided for filtering.", "warning"
                )  # Or log, or ignore

    users_pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Fetch all leaders for the filter dropdown
    all_leaders = (
        User.query.filter_by(role="leader", status=True).order_by(User.username).all()
    )

    return render_template(
        "admin/list_users.html",
        users_pagination=users_pagination,
        title="Manage Users",
        current_filters={
            "role": filter_role,
            "status": filter_status_str,
            "leader_id": filter_leader_id,
        },  # Pass current filters
        all_leaders=all_leaders,  # Pass leaders for dropdown
    )


@admin_bp.route("/users/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def create_user():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")
        status = request.form.get("status") == "true"  # Checkbox value
        leader_id_str = request.form.get("leader_id")

        # Basic validation
        if not username or not email or not password or not role:
            flash("Username, email, password, and role are required.", "danger")
            # Repopulate form with leaders for selection if validation fails
            leaders = User.query.filter_by(role="leader").all()
            return render_template(
                "admin/create_edit_user.html",
                title="Create User",
                leaders=leaders,
                user_data=request.form,
            )

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            leaders = User.query.filter_by(role="leader").all()
            return render_template(
                "admin/create_edit_user.html",
                title="Create User",
                leaders=leaders,
                user_data=request.form,
            )

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            leaders = User.query.filter_by(role="leader").all()
            return render_template(
                "admin/create_edit_user.html",
                title="Create User",
                leaders=leaders,
                user_data=request.form,
            )

        leader_id = None
        if role == "member" and leader_id_str:
            leader_id = int(leader_id_str) if leader_id_str.isdigit() else None
            if leader_id and not User.query.get(leader_id):
                flash("Selected leader is invalid.", "danger")
                leaders = User.query.filter_by(role="leader").all()
                return render_template(
                    "admin/create_edit_user.html",
                    title="Create User",
                    leaders=leaders,
                    user_data=request.form,
                )
        elif role == "member" and not leader_id_str:  # Member must have a leader
            flash("A leader must be selected for a member.", "danger")
            leaders = User.query.filter_by(role="leader").all()
            return render_template(
                "admin/create_edit_user.html",
                title="Create User",
                leaders=leaders,
                user_data=request.form,
            )

        new_user = User(
            username=username,
            email=email,
            role=role,
            status=status,
            leader_id=(
                leader_id if role == "member" else None
            ),  # Only set leader_id if role is member
        )
        new_user.set_password(password)  # Hashes the password

        try:
            db.session.add(new_user)
            db.session.commit()
            flash(f"User '{username}' created successfully!", "success")
            return redirect(url_for("admin.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating user: {str(e)}", "danger")
            # Log the exception e for debugging

    # GET request: Show the form
    leaders = User.query.filter_by(role="leader").all()  # For leader selection dropdown
    return render_template(
        "admin/create_edit_user.html", title="Create User", leaders=leaders
    )


@admin_bp.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.role == "admin":
        flash(
            "Admin users cannot be edited",
            "warning",
        )
        return redirect(url_for("admin.list_users"))

    leaders = User.query.filter(
        User.role == "leader", User.id != user_id
    ).all()  # Exclude self if user is a leader

    if request.method == "POST":
        original_username = user.username
        original_email = user.email

        user.username = request.form.get("username")
        user.email = request.form.get("email")
        new_password = request.form.get("password")
        user.role = request.form.get("role")
        user.status = request.form.get("status") == "true"
        leader_id_str = request.form.get("leader_id")

        if not user.username or not user.email or not user.role:
            flash("Username, email, and role are required.", "danger")
            return render_template(
                "admin/create_edit_user.html",
                title="Edit User",
                user=user,
                leaders=leaders,
                action_url=url_for("admin.edit_user", user_id=user_id),
            )

        # Check for username uniqueness (if changed)
        if (
            user.username != original_username
            and User.query.filter_by(username=user.username).first()
        ):
            flash("Username already exists.", "danger")
            user.username = original_username  # Revert to original
            return render_template(
                "admin/create_edit_user.html",
                title="Edit User",
                user=user,
                leaders=leaders,
                action_url=url_for("admin.edit_user", user_id=user_id),
            )

        # Check for email uniqueness (if changed)
        if (
            user.email != original_email
            and User.query.filter_by(email=user.email).first()
        ):
            flash("Email already registered.", "danger")
            user.email = original_email  # Revert to original
            return render_template(
                "admin/create_edit_user.html",
                title="Edit User",
                user=user,
                leaders=leaders,
                action_url=url_for("admin.edit_user", user_id=user_id),
            )

        if new_password:
            user.set_password(new_password)

        if user.role == "member" and leader_id_str:
            user.leader_id = int(leader_id_str) if leader_id_str.isdigit() else None
            if user.leader_id and not User.query.get(user.leader_id):
                flash("Selected leader is invalid.", "danger")
                return render_template(
                    "admin/create_edit_user.html",
                    title="Edit User",
                    user=user,
                    leaders=leaders,
                    action_url=url_for("admin.edit_user", user_id=user_id),
                )
        elif user.role == "member" and not leader_id_str:
            flash("A leader must be selected for a member.", "danger")
            return render_template(
                "admin/create_edit_user.html",
                title="Edit User",
                user=user,
                leaders=leaders,
                action_url=url_for("admin.edit_user", user_id=user_id),
            )
        elif user.role != "member":
            user.leader_id = None  # Ensure non-members don't have a leader_id

        try:
            db.session.commit()
            flash(f"User '{user.username}' updated successfully!", "success")
            return redirect(url_for("admin.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating user: {str(e)}", "danger")
            # Log the exception e

    # GET request: Show the form with user's current data
    return render_template(
        "admin/create_edit_user.html",
        title="Edit User",
        user=user,
        leaders=leaders,
        action_url=url_for("admin.edit_user", user_id=user_id),
    )


@admin_bp.route(
    "/users/delete/<int:user_id>", methods=["GET"]
)  # Usually POST/DELETE for actual deletion
@login_required
@role_required("admin")
def delete_user(user_id):
    # For now, just a placeholder to avoid BuildError.
    # Actual deletion logic will be added here.
    user_to_delete = User.query.get_or_404(user_id)

    if user_to_delete.id == session.get("user_id"):
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin.list_users"))

    # Prevent deleting any user with admin role
    if user_to_delete.role == "admin":
        flash("Admin users cannot be deleted for security reasons.", "danger")
        return redirect(url_for("admin.list_users"))

    # TEMPORARY: Redirect back with a message.
    # flash(
    #     f"Deletion for user '{user_to_delete.username}' is not yet implemented. Clicked delete for user ID: {user_id}",
    #     "warning",
    # )
    # return redirect(url_for("admin.list_users"))

    try:
        # Add logic here if users have dependent data (e.g., reassign sales, team members)
        # For example, if members are linked to this leader, you might want to nullify their leader_id
        if user_to_delete.role == "leader":
            members_of_leader = User.query.filter_by(leader_id=user_to_delete.id).all()
            for member in members_of_leader:
                member.leader_id = None
            flash(
                f"Members previously under '{user_to_delete.username}' are now unassigned.",
                "info",
            )

        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f"User '{user_to_delete.username}' deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting user: {str(e)}", "danger")
    # Log error e

    return redirect(url_for("admin.list_users"))


@admin_bp.route("/funds")
@login_required
@role_required("admin")
def manage_funds():  # Renaming to list_funds behaviorally, keeping route name for now
    # Fetch all funds and join with User to get creator's username
    # Order by created_at descending to show latest first
    funds_with_creators = (
        db.session.query(Fund, User.username.label("creator_username"))
        .join(User, Fund.created_by == User.id)
        .order_by(Fund.created_at.desc())
        .all()
    )

    return render_template(
        "admin/list_funds.html",
        funds_data=funds_with_creators,
        title="Manage Fund Entries",
        fund_types=FUND_TYPES,
    )


@admin_bp.route("/sales")
@login_required
@role_required("admin")
def list_sales():
    flash("Sales management page is under construction.", "info")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/funds/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def create_fund():
    if request.method == "POST":
        try:
            amount_str = request.form.get("amount")
            remarks = request.form.get("remarks")
            fund_type = request.form.get("fund_type")

            if not amount_str:
                flash("Amount is required.", "danger")
                return render_template(
                    "admin/create_edit_fund.html",
                    title="Create Fund Entry",
                    fund_data=request.form,
                    action_url=url_for("admin.create_fund"),
                    fund_types=FUND_TYPES,
                )

            if not fund_type or fund_type not in FUND_TYPES:
                flash("Valid Fund Type is required.", "danger")
                return render_template(
                    "admin/create_edit_fund.html",
                    title="Create Fund Entry",
                    fund_data=request.form,
                    action_url=url_for("admin.create_fund"),
                    fund_types=FUND_TYPES,
                )

            try:
                amount = float(amount_str)
                if amount <= 0:
                    raise ValueError("Amount must be positive.")
            except ValueError as e:
                flash(f"Invalid amount: {e}", "danger")
                return render_template(
                    "admin/create_edit_fund.html",
                    title="Create Fund Entry",
                    fund_data=request.form,
                    action_url=url_for("admin.create_fund"),
                    fund_types=FUND_TYPES,
                )

            new_fund_entry = Fund(
                amount=amount,
                remarks=remarks,
                fund_type=fund_type,
                created_by=current_user.id,  # Use current_user.id instead of session['user_id']
            )
            db.session.add(new_fund_entry)
            db.session.commit()
            flash("Fund entry created successfully!", "success")
            return redirect(url_for("admin.manage_funds"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating fund entry: {str(e)}", "danger")
            current_app.logger.error(f"Error creating fund entry: {e}", exc_info=True)
            return render_template(
                "admin/create_edit_fund.html",
                title="Create Fund Entry",
                fund_data=request.form,
                action_url=url_for("admin.create_fund"),
                fund_types=FUND_TYPES,
            )

    return render_template(
        "admin/create_edit_fund.html",
        title="Create Fund Entry",
        action_url=url_for("admin.create_fund"),
        fund_types=FUND_TYPES,
    )


@admin_bp.route("/funds/edit/<int:fund_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_fund(fund_id):
    fund = Fund.query.get_or_404(fund_id)

    if request.method == "POST":
        try:
            amount_str = request.form.get("amount")
            remarks = request.form.get("remarks")
            fund_type = request.form.get("fund_type")

            if not amount_str:
                flash("Amount is required.", "danger")
                return render_template(
                    "admin/create_edit_fund.html",
                    title="Edit Fund Entry",
                    fund_data=request.form,
                    fund=fund,
                    action_url=url_for("admin.edit_fund", fund_id=fund_id),
                    fund_types=FUND_TYPES,
                )

            if not fund_type or fund_type not in FUND_TYPES:
                flash("Valid Fund Type is required.", "danger")
                return render_template(
                    "admin/create_edit_fund.html",
                    title="Edit Fund Entry",
                    fund_data=request.form,
                    fund=fund,
                    action_url=url_for("admin.edit_fund", fund_id=fund_id),
                    fund_types=FUND_TYPES,
                )

            try:
                amount = float(amount_str)
                if amount <= 0:
                    raise ValueError("Amount must be positive.")
            except ValueError as e:
                flash(f"Invalid amount: {e}", "danger")
                return render_template(
                    "admin/create_edit_fund.html",
                    title="Edit Fund Entry",
                    fund_data=request.form,
                    fund=fund,
                    action_url=url_for("admin.edit_fund", fund_id=fund_id),
                    fund_types=FUND_TYPES,
                )

            fund.amount = amount
            fund.remarks = remarks
            fund.fund_type = fund_type

            db.session.commit()
            flash("Fund entry updated successfully!", "success")
            return redirect(url_for("admin.manage_funds"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating fund entry: {str(e)}", "danger")
            current_app.logger.error(f"Error updating fund entry: {e}", exc_info=True)
            return render_template(
                "admin/create_edit_fund.html",
                title="Edit Fund Entry",
                fund_data=request.form,
                fund=fund,
                action_url=url_for("admin.edit_fund", fund_id=fund_id),
                fund_types=FUND_TYPES,
            )

    return render_template(
        "admin/create_edit_fund.html",
        title="Edit Fund Entry",
        fund=fund,
        action_url=url_for("admin.edit_fund", fund_id=fund_id),
        fund_types=FUND_TYPES,
    )


@admin_bp.route(
    "/funds/delete/<int:fund_id>", methods=["GET", "POST"]
)  # POST for safety, or ensure CSRF if GET
@login_required
@role_required("admin")
def delete_fund(fund_id):
    fund_to_delete = Fund.query.get_or_404(fund_id)
    try:
        db.session.delete(fund_to_delete)
        db.session.commit()
        flash(f"Fund entry ID {fund_to_delete.id} deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting fund entry: {str(e)}", "danger")
        current_app.logger.error(
            f"Error deleting fund entry ID {fund_id}: {e}", exc_info=True
        )
    return redirect(url_for("admin.manage_funds"))


@admin_bp.route("/leaders_list_full")
@login_required
@role_required("admin")
def list_all_leaders():
    leaders_with_member_count = []
    all_users_who_are_leaders = (
        User.query.filter_by(role="leader").order_by(User.username).all()
    )

    for leader_user in all_users_who_are_leaders:
        member_count = User.query.filter_by(
            leader_id=leader_user.id
        ).count()  # More direct count
        leaders_with_member_count.append(
            {
                "username": leader_user.username,
                "email": leader_user.email,
                "member_count": member_count,
                "id": leader_user.id,
                "status": leader_user.status,
                "created_at": leader_user.created_at,
            }
        )

    # Optionally, sort this list as well if needed, e.g., by member count or username
    sorted_full_leaders_list = sorted(
        leaders_with_member_count, key=lambda x: x["member_count"], reverse=True
    )

    return render_template(
        "admin/list_all_leaders.html",
        title="Full Leaderboard",
        leaders_list=sorted_full_leaders_list,
    )
