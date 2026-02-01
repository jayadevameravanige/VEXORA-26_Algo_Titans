import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    
    # Check columns of voters table
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'voters';
    """)
    columns = cur.fetchall()
    print("Columns in 'voters' table:")
    for col in columns:
        print(f" - {col[0]}")
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
