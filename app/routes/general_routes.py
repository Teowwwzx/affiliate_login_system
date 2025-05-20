from ..database import db
from datetime import datetime
from ..database.models import User, Fund
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from sqlalchemy import func

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

@general_bp.route('/futuristic-dashboard')
# @login_required
def futuristic_dashboard():
    return render_template('test/futuristic_dashboard.html')

@general_bp.route('/test/new_admin_dashboard')
@login_required
def new_admin_dashboard_test():
    # --- Replicating data fetching from admin_routes.admin_dashboard --- 
    total_users = User.query.count()
    active_users = User.query.filter_by(status=True).count()
    count_leaders = User.query.filter_by(role="leader").count()
    count_members_under_leader = User.query.filter(User.leader_id.isnot(None)).count()

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

    general_operational_total_query = (
        db.session.query(func.sum(Fund.amount))
        .filter(Fund.fund_type == "general")
        .scalar()
    )
    general_operational_total = (
        general_operational_total_query if general_operational_total_query is not None else 0.0
    )

    leaders_with_member_count = []
    all_users_who_are_leaders = User.query.filter_by(role="leader").all()

    for leader_user in all_users_who_are_leaders:
        member_count = len(leader_user.members)
        leaders_with_member_count.append(
            {
                "username": leader_user.username,
                "member_count": member_count,
                "id": leader_user.id,
            }
        )

    sorted_leaders_by_member_count = sorted(
        leaders_with_member_count, key=lambda x: x["member_count"], reverse=True
    )

    all_referral_codes_users = User.query.filter(User.personal_referral_code.isnot(None)).order_by(User.created_at.desc()).all()

    stats = {
        "total_users": total_users,
        "active_users": active_users,
        "count_leaders": count_leaders,
        "count_members_under_leader": count_members_under_leader,
        "dynamic_prize_pool_total": dynamic_prize_pool_total,
        "static_prize_pool_total": static_prize_pool_total,
        "general_operational_total": general_operational_total,
        "leaders_for_sales_calc": sorted_leaders_by_member_count[:5], 
        "total_leader_count_for_view_all": len(sorted_leaders_by_member_count),
        "current_value_price": 5000, # Assuming this is a fixed value for now, as in admin_dashboard
    }
    
    return render_template(
        'test/new_admin_dashboard.html', 
        stats=stats, 
        referral_codes_users=all_referral_codes_users,
        title="New Admin Dashboard (Test)"
    )

@general_bp.context_processor
def inject_current_year():
    return dict(current_year=datetime.utcnow().year)
