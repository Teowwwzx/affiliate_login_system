# This file will contain the SQLAlchemy database models
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, Numeric

from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(30), nullable=False)
    account_status = db.Column(db.String(20), nullable=False, default='active')
    preferred_navigation = db.Column(db.String(10), nullable=False, default='sidebar')
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    can_view_financials = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint(role.in_(['system_administrator', 'team_leader', 'team_member']), name='check_role'),
        CheckConstraint(account_status.in_(['active', 'inactive']), name='check_account_status'),
        CheckConstraint(preferred_navigation.in_(['sidebar', 'navbar']), name='check_preferred_navigation'),
    )

    # Role descriptions
    ROLE_DESCRIPTIONS = {
        'system_administrator': 'System Administrator - Full access to all system features',
        'team_leader': 'Team Leader - Manages team members and views team performance',
        'team_member': 'Team Member - Tracks and reports personal performance metrics'
    }
    
    # Define relationship for team leader to access their team members
    team_members = db.relationship('User', backref=db.backref('team_leader', remote_side=[id]), lazy='dynamic')
    
    def __repr__(self):
        role_desc = self.ROLE_DESCRIPTIONS.get(self.role, 'Unknown Role')
        return f'<User {self.username} - {role_desc}>'

class FinancialAccount(db.Model):
    __tablename__ = 'financial_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    amount = db.Column(Numeric(15, 2), nullable=False, default=0.00)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    account_status = db.Column(db.String(20), nullable=False, default='active')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint(account_status.in_(['active', 'archived']), name='check_account_status'),
    )
    
    def __repr__(self):
        return f'<FinancialAccount {self.name}: {self.amount} {self.currency}>'

class PerformanceMetric(db.Model):
    __tablename__ = 'performance_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    reporting_period = db.Column(db.String(7), nullable=False)
    performance_metric = db.Column(Numeric(15, 2), nullable=False)
    metric_status = db.Column(db.String(20), nullable=False, default='final')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint(metric_status.in_(['provisional', 'final', 'corrected']), name='check_metric_status'),
        db.UniqueConstraint('account_id', 'reporting_period', name='uq_account_period'),
    )
    
    # Define relationship back to the user
    user = db.relationship('User', backref=db.backref('performance_metrics', lazy='dynamic'))
    
    def __repr__(self):
        user_info = self.user.username if self.user else f"UserID:{self.user_id}"
        return f'<PerformanceMetric for {user_info} ({self.reporting_period}): {self.performance_metric}>'
