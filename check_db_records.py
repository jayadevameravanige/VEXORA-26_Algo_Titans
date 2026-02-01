"""
Quick script to check what's actually in the database
"""
import os
import sys
from dotenv import load_dotenv

# Add api directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

load_dotenv('api/.env')

from api.models import db, Voter, AuditSession
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    # Check total voters in DB
    total_voters = Voter.query.count()
    print(f"\n📊 Total Voter records in DB: {total_voters}")
    
    # Check flagged voters
    flagged_voters = Voter.query.filter_by(is_flagged=True).count()
    print(f"🚩 Flagged voters (is_flagged=True): {flagged_voters}")
    
    # Check by risk type
    ghosts = Voter.query.filter_by(risk_type='Ghost').count()
    duplicates = Voter.query.filter_by(risk_type='Duplicate').count()
    print(f"👻 Ghost voters: {ghosts}")
    print(f"🔄 Duplicate voters: {duplicates}")
    
    # Check review statuses
    pending = Voter.query.filter_by(review_status='pending').count()
    under_review = Voter.query.filter_by(review_status='under_review').count()
    archived = Voter.query.filter_by(review_status='archived').count()
    print(f"\n📋 Review Statuses:")
    print(f"  - Pending: {pending}")
    print(f"  - Under Review: {under_review}")
    print(f"  - Archived: {archived}")
    
    # Show sample flagged records
    print(f"\n🔍 Sample Flagged Records (first 5):")
    sample = Voter.query.filter_by(is_flagged=True).limit(5).all()
    for v in sample:
        print(f"  - {v.voter_id}: {v.name}, Type: {v.risk_type}, Confidence: {v.risk_confidence}, Status: {v.review_status}")
    
    # Check audit sessions
    sessions = AuditSession.query.count()
    print(f"\n📝 Total Audit Sessions: {sessions}")
    if sessions > 0:
        last_session = AuditSession.query.order_by(AuditSession.timestamp.desc()).first()
        print(f"  Last session:")
        print(f"    - Total Records: {last_session.total_records}")
        print(f"    - Ghosts: {last_session.ghost_voters}")
        print(f"    - Duplicates: {last_session.duplicate_voters}")
        print(f"    - Created: {last_session.timestamp}")
