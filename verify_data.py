"""Quick verification script for voter_data.csv"""
import csv
from datetime import datetime

with open('voter_data.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print("=" * 60)
print("Voter Dataset Verification")
print("=" * 60)
print(f"\nTotal Records: {len(rows)}")

# Count ghosts (age > 110)
ghosts = []
for r in rows:
    dob = datetime.strptime(r['DOB'], '%d-%m-%Y')
    age = (datetime.now() - dob).days // 365
    if age > 110:
        ghosts.append((r, age))

print(f"Ghost Records (age > 110): {len(ghosts)}")

# Show sample records
print("\n" + "-" * 60)
print("Sample Normal Records:")
print("-" * 60)
for i, r in enumerate(rows[:3]):
    print(f"\nRecord {i+1}:")
    print(f"  Name: {r['Name']}")
    print(f"  DOB: {r['DOB']}")
    print(f"  Address: {r['Address'][:50]}...")
    print(f"  Pincode: {r['Pincode']}")
    print(f"  VoterID: {r['VoterID']}")

print("\n" + "-" * 60)
print("Sample Ghost Records (age > 110):")
print("-" * 60)
for r, age in ghosts[:3]:
    print(f"\n  Name: {r['Name']}")
    print(f"  DOB: {r['DOB']} (Age: {age} years)")
    print(f"  VoterID: {r['VoterID']}")

print("\n" + "=" * 60)
print("Verification Complete!")
print("=" * 60)
