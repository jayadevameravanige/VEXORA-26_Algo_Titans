# 🛡️ VoteGuard - Implementation Plan

> **AI-powered system to detect ghost and duplicate voters**

---

## 🎯 The Problem

```mermaid
flowchart LR
    A[👻 Ghost Voters] --> D[Corrupted Registry]
    B[🔄 Duplicates] --> D
    C[📅 Data Decay] --> D
    D --> E[❌ Electoral Integrity Risk]
```

| Problem | Description |
|---------|-------------|
| **Ghost Voters** | Deceased/migrated individuals still on rolls |
| **Duplicates** | Same person registered multiple times |
| **Manual Review** | Too slow for millions of records |

---

## ✅ Our Solution

```mermaid
flowchart TB
    subgraph Input
        DATA[(Voter Data\n10,000 records)]
    end
    
    subgraph AI["🤖 AI Detection"]
        GD[Ghost Detector\nIsolation Forest]
        DD[Duplicate Detector\nFuzzy Matching]
    end
    
    subgraph Output
        EXP[📋 Explanations]
        DASH[🖥️ Dashboard]
        REV[👤 Human Review]
    end
    
    DATA --> GD & DD
    GD --> EXP
    DD --> EXP
    EXP --> DASH --> REV
```

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|------------|
| **ML Engine** | Python, scikit-learn, RapidFuzz |
| **Backend** | Flask REST API |
| **Frontend** | HTML/CSS/JS + Chart.js |

---

## 🤖 How Detection Works

### Ghost Voter Detection
```mermaid
flowchart LR
    A[Voter Record] --> B{Age > 110?}
    B -->|Yes| C[🔴 High Confidence Flag]
    B -->|No| D{ML Anomaly?}
    D -->|Yes| E[🟡 Medium Confidence Flag]
    D -->|No| F[✅ Clean]
```

**Key Indicators:**
- Age exceeds 110 years
- No voting activity in 20+ years
- Registration before 1970

### Duplicate Detection
```mermaid
flowchart LR
    A[Group by DOB] --> B[Fuzzy Name Match]
    B --> C{Similarity > 85%?}
    C -->|Yes| D[Check Phonetics]
    D --> E[🔄 Flag as Duplicate]
    C -->|No| F[✅ Unique]
```

**Matching Criteria:**
- Same Date of Birth (required)
- Name similarity > 85%
- Phonetic match (Soundex/Metaphone)

---

## 🖥️ System Architecture

```
┌────────────────────────────────────────────────────────┐
│                    VOTEGUARD SYSTEM                    │
├──────────────┬──────────────┬──────────────────────────┤
│   ML Module  │   Flask API  │   Web Dashboard          │
│  ──────────  │  ──────────  │  ─────────────           │
│  • Preprocess│  /analyze    │  📊 Statistics           │
│  • Ghost Det.│  /flagged    │  📋 Flagged Records      │
│  • Dup. Det. │  /review     │  🔍 Detail Modal         │
│  • Explainer │  /audit-log  │  ✅ Review Actions       │
└──────────────┴──────────────┴──────────────────────────┘
```

---

## 📁 Project Files

```
VEXORA-26_Algo_Titans/
├── 🤖 ml/
│   ├── preprocessor.py      # Data cleaning
│   ├── ghost_detector.py    # Anomaly detection
│   ├── duplicate_detector.py# Fuzzy matching
│   └── explainer.py         # Generate reasons
│
├── ⚡ api/
│   └── app.py               # REST endpoints
│
├── 🖥️ frontend/
│   ├── index.html           # Dashboard UI
│   ├── styles.css           # Dark theme
│   └── app.js               # API integration
│
└── 📊 voter_data.csv        # 10,000 test records
```

---

## ⚖️ Ethical Safeguards

```mermaid
flowchart TB
    A[AI Flags Record] --> B[Human Reviews]
    B --> C{Decision}
    C -->|Confirm| D[Add to Action Queue]
    C -->|Dismiss| E[Mark as Valid]
    C -->|Escalate| F[Senior Review]
    
    style A fill:#6366f1
    style B fill:#f59e0b
    style D fill:#ef4444
    style E fill:#10b981
    style F fill:#8b5cf6
```

> **Key Principle:** AI assists, humans decide. No automated deletions.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start server
python api/app.py

# 3. Open browser
# → http://localhost:5000
```

---

## 👥 Team: Algo Titans

**VEXORA-26 Hackathon**
