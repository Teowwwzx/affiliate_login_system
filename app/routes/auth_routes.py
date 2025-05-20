from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask import jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import login_user, logout_user, current_user, login_required
from ..database.models import User
from ..database import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError

# Imports for password reset functionality
from ..forms import RequestResetForm, ResetPasswordForm
from ..utils import send_email

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
    form_data = {"username": None, "email": None, "referral_code": None}

    if request.method == "POST":
        # Update form_data with submitted values
        form_data["username"] = request.form.get("username")
        form_data["email"] = request.form.get("email")
        form_data["referral_code"] = request.form.get("referral_code")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Add your validation logic here
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template(
                "auth/register_member.html", title="Register Member", **form_data
            )

        # Server-side validation for referral code
        if not form_data["referral_code"]:
            flash("Referral code is required.", "danger")
            return render_template(
                "auth/register_member.html", title="Register Member", **form_data
            )

        # --- Start of new referral logic ---
        assigned_leader_id = None
        referrer = User.query.filter_by(
            personal_referral_code=form_data["referral_code"]
        ).first()
        if referrer:
            if referrer.role == "leader":
                assigned_leader_id = referrer.id
            else:  # Referrer is a member or another role
                assigned_leader_id = referrer.leader_id  # Assign the referrer's leader
        else:  # Referral code provided is invalid
            flash("Invalid referral code provided.", "warning")
            return render_template(
                "auth/register_member.html", title="Register Member", **form_data
            )
        # --- End of new referral logic ---

        # Create new user logic here
        new_member = User(
            username=form_data["username"],
            email=form_data["email"],
            role="member",
            status=True,
            signup_referral_code_used=form_data["referral_code"],
            leader_id=assigned_leader_id,  # Assign the determined leader_id
        )
        new_member.set_password(password)

        db.session.add(new_member)
        try:
            db.session.commit()
            flash(
                f"Account for {form_data['username']} created successfully! You can now log in.",
                "success",
            )
            return redirect(url_for("auth.login"))
        except IntegrityError:
            db.session.rollback()
            flash(
                "Registration failed. The username or email may already be in use. Please try different details.",
                "danger",
            )
            return render_template(
                "auth/register_member.html", title="Register Member", **form_data
            )
        except Exception as e:
            db.session.rollback()
            # For production, you would log this error. For now, keeping it simple for the user.
            # from flask import current_app
            # current_app.logger.error(f"Registration error for {form_data['username']}: {str(e)}")
            flash(
                "An unexpected error occurred during registration. Please try again later.",
                "danger",
            )
            return render_template(
                "auth/register_member.html", title="Register Member", **form_data
            )

    # For GET request or if POST logic falls through (e.g. validation error before try/except)
    return render_template(
        "auth/register_member.html", title="Register Member", **form_data
    )


@auth_bp.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # Validation checks
        if not current_password or not new_password or not confirm_password:
            flash("All password fields are required.", "warning")
            return redirect(url_for("auth.change_password"))

        if new_password != confirm_password:
            flash("New password and confirmation do not match.", "warning")
            return redirect(url_for("auth.change_password"))

        if len(new_password) < 6:
            flash("Password must be at least 6 characters long.", "warning")
            return redirect(url_for("auth.change_password"))

        # Verify current password
        if not check_password_hash(current_user.password_hash, current_password):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("auth.change_password"))

        # Update password
        current_user.password_hash = generate_password_hash(new_password)
        try:
            db.session.commit()
            flash("Password updated successfully.", "success")
            # Determine the correct dashboard to redirect to
            if current_user.role == "admin":
                return redirect(url_for("admin.admin_dashboard"))
            elif current_user.role == "leader":
                return redirect(url_for("leader.leader_dashboard"))
            elif current_user.role == "member":
                return redirect(url_for("member.member_dashboard"))
            else:
                # Fallback, though this case should ideally not be reached if roles are well-defined
                return redirect(url_for("general.index"))
        except Exception as e:
            db.session.rollback()
            flash(
                "An error occurred while updating your password. Please try again.",
                "danger",
            )
            return redirect(url_for("auth.change_password"))

    return render_template("auth/change_password.html", title="Change Password")


# --- Password Reset Routes ---


@auth_bp.route("/reset_password", methods=["GET", "POST"])
def request_reset_token():
    if current_user.is_authenticated:
        # Redirect to their specific dashboard if applicable, otherwise general index
        if current_user.role == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        elif current_user.role == "leader":
            return redirect(url_for("leader.leader_dashboard"))
        elif current_user.role == "member":
            return redirect(url_for("member.member_dashboard"))
        else:
            return redirect(url_for("general.index"))

    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.get_reset_password_token()
            subject = "Password Reset Request - RNAffiliate"
            html_content = render_template(
                "auth/email/reset_password.html", user=user, token=token
            )
            try:
                send_email(user.email, subject, html_content)
                flash(
                    "An email has been sent with instructions to reset your password.",
                    "info",
                )
            except Exception as e:
                # Log the exception e for debugging
                # from flask import current_app
                # current_app.logger.error(f"Failed to send password reset email to {user.email}: {e}")
                flash(
                    "There was an issue sending the password reset email. Please try again later.",
                    "danger",
                )
        else:
            # Generic message even if user not found, for security.
            flash(
                "If an account with that email exists, an email has been sent with instructions to reset your password.",
                "info",
            )
        return redirect(url_for("auth.login"))  # Redirect to login page after request
    return render_template(
        "auth/email/reset_request.html", title="Request Password Reset", form=form
    )


@auth_bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        # Redirect to their specific dashboard if applicable, otherwise general index
        if current_user.role == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        elif current_user.role == "leader":
            return redirect(url_for("leader.leader_dashboard"))
        elif current_user.role == "member":
            return redirect(url_for("member.member_dashboard"))
        else:
            return redirect(url_for("general.index"))

    user = User.verify_reset_password_token(token)
    if user is None:
        flash("That is an invalid or expired token.", "warning")
        return redirect(url_for("auth.request_reset_token"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        try:
            db.session.commit()
            flash(
                "Your password has been updated! You are now able to log in.", "success"
            )
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            # Log the exception e for debugging
            # from flask import current_app
            # current_app.logger.error(f"Failed to update password for user {user.username} after reset: {e}")
            flash(
                "There was an issue updating your password. Please try again.", "danger"
            )
            return redirect(
                url_for("auth.reset_token", token=token)
            )  # Stay on page if error

    return render_template("auth/email/reset_token.html", title="Reset Password", form=form)
