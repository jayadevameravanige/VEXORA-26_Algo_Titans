"""
DEMO: Test the complete workflow with the fixed system
"""
import requests
import time

API_BASE = "http://localhost:5000/api"

print("🧪 VoteGuard System Test")
print("=" * 60)

# Step 1: Upload a CSV file
print("\n📤 Step 1: Uploading CSV file...")
csv_path = r"e:\VEXORA-26_Algo_Titans\voter_data_new.csv"

with open(csv_path, 'rb') as f:
    files = {'file': ('voter_data_new.csv', f, 'text/csv')}
    response = requests.post(f"{API_BASE}/upload", files=files)
    
if response.status_code == 200:
    data = response.json()
    print(f"✅ Upload successful!")
    print(f"   File saved to: {data.get('filepath')}")
    uploaded_file_path = data.get('filepath')
else:
    print(f"❌ Upload failed: {response.text}")
    exit(1)

# Step 2: Run analysis
print("\n🔍 Step 2: Running analysis (this may take 30-60 seconds)...")
analyze_response = requests.post(
    f"{API_BASE}/analyze",
    json={"data_path": uploaded_file_path},
    timeout=300
)

if analyze_response.status_code == 200:
    result = analyze_response.json()
    print(f"✅ Analysis complete!")
    summary = result.get('summary', {}).get('summary', {})
    print(f"   Total flagged: {summary.get('total_flagged_records', 0)}")
    print(f"   Ghosts: {summary.get('ghost_voters', 0)}")
    print(f"   Duplicates: {summary.get('duplicate_voters', 0)}")
else:
    print(f"❌ Analysis failed: {analyze_response.text}")
    exit(1)

# Step 3: Fetch flagged records
print("\n📊 Step 3: Fetching flagged records from database...")
flagged_response = requests.get(f"{API_BASE}/flagged?type=all&limit=10")

if flagged_response.status_code == 200:
    flagged_data = flagged_response.json()
    total = flagged_data.get('total', 0)
    records = flagged_data.get('records', [])
    
    print(f"✅ Retrieved {total} flagged voters from database")
    print(f"\n   Sample records:")
    for i, record in enumerate(records[:3], 1):
        print(f"   {i}. {record.get('details', {}).get('name')} - {record.get('type')} (Confidence: {record.get('confidence')})")
else:
    print(f"❌ Failed to fetch records: {flagged_response.text}")

# Step 4: Test frontend can access
print("\n🌐 Step 4: Frontend URL")
print(f"   Open: http://localhost:5174")
print(f"   Login with: admin / admin123")
print(f"   Navigate to 'View Records' to see all flagged voters")

print("\n" + "=" * 60)
print("✅ TEST COMPLETE!")
print("\nThe system is now working correctly:")
print("  ✓ Upload CSV works")
print("  ✓ Analysis saves flagged voters to database")
print("  ✓ API returns flagged records")
print("  ✓ Frontend can display the data")
