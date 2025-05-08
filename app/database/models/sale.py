# app/database/models/sale.py
from .. import db
from datetime import datetime, timezone, date


class Sale(db.Model):
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)    
    member_count = db.Column(db.Integer, nullable=False, default=0)  # Members at time of snapshot
    value = db.Column(db.Float, nullable=False, default=0.0) # The actual MYR/member value used for this record
    total = db.Column(db.Float, nullable=False, default=0.0)   # Derived: member_count * value
    
    remarks = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc)) # Timestamp of when this row was created
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # User/system that triggered snapshot
    
    # Unique constraint for a leader on a specific snapshot date
    __table_args__ = (db.UniqueConstraint('leader_id', 'created_at', name='uq_leader_sales'),)

    def __repr__(self):
        return f'<Sale L:{self.leader_id} Date:{self.created_at.strftime("%Y-%m-%d")} Total:{self.total}>'