from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from ..utils import login_required, admin_required
from ..models import User, db, CompanySetting, PerformanceData
from sqlalchemy import func, extract
import pandas as pd
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import HiddenField

class DeleteUserForm(FlaskForm):
    csrf_token = HiddenField()

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def admin_dashboard():
    setting = CompanySetting.query.filter_by(key='total_funds').first()
    total_funds = setting.value if setting else "N/A"

    total_performance_result = db.session.query(func.coalesce(func.sum(PerformanceData.metric_value), 0.0)).scalar()
    total_performance = round(total_performance_result, 2) if total_performance_result is not None else 0.00

    leader_count = User.query.filter_by(role='leader').count()
    offline_user_count = User.query.filter_by(role='offline').count()

    monthly_performance = db.session.query(
        PerformanceData.period,
        func.coalesce(func.sum(PerformanceData.metric_value), 0.0).label('total_sales')
    ).outerjoin(User)\
    .filter(User.role == 'offline')\
    .group_by(PerformanceData.period)\
    .order_by(PerformanceData.period.asc())\
    .all()

    chart_labels = [p.period for p in monthly_performance]
    chart_data = [float(p.total_sales) for p in monthly_performance]

    return render_template('admin/dashboard.html',
                           total_funds=total_funds,
                           total_performance=total_performance,
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           leader_count=leader_count,
                           offline_user_count=offline_user_count)

@admin_bp.route('/users')
@login_required
@admin_required
def list_users():
    users = User.query.order_by(User.role, User.username).all()
    form = DeleteUserForm()
    return render_template('admin/users.html', users=users, form=form)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user_form():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        leader_username = request.form.get('leader_username')
        can_view_funds = 'can_view_funds' in request.form

        error = None
        if not username or not password or not role:
            error = 'Username, password, and role are required.'
        elif User.query.filter_by(username=username).first():
            error = f"Username '{username}' is already taken."
        elif role not in ['admin', 'leader', 'offline']:
            error = 'Invalid role specified.'

        leader_user = None
        if role == 'offline':
            if not leader_username:
                error = "Leader username is required for role 'offline'."
            else:
                leader_user = User.query.filter_by(username=leader_username, role='leader').first()
                if not leader_user:
                    error = f"Leader with username '{leader_username}' not found or is not a leader."
        elif leader_username:
            flash("Leader username is ignored for roles other than 'offline'.", 'warning')

        if role != 'leader' and can_view_funds:
            flash("Can View Funds flag is ignored for roles other than 'leader'.", 'warning')
            can_view_funds = False

        if error is None:
            hashed_password = generate_password_hash(password)
            new_user = User(
                username=username,
                password_hash=hashed_password,
                role=role,
                leader_id=leader_user.id if leader_user else None,
                can_view_funds=can_view_funds
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f"User '{username}' ({role}) created successfully.", 'success')
            return redirect(url_for('admin.list_users'))
        else:
            flash(error, 'danger')

    leaders = User.query.filter_by(role='leader').order_by(User.username).all()
    return render_template('admin/create_user.html', leaders=leaders)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user_to_edit = User.query.get_or_404(user_id)

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        leader_username = request.form.get('leader_username')
        can_view_funds = 'can_view_funds' in request.form

        error = None
        if username != user_to_edit.username and User.query.filter_by(username=username).first():
            error = f"Username '{username}' is already taken."
        elif not username or not role:
            error = 'Username is required.'
        elif role not in ['admin', 'leader', 'offline']:
            error = 'Invalid role specified.'

        leader_user = None
        if role == 'offline':
            if not leader_username:
                error = "Leader username is required for role 'offline'."
            else:
                leader_user = User.query.filter_by(username=leader_username, role='leader').first()
                if not leader_user:
                    error = f"Leader with username '{leader_username}' not found or is not a leader."
        elif leader_username:
            flash("Leader username is ignored for roles other than 'offline'.", 'warning')

        if role != 'leader' and can_view_funds:
            flash("Can View Funds flag is ignored for roles other than 'leader'.", 'warning')
            can_view_funds = False

        if error is None:
            user_to_edit.username = username
            user_to_edit.role = role
            if password:
                user_to_edit.password_hash = generate_password_hash(password)
            user_to_edit.leader_id = leader_user.id if leader_user else None
            user_to_edit.can_view_funds = can_view_funds if role == 'leader' else False

            db.session.commit()
            flash(f"User '{user_to_edit.username}' updated successfully.", 'success')
            return redirect(url_for('admin.list_users'))
        else:
            flash(error, 'danger')

    leaders = User.query.filter_by(role='leader').order_by(User.username).all()
    return render_template('admin/edit_user.html', user=user_to_edit, leaders=leaders)

