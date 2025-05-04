# This file will contain the SQLAlchemy database models
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False) # Increased length for hash
    role = db.Column(db.String(20), nullable=False) # 'admin', 'leader', 'offline'
    leader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Self-referential foreign key
    can_view_funds = db.Column(db.Boolean, default=False, nullable=False) # Only relevant for leaders
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    preferred_nav = db.Column(db.String(10), default='sidebar', nullable=False) # 'sidebar' or 'navbar'

    # Define relationship for leader to access their offline users
    offline_users = db.relationship('User', backref=db.backref('leader', remote_side=[id]), lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

class CompanySetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False) # e.g., 'total_funds'
    value = db.Column(db.String(200), nullable=True) # Store value as string, convert as needed
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<CompanySetting {self.key}>'

class PerformanceData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    offline_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    metric_value = db.Column(db.Float, nullable=False) # Assuming sales amount is a float
    period = db.Column(db.String(7), nullable=False) # e.g., '2025-05' for YYYY-MM
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationship back to the offline user
    user = db.relationship('User', backref=db.backref('performance_records', lazy='dynamic'))

    def __repr__(self):
        user_info = self.user.username if self.user else f"UserID:{self.offline_user_id}"
        return f'<PerformanceData for {user_info} ({self.period}): {self.metric_value}>'
