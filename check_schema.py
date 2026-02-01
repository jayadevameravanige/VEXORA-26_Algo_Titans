"""
Check exact database schema from Supabase
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

load_dotenv('api/.env')

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

print("\n🔍 Checking 'voters' table schema in Supabase...")
print("=" * 60)

inspector = inspect(engine)

# Get column info
columns = inspector.get_columns('voters')

print(f"\n📋 Columns in 'voters' table:")
for col in columns:
    nullable = "NULL" if col['nullable'] else "NOT NULL"
    default = f" DEFAULT {col['default']}" if col['default'] else ""
    print(f"  - {col['name']}: {col['type']} {nullable}{default}")

print(f"\n✅ Total columns: {len(columns)}")
