from .. import db
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy.orm import relationship
import secrets
import string
from flask import current_app
from itsdangerous import URLSafeTimedSerializer as Serializer

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    status = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    personal_referral_code = db.Column(db.String(10), unique=True, nullable=True, index=True)
    signup_referral_code_used = db.Column(db.String(10), nullable=True) 
    
    # Relationships
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    members = db.relationship('User', backref=db.backref('leader', remote_side=[id]))
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if not hasattr(self, 'personal_referral_code') or not self.personal_referral_code:
            self.personal_referral_code = self._generate_unique_personal_code() 

    @staticmethod
    def _generate_unique_personal_code(length_alpha=2, length_num=4):
        """
        Generate a unique referral code in the format AA9999 (2 letters + 4 digits).
        """
        while True:
            letters = ''.join(secrets.choice(string.ascii_uppercase) for _ in range(length_alpha))
            numbers = ''.join(secrets.choice(string.digits) for _ in range(length_num))
            code = letters + numbers
            if not User.query.filter_by(personal_referral_code=code).first():
                return code

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_active(self):
        """True if the user's account is active."""
        return self.status
    
    def get_reset_password_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_password_token(token, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expires_sec)
            user_id = data.get('user_id')
        except Exception: 
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f'<User {self.username}>'