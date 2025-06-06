from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    flash,
    current_app,
)
from flask_login import login_required, current_user
from ..database import db
from ..database.models import User, Fund, Sale, FundHistory
from ..utils import role_required
from werkzeug.security import (
    generate_password_hash,
)
from flask import request
from sqlalchemy import func, extract, desc
from datetime import datetime
import json

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

FUND_TYPES = {
    "insurance_bucket_sale": "Insurance Bucket Sale",
    "robot_ai_bucket_sale": "Robot Ai Bucket Sale",
}


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    total_users = User.query.count()
    active_users = User.query.filter_by(status=True).count()
    count_leaders = User.query.filter_by(role="leader").count()
    count_members_under_leader = User.query.filter(User.leader_id.isnot(None)).count()
    total_referral_codes_generated = User.query.filter(
        User.personal_referral_code.isnot(None)
    ).count()
    users_joined_via_referral = User.query.filter(
        User.signup_referral_code_used.isnot(None)
    ).count()

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

    all_referral_codes_users = (
        User.query.filter(User.personal_referral_code.isnot(None))
        .order_by(User.created_at.desc())
        .all()
    )

    funds_data = (
        db.session.query(
            Fund.fund_type,
            func.coalesce(func.sum(Fund.sales), 0).label("total_sales"),
            func.coalesce(func.sum(Fund.payout), 0).label("total_payout"),
            (func.coalesce(func.sum(Fund.sales), 0) - func.coalesce(func.sum(Fund.payout), 0)).label("total_net_profit")
        )
        .group_by(Fund.fund_type)
        .all()
    )

    funds_summary = {
        fund_type: {
            "sales": 0.0,
            "payout": 0.0,
            "net_profit": 0.0,
            "display_name": display_name,
        }
        for fund_type, display_name in FUND_TYPES.items()
    }

    for fund_type, sales, payout, net_profit in funds_data:
        if fund_type in funds_summary:
            funds_summary[fund_type].update(
                {
                    "sales": float(sales or 0),
                    "payout": float(payout or 0),
                    "net_profit": float(net_profit or 0),
                }
            )

    stats = {
        # User Stats
        "total_users": total_users,
        "active_users": active_users,
        "count_leaders": count_leaders,
        "count_members_under_leader": count_members_under_leader,

        # Fund Stats
        "funds_summary": funds_summary,
        "total_sales": sum(f["sales"] for f in funds_summary.values()),
        "total_payout": sum(f["payout"] for f in funds_summary.values()),
        "total_sales_and_payout": sum(f["sales"] + f["payout"] for f in funds_summary.values()),
        "total_net_profit": (sum(f["sales"] - f["payout"] for f in funds_summary.values()) * 0.30) / 50,

        # Leader Stats
        "leaders_for_sales_calc": sorted_leaders_by_member_count[:5],
        "total_leader_count_for_view_all": len(sorted_leaders_by_member_count),
        "current_value_price": 5000,

        # Referral Stats
        "total_referral_codes_generated": total_referral_codes_generated,
        "users_joined_via_referral": users_joined_via_referral,
    }
    return render_template(
        "admin/new_admin_dashboard.html",
        title="Admin Dashboard",
        stats=stats,
        fund_types=FUND_TYPES,
        referral_codes_users=all_referral_codes_users,
    )


