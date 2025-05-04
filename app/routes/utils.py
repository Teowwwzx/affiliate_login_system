from functools import wraps
from flask import session, redirect, url_for, flash
from .models import User, db

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'danger')
            return redirect(url_for('auth.login'))
        user = User.query.get(session['user_id'])
        if user is None or user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('general.index'))
        return f(*args, **kwargs)
    return decorated_function

def leader_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'danger')
            return redirect(url_for('auth.login'))
        user = User.query.get(session['user_id'])
        if user is None or user.role != 'leader':
            flash('Leader access required.', 'danger')
            return redirect(url_for('general.index'))
        return f(*args, **kwargs)
    return decorated_function
