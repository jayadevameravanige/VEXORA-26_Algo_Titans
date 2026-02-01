# VoteGuard - AI Ghost & Duplicate Voter Detection System

![VoteGuard](https://img.shields.io/badge/VoteGuard-AI%20Powered-6366f1?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=for-the-badge&logo=flask)

> **AI-powered decision-support system** to help election authorities identify suspicious or invalid voter records in large databases.

## 🎯 Problem Statement

Voter registries accumulate records of people who have migrated, passed away, or registered multiple times. VoteGuard addresses:

- **Ghost Voters**: Deceased or non-existent individuals still listed as active voters
- **Duplicate Voters**: Same person registered multiple times with name variations
- **Data Decay**: Cluttered registries that are inefficient to clean manually

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Detection** | Isolation Forest for ghost detection, DBSCAN + fuzzy matching for duplicates |
| 📊 **Explainability** | Every flag includes human-readable reasons and confidence scores |
| 👤 **Human-in-the-Loop** | AI assists, humans decide - no automated deletions |
| 🛡️ **Privacy-First** | No demographic-based decisions, transparent thresholds |
| 📋 **Audit Trail** | Complete logging of all analysis and review actions |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VoteGuard System                         │
├─────────────────┬─────────────────┬─────────────────────────┤
│   ML Engine     │   Flask API     │   Frontend Dashboard    │
│  ───────────    │  ──────────     │  ──────────────────     │
│  • Preprocessor │  • /api/analyze │  • Statistics View      │
│  • Ghost Det.   │  • /api/flagged │  • Flagged Records      │
│  • Duplicate Det│  • /api/review  │  • Review Workflow      │
│  • Explainer    │  • /api/audit   │  • Audit Log            │
└─────────────────┴─────────────────┴─────────────────────────┘
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate Sample Data (Optional - already included)

```bash
python datset.py
```

### 3. Run the API Server

```bash
python api/app.py
```

### 4. Open the Dashboard

Open `http://localhost:5000` in your browser, then click **"Run Analysis"** to detect suspicious records.

## 📁 Project Structure

```
VEXORA-26_Algo_Titans/
├── ml/                     # Machine Learning Module
│   ├── preprocessor.py     # Data preprocessing & feature engineering
│   ├── ghost_detector.py   # Isolation Forest ghost detection
│   ├── duplicate_detector.py # DBSCAN + fuzzy matching
│   ├── explainer.py        # Human-readable explanations
│   └── pipeline.py         # Detection orchestration
│
├── api/                    # Flask REST API
│   └── app.py              # API endpoints & server
│
├── frontend/               # Web Dashboard
│   ├── index.html          # Main HTML
│   ├── styles.css          # Glassmorphism CSS
│   └── app.js              # Frontend logic
│
├── datset.py               # Synthetic data generator
├── voter_data.csv          # Sample dataset (10,000 records)
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## 🧪 Sample Dataset

The included `voter_data.csv` contains 10,000 synthetic Indian voter records:

| Record Type | Count | Description |
|-------------|-------|-------------|
| Normal | 9,000 | Valid voter records |
| Ghost | 500 (5%) | Age > 110 years |
| Duplicate | 500 (5%) | Same DOB, similar names |

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/analyze` | POST | Run detection pipeline |
| `/api/stats` | GET | Get detection statistics |
| `/api/flagged` | GET | Get flagged records (with filters) |
| `/api/record/<id>` | GET | Get record details with explanation |
| `/api/review/<id>` | POST | Submit human review decision |
| `/api/audit-log` | GET | Get audit trail |
| `/api/export` | GET | Export results as JSON |

## 🤖 ML Approach

### Ghost Voter Detection
- **Algorithm**: Isolation Forest (unsupervised anomaly detection)
- **Key Features**: Age, voting activity, registration age, inactivity period
- **Threshold**: Voters with age > 110 are automatically flagged with high confidence

### Duplicate Voter Detection
- **Algorithm**: DBSCAN clustering + RapidFuzz string matching
- **Key Matching Criteria**:
  - Same Date of Birth (required)
  - Name similarity > 80% (fuzzy match)
  - Phonetic matching (Soundex/Metaphone)
  - Same masked Aadhaar pattern

## ⚖️ Ethical Safeguards

1. **No Automated Deletions**: AI flags, humans decide
2. **No Demographic Features**: Gender, religion, caste are never used
3. **Transparent Thresholds**: All parameters are configurable
4. **Conservative Flagging**: Prefer false negatives over false positives
5. **Complete Audit Trail**: Every action is logged

## 👥 Team: Algo Titans

Built for **VEXORA-26 Hackathon**

---

*"Empowering electoral integrity through ethical AI"*
