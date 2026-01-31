"""
Indian Voter Dataset Generator
Generates 10,000 synthetic Indian voter records with:
- 5% duplicate records (slight name variations)
- 5% ghost records (age > 110 years)

Fields: Voter_ID, First_Name, Last_Name, DOB, Gender, Address, Pincode, 
        Registration_Year, Last_Voted_Year, Masked_Aadhaar
"""

import csv
import random
import string
from datetime import datetime, timedelta
from faker import Faker

# Initialize Faker with Indian locale
fake = Faker('en_IN')
Faker.seed(42)  # For reproducibility
random.seed(42)

# Configuration
TOTAL_RECORDS = 10000
DUPLICATE_PERCENTAGE = 0.05  # 5% duplicates
GHOST_PERCENTAGE = 0.05      # 5% ghost records

# Calculate counts
NUM_DUPLICATES = int(TOTAL_RECORDS * DUPLICATE_PERCENTAGE)
NUM_GHOSTS = int(TOTAL_RECORDS * GHOST_PERCENTAGE)
NUM_NORMAL = TOTAL_RECORDS - NUM_DUPLICATES - NUM_GHOSTS

# Last 6 Indian General Election Years
ELECTION_YEARS = [2024, 2019, 2014, 2009, 2004, 1999]

def generate_voter_id():
    """Generate a unique 10-character Voter ID (EPIC number format)"""
    state_code = random.choice(['DL', 'MH', 'KA', 'TN', 'UP', 'GJ', 'RJ', 'WB', 'MP', 'AP', 'KL', 'HR', 'PB', 'BR', 'OR'])
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers = ''.join(random.choices(string.digits, k=7))
    return f"{state_code}{letters}{numbers}"

def generate_dob(min_age=18, max_age=90):
    """Generate a date of birth within the specified age range"""
    today = datetime.now()
    start_date = today - timedelta(days=max_age * 365)
    end_date = today - timedelta(days=min_age * 365)
    random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
    return random_date.strftime('%d-%m-%Y'), random_date.year

def generate_ghost_dob():
    """Generate a ghost record DOB (age > 110 years)"""
    today = datetime.now()
    min_age = 111
    max_age = 150
    start_date = today - timedelta(days=max_age * 365)
    end_date = today - timedelta(days=min_age * 365)
    random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
    return random_date.strftime('%d-%m-%Y'), random_date.year

def generate_address():
    """Generate a complete Indian address"""
    house_no = random.randint(1, 999)
    street = fake.street_name()
    area = fake.city_suffix() + " " + fake.last_name() + " Nagar"
    city = fake.city()
    state = fake.state()
    return f"{house_no}, {street}, {area}, {city}, {state}"

def generate_pincode():
    """Generate a valid Indian pincode (6 digits, starting with 1-9)"""
    first_digit = random.randint(1, 8)  # Indian pincodes start with 1-8
    remaining = ''.join(random.choices(string.digits, k=5))
    return f"{first_digit}{remaining}"

def generate_registration_year(birth_year, is_ghost=False):
    """Generate registration year (must be at least 18 years after birth, between 1949-2026)"""
    min_reg_year = max(1949, birth_year + 18)  # Must be 18+ to register
    max_reg_year = 2026
    
    if min_reg_year > max_reg_year:
        # For ghost records with very old birth years
        return random.randint(1949, 1980)
    
    return random.randint(min_reg_year, max_reg_year)

def generate_last_voted_year(registration_year):
    """Generate last voted year from the last 6 elections"""
    # Filter elections that happened after registration
    valid_elections = [year for year in ELECTION_YEARS if year >= registration_year]
    
    if not valid_elections:
        return "Never Voted"
    
    # 10% chance of never having voted
    if random.random() < 0.10:
        return "Never Voted"
    
    return random.choice(valid_elections)

def generate_masked_aadhaar():
    """Generate a masked Aadhaar number (XXXX-XXXX-1234 format)"""
    last_four = ''.join(random.choices(string.digits, k=4))
    return f"XXXX-XXXX-{last_four}"

def generate_gender():
    """Generate gender with realistic distribution"""
    # Approximate distribution: 48% Female, 51% Male, 1% Other
    rand = random.random()
    if rand < 0.48:
        return "Female"
    elif rand < 0.99:
        return "Male"
    else:
        return "Other"

def create_name_variation(first_name, last_name):
    """Create slight variations in name for duplicate records"""
    name_to_vary = random.choice(['first', 'last', 'both'])
    
    variations = [
        lambda n: n.replace('a', 'aa', 1) if 'a' in n else n + 'a',  # Double vowel
        lambda n: n.replace('i', 'ee', 1) if 'i' in n else n,  # Common spelling variation
        lambda n: n.replace('u', 'oo', 1) if 'u' in n else n,  # Common spelling variation
        lambda n: n.replace('sh', 's', 1) if 'sh' in n else n,  # Simplify
        lambda n: n.replace('th', 't', 1) if 'th' in n else n,  # Simplify
        lambda n: n[:-1] if len(n) > 3 else n,  # Missing last letter
        lambda n: n + n[-1] if len(n) > 2 else n,  # Double last letter
        lambda n: n.lower().title(),  # Case variation
    ]
    
    variation_func = random.choice(variations)
    
    if name_to_vary == 'first':
        return variation_func(first_name), last_name
    elif name_to_vary == 'last':
        return first_name, variation_func(last_name)
    else:
        return variation_func(first_name), variation_func(last_name)

