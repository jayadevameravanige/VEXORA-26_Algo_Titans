import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL')

print(f"Connecting to: {url.split('@')[-1]}")

try:
    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()
    
    print("Dropping tables using raw SQL...")
    cur.execute("DROP TABLE IF EXISTS voters CASCADE;")
    cur.execute("DROP TABLE IF EXISTS audit_sessions CASCADE;")
    
    print("Tables dropped.")
    cur.close()
    conn.close()
    
    # Now use SQLAlchemy to recreate them
    print("Recreating tables using SQLAlchemy...")
    from app import create_app
    from models import db
    
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Tables recreated successfully!")
        
except Exception as e:
    print(f"Error: {e}")
