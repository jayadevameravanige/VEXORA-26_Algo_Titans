"""
Simple test to see if UPDATE actually works
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv('api/.env')
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

print("Testing database UPDATE...")

with engine.begin() as conn:
    # Get first voter
    result = conn.execute(text("SELECT voter_id, is_flagged FROM voters LIMIT 1"))
    row = result.fetchone()
    test_id = row[0]
    current_flagged = row[1]
    
    print(f"\nBefore UPDATE:")
    print(f"  voter_id: {test_id}")
    print(f"  is_flagged: {current_flagged}")
    
    # Try  to UPDATE
    print(f"\nExecuting UPDATE...")
    conn.execute(text("""
        UPDATE voters 
        SET is_flagged = true,
            risk_type = 'Ghost',
            risk_confidence = 0.95
        WHERE voter_id = :vid
    """), {'vid': test_id})
    
print(f"\n✅ UPDATE executed (transaction committed)")

# Verify in new connection
print(f"\nVerifying...")
with engine.connect() as conn:
    result = conn.execute(text("SELECT voter_id, is_flagged, risk_type, risk_confidence FROM voters WHERE voter_id = :vid"), {'vid': test_id})
    row = result.fetchone()
    
    print(f"\nAfter UPDATE:")
    print(f"  voter_id: {row[0]}")
    print(f"  is_flagged: {row[1]}")
    print(f"  risk_type: {row[2]}")
    print(f"  risk_confidence: {row[3]}")
    
    if row[1] == True:
        print(f"\n✅ SUCCESS! UPDATE worked!")
    else:
        print(f"\n❌ FAILED! is_flagged is still False")