@admin_bp.route("/users")
@login_required
@role_required("admin")
def list_users():
    page = request.args.get("page", 1, type=int)
    per_page = 10

    filter_role = request.args.get("role", None)
    filter_status_str = request.args.get("status", None)
    filter_leader_id = request.args.get("leader_id_filter", None)

    query = User.query

    if filter_role:
        query = query.filter(User.role == filter_role)

    if filter_status_str and filter_status_str in ("true", "false"):
        filter_status = filter_status_str.lower() == "true"
        query = query.filter(User.status == filter_status)

    if filter_leader_id:
        if filter_leader_id == "0":
            query = query.filter(User.leader_id.is_(None))
        else:
            try:
                leader_id_int = int(filter_leader_id)
                query = query.filter(User.leader_id == leader_id_int)
            except ValueError:
                flash("Invalid Leader ID provided for filtering.", "warning")

    users_pagination = query.options(
        db.load_only(
            User.id,
            User.username,
            User.email,
            User.role,
            User.status,
            User.created_at,
            User.personal_referral_code,
            User.leader_id  # Needed for the leader relationship
        )
    ).order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

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
        },
        all_leaders=all_leaders,
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
        status = request.form.get("status") == "true"
        leader_id_str = request.form.get("leader_id")

        if not username or not email or not password or not role:
            flash("Username, email, password, and role are required.", "danger")
            leaders = User.query.filter_by(role="leader").all()
            return render_template(
                "admin/create_edit_user.html",
                title="Create User",
                leaders=leaders,
                user_data=request.form,
            )
            
        if len(password) < 4:
            flash("Password must be at least 4 characters long.", "danger")
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
        elif role == "member" and not leader_id_str:
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
            leader_id=(leader_id if role == "member" else None),
        )
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash(f"User '{username}' created successfully!", "success")
            return redirect(url_for("admin.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating user: {str(e)}", "danger")
            leaders = User.query.filter_by(role="leader").all()
            return render_template(
                "admin/create_edit_user.html",
                title="Create User",
                leaders=leaders,
                user_data=request.form,
            )

    leaders = User.query.filter_by(role="leader").all()
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

    leaders = User.query.filter(User.role == "leader", User.id != user_id).all()

    if request.method == "POST":
        original_username = user.username
        original_email = user.email

        user.username = request.form.get("username")
        user.email = request.form.get("email")
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
                user_data=user,
                is_edit_mode=True,
            )
            
    

        if user.username != original_username:
            existing_user = User.query.filter(
                User.username == user.username, User.id != user.id
            ).first()
            if existing_user:
                flash("Username already exists.", "danger")
                user.username = original_username
                return render_template(
                    "admin/create_edit_user.html",
                    title="Edit User",
                    user=user,
                    leaders=leaders,
                    action_url=url_for("admin.edit_user", user_id=user_id),
                    user_data=user,
                    is_edit_mode=True,
                )

        if user.email != original_email:
            existing_email = User.query.filter(
                User.email == user.email, User.id != user.id
            ).first()
            if existing_email:
                flash("Email already registered.", "danger")
                user.email = original_email
                return render_template(
                    "admin/create_edit_user.html",
                    title="Edit User",
                    user=user,
                    leaders=leaders,
                    action_url=url_for("admin.edit_user", user_id=user_id),
                    user_data=user,
                    is_edit_mode=True,
                )

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
                    user_data=user,
                    is_edit_mode=True,
                )
        elif user.role == "member" and not leader_id_str:
            flash("A leader must be selected for a member.", "danger")
            return render_template(
                "admin/create_edit_user.html",
                title="Edit User",
                user=user,
                leaders=leaders,
                action_url=url_for("admin.edit_user", user_id=user_id),
                user_data=user,
                is_edit_mode=True,
            )
        elif user.role != "member":
            user.leader_id = None

        try:
            db.session.commit()
            flash(f"User '{user.username}' updated successfully!", "success")
            return redirect(url_for("admin.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating user: {str(e)}", "danger")
            return render_template(
                "admin/create_edit_user.html",
                title="Edit User",
                user=user,
                leaders=leaders,
                action_url=url_for("admin.edit_user", user_id=user_id),
                user_data=user,
                is_edit_mode=True,
            )

    return render_template(
        "admin/create_edit_user.html",
        title="Edit User",
        user=user,
        leaders=leaders,
        action_url=url_for("admin.edit_user", user_id=user_id),
        user_data=user,
        is_edit_mode=True,
    )


@admin_bp.route("/users/delete/<int:user_id>", methods=["GET"])
@login_required
@role_required("admin")
def delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)

    if user_to_delete.id == session.get("user_id"):
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin.list_users"))

    if user_to_delete.role == "admin":
        flash("Admin users cannot be deleted for security reasons.", "danger")
        return redirect(url_for("admin.list_users"))

    try:
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
    return redirect(url_for("admin.list_users"))


