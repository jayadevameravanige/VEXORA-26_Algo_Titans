"""
Clear the voters table in Supabase
This removes all pre-loaded voter data while keeping users and audit sessions
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))
load_dotenv('api/.env')

from api.models import db, Voter, User, AuditSession
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    print("🗑️  Clearing Supabase Database...")
    print("=" * 60)
    
    # Check what we have
    voter_count = Voter.query.count()
    user_count = User.query.count()
    session_count = AuditSession.query.count()
    
    print(f"\n📊 Current Database State:")
    print(f"   Voters: {voter_count}")
    print(f"   Users: {user_count}")
    print(f"   Audit Sessions: {session_count}")
    
    if voter_count == 0:
        print(f"\n✅ Voters table is already empty! Nothing to delete.")
    else:
        print(f"\n⚠️  About to delete {voter_count} voter records...")
        print(f"   (Users and Audit Sessions will be preserved)")
        
        confirm = input("\nType 'DELETE' to confirm: ")
        
        if confirm == 'DELETE':
            Voter.query.delete()
            db.session.commit()
            
            # Verify
            remaining = Voter.query.count()
            print(f"\n✅ Deleted! Remaining voter records: {remaining}")
            
            if remaining == 0:
                print(f"\n🎉 SUCCESS! Voters table is now clean.")
                print(f"\n📝 What's preserved:")
                print(f"   ✓ Users: {User.query.count()}")
                print(f"   ✓ Audit Sessions: {AuditSession.query.count()}")
                
                print(f"\n🚀 Next Steps:")
                print(f"   1. Go to http://localhost:5174")
                print(f"   2. Login (admin / admin123)")
                print(f"   3. Upload your CSV file")
                print(f"   4. System will analyze and save ONLY flagged voters")
            else:
                print(f"⚠️  Warning: {remaining} records still remain")
        else:
            print(f"\n❌ Deletion cancelled. Type 'DELETE' (all caps) to confirm.")
    
    print("\n" + "=" * 60)
