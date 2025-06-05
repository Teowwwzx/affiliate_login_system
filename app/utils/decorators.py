# app/utils/decorators.py
from functools import wraps
from flask import flash, redirect, url_for, abort, request
from flask_login import current_user

def login_required(f):
    """Decorate routes to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role_name):
    """Decorate routes to require a specific role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                # This check is somewhat redundant if login_required is also used,
                # but good for standalone use or defense in depth.
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            if current_user.role != role_name:
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator

admin_required = role_required('admin')
leader_required = role_required('leader')
member_required = role_required('member') # Adding member_required for consistency
