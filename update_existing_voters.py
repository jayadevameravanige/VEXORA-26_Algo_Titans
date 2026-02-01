"""
Update existing voter records in the database to mark them as flagged
"""
import os
import sys
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))
load_dotenv('api/.env')

from ml.pipeline import VoteGuardPipeline

print("🚀 Running analysis to get flagged voters...")
print("=" * 60)

# Run the pipeline
pipeline = VoteGuardPipeline()
result = pipeline.run(r"e:\VEXORA-26_Algo_Titans\voter_data.csv")

print(f"\n✅ Analysis complete!")
print(f"   Ghosts: {result.ghost_voters_flagged}")
print(f"   Duplicates: {result.duplicate_voters_flagged}")

# Connect to database
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

print(f"\n💾 Updating existing voter records in database...")

with engine.begin() as conn:  # Use begin() for auto-commit
    # First, reset all flags
    print(f"   Resetting all voter flags...")
    conn.execute(text("""
        UPDATE voters 
        SET is_flagged = false, 
            risk_type = NULL, 
            risk_score = 0.0, 
            risk_confidence = 0.0,
            review_status = 'pending'
    """))
    
    # Update ghosts
    ghost_count = 0
    print(f"   Updating {len(result.ghost_explanations)} ghost voters...")
    for g in result.ghost_explanations:
        v_id = g.get('voter_id')
        if not v_id:
            continue
        
        confidence = g.get('confidence', 0)
        reasons_json = json.dumps(g.get('contributing_factors', []))
        
        conn.execute(text("""
            UPDATE voters 
            SET is_flagged = true,
                risk_type = 'Ghost',
                risk_score = :confidence,
                risk_confidence = :confidence,
                reasons = :reasons,
                review_status = 'pending'
            WHERE voter_id = :voter_id
        """), {
            'voter_id': str(v_id),
            'confidence': confidence,
            'reasons': reasons_json
        })
        ghost_count += 1
        
        if ghost_count % 500 == 0:
            print(f"      Processed {ghost_count} ghosts...")
    
    print(f"   ✅ Updated {ghost_count} ghost voters")
    
    # Update duplicates
    dup_count = 0
    print(f"   Updating {len(result.duplicate_explanations)} duplicate voters...")
    for dup in result.duplicate_explanations:
        v_id = dup.get('voter_id')
        if not v_id:
            continue
        
        confidence = dup.get('confidence', 0)
        reasons_json = json.dumps(dup.get('contributing_factors', []))
        
        conn.execute(text("""
            UPDATE voters 
            SET is_flagged = true,
                risk_type = 'Duplicate',
                risk_score = :confidence,
                risk_confidence = :confidence,
                reasons = :reasons,
                review_status = 'pending'
            WHERE voter_id = :voter_id
        """), {
            'voter_id': str(v_id),
            'confidence': confidence,
            'reasons': reasons_json
        })
        dup_count += 1
        
        if dup_count % 500 == 0:
            print(f"      Processed {dup_count} duplicates...")
    
    print(f"   ✅ Updated {dup_count} duplicate voters")

# Verify
print(f"\n🔍 Verifying database...")
with engine.connect() as conn:
    result_check = conn.execute(text("SELECT COUNT(*) FROM voters WHERE is_flagged = true"))
    flagged_count = result_check.scalar()
    
    result_ghosts = conn.execute(text("SELECT COUNT(*) FROM voters WHERE risk_type = 'Ghost'"))
    ghost_db_count = result_ghosts.scalar()
    
    result_dups = conn.execute(text("SELECT COUNT(*) FROM voters WHERE risk_type = 'Duplicate'"))
    dup_db_count = result_dups.scalar()
    
    print(f"   Total flagged: {flagged_count}")
    print(f"   Ghosts: {ghost_db_count}")
    print(f"   Duplicates: {dup_db_count}")
    
    if flagged_count > 0:
        print(f"\n🎉 SUCCESS! Database updated successfully!")
        print(f"\n✅ Now refresh your browser at http://localhost:5174")
        print(f"   Go to 'View Records' page and you should see all flagged voters!")
    else:
        print(f"\n❌ ERROR: Update failed!")
