import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL')
print(f"Testing connection to: {url.split('@')[-1]}") # Hide password in logs

try:
    conn = psycopg2.connect(url)
    print("Success!")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
