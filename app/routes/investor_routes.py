# app/routes/investor_routes.py
from flask import Blueprint, render_template, session, flash, redirect, url_for, request
from functools import wraps
from app.database.models import User, Fund
from app import db
from sqlalchemy import func
from datetime import datetime
from .admin_routes import FUND_TYPES # Assuming FUND_TYPES is still relevant or can be adapted
from werkzeug.security import generate_password_hash, check_password_hash # Not used directly in routes, but good to keep if models use it
from flask_login import current_user, login_required
import json

investor_bp = Blueprint("investor", __name__, url_prefix="/investor")


# Decorator to ensure user is an investor
def investor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))

        if current_user.role != "investor": # Changed from "leader"
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("general.dashboard")) # Or a more appropriate redirect

        return f(*args, **kwargs)

    return decorated_function


@investor_bp.route("/dashboard")
@investor_required # Changed from leader_required
def investor_dashboard(): # Renamed function
    investor_user = User.query.get(current_user.id) # Renamed variable

    if not investor_user:
        flash("Investor information not found. Please log in again.", "danger")
        return redirect(url_for("auth.login"))

    investor_referral_code = investor_user.personal_referral_code or "NA" # Renamed variable
    
    # For an exact duplicate, investors would also see "members" they referred or similar.
    # This might need semantic adjustment later if "downlines" don't apply to investors.
    members = User.query.filter_by(leader_id=investor_user.id).order_by(User.username).all() # Assuming investors can also refer
    downline_count = len(members)

    days_since_joined = 1
    if investor_user.created_at:
        days_difference = (datetime.utcnow() - investor_user.created_at).days
        days_since_joined = max(1, days_difference)

    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Query fund entries with pagination - assuming investors see the same fund view
    funds_query = Fund.query.join(
        User, Fund.created_by == User.id
    ).add_columns(
        Fund.id,
        Fund.sales,
        Fund.payout,
        Fund.net_profit,
        Fund.fund_type,
        Fund.remarks,
        Fund.created_at,
        User.username.label('creator_username')
    ).order_by(Fund.created_at.desc())

    funds_pagination = funds_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Calculate totals for all funds - assuming investors see the same stats
    total_result = db.session.query(
        func.coalesce(func.sum(Fund.sales), 0).label('total_sales'),
        func.coalesce(func.sum(Fund.payout), 0).label('total_payout')
    ).first()
    
    total_sales = float(total_result[0]) if total_result[0] is not None else 0.0
    total_payout = float(total_result[1]) if total_result[1] is not None else 0.0
    total_sales_and_payout = total_sales + total_payout
    # Assuming the net profit calculation is consistent for this duplicated view
    total_net_profit = (total_sales_and_payout * 0.30) / 50 
    
    funds_stats = {
        'total_sales': total_sales,
        'total_payout': total_payout,
        'total_sales_and_payout': total_sales_and_payout,
        'total_net_profit': total_net_profit
    }

    return render_template(
        "investor/investor_dashboard.html", # Changed template path
        title="Investor Dashboard", # Changed title
        investor=investor_user, # Renamed context variable
        members=members, # Kept for duplication, might need review
        days_since_joined=days_since_joined,
        downline_count=downline_count, # Kept for duplication
        investor_referral_code=investor_referral_code, # Renamed
        funds_pagination=funds_pagination,
        fund_types=FUND_TYPES,
        funds_stats=funds_stats,
    )

@investor_bp.route("/my-downlines") # Path kept for duplication, might need semantic review
@investor_required # Changed
def my_downlines(): # Function name kept for duplication
    investor_id = current_user.id # Renamed variable for clarity
    search_query = request.args.get("q", "").strip()

    # Assuming investors can also have "downlines" or referred users
    query = User.query.filter_by(leader_id=investor_id) 

    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            db.or_(User.username.ilike(search_term), User.email.ilike(search_term))
        )

    downline_members = query.order_by(User.username).all()

    return render_template(
        "investor/my_downlines.html", # Changed template path
        title="My Referrals", # Changed title (example, can be "My Downlines" if preferred)
        downline_members=downline_members,
        search_query=search_query,
    )
