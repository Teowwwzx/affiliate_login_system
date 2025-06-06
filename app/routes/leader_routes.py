# app/routes/leader_routes.py
from flask import Blueprint, render_template, session, flash, redirect, url_for, request
from functools import wraps
from app.database.models import User, Fund, FundHistory
from app import db
from sqlalchemy import func, extract, desc
from datetime import datetime, timedelta
from .admin_routes import FUND_TYPES
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, login_required
import json

leader_bp = Blueprint("leader", __name__, url_prefix="/leader")


# Decorator to ensure user is a leader
def leader_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))

        if current_user.role != "leader":
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("general.dashboard"))

        return f(*args, **kwargs)

    return decorated_function


@leader_bp.route("/dashboard")
@leader_required
def leader_dashboard():
    leader = User.query.get(current_user.id)

    if not leader:
        flash("Leader information not found. Please log in again.", "danger")
        return redirect(url_for("auth.login"))

    leader_referral_code = leader.personal_referral_code or "NA"
    members = User.query.filter_by(leader_id=leader.id).order_by(User.username).all()
    downline_count = len(members)

    days_since_joined = 1
    if leader.created_at:
        days_difference = (datetime.utcnow() - leader.created_at).days
        days_since_joined = max(1, days_difference)
    
    # Query fund entries with pagination
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

    
    total_result = db.session.query(
        func.coalesce(func.sum(Fund.sales), 0).label('total_sales'),
        func.coalesce(func.sum(Fund.payout), 0).label('total_payout')
    ).first()
    
    total_sales = float(total_result[0]) if total_result[0] is not None else 0.0
    total_payout = float(total_result[1]) if total_result[1] is not None else 0.0
    total_sales_and_payout = total_sales - total_payout
    total_net_profit = (total_sales_and_payout * 0.30) / 50
    
    funds_stats = {
        'total_sales': total_sales,
        'total_payout': total_payout,
        'total_sales_and_payout': total_sales_and_payout,
        'total_net_profit': total_net_profit
    }


    page = request.args.get('page', 1, type=int)
    per_page = 10

    funds_pagination = funds_query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "leader/leader_dashboard.html",
        title="Leader Dashboard",
        leader=leader,
        members=members,
        days_since_joined=days_since_joined,
        downline_count=downline_count,
        leader_referral_code=leader_referral_code,
        funds_pagination=funds_pagination,
        fund_types=FUND_TYPES,
        funds_stats=funds_stats,
    )

@leader_bp.route("/my-downlines")
@leader_required
def my_downlines():
    leader_id = current_user.id
    search_query = request.args.get("q", "").strip()

    query = User.query.filter_by(leader_id=leader_id)

    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            db.or_(User.username.ilike(search_term), User.email.ilike(search_term))
        )

    downline_members = query.order_by(User.username).all()

    return render_template(
        "leader/my_downlines.html",
        title="My Downlines",
        downline_members=downline_members,
        search_query=search_query,
    )

@leader_bp.route("/fund-history")
@leader_required
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
        title="Fund History (Leader)", # Standardized title
        fund_type_details=fund_type_details,
        monthly_summary=monthly_summary,
        available_dates=available_dates_for_template, # Use simplified list
        current_year=current_year,
        current_month=current_month,
        month_names=month_names
    )
