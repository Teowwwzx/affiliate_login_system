# app/routes/member_routes.py
from flask import Blueprint, render_template, session, flash, redirect, url_for, request
from functools import wraps
from app.database.models import User
from app import db
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import current_user, login_required
from datetime import datetime

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
    # Query the member by ID to ensure we have the latest data
    member = User.query.get(current_user.id)
    if not member:
        flash("Member not found. Please log in again.", "danger")
        return redirect(url_for("auth.login"))

    leader = None
    if member.leader_id:
        leader = User.query.get(member.leader_id)

    # Calculate days since joined (minimum 1 day)
    days_since_joined = 1
    if member.created_at:
        days_difference = (datetime.utcnow() - member.created_at).days
        days_since_joined = max(1, days_difference)

    # Get referral code or 'NA' if not available
    referral_code = member.personal_referral_code or 'NA'

    return render_template(
        "member/member_dashboard.html",
        title="Member Dashboard",
        member=member,
        leader=leader,
        days_since_joined=days_since_joined,
        referral_code=referral_code,
    )


@member_bp.route("/change-password", methods=["GET", "POST"])
@member_required
@login_required
def change_password():
    # Redirect to the central change_password route in auth_routes.py
    # This maintains backward compatibility for any existing links
    return redirect(url_for("auth.change_password"))


# Add other member-specific routes if any, e.g., viewing personal sales, profile details
