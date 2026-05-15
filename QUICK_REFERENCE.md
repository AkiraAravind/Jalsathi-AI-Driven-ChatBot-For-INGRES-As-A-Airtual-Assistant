# INGRES Project - Quick Reference Cheat Sheet

## 🚀 START HERE (5-Minute Overview)

**What is INGRES?** 
An AI chatbot that makes India's groundwater data queryable. Users ask → System retrieves data → LLM generates answer with citations.

**Architecture**: 
`Frontend (React) → Backend (FastAPI) → Database (PostgreSQL+pgvector) → LLM (Gemini 2.5 Flash)`

---

## 🔑 Key Concepts

### Query Processing Flow
```
User: "Which districts in Rajasthan are Over-Exploited?"
  ↓ [Classify] Query type = BLOCK_RISK
  ↓ [Extract] state = "Rajasthan"
  ↓ [Embed] Convert question to 1024-dim vector
  ↓ [Search] Vector search in annexure_block_risk table
  ↓ [Format] Add citations: "[Source: Annexure4A, 2022]"
  ↓ [Generate] Call Gemini 2.5 Flash with context
  ↓ [Return] Answer + citations to frontend
```

### Data Storage (Main Tables)
| Table | Purpose | Key Columns |
|-------|---------|------------|
| `groundwater_time_series` | All GEC data (153 cols) | state, district, year, stage_pct, **semantic_vector**, **jepa_vector** |
| `gec_manual_index` | GEC methodology texts | section_title, content, **embedding** |
| `annexure_block_risk` | At-risk blocks catalog | state, district, block_name, categorization, **embedding** |
| `users` | Authentication | email, role ('public'/'official'/'admin'), password_hash |
| `chat_history` | Conversation logs | session_id, content, citations, user_email |

---

## 📁 Directory Map

```
project/
├─ backend/
│  ├─ main.py                    [API endpoints & orchestration]
│  ├─ rag_engine.py             [Core RAG: classify, retrieve, generate]
│  ├─ auth_utils.py             [JWT, OTP, email]
│  ├─ pdf_utils.py              [PDF export]
│  ├─ ingestion/
│  │  ├─ ingestor.py            [Main data pipeline orchestrator]
│  │  ├─ column_map.py          [153-col GEC schema mapping]
│  │  ├─ embedder.py            [multilingual-e5-large → vectors]
│  │  └─ jepa_encoder.py        [Temporal trajectory encoding]
│  └─ requirements.txt
│
├─ frontend/
│  ├─ src/
│  │  ├─ App.tsx                [React routing]
│  │  ├─ pages/Dashboard.tsx    [Main chat UI]
│  │  ├─ services/api.ts        [API client]
│  │  └─ components/            [UI components]
│  ├─ package.json
│  └─ Dockerfile
│
├─ database/
│  ├─ schema.sql                [DB design, indices, RPC]
│  └─ migrations/               [Schema versions]
│
└─ .env                         [API keys, credentials]
```

---

## 🔧 Configuration Steps

### 1️⃣ Get API Keys
```bash
# Supabase (Database)
https://supabase.com → New Project → Copy URL & Keys

# OpenRouter (LLM)
https://openrouter.ai → Create API Key

# Gmail (OTP Emails)
myaccount.google.com → Security → App Passwords

# Generate JWT Secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2️⃣ Update `.env`
```bash
SUPABASE_URL=https://XXX.supabase.co
SUPABASE_ANON_KEY=your-key
SUPABASE_SERVICE_ROLE_KEY=your-key
OPENROUTER_API_KEY=your-key
MAIL_USERNAME=your-gmail@gmail.com
MAIL_PASSWORD=your-app-password
JWT_SECRET=your-generated-secret
```

### 3️⃣ Run Everything
```bash
docker-compose up --build
# Frontend: localhost:3000
# Backend: localhost:8000/docs
```

---

## 🐘 Database Schema (Simple Version)

### groundwater_time_series
```
state: "Telangana"
district: "Nalgonda"
assessment_year: 2022
stage_of_extraction_pct: 87.2
categorization: "Semi-Critical"
semantic_vector: [0.123, -0.045, ...] (1024 numbers)
jepa_vector: [0.567, 0.234, ...] (1024 numbers - trajectory)
raw_metrics: {all unmapped 153 columns}
```

### Why Two Vectors?
- **semantic_vector**: Find "what's the status now?" queries
- **jepa_vector**: Find "is it getting worse?" queries (trends)

---

## 🔄 Data Ingestion (Batch Process)

```bash
# Load all data sources
python -m project.backend.ingestion.ingestor --source all

