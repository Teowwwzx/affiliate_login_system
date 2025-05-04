from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from ..utils import login_required, leader_required
from ..models import User, CompanySetting, db, PerformanceData
from sqlalchemy import func
from werkzeug.security import generate_password_hash
import pandas as pd
from werkzeug.utils import secure_filename
import os
from datetime import datetime

leader_bp = Blueprint('leader', __name__, url_prefix='/leader')

@leader_bp.route('/dashboard')
@login_required
@leader_required
def leader_dashboard():
    leader_id = session.get('user_id')
    leader = User.query.get(leader_id)
    if not leader:
        flash("Leader not found.", "danger")
        session.clear()
        return redirect(url_for('auth.login'))

    offline_user_count = User.query.filter_by(leader_id=leader_id).count()

    company_funds_display = None
    can_view = session.get('user_can_view_funds', False)
    if can_view:
        setting = CompanySetting.query.filter_by(key='total_funds').first()
        company_funds_display = setting.value if setting else "N/A"

    total_performance_result = db.session.query(func.coalesce(func.sum(PerformanceData.metric_value), 0.0))\
        .join(User)\
        .filter(User.leader_id == leader_id)\
        .scalar()
    total_performance = round(total_performance_result, 2) if total_performance_result is not None else 0.00

    monthly_performance = db.session.query(
        PerformanceData.period,
        func.coalesce(func.sum(PerformanceData.metric_value), 0.0).label('total_sales')
    ).join(User)\
    .filter(User.leader_id == leader_id)\
    .group_by(PerformanceData.period)\
    .order_by(PerformanceData.period.asc())\
    .all()

    chart_labels = [p.period for p in monthly_performance]
    chart_data = [float(p.total_sales) for p in monthly_performance]

    top_offline_users = db.session.query(
        User.username,
        func.coalesce(func.sum(PerformanceData.metric_value), 0.0).label('total_sales')
    ).outerjoin(PerformanceData)\
    .filter(User.leader_id == leader_id)\
    .group_by(User.username)\
    .order_by(func.coalesce(func.sum(PerformanceData.metric_value), 0.0).desc())\
    .limit(3)\
    .all()

    return render_template('leader/dashboard.html',
                           offline_user_count=offline_user_count,
                           total_performance=total_performance,
                           company_funds_display=company_funds_display,
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           top_offline_users=top_offline_users)

@leader_bp.route('/offline-users')
@login_required
@leader_required
def list_offline_users():
    leader_id = session.get('user_id')
    leader = User.query.get(leader_id)

    offline_users_with_performance = db.session.query(
        User.id,
        User.username,
        User.created_at,
        func.coalesce(func.sum(PerformanceData.metric_value), 0.0).label('total_sales')
    ).outerjoin(PerformanceData)\
    .filter(User.leader_id == leader_id)\
    .group_by(User.id, User.username, User.created_at)\
    .order_by(User.username)\
    .all()

    return render_template('leader/offline_users.html', users=offline_users_with_performance)

@leader_bp.route('/offline-users/create', methods=['GET', 'POST'])
@login_required
@leader_required
def create_offline_user():
    leader_id = session.get('user_id')

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        error = None
        if not username or not password:
            error = 'Username and password are required.'
        elif User.query.filter_by(username=username).first():
            error = f"Username '{username}' is already taken."

        if error is None:
            hashed_password = generate_password_hash(password)
            new_user = User(
                username=username,
                password_hash=hashed_password,
                role='offline',
                leader_id=leader_id
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f"Offline user '{username}' created successfully.", 'success')
            return redirect(url_for('leader.list_offline_users'))
        else:
            flash(error, 'danger')

    return render_template('leader/create_offline_user.html')
