# app/routes/member_routes.py
from flask import Blueprint, render_template, session, flash, redirect, url_for, request
from functools import wraps
from app.database.models import User, Fund, FundHistory
from app import db
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import current_user, login_required
from datetime import datetime, timedelta
from sqlalchemy import func, extract, desc
from .admin_routes import FUND_TYPES

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
def member_dashboard():
    member = User.query.get(current_user.id)

    if not member:
        flash("Member not found. Please log in again.", "danger")
        return redirect(url_for("auth.login"))

    leader = None
    if member.leader_id:
        leader = User.query.get(member.leader_id)

    days_since_joined = 1
    if member.created_at:
        days_difference = (datetime.utcnow() - member.created_at).days
        days_since_joined = max(1, days_difference)
    referral_code = member.personal_referral_code or 'NA'

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
    total_net_profit = (total_sales_and_payout * 0.30) / 0.5

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
        "member/member_dashboard.html",
        title="Member Dashboard",
        member=member,
        leader=leader,
        days_since_joined=days_since_joined,
        referral_code=referral_code,
        funds_pagination=funds_pagination,
        fund_types=FUND_TYPES,
        funds_stats=funds_stats,
    )

@member_bp.route("/fund-history")
@member_required
def fund_history():
    page = request.args.get("page", 1, type=int)
    per_page = 10

    selected_year = request.args.get('year', type=int)
    selected_month = request.args.get('month', type=int)

    # Get available year/month pairs for the filter dropdown
    # For members, we might want to restrict this to only their relevant history if applicable
    # For now, it shows all available history dates like admin/leader
    available_dates_query = db.session.query(
        extract('year', FundHistory.snapshot_date).label('year'),
        extract('month', FundHistory.snapshot_date).label('month')
    ).distinct().order_by(
        desc(extract('year', FundHistory.snapshot_date)),
        desc(extract('month', FundHistory.snapshot_date))
    )
    available_raw_dates = available_dates_query.all()

    available_dates_for_filter = []
    if available_raw_dates:
        for yr, mn in available_raw_dates:
            if yr is not None and mn is not None:
                available_dates_for_filter.append({
                    'year': int(yr),
                    'month': int(mn),
                    'month_name': datetime(int(yr), int(mn), 1).strftime('%B')
                })

    current_year_for_query = selected_year
    current_month_for_query = selected_month

    if not available_dates_for_filter:
        now = datetime.utcnow()
        current_year_for_query = current_year_for_query or now.year
        current_month_for_query = current_month_for_query or now.month
        if not any(d['year'] == current_year_for_query and d['month'] == current_month_for_query for d in available_dates_for_filter):
            available_dates_for_filter.insert(0, {
                'year': current_year_for_query,
                'month': current_month_for_query,
                'month_name': datetime(current_year_for_query, current_month_for_query, 1).strftime('%B')
            })
    else:
        if current_year_for_query is None or current_month_for_query is None:
            current_year_for_query = available_dates_for_filter[0]['year']
            current_month_for_query = available_dates_for_filter[0]['month']

    # Query for fund type details for the selected/defaulted month
    # Note: Currently, FundHistory is global. If member-specific history is needed,
    # this query would need to be filtered by current_user.id or similar.
    fund_type_details_query = FundHistory.query.filter(
        extract('year', FundHistory.snapshot_date) == current_year_for_query,
        extract('month', FundHistory.snapshot_date) == current_month_for_query,
        FundHistory.fund_type != 'MONTHLY_SALES'
    ).order_by(FundHistory.fund_type)
    
    fund_type_details = fund_type_details_query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Query for the overall monthly summary for the selected/defaulted month
    monthly_summary = FundHistory.query.filter(
        extract('year', FundHistory.snapshot_date) == current_year_for_query,
        extract('month', FundHistory.snapshot_date) == current_month_for_query,
        FundHistory.fund_type == 'MONTHLY_SALES'
    ).first()

    month_names = {m: datetime(2000, m, 1).strftime('%B') for m in range(1, 13)}
    
    title = f"Fund History - {month_names.get(current_month_for_query, '')} {current_year_for_query}"
    if not selected_year and not selected_month and not available_raw_dates:
        title = "Fund History - No Data Available"
    elif not selected_year and not selected_month and available_raw_dates:
        pass # Title is already set correctly for this case (defaults to most recent)

    return render_template(
        "shared/fund_history.html",
        title=title,
        fund_type_details=fund_type_details,
        monthly_summary=monthly_summary,
        available_dates=available_dates_for_filter,
        current_year=current_year_for_query, 
        current_month=current_month_for_query, 
        month_names=month_names
    )