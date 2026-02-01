# VoteGuard Architecture & Database Design

## 🏗️ System Architecture

### **Database Purpose (Supabase PostgreSQL)**

The Supabase database stores **ONLY** the following:

#### 1. **User Authentication** (Persistent)
- `users` table: Admin/Auditor accounts
- `login_sessions` table: Active user sessions with tokens

#### 2. **Audit Metadata** (Persistent)
- `audit_sessions` table: History of all analysis runs
  - Total records analyzed
  - Number of ghosts/duplicates found
  - Timestamp and status

#### 3. **Flagged Voters ONLY** (Cleared per analysis)
- `voters` table: **Only stores flagged/suspicious voters**
  - NOT all 15,000 voters!
  - Cleared before each new analysis
  - Populated with flagged voters from current analysis

---

## 📂 Data Flow

### **Upload & Analysis Workflow:**

```
1. User uploads CSV via frontend
   ↓
2. CSV saved to /uploads directory
   ↓
3. Backend runs ML pipeline on uploaded CSV
   ↓
4. Database operations:
   a) Clear old voter records (Voter.query.delete())
   b) Create new audit session entry
   c) Save ONLY flagged voters (ghosts + duplicates)
   ↓
5. Frontend fetches flagged voters via /api/flagged
   ↓
6. Display in "View Records" page
```

---

## 🗄️ Database Tables

### **users**
```sql
- id (PK)
- username (unique)
- password_hash
- role (Admin/Auditor)
- created_at
```

### **login_sessions**
```sql
- id (PK)
- user_id (FK)
- token (unique session token)
- created_at
- expires_at
- is_active
```

### **audit_sessions**
```sql
- id (PK)
- timestamp
- total_records (total voters analyzed)
- ghost_voters (number flagged as ghosts)
- duplicate_voters (number flagged as duplicates)
- status (completed/failed)
```

### **voters** (ONLY FLAGGED VOTERS!)
```sql
- id (PK)
- voter_id (from CSV)
- name
- age
- gender
- address
- pincode
- risk_score
- risk_type (Ghost/Duplicate)
- risk_confidence
- reasons (JSON of contributing factors)
- is_flagged (always TRUE for records in this table)
- review_status (pending/under_review/archived)
- last_updated
```

---

## 🔧 Key Design Decisions

### **Why NOT store all voters?**
❌ **Bad**: Store all 15,000 voters → Database grows huge → Query slow
✅ **Good**: Store only flagged voters (~3-5% of total) → Small, fast queries

### **Why clear voters on each analysis?**
- Each CSV upload is a NEW analysis session
- Old flagged voters from previous CSV are irrelevant
- Keeps database clean and current
- audit_sessions table preserves history

### **What happens to analysis history?**
- `audit_sessions` table preserves metadata (counts, timestamps)
- Frontend "Records History" page shows archived voters (from memory during session)
- For long-term history, export to CSV before running new analysis

---

## 🚀 Current Implementation

### **Fixed Issues:**
1. ✅ Database now clears old voter records before each analysis
2. ✅ Only flagged voters are stored (not all voters)
3. ✅ Dictionary keys fixed (confidence vs confidence_score)
4. ✅ Frontend API URL fixed (5000 instead of 5173)
5. ✅ Proper logging added for debugging

### **How to Use:**
1. Login at http://localhost:5174
2. Upload your CSV file (any size)
3. System automatically:
   - Clears old voter data
   - Runs analysis
   - Saves ONLY flagged voters
4. View flagged voters in "View Records" page
5. Review and manage flagged voters
6. Export audit report at any time

---

## 📝 Testing the Fix

Run this test to verify the system works:

```bash
# 1. Check current database state
python simple_db_check.py

# 2. Upload CSV via frontend UI
# Or trigger analysis via API:
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"data_path": "path/to/your/file.csv"}'

# 3. Check database again - should see flagged voters
python simple_db_check.py
```

---

## 🎯 Summary

**Before (Problem):**
- Database had 15,000 pre-loaded voters with IDs like V02666
- Analysis ran on different CSV with IDs like TNUPO7737962
- Voter IDs didn't match → Updates failed → 0 flagged voters

**After (Solution):**
- Database starts empty (only users/sessions)
- Upload CSV → Clear old voters → Save only flagged voters
- Voter IDs always match because they come from same source
- ✅ System works correctly!

---

**Last Updated:** 2026-02-01
**Status:** ✅ Fixed and Ready to Use