@admin_bp.route('/settings/funds', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_funds():
    setting = CompanySetting.query.filter_by(key='total_funds').first()

    if request.method == 'POST':
        new_value = request.form.get('total_funds')
        if new_value:
            try:
                float(new_value)
                if setting:
                    setting.value = new_value
                else:
                    setting = CompanySetting(key='total_funds', value=new_value)
                    db.session.add(setting)
                db.session.commit()
                flash('Total funds updated successfully.', 'success')
            except ValueError:
                flash('Invalid amount entered. Please enter a number.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating funds: {e}', 'danger')
        else:
            flash('Funds value cannot be empty.', 'warning')
        setting = CompanySetting.query.filter_by(key='total_funds').first()

    current_value = setting.value if setting else '0.00'
    last_updated = setting.last_updated if setting else None

    return render_template('admin/manage_funds.html', current_value=current_value, last_updated=last_updated)

@admin_bp.route('/users/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_users():
    if request.method == 'POST':
        if 'user_file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['user_file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.csv')):
            try:
                if file.filename.endswith('.xlsx'):
                    df = pd.read_excel(file, engine='openpyxl')
                else:
                    try:
                        df = pd.read_csv(file)
                    except UnicodeDecodeError:
                        file.seek(0)
                        df = pd.read_csv(file, encoding='latin1')

                required_columns = ['username', 'password', 'role']
                if not all(col in df.columns for col in required_columns):
                    flash(f'Missing required columns. Need: {required_columns}', 'danger')
                    return redirect(request.url)

                created_count = 0
                skipped_count = 0
                errors = []

                for index, row in df.iterrows():
                    username = str(row['username']).strip() if pd.notna(row['username']) else ''
                    password = str(row['password']).strip() if pd.notna(row['password']) else ''
                    role = str(row['role']).strip() if pd.notna(row['role']) else ''
                    leader_username = str(row.get('leader_username', '')).strip() if pd.notna(row.get('leader_username', '')) else ''
                    can_view_funds = str(row.get('can_view_funds', '')).strip().lower() == 'true' if pd.notna(row.get('can_view_funds', '')) else False

                    row_num = index + 2
                    error_prefix = f"Row {row_num}: "
                    row_errors = []

                    if not username or not password or not role:
                        row_errors.append(f"{error_prefix}Missing username, password, or role.")
                    existing_user = User.query.filter(User.username.ilike(username)).first()
                    if existing_user:
                        row_errors.append(f"{error_prefix}Username '{username}' already exists.")
                    if role not in ['admin', 'leader', 'offline']:
                        row_errors.append(f"{error_prefix}Invalid role '{role}' for user '{username}'.")

                    leader_user = None
                    if role == 'offline':
                        if not leader_username:
                            row_errors.append(f"{error_prefix}Leader username is required for role 'offline'.")
                            continue
                        leader_user = User.query.filter(User.username.ilike(leader_username), User.role == 'leader').first()
                        if not leader_user:
                            row_errors.append(f"{error_prefix}Leader with username '{leader_username}' not found or is not a leader.")
                            continue
                    elif leader_username:
                        flash("Leader username is ignored for roles other than 'offline'.", 'warning')

                    if role != 'leader' and can_view_funds:
                        flash("Can View Funds flag is ignored for roles other than 'leader'.", 'warning')
                        can_view_funds = False

                    if row_errors:
                        errors.extend(row_errors)
                        skipped_count += 1
                        continue

                    try:
                        hashed_password = generate_password_hash(password)
                        new_user = User(
                            username=username,
                            password_hash=hashed_password,
                            role=role,
                            leader_id=leader_user.id if leader_user else None,
                            can_view_funds=can_view_funds
                        )
                        db.session.add(new_user)
                        created_count += 1
                    except Exception as e:
                        errors.append(f"{error_prefix}Error creating user '{username}': {e}")
                        skipped_count += 1
                        db.session.rollback()

                if errors and created_count == 0:
                    db.session.rollback()
                    flash('Import failed. No users were created. See errors below.', 'danger')
                elif errors:
                    try:
                        db.session.commit()
                        flash(f'Import partially successful. Created: {created_count}, Skipped: {skipped_count}. See errors below.', 'warning')
                    except Exception as commit_error:
                        db.session.rollback()
                        flash(f'Import failed during final commit after partial success. Error: {commit_error}', 'danger')
                        for error in errors:
                            flash(error, 'danger')
                        return redirect(request.url)
                else:
                    db.session.commit()
                    flash(f'User import successful! Created: {created_count}', 'success')

                for error in errors:
                    flash(error, 'danger')

                return redirect(url_for('admin.list_users'))

            except Exception as e:
                db.session.rollback()
                flash(f'An critical error occurred during file processing: {e}', 'danger')
                return redirect(request.url)

        else:
            flash('Invalid file type. Please upload .xlsx or .csv', 'danger')
            return redirect(request.url)

    return render_template('admin/import_users.html')

@admin_bp.route('/performance/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_performance():
    if request.method == 'POST':
        if 'perf_file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['perf_file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.csv')):
            try:
                if file.filename.endswith('.xlsx'):
                    df = pd.read_excel(file, engine='openpyxl')
                else:
                    try:
                        df = pd.read_csv(file)
                    except UnicodeDecodeError:
                        file.seek(0)
                        df = pd.read_csv(file, encoding='latin1')

                required_columns = ['offline_username', 'period', 'sales_amount']
                if not all(col in df.columns for col in required_columns):
                    flash(f'Missing required columns. Need: {required_columns}', 'danger')
                    return redirect(request.url)

                created_count = 0
                updated_count = 0
                skipped_count = 0
                errors = []

                for index, row in df.iterrows():
                    username = str(row['offline_username']).strip() if pd.notna(row['offline_username']) else ''
                    period = str(row['period']).strip() if pd.notna(row['period']) else ''
                    sales_amount_str = str(row['sales_amount']).strip() if pd.notna(row['sales_amount']) else ''

                    row_num = index + 2
                    error_prefix = f"Row {row_num}: "
                    row_errors = []

                    if not username or not period or not sales_amount_str:
                        row_errors.append(f"{error_prefix}Missing offline_username, period, or sales_amount.")

                    if not (len(period) == 7 and period[4] == '-' and period[:4].isdigit() and period[5:].isdigit()):
                        row_errors.append(f"{error_prefix}Invalid period format '{period}'. Use YYYY-MM.")

                    try:
                        sales_amount = float(sales_amount_str)
                    except ValueError:
                        row_errors.append(f"{error_prefix}Invalid sales_amount '{sales_amount_str}'. Must be a number.")

                    offline_user = None
                    if username:
                        offline_user = User.query.filter(User.username.ilike(username), User.role == 'offline').first()
                        if not offline_user:
                            row_errors.append(f"{error_prefix}Offline user '{username}' not found.")

                    if row_errors:
                        errors.extend(row_errors)
                        skipped_count += 1
                        continue

                    existing_record = PerformanceData.query.filter_by(
                        offline_user_id=offline_user.id,
                        period=period
                    ).first()

                    try:
                        if existing_record:
                            existing_record.metric_value = sales_amount
                            existing_record.recorded_at = datetime.utcnow()
                            updated_count += 1
                        else:
                            new_record = PerformanceData(
                                offline_user_id=offline_user.id,
                                period=period,
                                metric_value=sales_amount
                            )
                            db.session.add(new_record)
                            created_count += 1
                    except Exception as e:
                        errors.append(f"{error_prefix}Error saving performance for '{username}' period '{period}': {e}")
                        skipped_count += 1
                        db.session.rollback()

                if errors and (created_count + updated_count == 0):
                    db.session.rollback()
                    flash('Import failed. No performance data saved. See errors below.', 'danger')
                elif errors:
                    try:
                        db.session.commit()
                        flash(f'Import partially successful. Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}. See errors below.', 'warning')
                    except Exception as commit_error:
                        db.session.rollback()
                        flash(f'Import failed during final commit. Error: {commit_error}', 'danger')
                        for error in errors:
                            flash(error, 'danger')
                        return redirect(request.url)
                else:
                    db.session.commit()
                    flash(f'Performance import successful! Created: {created_count}, Updated: {updated_count}', 'success')

                for error in errors:
                    flash(error, 'danger')

                return redirect(url_for('admin.admin_dashboard'))

            except Exception as e:
                db.session.rollback()
                flash(f'An critical error occurred during file processing: {e}', 'danger')
                return redirect(request.url)

        else:
            flash('Invalid file type. Please upload .xlsx or .csv', 'danger')
            return redirect(request.url)

    return render_template('admin/import_performance.html')
