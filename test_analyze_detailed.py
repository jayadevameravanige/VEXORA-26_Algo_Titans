"""
Trigger analysis and watch the backend logs
"""
import requests
import json
import time

url = "http://localhost:5000/api/analyze"
payload = {"data_path": r"e:\VEXORA-26_Algo_Titans\voter_data.csv"}

print("🚀 Triggering analysis...")
print("Watch the backend terminal for DTO-DEBUG messages")
print("=" * 60)

try:
    response = requests.post(url, json=payload, timeout=300)
    print(f"\n✅ Response received!")
    print(f"Status Code: {response.status_code}")
    print(f"Content Type: {response.headers.get('content-type')}")
    print(f"\nRaw Response:")
    print(response.text[:1000])  # First 1000 chars
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"\n📊 Success!")
            print(json.dumps(data, indent=2))
        except:
            print(f"Response is not JSON")
    
    # Wait a bit then check database
    print("\n⏳ Waiting 3 seconds...")
    time.sleep(3)
    
    # Check database
    print("\n🔍 Checking database...")
    import os
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text
    
    load_dotenv('api/.env')
    DATABASE_URL = os.getenv('DATABASE_URL')
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM voters WHERE is_flagged = true"))
        count = result.scalar()
        print(f"✅ Flagged voters in DB: {count}")
        
        if count > 0:
            result = conn.execute(text("SELECT voter_id, name, risk_type, risk_confidence FROM voters WHERE is_flagged = true LIMIT 3"))
            print(f"\n📋 Sample flagged records:")
            for row in result:
                print(f"  - {row[0]}: {row[1]}, Type: {row[2]}, Conf: {row[3]}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
