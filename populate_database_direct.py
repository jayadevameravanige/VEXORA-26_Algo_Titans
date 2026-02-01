"""
Direct database population from analysis results
This bypasses the API and directly saves flagged voters
"""
import os
import sys
import json
from dotenv import load_dotenv

# Add api directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

load_dotenv('api/.env')

from api.models import db, Voter, AuditSession
from flask import Flask
from ml.pipeline import VoteGuardPipeline

print("🚀 Running analysis and saving to database...")
print("=" * 60)

# Create Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    # Run the pipeline
    print("\n📊 Running VoteGuard pipeline...")
    pipeline = VoteGuardPipeline()
    result = pipeline.run(r"e:\VEXORA-26_Algo_Titans\voter_data.csv")
    
    print(f"\n✅ Analysis complete!")
    print(f"   Ghosts: {result.ghost_voters_flagged}")
    print(f"   Duplicates: {result.duplicate_voters_flagged}")
    
    # Save to database
    print(f"\n💾 Saving to database...")
    
    try:
        # Create audit session
        new_session = AuditSession(
            total_records=result.total_records,
            ghost_voters=result.ghost_voters_flagged,
            duplicate_voters=result.duplicate_voters_flagged,
            status='completed'
        )
        db.session.add(new_session)
        db.session.commit()
        print(f"   ✅ Audit session created")
        
        # Process ghosts
        ghost_count = 0
        for g in result.ghost_explanations:
            v_id = g.get('voter_id')
            if not v_id:
                continue
            
            voter = Voter.query.filter_by(voter_id=v_id).first()
            if not voter:
                voter = Voter(voter_id=v_id)
            
            details = g.get('voter_details', {})
            voter.name = details.get('name', 'Unknown')
            
            # Convert age
            age_val = details.get('Age')
            try:
                voter.age = int(float(str(age_val))) if age_val else None
            except:
                voter.age = None
            
            voter.gender = details.get('Gender')
            voter.address = details.get('Address')
            voter.pincode = details.get('Pincode')
            voter.risk_score = g.get('confidence', 0)
            voter.risk_type = 'Ghost'
            voter.risk_confidence = g.get('confidence', 0)
            voter.reasons = json.dumps(g.get('contributing_factors', []))
            voter.is_flagged = True
            voter.review_status = 'pending'
            
            db.session.add(voter)
            ghost_count += 1
            
            if ghost_count % 100 == 0:
                print(f"   Processed {ghost_count} ghosts...")
        
        print(f"   ✅ Processed {ghost_count} ghost voters")
        
        # Process duplicates
        dup_count = 0
        for dup in result.duplicate_explanations:
            v_id = dup.get('voter_id')
            if not v_id:
                continue
            
            voter = Voter.query.filter_by(voter_id=v_id).first()
            if not voter:
                voter = Voter(voter_id=v_id)
            
            details = dup.get('voter_details', {})
            voter.name = details.get('name', 'Unknown')
            
            # Convert age
            age_val = details.get('Age')
            try:
                voter.age = int(float(str(age_val))) if age_val else None
            except:
                voter.age = None
            
            voter.gender = details.get('Gender')
            voter.address = details.get('Address')
            voter.pincode = details.get('Pincode')
            voter.risk_score = dup.get('confidence', 0)
            voter.risk_type = 'Duplicate'
            voter.risk_confidence = dup.get('confidence', 0)
            voter.reasons = json.dumps(dup.get('contributing_factors', []))
            voter.is_flagged = True
            voter.review_status = 'pending'
            
            db.session.add(voter)
            dup_count += 1
            
            if dup_count % 100 == 0:
                print(f"   Processed {dup_count} duplicates...")
        
        print(f"   ✅ Processed {dup_count} duplicate voters")
        
        # Commit all changes
        print(f"\n💾 Committing to database...")
        db.session.commit()
        print(f"   ✅ Commit successful!")
        
        # Verify
        flagged_count = Voter.query.filter_by(is_flagged=True).count()
        ghost_db_count = Voter.query.filter_by(risk_type='Ghost').count()
        dup_db_count = Voter.query.filter_by(risk_type='Duplicate').count()
        
        print(f"\n✅ DATABASE VERIFICATION:")
        print(f"   Total flagged: {flagged_count}")
        print(f"   Ghosts: {ghost_db_count}")
        print(f"   Duplicates: {dup_db_count}")
        
        if flagged_count > 0:
            print(f"\n🎉 SUCCESS! Flagged voters are now in the database.")
            print(f"   Now go to http://localhost:5174 and view the 'View Records' page")
        else:
            print(f"\n❌ ERROR: No flagged voters in database after commit!")
        
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
