"""
VoteGuard Flask Application
Main application file with route definitions
"""

import os
import sys
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import json
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.pipeline import VoteGuardPipeline
from models import db, Voter, AuditSession
from dotenv import load_dotenv

load_dotenv()


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__, static_folder='../frontend')
    CORS(app)  # Enable CORS for frontend
    
    # Database configuration
    db_url = os.getenv('DATABASE_URL')
    if not db_url or "your_supabase" in db_url:
        print("⚠️ Warning: No Supabase URL found. Falling back to local SQLite.")
        db_url = "sqlite:///voteguard_local.db"
        
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    # Create tables
    with app.app_context():
        try:
            # FORCE RECREATE (Fixes the UndefinedColumn error by syncing schema)
            # db.drop_all() 
            db.create_all()
            print("✅ Database tables initialized!")
        except Exception as e:
            print(f"❌ Database error: {str(e)}")
    
    # Legacy state (will migrate away from these)
    app.pipeline = None
    app.detection_result = None
    app.audit_log = []
    
    # ========================
    # API Routes
    # ========================
    
    @app.route('/api/login', methods=['POST'])
    def login():
        """Backend authentication for Admin Auditor"""
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # In a real system, these would be checked against a database with hashed passwords
        # and secrets would be in environment variables
        if username == 'admin' and password == 'admin123':
            # SIMULATED TOKEN: In production, we use JWT or secure sessions
            token = "vg_session_" + datetime.now().strftime('%Y%H%M%S')
            
            app.audit_log.append({
                'action': 'LOGIN',
                'user': username,
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            })
            
            return jsonify({
                'status': 'success',
                'user': {
                    'name': 'Admin Auditor',
                    'role': 'Super User',
                    'initials': 'AD'
                },
                'token': token
            })
        
        return jsonify({
            'status': 'error',
            'message': 'Invalid credentials'
        }), 401

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        })
    
    @app.route('/api/analyze', methods=['POST'])
    def analyze_data():
        """
        Run the detection pipeline on voter data.
        
        Request body (optional):
            {
                "data_path": "path/to/voter_data.csv"
            }
        """
        try:
            # Get data path from request or use default
            data = request.get_json() or {}
            data_path = data.get('data_path', 'voter_data.csv')
            
            # Check if file exists
            if not os.path.exists(data_path):
                return jsonify({
                    'error': f'Data file not found: {data_path}',
                    'status': 'error'
                }), 404
            
            # Run the pipeline
            app.pipeline = VoteGuardPipeline()
            app.detection_result = app.pipeline.run(data_path)
            
            # DATABASE OPERATIONS
            # 1. Clear old records as requested (Clean Slate approach)
            Voter.query.delete()
            
            # 2. Record this audit session
            session = AuditSession(
                total_records=app.detection_result.total_records,
                ghost_count=app.detection_result.ghost_voters_flagged,
                duplicate_count=app.detection_result.duplicate_voters_flagged,
                status='completed'
            )
            db.session.add(session)
            
            # 3. Save ONLY flagged voters
            # Collect all ghost voter IDs
            ghost_map = {str(r['voter_id']): r for r in app.detection_result.ghost_explanations}
            # Collect all duplicate voter IDs
            dupe_map = {str(r['voter_id']): r for r in app.detection_result.duplicate_explanations}
            
            flagged_voter_ids = set(ghost_map.keys()) | set(dupe_map.keys())
            
            # Get full details from dataframe for these IDs
            df = app.pipeline.df
            for vid in flagged_voter_ids:
                row = df[df['Voter_ID'] == vid].iloc[0]
                
                # Determine risk type
                is_ghost = vid in ghost_map
                is_dupe = vid in dupe_map
                
                r_type = 'None'
                if is_ghost and is_dupe: r_type = 'Both'
                elif is_ghost: r_type = 'Ghost'
                elif is_dupe: r_type = 'Duplicate'
                
                # Calculate confidence and reasons
                confidence = 0.0
                primary_reason = ""
                all_factors = []
                
                if is_ghost:
                    g_data = ghost_map[vid]
                    confidence = max(confidence, g_data.get('confidence', 0))
                    primary_reason = g_data.get('primary_reason', "Ghost voter risk detected")
                    all_factors.extend(g_data.get('contributing_factors', []))

                if is_dupe:
                    d_data = dupe_map[vid]
                    confidence = max(confidence, d_data.get('confidence', 0))
                    if not primary_reason:
                        primary_reason = d_data.get('primary_reason', "Duplicate registration risk")
                    elif is_ghost:
                        primary_reason = "Multiple risks: Ghost & Duplicate detected"
                    
                    all_factors.extend(d_data.get('contributing_factors', []))

                voter = Voter(
                    voter_id=vid,
                    name=f"{str(row.get('First_Name', ''))} {str(row.get('Last_Name', ''))}".strip(),
                    age=0, # Calculate from DOB if needed
                    gender=str(row.get('Gender', 'Unknown')),
                    address=str(row.get('Address', 'Unknown')),
                    pincode=str(row.get('Pincode', '')),
                    risk_score=confidence * 100,
                    risk_type=r_type,
                    risk_confidence=confidence,
                    primary_reason=primary_reason,
                    contributing_factors=json.dumps(all_factors)
                )
                db.session.add(voter)
            
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Analysis complete and records saved to Supabase',
                'summary': app.detection_result.summary_report
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'error': str(e),
                'status': 'error'
            }), 500
    
    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        """
        Upload a CSV file for analysis.
        Returns the filename to use with /api/analyze
        """
        if 'file' not in request.files:
            return jsonify({
                'error': 'No file provided',
                'status': 'error'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'error': 'No file selected',
                'status': 'error'
            }), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({
                'error': 'Only CSV files are supported',
                'status': 'error'
            }), 400
        
        # Save to uploads directory
        uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Generate safe filename with timestamp
        from werkzeug.utils import secure_filename
        safe_name = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{safe_name}"
        filepath = os.path.join(uploads_dir, filename)
        
        file.save(filepath)
        
        # Log the upload
        app.audit_log.append({
            'action': 'UPLOAD',
            'timestamp': datetime.now().isoformat(),
            'filename': filename,
            'original_name': file.filename
        })
        
        return jsonify({
            'status': 'success',
            'message': 'File uploaded successfully',
            'filename': filename,
            'filepath': filepath
        })
    
    @app.route('/api/stats', methods=['GET'])
    def get_stats():
        """Get detection statistics from database"""
        try:
            # Get the latest audit session
            latest_session = AuditSession.query.order_by(AuditSession.timestamp.desc()).first()
            
            if not latest_session:
                return jsonify({
                    'error': 'No analysis has been run yet',
                    'status': 'pending'
                }), 200 # Return 200 with status pending for frontend
                
            # Aggregate risk by region from current flagged voters
            voters = Voter.query.filter_by(is_archived=False).all()
            risk_by_region = {}
            
            for v in voters:
                # Try to extract state/region from address
                parts = [p.strip() for p in (v.address or '').split(',')]
                region = parts[-1] if parts else 'Unknown'
                
                if region not in risk_by_region:
                    risk_by_region[region] = {'ghost': 0, 'duplicate': 0, 'total': 0}
                
                if v.risk_type in ['Ghost', 'Both']: risk_by_region[region]['ghost'] += 1
                if v.risk_type in ['Duplicate', 'Both']: risk_by_region[region]['duplicate'] += 1
                risk_by_region[region]['total'] += 1
                
            region_stats = []
            for region, counts in risk_by_region.items():
                region_stats.append({
                    'region': region,
                    'ghost': counts['ghost'],
                    'duplicate': counts['duplicate'],
                    'total': counts['total']
                })
            region_stats.sort(key=lambda x: x['total'], reverse=True)
            
            # Count flagged as both (High Risk)
            flagged_as_both = Voter.query.filter_by(risk_type='Both', is_archived=False).count()
            
            # Count current active flagged records
            ghost_voters_flagged = Voter.query.filter(Voter.risk_type.in_(['Ghost', 'Both']), Voter.is_archived == False).count()
            duplicate_voters_flagged = Voter.query.filter(Voter.risk_type.in_(['Duplicate', 'Both']), Voter.is_archived == False).count()
            
            return jsonify({
                'status': 'success',
                'timestamp': latest_session.timestamp.isoformat() if latest_session.timestamp else datetime.now().isoformat(),
                'total_records': latest_session.total_records,
                'ghost_voters_flagged': ghost_voters_flagged,
                'duplicate_voters_flagged': duplicate_voters_flagged,
                'summary': {
                    'summary': {
                        'flagged_as_both': flagged_as_both
                    }
                },
                'risk_by_region': region_stats,
                'reviews_completed': Voter.query.filter(Voter.review_status != 'pending').count()
            })
        except Exception as e:
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/flagged', methods=['GET'])
    def get_flagged_records():
        """Get flagged records from database"""
        try:
            flag_type = request.args.get('type', 'all').capitalize()
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
            
            query = Voter.query.filter_by(is_archived=False)
            
            if flag_type != 'All':
                if flag_type == 'Ghost':
                    query = query.filter(Voter.risk_type.in_(['Ghost', 'Both']))
                elif flag_type == 'Duplicate':
                    query = query.filter(Voter.risk_type.in_(['Duplicate', 'Both']))
            
            total = query.count()
            voters = query.order_by(Voter.risk_confidence.desc()).offset(offset).limit(limit).all()
            
            return jsonify({
                'status': 'success',
                'total': total,
                'records': [v.to_dict() for v in voters]
            })
        except Exception as e:
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/record/<voter_id>', methods=['GET'])
    def get_record_detail(voter_id: str):
        """Get detailed information for a specific voter record from database"""
        try:
            voter = Voter.query.filter_by(voter_id=voter_id).first()
            if not voter:
                return jsonify({
                    'error': f'Record not found: {voter_id}',
                    'status': 'not_found'
                }), 404
            
            return jsonify({
                'status': 'success',
                'record': voter.to_dict()
            })
        except Exception as e:
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/review/<voter_id>', methods=['POST'])
    def submit_review(voter_id: str):
        """Submit a human review decision for a flagged record in database"""
        try:
            data = request.get_json()
            decision = data.get('decision')
            if decision not in ['confirm', 'dismiss', 'escalate']:
                return jsonify({'error': 'Invalid decision', 'status': 'error'}), 400
            
            voter = Voter.query.filter_by(voter_id=voter_id).first()
            if not voter:
                return jsonify({'error': 'Record not found', 'status': 'error'}), 404
                
            voter.review_status = decision
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': f'Review submitted for {voter_id}',
                'review': voter.to_dict()
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/delete', methods=['POST'])
    def delete_records():
        """Move records to history (soft delete) in database"""
        try:
            data = request.get_json()
            voter_ids = data.get('voter_ids', [])
            decision = data.get('decision', 'pending') # 'approved', 'deleted', or 'pending'
            
            if not voter_ids:
                return jsonify({'error': 'No voter IDs provided', 'status': 'error'}), 400
                
            voters = Voter.query.filter(Voter.voter_id.in_(voter_ids)).all()
            for v in voters:
                v.is_archived = True
                v.archive_status = decision
                v.archived_at = datetime.utcnow()
                
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': f'Successfully {decision} {len(voters)} records',
                'count': len(voters)
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e), 'status': 'error'}), 500

    @app.route('/api/history', methods=['GET'])
    def get_history():
        """Get all deleted/archived records from database"""
        try:
            voters = Voter.query.filter_by(is_archived=True).order_by(Voter.archived_at.desc()).all()
            return jsonify({
                'status': 'success',
                'total': len(voters),
                'records': [v.to_dict() for v in voters]
            })
        except Exception as e:
            return jsonify({'error': str(e), 'status': 'error'}), 500

    @app.route('/api/audit-log', methods=['GET'])
    def get_audit_log():
        """Get the audit log of all actions"""
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        total = len(app.audit_log)
        logs = app.audit_log[offset:offset + limit]
        
        return jsonify({
            'status': 'success',
            'total': total,
            'limit': limit,
            'offset': offset,
            'logs': logs
        })
    
        return jsonify({
            'status': 'success',
            'data': app.detection_result.to_dict()
        })
    
    @app.route('/api/export/csv', methods=['GET'])
    def export_csv():
        """Export flagged dataset as CSV from database"""
        try:
            scope = request.args.get('scope', 'audit') # 'audit' or 'history'
            
            if scope == 'history':
                voters = Voter.query.filter_by(is_archived=True).all()
                filename = "voteguard_history_archive.csv"
            else:
                voters = Voter.query.filter_by(is_archived=False).all()
                filename = "voteguard_audit_report.csv"
                
            if not voters:
                return jsonify({'error': 'No records found to export', 'status': 'error'}), 400
                
            # Create CSV
            import csv
            from io import StringIO
            output = StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow(['Voter_ID', 'Name', 'Risk_Type', 'Confidence', 'Status', 'Address'])
            
            for v in voters:
                writer.writerow([
                    v.voter_id,
                    v.name,
                    v.risk_type,
                    v.risk_confidence,
                    v.review_status,
                    v.address
                ])
                
            from flask import make_response
            response = make_response(output.getvalue())
            response.headers["Content-Disposition"] = f"attachment; filename={filename}"
            response.headers["Content-type"] = "text/csv"
            return response
        except Exception as e:
            return jsonify({'error': str(e), 'status': 'error'}), 500

        # Apply using result_type='expand' for multiple columns or just assign separately
    
    # ========================
    # Static File Serving
    # ========================
    
    @app.route('/')
    def serve_frontend():
        """Serve the frontend index.html"""
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        """Serve static files"""
        return send_from_directory(app.static_folder, path)
    
    return app


# Create the app instance
app = create_app()


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("VoteGuard API Server")
    print("=" * 60)
    print("\nStarting server on http://localhost:5000")
    print("API Documentation:")
    print("   * GET  /api/health     - Health check")
    print("   * POST /api/analyze    - Run detection pipeline")
    print("   * GET  /api/stats      - Get statistics")
    print("   * GET  /api/flagged    - Get flagged records")
    print("   * GET  /api/record/<id> - Get record details")
    print("   * POST /api/review/<id> - Submit review decision")
    print("   * GET  /api/audit-log  - Get audit log")
    print("   * GET  /api/export     - Export results")
    print("\n" + "=" * 60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
