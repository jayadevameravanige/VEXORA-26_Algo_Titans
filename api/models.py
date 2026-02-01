from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Voter(db.Model):
    __tablename__ = 'voters'
    
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(255))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(50))
    address = db.Column(db.Text)
    pincode = db.Column(db.String(20))
    
    # Analysis results
    risk_score = db.Column(db.Float, default=0.0)
    risk_type = db.Column(db.String(50)) # 'Ghost', 'Duplicate', 'Both', 'None'
    risk_confidence = db.Column(db.Float, default=0.0)
    primary_reason = db.Column(db.String(500))
    contributing_factors = db.Column(db.Text) # Stored as JSON string
    
    # Audit status
    review_status = db.Column(db.String(50), default='pending') # 'pending', 'confirmed', 'dismissed'
    is_archived = db.Column(db.Boolean, default=False)
    archive_status = db.Column(db.String(50)) # 'approved', 'deleted'
    archived_at = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'voter_id': self.voter_id,
            'voter_details': {
                'name': self.name,
                'Age': self.age,
                'Gender': self.gender,
                'Address': self.address,
                'Pincode': self.pincode
            },
            'risk_score': self.risk_score,
            'record_type': self.risk_type.lower() if self.risk_type else 'none',
            'archive_type': self.risk_type.lower() if self.risk_type else 'none',
            'confidence': self.risk_confidence,
            'primary_reason': self.primary_reason,
            'contributing_factors': json.loads(self.contributing_factors) if self.contributing_factors else [],
            'review_status': self.review_status,
            'is_archived': self.is_archived,
            'archive_status': self.archive_status,
            'archived_at': self.archived_at.isoformat() if self.archived_at else None
        }

class AuditSession(db.Model):
    __tablename__ = 'audit_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    total_records = db.Column(db.Integer)
    ghost_count = db.Column(db.Integer)
    duplicate_count = db.Column(db.Integer)
    status = db.Column(db.String(50)) # 'completed', 'failed'
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'total_records': self.total_records,
            'ghost_voters_flagged': self.ghost_count,
            'duplicate_voters_flagged': self.duplicate_count,
            'status': self.status
        }
