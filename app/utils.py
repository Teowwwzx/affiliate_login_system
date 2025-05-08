# This file will contain utility functions, e.g., for permission checks
from functools import wraps
from flask import session, flash, redirect, url_for, abort, request


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
    """Decorate routes to require a specific role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            if session.get('user_role') != role_name:
                abort(403) # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator

admin_required = role_required('admin')
leader_required = role_required('leader')
# member users likely won't have specific restricted routes beyond login_required
