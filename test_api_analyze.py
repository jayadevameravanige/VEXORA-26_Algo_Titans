"""
Test the /api/analyze endpoint directly
"""
import requests
import json

# Run analysis on the voter data
print("🔍 Testing /api/analyze endpoint...")
print("=" * 60)

url = "http://localhost:5000/api/analyze"
payload = {"data_path": r"e:\VEXORA-26_Algo_Titans\voter_data.csv"}

print(f"\n📤 POST {url}")
print(f"📦 Payload: {payload}")

try:
    response = requests.post(url, json=payload, timeout=300)
    
    print(f"\n✅ Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n📊 Response:")
        print(json.dumps(result, indent=2))
        
        # Now check the /api/flagged endpoint
        print("\n" + "=" * 60)
        print("🔍 Testing /api/flagged endpoint...")
        flagged_url = "http://localhost:5000/api/flagged"
        flagged_response = requests.get(flagged_url)
        
        print(f"\n✅ Status Code: {flagged_response.status_code}")
        flagged_data = flagged_response.json()
        print(f"\n📊 Flagged Records Response:")
        print(f"  Total: {flagged_data.get('total', 0)}")
        print(f"  Records returned: {len(flagged_data.get('records', []))}")
        
        if flagged_data.get('records'):
            print(f"\n  Sample record:")
            print(json.dumps(flagged_data['records'][0], indent=4))
    else:
        print(f"❌ Error: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
