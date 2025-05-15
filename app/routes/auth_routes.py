# app/routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import login_user, logout_user, current_user, login_required
from ..database.models import User
from .. import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:  # Check if already logged in
        if current_user.role == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        elif current_user.role == "leader":
            return redirect(url_for("leader.leader_dashboard"))
        elif current_user.role == "member":
            return redirect(url_for("member.member_dashboard"))
        else:
            return redirect(url_for("general.index"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Please check your login details and try again.", "danger")
            return redirect(url_for("auth.login"))

        # Check if user account is active
        if not user.status:
            flash(
                "Your account is inactive. Please contact an administrator.", "warning"
            )
            return redirect(url_for("auth.login"))

        # Use Flask-Login's login_user function
        login_user(user)

        # Store user info in session for convenience (Flask-Login handles user_id)
        session["username"] = user.username

        # flash(f'Welcome back, {user.username}!', 'success')

        # Handle the next parameter if it exists
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):  # Ensure it's a relative URL
            return redirect(next_page)

        # Redirect to appropriate dashboard based on role
        if user.role == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        elif user.role == "leader":
            return redirect(url_for("leader.leader_dashboard"))
        elif user.role == "member":
            return redirect(url_for("member.member_dashboard"))
        else:
            flash("Login successful, but role dashboard not found.", "warning")
            return redirect(url_for("general.index"))

    return render_template("auth/login.html", title="Login")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()  # Use Flask-Login's logout_user function
    session.clear()  # Clear any custom session data
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("general.index"))


# New Member Registration with Referral Code
@auth_bp.route("/register_member", methods=["GET", "POST"])
def register_member():
    if current_user.is_authenticated:
        return redirect(url_for("general.index"))

    # Initialize form data variables to None for GET requests or if not set in POST
    form_data = {'username': None, 'email': None, 'referral_code': None}

    if request.method == "POST":
        # Update form_data with submitted values
        form_data['username'] = request.form.get('username')
        form_data['email'] = request.form.get('email')
        form_data['referral_code'] = request.form.get('referral_code')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Add your validation logic here
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register_member.html', title='Register Member', **form_data)

        # Server-side validation for referral code
        if not form_data['referral_code']:
            flash('Referral code is required.', 'danger')
            return render_template('auth/register_member.html', title='Register Member', **form_data)

        # --- Start of new referral logic ---
        assigned_leader_id = None
        referrer = User.query.filter_by(personal_referral_code=form_data['referral_code']).first()
        if referrer:
            if referrer.role == 'leader':
                assigned_leader_id = referrer.id
            else: # Referrer is a member or another role
                assigned_leader_id = referrer.leader_id # Assign the referrer's leader
        else: # Referral code provided is invalid
            flash('Invalid referral code provided.', 'warning')
            return render_template('auth/register_member.html', title='Register Member', **form_data)
        # --- End of new referral logic ---

        # Create new user logic here
        new_member = User(
            username=form_data['username'],
            email=form_data['email'],
            role='member',
            status=True,
            signup_referral_code_used=form_data['referral_code'],
            leader_id=assigned_leader_id # Assign the determined leader_id
        )
        new_member.set_password(password)

        db.session.add(new_member)
        try:
            db.session.commit()
            flash(f"Account for {form_data['username']} created successfully! You can now log in.", 'success')
            return redirect(url_for('auth.login'))
        except IntegrityError: 
            db.session.rollback()
            flash('Registration failed. The username or email may already be in use. Please try different details.', 'danger')
            return render_template('auth/register_member.html', title='Register Member', **form_data)
        except Exception as e: 
            db.session.rollback()
            # For production, you would log this error. For now, keeping it simple for the user.
            # from flask import current_app
            # current_app.logger.error(f"Registration error for {form_data['username']}: {str(e)}")
            flash('An unexpected error occurred during registration. Please try again later.', 'danger')
            return render_template('auth/register_member.html', title='Register Member', **form_data)

    # For GET request or if POST logic falls through (e.g. validation error before try/except)
    return render_template('auth/register_member.html', title='Register Member', **form_data)
