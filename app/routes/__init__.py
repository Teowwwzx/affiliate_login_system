from .general_routes import general_bp
from .auth_routes import auth_bp
from .admin_routes import admin_bp
from .leader_routes import leader_bp
from .member_routes import member_bp


__all__ = ['general_bp', 'auth_bp', 'admin_bp', 'leader_bp', 'member_bp']