@admin_bp.route("/funds")
@login_required
@role_required("admin")
def manage_funds():
    # Get funds with creator usernames
    funds_with_creators = (
        db.session.query(Fund, User.username.label("creator_username"))
        .join(User, Fund.created_by == User.id)
        .order_by(Fund.created_at.desc())
        .all()
    )
    
    # Debug: Print the first fund's data if it exists
    if funds_with_creators:
        fund, creator = funds_with_creators[0]
        print(f"Debug - First fund data: sales={fund.sales}, payout={fund.payout}, net_profit={fund.net_profit}")
    
    # Calculate totals directly from the database
    result = db.session.query(
        func.coalesce(func.sum(Fund.sales), 0).label('total_sales'),
        func.coalesce(func.sum(Fund.payout), 0).label('total_payout'),
        func.coalesce(func.sum(Fund.net_profit), 0).label('total_net_profit')
    ).first()
    
    # Debug: Print the calculated totals
    print(f"Debug - Calculated totals: sales={result[0]}, payout={result[1]}, net_profit={result[2]}")

    # Calculate the sum of sales and payout for the net profit formula
    total_sales = float(result[0]) if result[0] is not None else 0.0
    total_payout = float(result[1]) if result[1] is not None else 0.0
    total_sales_and_payout = total_sales - total_payout
    
    stats = {
        'total_sales': total_sales,
        'total_payout': total_payout,
        'total_sales_and_payout': total_sales_and_payout,
        'total_net_profit': (total_sales_and_payout * 0.30) / 50  # Using the new formula
    }
    
    # Debug: Print the final stats being passed to template
    print(f"Debug - Final stats: {stats}")

    return render_template(
        "admin/list_funds.html",
        funds_data=funds_with_creators,
        title="Manage Fund Entries",
        fund_types=FUND_TYPES,
        stats=stats,
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
            sales_str = request.form.get("sales", "0").replace(',', '')
            payout_str = request.form.get("payout", "0").replace(',', '')
            remarks = request.form.get("remarks")
            fund_type = request.form.get("fund_type")

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
                sales = float(sales_str) if sales_str else 0.0
                payout = float(payout_str) if payout_str else 0.0
                if sales < 0 or payout < 0:
                    raise ValueError("Values cannot be negative.")
                net_profit = sales - payout
            except ValueError as e:
                flash(f"Invalid values: {e}", "danger")
                return render_template(
                    "admin/create_edit_fund.html",
                    title="Create Fund Entry",
                    fund_data=request.form,
                    action_url=url_for("admin.create_fund"),
                    fund_types=FUND_TYPES,
                )

            new_fund_entry = Fund(
                sales=sales,
                payout=payout,
                net_profit=net_profit,
                remarks=remarks,
                fund_type=fund_type,
                created_by=current_user.id,
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
    display_fund_types = FUND_TYPES.copy()
    if fund.fund_type not in display_fund_types:
        display_fund_types[fund.fund_type] = fund.fund_type.replace("_", " ").title()

    if request.method == "POST":
        try:
            sales_str = request.form.get("sales", "0").replace(',', '')
            payout_str = request.form.get("payout", "0").replace(',', '')
            remarks = request.form.get("remarks")
            fund_type = request.form.get("fund_type")

            if not fund_type or fund_type not in FUND_TYPES:
                flash("Valid Fund Type is required.", "danger")
                return render_template(
                    "admin/create_edit_fund.html",
                    title="Edit Fund Entry",
                    fund_data=request.form,
                    fund=fund,
                    action_url=url_for("admin.edit_fund", fund_id=fund_id),
                    fund_types=display_fund_types,
                )

            try:
                sales = float(sales_str) if sales_str else 0.0
                payout = float(payout_str) if payout_str else 0.0
                if sales < 0 or payout < 0:
                    raise ValueError("Values cannot be negative.")
                net_profit = sales - payout
            except ValueError as e:
                flash(f"Invalid values: {e}", "danger")
                return render_template(
                    "admin/create_edit_fund.html",
                    title="Edit Fund Entry",
                    fund_data=request.form,
                    fund=fund,
                    action_url=url_for("admin.edit_fund", fund_id=fund_id),
                    fund_types=display_fund_types,
                )

            fund.sales = sales
            fund.payout = payout
            fund.net_profit = net_profit
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
                fund_types=display_fund_types,
            )

    return render_template(
        "admin/create_edit_fund.html",
        title="Edit Fund Entry",
        fund=fund,
        action_url=url_for("admin.edit_fund", fund_id=fund_id),
        fund_types=display_fund_types,
    )


@admin_bp.route("/funds/delete/<int:fund_id>", methods=["GET", "POST"])
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
    page = request.args.get("page", 1, type=int)
    per_page = 10

    sort_by = request.args.get("sort_by", "member_count")
    sort_order = request.args.get("sort_order", "desc")

    leaders_query = User.query.filter_by(role="leader")

    total_leaders = leaders_query.count()

    if sort_by == "username":
        if sort_order == "asc":
            leaders_query = leaders_query.order_by(User.username.asc())
        else:
            leaders_query = leaders_query.order_by(User.username.desc())
    else:
        pass

    leaders_pagination = leaders_query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    leaders_with_member_count = []
    for leader_user in leaders_pagination.items:
        member_count = User.query.filter_by(leader_id=leader_user.id).count()
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

    if sort_by == "member_count":
        leaders_with_member_count.sort(
            key=lambda x: x["member_count"], reverse=(sort_order == "desc")
        )

    return render_template(
        "admin/list_all_leaders.html",
        title="Full Leaderboard",
        leaders_list=leaders_with_member_count,
        pagination=leaders_pagination,
        current_value_price=5000,
        sort_by=sort_by,
        sort_order=sort_order,
    )

@admin_bp.route("/fund_history")
@login_required
@role_required("admin")
def fund_history():
    page = request.args.get("page", 1, type=int)
    per_page = 10 # Or a configurable value

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

    available_dates_for_filter = []
    if available_raw_dates:
        for yr, mn in available_raw_dates:
            if yr is not None and mn is not None: # Ensure dates are not NULL
                available_dates_for_filter.append({
                    'year': int(yr),
                    'month': int(mn),
                    'month_name': datetime(int(yr), int(mn), 1).strftime('%B')
                })

    current_year = selected_year
    current_month = selected_month

    if not available_dates_for_filter:
        # No data in FundHistory, default to current system month/year for filter display
        # but queries will likely return nothing.
        now = datetime.utcnow()
        current_year = current_year or now.year
        current_month = current_month or now.month
        # Add current month to filter options if no data exists, for UI consistency
        if not any(d['year'] == current_year and d['month'] == current_month for d in available_dates_for_filter):
            available_dates_for_filter.insert(0, {
                'year': current_year,
                'month': current_month,
                'month_name': datetime(current_year, current_month, 1).strftime('%B')
            })
    else:
        if current_year is None or current_month is None:
            # Default to the most recent available date if no specific filter applied
            current_year = available_dates_for_filter[0]['year']
            current_month = available_dates_for_filter[0]['month']

    # Query for fund type details for the selected/defaulted month (excluding overall summary)
    fund_type_details_query = FundHistory.query.filter(
        extract('year', FundHistory.snapshot_date) == current_year,
        extract('month', FundHistory.snapshot_date) == current_month,
        FundHistory.fund_type != 'MONTHLY_SALES'  # As per user's change in fund_utils.py
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

    return render_template(
        "admin/list_fund_history.html",
        title="Fund History",
        fund_type_details=fund_type_details,
        monthly_summary=monthly_summary,
        available_dates=available_dates_for_filter,
        current_year=current_year,
        current_month=current_month,
        month_names={m: datetime(2000, m, 1).strftime('%B') for m in range(1, 13)} # For displaying month name if needed
    )


