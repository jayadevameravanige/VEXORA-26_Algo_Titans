"""
Check if voter IDs from analysis match voter IDs in database
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))
load_dotenv('api/.env')

from ml.pipeline import VoteGuardPipeline

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

# Run quick analysis
print("Running quick analysis...")
pipeline = VoteGuardPipeline()
result = pipeline.run(r"e:\VEXORA-26_Algo_Titans\smoketest_data.csv")

print(f"\nAnalysis found:")
print(f"  Ghosts: {len(result.ghost_explanations)}")
print(f"  Duplicates: {len(result.duplicate_explanations)}")

if result.ghost_explanations:
    print(f"\nSample ghost voter IDs from analysis:")
    for g in result.ghost_explanations[:3]:
        print(f"  - {g.get('voter_id')} (type: {type(g.get('voter_id'))})")

# Check database
with engine.connect() as conn:
    # Get sample voter IDs from database
    result_db = conn.execute(text("SELECT voter_id FROM voters LIMIT 5"))
    print(f"\nSample voter IDs from database:")
    for row in result_db:
        print(f"  - {row[0]} (type: {type(row[0])})")
    
    # Try to match first ghost
    if result.ghost_explanations:
        test_id = str(result.ghost_explanations[0].get('voter_id'))
        print(f"\nTesting UPDATE for voter_id: {test_id}")
        
        # Check if it exists
        check = conn.execute(text("SELECT voter_id, name, is_flagged FROM voters WHERE voter_id = :vid"), {'vid': test_id})
        row = check.fetchone()
        if row:
            print(f"  EXISTS in DB: voter_id={row[0]}, name={row[1]}, is_flagged={row[2]}")
        else:
            print(f"  NOT FOUND in database!")
            
            # Try exact match
            check2 = conn.execute(text("SELECT COUNT(*) FROM voters"))
            total = check2.scalar()
            print(f"  Total voters in DB: {total}")