def generate_voter_record(is_ghost=False):
    """Generate a single voter record"""
    # Generate name
    full_name = fake.name()
    name_parts = full_name.split()
    
    if len(name_parts) >= 2:
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:])
    else:
        first_name = name_parts[0]
        last_name = fake.last_name()
    
    # Generate DOB
    if is_ghost:
        dob, birth_year = generate_ghost_dob()
    else:
        dob, birth_year = generate_dob()
    
    # Generate registration and voting years
    registration_year = generate_registration_year(birth_year, is_ghost)
    last_voted_year = generate_last_voted_year(registration_year)
    
    return {
        'Voter_ID': generate_voter_id(),
        'First_Name': first_name,
        'Last_Name': last_name,
        'DOB': dob,
        'Gender': generate_gender(),
        'Address': generate_address(),
        'Pincode': generate_pincode(),
        'Registration_Year': registration_year,
        'Last_Voted_Year': last_voted_year,
        'Masked_Aadhaar': generate_masked_aadhaar()
    }

def generate_duplicate_record(original_record):
    """Generate a duplicate record with slight name variation"""
    duplicate = original_record.copy()
    
    # Create name variation
    new_first, new_last = create_name_variation(
        original_record['First_Name'], 
        original_record['Last_Name']
    )
    duplicate['First_Name'] = new_first
    duplicate['Last_Name'] = new_last
    
    # Generate new Voter ID (simulating fraudulent duplicate registration)
    duplicate['Voter_ID'] = generate_voter_id()
    
    # Generate new masked Aadhaar (different card)
    duplicate['Masked_Aadhaar'] = generate_masked_aadhaar()
    
    return duplicate

def main():
    """Main function to generate the dataset"""
    print("=" * 70)
    print("Indian Voter Dataset Generator")
    print("=" * 70)
    
    records = []
    used_voter_ids = set()
    
    # Generate normal records
    print(f"\n📊 Generating {NUM_NORMAL} normal voter records...")
    for i in range(NUM_NORMAL):
        record = generate_voter_record(is_ghost=False)
        # Ensure unique voter ID
        while record['Voter_ID'] in used_voter_ids:
            record['Voter_ID'] = generate_voter_id()
        used_voter_ids.add(record['Voter_ID'])
        records.append(record)
        
        if (i + 1) % 1000 == 0:
            print(f"   Generated {i + 1} normal records...")
    
    # Generate ghost records (age > 110)
    print(f"\n👻 Generating {NUM_GHOSTS} ghost records (age > 110)...")
    for i in range(NUM_GHOSTS):
        record = generate_voter_record(is_ghost=True)
        while record['Voter_ID'] in used_voter_ids:
            record['Voter_ID'] = generate_voter_id()
        used_voter_ids.add(record['Voter_ID'])
        records.append(record)
    
    # Generate duplicate records with name variations
    print(f"\n🔄 Generating {NUM_DUPLICATES} duplicate records with name variations...")
    # Select random records to duplicate
    records_to_duplicate = random.sample(records[:NUM_NORMAL], NUM_DUPLICATES)
    for original in records_to_duplicate:
        duplicate = generate_duplicate_record(original)
        while duplicate['Voter_ID'] in used_voter_ids:
            duplicate['Voter_ID'] = generate_voter_id()
        used_voter_ids.add(duplicate['Voter_ID'])
        records.append(duplicate)
    
    # Shuffle records to mix duplicates and ghosts throughout
    random.shuffle(records)
    
    # Save to CSV
    output_file = 'voter_data.csv'
    print(f"\n💾 Saving dataset to {output_file}...")
    
    fieldnames = [
        'Voter_ID', 'First_Name', 'Last_Name', 'DOB', 'Gender', 
        'Address', 'Pincode', 'Registration_Year', 'Last_Voted_Year', 'Masked_Aadhaar'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    
    # Print summary
    print("\n" + "=" * 70)
    print("✅ Dataset Generation Complete!")
    print("=" * 70)
    print(f"\n📈 Summary:")
    print(f"   • Total Records: {len(records)}")
    print(f"   • Normal Records: {NUM_NORMAL}")
    print(f"   • Ghost Records (age > 110): {NUM_GHOSTS} ({GHOST_PERCENTAGE*100}%)")
    print(f"   • Duplicate Records: {NUM_DUPLICATES} ({DUPLICATE_PERCENTAGE*100}%)")
    print(f"   • Output File: {output_file}")
    
    # Show sample records
    print(f"\n📋 Sample Records:")
    print("-" * 70)
    for i, record in enumerate(records[:3]):
        print(f"\nRecord {i+1}:")
        for key, value in record.items():
            print(f"   {key}: {value}")
    
    # Show a sample ghost record
    print(f"\n👻 Sample Ghost Record (age > 110):")
    print("-" * 70)
    for record in records:
        dob = datetime.strptime(record['DOB'], '%d-%m-%Y')
        age = (datetime.now() - dob).days // 365
        if age > 110:
            for key, value in record.items():
                print(f"   {key}: {value}")
            print(f"   Calculated Age: {age} years")
            break
    
    # Show election years info
    print(f"\n🗳️  Election Years Used for Last_Voted_Year:")
    print(f"   {ELECTION_YEARS}")
    
    print("\n" + "=" * 70)
    print("Done! Check 'voter_data.csv' for the generated dataset.")
    print("=" * 70)

if __name__ == "__main__":
    main()
