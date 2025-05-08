# This file will contain utility functions, e.g., for permission checks
from functools import wraps
from flask import session, flash, redirect, url_for, abort, request, current_app
from flask_login import current_user


def login_required(f):
    """Decorate routes to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role_name):
    """Decorate routes to require a specific role, using current_user."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # @login_required (from Flask-Login, used on the route)
            # should ensure current_user is loaded and authenticated.
            if not current_user.is_authenticated:
                # This should ideally be caught by Flask-Login's @login_required first.
                flash('Authentication required to check roles. Please log in.', 'warning')
                return redirect(url_for('auth.login', next=request.url))

            # Check the role using current_user
            user_role = getattr(current_user, 'role', None)
            if user_role != role_name:
                current_app.logger.warning(
                    f"Role check failed for user '{getattr(current_user, 'email', 'Anonymous')}' "
                    f"attempting to access {request.path}. "
                    f"Required role: '{role_name}', Actual role: '{user_role}'."
                )
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator

admin_required = role_required('admin')
leader_required = role_required('leader')
# member users likely won't have specific restricted routes beyond login_required
