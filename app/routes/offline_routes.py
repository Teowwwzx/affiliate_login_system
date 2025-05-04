from flask import Blueprint, render_template, request, flash, redirect, url_for, session, abort
from ..utils import login_required
from ..models import User

offline_bp = Blueprint('offline', __name__, url_prefix='/offline')

@offline_bp.route('/dashboard')
@login_required
def offline_dashboard():
    if session.get('user_role') != 'offline':
        abort(403)

    user_id = session.get('user_id')
    user = User.query.get(user_id)
    leader_name = user.leader.username if user.leader else "Not Assigned"

    return render_template('offline/dashboard.html', leader_name=leader_name)
