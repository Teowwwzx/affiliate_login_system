# app/routes/investor_routes.py
from flask import Blueprint, render_template, session, flash, redirect, url_for, request
from functools import wraps
from app.database.models import User, Fund, FundHistory
from app import db
from sqlalchemy import func, extract, desc
from datetime import datetime
from .admin_routes import FUND_TYPES # Assuming FUND_TYPES is still relevant or can be adapted
from werkzeug.security import generate_password_hash, check_password_hash # Not used directly in routes, but good to keep if models use it
from flask_login import current_user, login_required
from app.utils.decorators import investor_required # Import central decorator
import json

investor_bp = Blueprint("investor", __name__, url_prefix="/investor")


@investor_bp.route("/dashboard")
@login_required # Add login_required for consistency
@investor_required
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
    # Corrected net profit calculation
    total_net_profit = (total_sales + total_payout) * 0.15 / 0.5 
    
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


@investor_bp.route("/fund-history")
@investor_required
def fund_history():
    page = request.args.get("page", 1, type=int)
    per_page = 10

    selected_year = request.args.get('year', type=int)
    selected_month = request.args.get('month', type=int)

    # Get available year/month pairs for the filter dropdown
    available_dates_query = db.session.query(
        extract('year', FundHistory.snapshot_date).label('year'),
        extract('month', FundHistory.snapshot_date).label('month')
    ).distinct().order_by(
        desc(extract('year', FundHistory.snapshot_date)),
        desc(extract('month', FundHistory.snapshot_date))
    )
    available_raw_dates = available_dates_query.all()

    # Simplify available_dates to be a list of dicts: [{'year': YYYY, 'month': MM}, ...]
    available_dates_for_template = []
    if available_raw_dates:
        for yr, mn in available_raw_dates:
            if yr is not None and mn is not None:
                available_dates_for_template.append({'year': int(yr), 'month': int(mn)})

    current_year = selected_year
    current_month = selected_month

    if not available_dates_for_template:
        now = datetime.utcnow()
        current_year = current_year or now.year
        current_month = current_month or now.month
        if not any(d['year'] == current_year and d['month'] == current_month for d in available_dates_for_template):
            available_dates_for_template.insert(0, {'year': current_year, 'month': current_month})
    else:
        if current_year is None or current_month is None:
            current_year = available_dates_for_template[0]['year']
            current_month = available_dates_for_template[0]['month']
        elif not any(d['year'] == current_year and d['month'] == current_month for d in available_dates_for_template):
            available_dates_for_template.append({'year': current_year, 'month': current_month})
            available_dates_for_template.sort(key=lambda x: (x['year'], x['month']), reverse=True)

    # Query for fund type details for the selected/defaulted month
    fund_type_details_query = FundHistory.query.filter(
        extract('year', FundHistory.snapshot_date) == current_year,
        extract('month', FundHistory.snapshot_date) == current_month,
        FundHistory.fund_type != 'MONTHLY_SALES'
    ).order_by(FundHistory.fund_type)
    
    fund_type_details = fund_type_details_query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Query for the overall monthly summary for the selected/defaulted month
    monthly_summary = FundHistory.query.filter(
        extract('year', FundHistory.snapshot_date) == current_year,
        extract('month', FundHistory.snapshot_date) == current_month,
        FundHistory.fund_type == 'MONTHLY_SALES'
    ).first()

    month_names = {m: datetime(2000, m, 1).strftime('%B') for m in range(1, 13)}
    
    return render_template(
        "shared/fund_history.html",
        title="Fund History (Investor)", # Standardized title
        fund_type_details=fund_type_details,
        monthly_summary=monthly_summary,
        available_dates=available_dates_for_template, # Use simplified list
        current_year=current_year,
        current_month=current_month,
        month_names=month_names
    )


# @investor_bp.route("/my-downlines") # Path kept for duplication, might need semantic review
# @investor_required # Changed
# def my_downlines(): # Function name kept for duplication
#     investor_id = current_user.id # Renamed variable for clarity
#     search_query = request.args.get("q", "").strip()

#     # Assuming investors can also have "downlines" or referred users
#     query = User.query.filter_by(leader_id=investor_id) 

#     if search_query:
#         search_term = f"%{search_query}%"
#         query = query.filter(
#             db.or_(User.username.ilike(search_term), User.email.ilike(search_term))
#         )

#     downline_members = query.order_by(User.username).all()

#     return render_template(
#         "investor/my_downlines.html", # Changed template path
#         title="My Referrals", # Changed title (example, can be "My Downlines" if preferred)
#         downline_members=downline_members,
#         search_query=search_query,
#     )
