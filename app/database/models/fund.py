# app/database/models/fund.py
from .. import db
from datetime import datetime, timezone
from sqlalchemy import Numeric

class Fund(db.Model):
    __tablename__ = 'funds'
    
    id = db.Column(db.Integer, primary_key=True)
    net_profit = db.Column(Numeric(10, 2), nullable=False, default=0.00) 
    sales = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    payout = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    fund_type = db.Column(db.String(50), nullable=False, default='general', index=True)
    remarks = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __repr__(self):
        return f'<Fund {self.fund_type} ({self.created_at.strftime("%Y-%m-%d")}): Net Profit ${self.net_profit}>'