# app/database/models/fund_monthly_summary.py
from .. import db
from datetime import datetime, timezone
from sqlalchemy import Numeric, Date

class FundHistory(db.Model):
    __tablename__ = 'fund_history'

    id = db.Column(db.Integer, primary_key=True)
    snapshot_date = db.Column(db.Date, nullable=False, index=True, comment="The last day of the month this summary represents")
    fund_type = db.Column(db.String(50), nullable=False, index=True, default='general', comment="Type of fund or 'ALL_TYPES_MONTHLY_SUMMARY' for overall total")
    sales = db.Column(Numeric(12, 2), nullable=False, default=0.00)
    payout = db.Column(Numeric(12, 2), nullable=False, default=0.00)
    total_profit = db.Column(Numeric(12, 2), nullable=False, default=0.00)
    total_net_profit = db.Column(Numeric(12, 2), nullable=False, default=0.00)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<FundHistory {self.snapshot_date.strftime("%Y-%m-%d")}>'
