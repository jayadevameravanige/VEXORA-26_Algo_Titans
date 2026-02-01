"""
Simple database check using raw SQL
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv('api/.env')

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

print("\n🔍 Checking Database...")

with engine.connect() as conn:
    # Check if voters table exists and count records
    try:
        result = conn.execute(text("SELECT COUNT(*) FROM voters"))
        count = result.scalar()
        print(f"✅ Total records in voters table: {count}")
    except Exception as e:
        print(f"❌ Error querying voters table: {e}")
    
    # Check flagged voters
    try:
        result = conn.execute(text("SELECT COUNT(*) FROM voters WHERE is_flagged = true"))
        count = result.scalar()
        print(f"🚩 Flagged voters: {count}")
    except Exception as e:
        print(f"❌ Error querying flagged voters: {e}")
    
    # Check by risk type
    try:
        result = conn.execute(text("SELECT risk_type, COUNT(*) FROM voters WHERE risk_type IS NOT NULL GROUP BY risk_type"))
        print(f"\n📊 Voters by Risk Type:")
        for row in result:
            print(f"  - {row[0]}: {row[1]}")
    except Exception as e:
        print(f"❌ Error querying by risk type: {e}")
    
    # Sample flagged records
    try:
        result = conn.execute(text("SELECT voter_id, name, risk_type, risk_confidence, review_status FROM voters WHERE is_flagged = true LIMIT 5"))
        print(f"\n🔍 Sample Flagged Records:")
        for row in result:
            print(f"  - {row[0]}: {row[1]}, Type: {row[2]}, Conf: {row[3]}, Status: {row[4]}")
    except Exception as e:
        print(f"❌ Error querying sample records: {e}")

print("\n✅ Done!")
