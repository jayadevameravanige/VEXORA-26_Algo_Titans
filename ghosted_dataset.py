import pandas as pd
import random
from faker import Faker
from datetime import date, timedelta

# Initialize Faker
fake = Faker('en_IN')

records = []
today = date.today()

TOTAL_RECORDS = 15000
DUPLICATE_COUNT = 1500    # ~8% duplicates
GHOST_COUNT = 500          # ~3% ghost voters

base_records = []

# -------------------------------
# STEP 1: Generate BASE records
# -------------------------------
for i in range(1, TOTAL_RECORDS - DUPLICATE_COUNT - GHOST_COUNT + 1):
    gender = random.choice(["Male", "Female"])
    
    if gender == "Male":
        name = fake.name_male()
    elif gender == "Female":
        name = fake.name_female()
    
    dob = fake.date_of_birth(minimum_age=18, maximum_age=90)
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    
    record = {
        "voter_id": f"V{i:05d}",
        "name": name,
        "dob": dob,
        "age": age,
        "gender": gender,
        "address": fake.city(),
        "pincode": fake.postcode(),
        "id_number": f"XXXX-{random.randint(1000,9999)}",
        "registration_year": random.randint(1950, 2026),
        "last_voted_year": random.choice([1999, 2004, 2009, 2014, 2019, 2024, ])
    }
    
    base_records.append(record)

# -------------------------------
# STEP 2: Inject DUPLICATES
# -------------------------------
duplicate_records = []
for i in range(DUPLICATE_COUNT):
    original = random.choice(base_records)
    
    duplicate = original.copy()
    duplicate["voter_id"] = f"VD{10000+i}"
    
    # Small variations to simulate real duplicates
    duplicate["name"] = duplicate["name"].replace(" ", " ")[:random.randint(6, len(duplicate["name"]))]
    
    duplicate_records.append(duplicate)

# -------------------------------
# STEP 3: Inject GHOST VOTERS
# -------------------------------
ghost_records = []
for i in range(GHOST_COUNT):
    dob = today - timedelta(days=random.randint(115*365, 130*365))
    age = today.year - dob.year
    
    ghost = {
        "voter_id": f"VG{20000+i}",
        "name": fake.name(),
        "dob": dob,
        "age": age,
        "gender": random.choice(["Male", "Female"]),
        "address": fake.city(),
        "pincode": fake.postcode(),
        "id_number": f"XXXX-{random.randint(1000,9999)}",
        "registration_year": random.randint(1950, 1980),
        "last_voted_year": random.choice([None, 1999, 2004, 2009])
    }
    
    ghost_records.append(ghost)

# -------------------------------
# STEP 4: Combine All Records
# -------------------------------
all_records = base_records + duplicate_records + ghost_records
df = pd.DataFrame(all_records)

# Shuffle dataset
df = df.sample(frac=1).reset_index(drop=True)

# Save to CSV
file_path = "voterguard_15k(2)_test_dataset.csv"
df.to_csv(file_path, index=False)

print(f"Dataset saved to: {file_path}")