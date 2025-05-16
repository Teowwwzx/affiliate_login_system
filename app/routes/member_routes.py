# app/routes/member_routes.py
from flask import Blueprint, render_template, session, flash, redirect, url_for, request
from functools import wraps
from app.database.models import User
from app import db
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import current_user, login_required

member_bp = Blueprint("member", __name__, url_prefix="/member")


# Decorator to ensure user is a member
def member_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))

        if current_user.role != "member":
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("general.dashboard"))

        return f(*args, **kwargs)

    return decorated_function


@member_bp.route("/dashboard")
@member_required
@login_required
def member_dashboard():
    member = current_user

    leader = None
    if member.leader_id:
        leader = User.query.get(member.leader_id)

    return render_template(
        "member/member_dashboard.html",
        title="Member Dashboard",
        member=member,
        leader=leader,
    )


@member_bp.route("/change-password", methods=["GET", "POST"])
@member_required
@login_required
def change_password():
    # Redirect to the central change_password route in auth_routes.py
    # This maintains backward compatibility for any existing links
    return redirect(url_for("auth.change_password"))


# Add other member-specific routes if any, e.g., viewing personal sales, profile details