# Or specific source
python -m project.backend.ingestion.ingestor --source central
python -m project.backend.ingestion.ingestor --source state
python -m project.backend.ingestion.ingestor --source annexure4
```

**What Happens:**
1. Load Excel files from `datasets/`
2. Map columns to canonical names (column_map.py)
3. Build narratives per row
4. Encode to vectors (multilingual-e5-large)
5. Encode trajectories (JEPA encoder)
6. Insert into PostgreSQL
7. Create IVFFlat indices for fast search

---

## 🔐 Security Essentials

### Environment Secrets
- **NEVER** commit `.env` to Git
- Add to `.gitignore`: `.env, .env.local, venv/`
- **NEVER** hardcode API keys in Python files

### JWT Secret
```python
# Use one per deployment
JWT_SECRET = os.getenv("JWT_SECRET")  # ✅ Good
JWT_SECRET = "my_secret_123"          # ❌ Bad
```

### OTP Authentication
- Uses PyOTP (time-based)
- 6-digit code, 10-min validity
- Sent via Gmail SMTP
- Never store passwords (OTP only)

---

## 📝 API Endpoints (Main Ones)

### Chat
```
POST /api/chat
├─ Body: {message, session_id?, stream?}
└─ Response: {answer, citations, query_type, language}

GET /api/chat/history
└─ Response: {sessions: [{id, title, messages}]}
```

### Auth
```
POST /api/auth/register
├─ Body: {email, name?}
└─ Response: {status, message} (sends OTP)

POST /api/auth/verify
├─ Body: {email, otp}
└─ Response: {token, role, name} (JWT)
```

### Admin
```
GET /api/portal/dashboard-data
└─ Requires: role="official|admin"
└─ Response: {state_stats, total_queries, at_risk_blocks}
```

---

## 🛠️ Common Tasks

### Task: Change LLM Model
**File**: `project/backend/rag_engine.py` (line ~150)
```python
# Current (Gemini 2.5):
model="google/gemini-2.5-flash"

# Change to GPT-4:
model="openai/gpt-4"
```

### Task: Add New Data Source
**File**: `project/backend/ingestion/column_map.py`
```python
COLUMN_MAPPINGS['MyNewSource'] = {
    'State': 'state',
    'Stage %': 'stage_of_extraction_pct',
    # ... map all columns
}
```

### Task: Change Response Tone
**File**: `project/backend/rag_engine.py` (line ~200)
```python
system_prompt = """You are a groundwater expert. 
Be casual and explain complex concepts simply."""
```

### Task: Add New Role
**File**: `database/schema.sql`
```sql
ALTER TABLE users 
ADD CONSTRAINT role_values 
CHECK (role IN ('public', 'researcher', 'official', 'admin'));
```

---

## 📊 Monitor System Health

```bash
# Check backend logs
docker-compose logs backend

# Check frontend logs
docker-compose logs frontend

# Test database connection
python -c "from supabase import create_client; ..."

# Check vector indices exist
SELECT COUNT(*) FROM groundwater_time_series 
WHERE semantic_vector IS NOT NULL;

# API docs (auto-generated)
http://localhost:8000/docs
```

---

## 🚨 Troubleshooting

### "Connection refused" to database?
- Check `.env` SUPABASE_URL is correct
- Verify you're running with correct network: `docker network create supabase_network_INGRES_TBP`

### "No results" from queries?
- Check ingestion completed: `SELECT COUNT(*) FROM groundwater_time_series`
- Check vectors exist: `WHERE semantic_vector IS NOT NULL`
- Run ingestion again: `python -m ingestion.ingestor --source all`

### Frontend can't connect to backend?
- Verify backend running: `curl http://localhost:8000/docs`
- Check VITE_API_BASE_URL in `.env.local`

### Email not sending OTP?
- Verify MAIL_USERNAME & MAIL_PASSWORD in `.env`
- Must use **Gmail App Password**, not account password
- Check 2FA enabled

---

## 📚 Tech Stack at a Glance

| Component | Tech | Version |
|-----------|------|---------|
| Language (Backend) | Python | 3.10+ |
| Framework | FastAPI | Latest |
| Database | PostgreSQL | 15 |
| Vector DB | pgvector | - |
| Embedding Model | multilingual-e5-large | 1024-dim |
| LLM | Gemini 2.5 Flash | via OpenRouter |
| Language (Frontend) | TypeScript | Latest |
| Frontend Framework | React | 18+ |
| Build Tool | Vite | Latest |
| CSS | Tailwind | Latest |
| Container | Docker | Latest |

---

## ✅ Verification Checklist

Before deploying or sharing:
- [ ] `.env` has all API keys
- [ ] JW​T_SECRET changed from default
- [ ] `.env` NOT committed to Git
- [ ] `docker-compose up --build` works
- [ ] Frontend: http://localhost:3000 loads
- [ ] Backend: http://localhost:8000/docs opens
- [ ] Can register and get OTP
- [ ] Can ask question and get answer
- [ ] Answer has citations
- [ ] Export to PDF works

---

## 📖 Further Reading

- **Full Details**: See `PROJECT_TAKEOVER_GUIDE.md` in project root
- **API Docs**: http://localhost:8000/docs (Swagger UI, auto-generated)
- **Database Schema**: `database/schema.sql`

---

**Last Updated**: 2026-04-10  
**For**: Project INGRES Handover  
**Questions?** Check the full PROJECT_TAKEOVER_GUIDE.md
