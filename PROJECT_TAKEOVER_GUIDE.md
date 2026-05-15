# INGRES Project Takeover Guide
## Complete Technical Handover Documentation

**Project**: INGRES (India National Groundwater Resources Expert System)  
**Built For**: Smart India Hackathon 2025 (SIH25066)  
**Status**: Ready for handover and continuation

---

## TABLE OF CONTENTS
1. [Overall Project Structure](#1-overall-project-structure)
2. [Data Flow & APIs](#2-data-flow--apis)
3. [RAG Implementation](#3-rag-implementation)
4. [Docker Usage](#4-docker-usage)
5. [Technology Stack](#5-technology-stack)
6. [Features Breakdown](#6-features-breakdown)
7. [Security & Configuration](#7-security--configuration)
8. [Getting Started](#8-getting-started)
9. [Common Tasks & Modifications](#9-common-tasks--modifications)

---

## 1. OVERALL PROJECT STRUCTURE

### **What INGRES Does**

INGRES is an **AI-powered RAG (Retrieval-Augmented Generation) chatbot** that makes India's groundwater data accessible through natural language queries. Instead of manually searching through Excel files with 150+ columns, government officials and citizens can ask questions like:

- *"Which districts in Maharashtra are Over-Exploited?"*
- *"What's the fluoride contamination status in Rajasthan?"*
- *"Show me the trend of groundwater extraction from 2017 to 2022"*

The system retrieves relevant data from a PostgreSQL database and generates accurate answers using Google's Gemini 2.5 Flash LLM.

### **High-Level Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                  REACT FRONTEND (Port 3000)                 │
│  • Chat UI, message history, session management             │
│  • Export conversations to PDF, upload custom data          │
│  • Authentication (OTP-based login)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓↑ (REST API)
┌─────────────────────────────────────────────────────────────┐
│              FASTAPI BACKEND (Port 8000)                    │
│  • JWT authentication & authorization                       │
│  • RAG Engine: query classification, retrieval, generation  │
│  • Data ingestion pipeline (batch process)                  │
│  • Email services (OTP, feedback, PDF export)               │
└─────────────────────────────────────────────────────────────┘
                            ↓↑ (Python SDK)
┌─────────────────────────────────────────────────────────────┐
│    SUPABASE (PostgreSQL 15 + pgvector)                      │
│  • Tables: users, chat_history, groundwater_time_series    │
│  • Vector indices: semantic_vector, jepa_vector            │
│  • RPC functions: search_gec_manual(), search_groundwater()│
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           EXTERNAL SERVICES                                 │
│  • OpenRouter API → Gemini 2.5 Flash (LLM)                 │
│  • HuggingFace → multilingual-e5-large (embeddings)        │
│  • Gmail SMTP → OTP & email delivery                        │
└─────────────────────────────────────────────────────────────┘
```

### **Main Components & How They Interact**

| Component | Purpose | Talks To |
|-----------|---------|----------|
| **React Frontend** | User interface for chat | Backend API |
| **FastAPI Backend** | Orchestrates everything | RAG engine, Database, LLM |
| **RAG Engine** | Retrieves context + generates answers | Embedder, Database, LLM |
| **Embedder** | Converts text to 1024-dim vectors | HuggingFace, Database |
| **JEPA Encoder** | Encodes temporal trends into vectors | Database |
| **Supabase** | Stores data, vectors, chat history | All services |
| **OpenRouter** | Provides LLM capabilities | Backend |

---

## 2. DATA FLOW & APIs

### **Where Data Comes From & How It Moves**

#### **Data Ingestion** (Batch, run manually)

```
Step 1: Load Excel Files
├─ GEC Attribute Tables (~8,000 rows per state)
├─ Central Reports (all states, 153 columns)
├─ State Reports (block-level, 36 states × 6 years)
├─ Annexure-4A (at-risk blocks categorization)
└─ Annexure-4B (blocks with water quality issues)

Step 2: Transform & Normalize
├─ Map 153 columns to canonical field names (column_map.py)
├─ Preserve unmapped data in `raw_metrics` JSONB column (zero data loss)
├─ Flatten nested structures
└─ Validate data types (ensure numbers are floats, dates are dates)

Step 3: Create Vector Embeddings
├─ Build human-readable narrative for each row:
│  "In Nalgonda 2022, Stage=87.2% (Semi-Critical), AEGR=1234 Ham, ..."
├─ Encode with multilingual-e5-large → 1024-dim semantic_vector
├─ Encode 5-year temporal trend → 1024-dim jepa_vector (KEY INNOVATION)
└─ Compute JEPA velocity (annual change %), acceleration, etc.

Step 4: Store in Database
└─ Insert into groundwater_time_series with 2 vector columns + metadata
```

**Run Ingestion:**
```bash
python -m project.backend.ingestion.ingestor --source all
```

#### **Query Processing** (Runtime, happens when user sends chat message)

```
User Query: "Which districts are worsening?"

Step 1: Classification & Entity Extraction
├─ Identify query type: TREND_JEPA (signal: "worsening")
├─ Extract state: None (query about all India)
├─ Extract year: None (all years)
└─ Detect language: English

Step 2: Vector Retrieval (Dual Strategy!)
├─ Method A (Semantic Vector):
│  • Embed query → 1024-dim
│  • Search groundwater_time_series.semantic_vector
│  • Return top-10 rows with highest cosine similarity
│
└─ Method B (JEPA Trajectory Vector):
   • Encode query as trajectory concept
   • Search groundwater_time_series.jepa_vector
   • Filter for jepa_trend_direction = "worsening*"
   • Return districts with similar worsening patterns

Step 3: Context Assembly
├─ De-duplicate results
├─ Format with citations: "[Source: Telangana, 2022, Central Report]"
├─ Add metadata (state, year, extraction stage)
└─ Prepare prompt for LLM

Step 4: Generate Answer
├─ Call Gemini 2.5 Flash via OpenRouter
├─ Enforce citation format in system prompt
├─ Stream tokens to frontend
└─ Save to chat_history table (for persistence)
```

### **API Endpoints (How Your Frontend Talks to Backend)**

#### **Chat Endpoints**

| Endpoint | Method | What It Does | Requires |
|----------|--------|--------------|----------|
| `/api/chat` | POST | Send query, get answer | JWT token, `{message, session_id?}` |
| `/api/chat/history` | GET | Get all past sessions | JWT token |
| `/api/chat/export` | POST | Export session as PDF | JWT token, `{session_id}` |

#### **Auth Endpoints**

| Endpoint | Method | What It Does |
|----------|--------|--------------|
| `/api/auth/register` | POST | Start registration (sends OTP) |
| `/api/auth/login` | POST | Start login (sends OTP) |
| `/api/auth/verify` | POST | Verify OTP, get JWT token |

#### **Example Request/Response**

```json
// POST /api/chat
Request Body:
{
  "message": "Which districts in Rajasthan are Over-Exploited?",
  "session_id": "sess_12345",
  "stream": true
}

Response (Streaming via SSE):
event: token
data: "In"

event: token
data: " Rajasthan,"

...

event: final
data: {
  "type": "final",
  "answer": "In Rajasthan, 4 districts are Over-Exploited: Barmer, Bikaner, Jaisalmer, and Jodhpur [Source: Central Report, 2022]",
  "citations": ["Central Report, 2022", "Annexure4A, 2022"],
  "query_type": "block_risk",
  "language": "en"
}
```

### **Key Files to Understand Data Flow**

| File | What It Does |
|------|-------------|
| `project/backend/ingestion/ingestor.py` | Orchestrates entire ingestion pipeline |
| `project/backend/ingestion/column_map.py` | Maps 153 GEC columns to canonical names |
| `project/backend/ingestion/embedder.py` | Converts text to semantic vectors |
| `project/backend/ingestion/jepa_encoder.py` | Encodes temporal trends (INNOVATION!) |
| `project/backend/rag_engine.py` | Handles query → retrieval → generation |
| `database/schema.sql` | Database design, indices, RPC functions |

---

## 3. RAG IMPLEMENTATION

### **How Retrieval-Augmented Generation Works**

```
RAG = Retrieve Relevant Data + Generate Answer Using LLM

Problem: LLM alone can hallucinate or give outdated info
Solution: Search database first for actual data, then feed to LLM
```

### **The Dual-Vector Innovation in INGRES**

Regular RAG systems use ONE embedding vector. INGRES uses TWO:

#### **Vector 1: Semantic Vector** (What's the current status?)
```
Query: "Tell me about Nalgonda 2022"
→ Embed to 1024-dim
→ Search database for similar snapshots
→ Find: "Nalgonda 2022: Stage=87.2%, Semi-Critical, Fluoride issue"
```

#### **Vector 2: JEPA Trajectory Vector** (Is it getting worse or better?)
```
Query: "Which districts are worsening?" (Trend analysis!)
→ Encode query's DIRECTIONAL INTENT
→ Search database for similar TRENDS
→ Find: "District X: Stage went 65% → 78% → 92% (worsening)"
```

**Why JEPA?** Named after V. Jepa (a temporal ML concept). It captures:
- Velocity (rate of change per year)
- Acceleration (change in velocity)
- Direction (improving/stable/worsening)
- Turnpoints (when trend changed)

### **Retrieval Process (Step-by-Step)**

```python
# 1. QUERY CLASSIFICATION
if "worsening" in query:
    query_type = QueryType.TREND_JEPA  # Use trajectory search
elif "define AEGR" in query:
    query_type = QueryType.MANUAL      # Use manual/methodology search
else:
    query_type = QueryType.DATA_LOOKUP # Use semantic search

# 2. ENTITY EXTRACTION
state = extract_state(query)           # "Rajasthan" from query
district = extract_district(query)     # "Jaisalmer"
year = extract_year(query)             # 2022

# 3. VECTOR SEARCH (the intelligent part!)
query_vector = embed(query)            # multilingual-e5-large model

if query_type == TREND_JEPA:
    # Search trajectory vectors for worsening trends
    results = database.search_groundwater(
        embedding=query_vector,
        search_type="jepa",            # Use JEPA vector index
        state_filter=state,
        match_count=10
    )
else:
    # Search semantic vectors for point-in-time data
    results = database.search_groundwater(
        embedding=query_vector,
        search_type="semantic",        # Use semantic vector index
        state_filter=state,
        match_count=10
    )

# 4. CONTEXT ASSEMBLY
context = ""
for result in results:
    context += f"{result['narrative']} [Source: {result['source']}, {result['year']}]\n"

# 5. LLM GENERATION
answer = llm.generate(
    system_prompt="You are a groundwater expert. Always cite sources.",
    context=context,
    query=query
)

return answer
```

### **Key RAG Files**

| File | What It Does | Important Functions |
|------|-------------|---------------------|
| `project/backend/rag_engine.py` | Core RAG orchestration | `classify_query()`, `search_and_generate()`, `format_citations()` |
| `project/backend/ingestion/embedder.py` | Vector encoding | `embed_text()` |
| `project/backend/ingestion/jepa_encoder.py` | Trajectory encoding | `encode_jepa_trajectory()` |

---

## 4. DOCKER USAGE

### **Why Use Docker?**

Docker ensures:
- ✅ Same environment everywhere (dev = production)
- ✅ Easy to run both backend + frontend together
- ✅ Isolated services (backend doesn't mess with frontend)
- ✅ Easy to scale (add more containers)

### **What's in Each Container**

```
Backend Container (Python FastAPI)
├─ Python 3.10 runtime
├─ FastAPI server (port 8000)
├─ All Python dependencies (requirements.txt)
├─ Connected to Supabase PostgreSQL
└─ Downloads HuggingFace models on startup

Frontend Container (React + nginx)
├─ Node.js (build stage)
├─ Vite (React bundler)
├─ nginx server (port 3000)
└─ Serves static React app
```

### **How Containers Communicate**

```
User Browser 
    ↓ (localhost:3000)
Nginx (Frontend Container)
    ↓ (backend:8000 via Docker network)
FastAPI (Backend Container)
    ↓ (SUPABASE_URL via internet)
Supabase PostgreSQL (External)
```

### **Running Locally with Docker**

```bash
# 1. Ensure .env file has all API keys
cat .env

# 2. Create Supabase network
docker network create supabase_network_INGRES_TBP

# 3. Build & run
docker-compose up --build

# 4. Access
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### **Key Docker Files**

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Defines both services, ports, volumes, networks |
| `project/backend/Dockerfile` | How to build backend container |
| `project/frontend/Dockerfile` | How to build frontend container (multi-stage) |
| `project/frontend/nginx.conf` | nginx configuration for serving React |

---

## 5. TECHNOLOGY STACK

### **Essential** (Can't Run Without These)

| Layer | Technology | Version | Why |
|-------|-----------|---------|-----|
| **Backend Framework** | FastAPI | Latest | Async HTTP, auto API docs |
| **Language** | Python | 3.10+ | Core backend runtime |
| **Database** | Supabase PostgreSQL | 15 | Structured data + pgvector |
| **Vector DB** | pgvector | - | Fast semantic search |
| **Embeddings** | multilingual-e5-large | 1024-dim | EN/HI/TE support |
| **LLM** | Gemini 2.5 Flash | - | Answer generation |
| **Frontend** | React | 18+ | User interface |
| **Frontend Build** | Vite | Latest | Fast development |
| **Language (FE)** | TypeScript | Latest | Type safety |
| **Auth** | JWT + OTP | - | Secure login |

### **Supporting** (Nice to Have, Enables Features)

| Technology | Purpose |
|-----------|---------|
| Docker | Containerization |
| nginx | Reverse proxy for frontend |
| pandas | Data ingestion |
| numpy | Matrix math for JEPA |
| Tailwind CSS | Frontend styling |
| Framer Motion | Animations |

### **Optional** (Can Remove Safely)

| Technology | What It Does | Can Skip? |
|-----------|-------------|----------|
| torch | Deep learning (not used) | ✅ Yes |
| Prettier | Code formatting | ✅ Yes |
| ESLint | Code linting | ✅ Yes |

---

## 6. FEATURES BREAKDOWN

### **What Each Feature Does** (In Simple Terms)

#### **1. Chat Interface**
- **What**: Users type questions, get answers with data sources
- **How**: RAG engine retrieves data, LLM generates response
- **Modify**: Edit prompt in `rag_engine.py` line 250
- **Safe to Change**: ✅ Prompts, temperature (0.3 = factual)

#### **2. Session History**
- **What**: Users can see past conversations
- **How**: Stored in `chat_history` table, grouped by session_id
- **Modify**: Change retention period in `main.py`
- **Safe to Change**: ✅ UI layout, export format

#### **3. Authentication (OTP-Based)**
- **What**: Users sign up with email, get OTP, no passwords needed
- **How**: PyOTP generates time-based OTP, sent via Gmail
- **Modify**: Implement different auth (SSO, API key, etc.)
- **Safe to Change**: ✅ Email template, OTP duration (default 10 min)
- **Don't Change**: ❌ JWT secret (rotate it, don't modify logic)

#### **4. Role-Based Access Control**
- **What**: "Public" users see only Safe data, "Official" users see all
- **How**: Middleware checks JWT role, filters queries accordingly
- **Modify**: Add new roles, change permission levels
- **Safe to Change**: ✅ Role names, permission mappings
- **Don't Change**: ❌ Remove role checks (security issue!)

#### **5. Data Ingestion Pipeline**
- **What**: Loads Excel files, processes them, stores in database
- **How**: Batch operation by ingestion pipeline
- **Modify**: Add new data sources, change encoding method
- **Safe to Change**: ✅ Add new column mappings in `column_map.py`
- **Don't Change**: ❌ Remove vector encoding (breaks search)

#### **6. Vector Search (Semantic + JEPA)**
- **What**: Finds relevant data without exact keyword matching
- **How**: Embeddings + IVFFlat PostgreSQL indices
- **Modify**: Try different embedding models, adjust match_count
- **Safe to Change**: ✅ Retrieval parameters (top-10, threshold)
- **Don't Change**: ❌ Vector dimensions (1024 is hardcoded)

#### **7. PDF Export**
- **What**: Users can download chat as PDF document
- **How**: ReportLab generates PDF, sent to email
- **Modify**: Change PDF styling, add logos, include charts
- **Safe to Change**: ✅ Template, formatting, metadata

#### **8. Admin Dashboard (Government Portal)**
- **What**: Officials see state-level aggregates, monitoring stats
- **How**: Separate endpoint `/api/portal/dashboard-data`
- **Modify**: Add new charts, change visualizations
- **Safe to Change**: ✅ Metrics, charts, display format
- **Don't Change**: ❌ Remove role check (only officials can access)

#### **9. Multilingual Support**
- **What**: Supports English, Hindi, Telugu queries
- **How**: multilingual-e5-large model detects language automatically
- **Modify**: Add new languages (requires model that supports them)
- **Safe to Change**: ✅ Add language preference UI
- **Don't Change**: ❌ Switch to English-only model (lose functionality)

---

## 7. SECURITY & CONFIGURATION

### **Sensitive Information Storage**

#### **Environment Variables** (`.env` file - NEVER commit to Git)

```bash
# Database
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# LLM API
OPENROUTER_API_KEY=your-openrouter-key

# Email (for OTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-gmail@gmail.com
MAIL_PASSWORD=your-app-specific-password  # NOT your Gmail password!

# JWT Signing
JWT_SECRET=super_secret_key_change_this

# Optional
HF_TOKEN=huggingface-token-for-private-models
PRELOAD_EMBEDDINGS_ON_STARTUP=1
```

### **How to Replace API Keys for Your Own Use**

#### **Step 1: Get Your Own Supabase Project**
```bash
# 1. Go to supabase.com → Sign up
# 2. Create new project → Copy URL and keys
# 3. Edit .env:
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=<<<your-new-key>>>
SUPABASE_SERVICE_ROLE_KEY=<<<your-new-key>>>
```

#### **Step 2: Get OpenRouter Key**
```bash
# 1. Go to openrouter.ai → Sign up
# 2. Go to keys → Create API key
# 3. Edit .env:
OPENROUTER_API_KEY=<<<your-new-key>>>
```

#### **Step 3: Set Up Gmail for Sending OTP**
```bash
# 1. Go to myaccount.google.com → Security
# 2. Enable 2-Factor Authentication
# 3. Create App Password → Copy it
# 4. Edit .env:
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=<<<app-password-from-google>>>
```

#### **Step 4: Change JWT Secret**
```bash
# 1. Generate random string (at least 32 characters):
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Edit .env:
JWT_SECRET=<<<generated-secret>>>
```

### **Rotation Schedule**

| Secret | Rotation | How |
|--------|----------|-----|
| JWT_SECRET | Before deployment | Generate new value |
| SUPABASE_ANON_KEY | Every 6 months | Rotate in Supabase console |
| OPENROUTER_API_KEY | On key compromise | Generate new key |
| MAIL_PASSWORD | Never (use App Password) | Delete app password, create new one |

### **Security Best Practices**

```python
# ❌ BAD: Hardcoded secrets
API_KEY = "sk-1234567890abcdef"

# ✅ GOOD: Load from environment
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    raise ValueError("❌ OPENROUTER_API_KEY not set in .env")

# ✅ BETTER: Validate on startup
if os.getenv("JWT_SECRET") == "super_secret_key_change_this":
    raise ValueError("❌ Override default JWT_SECRET in .env!")
```

### **What NOT to Commit to GitHub**

Create `.gitignore`:
```
.env
.env.local
.DS_Store
node_modules/
dist/
build/
__pycache__/
*.pyc
.venv/
venv/
```

---

## 8. GETTING STARTED

### **Quick Start (5 Minutes)**

#### **1. Clone & Setup**
```bash
cd /path/to/INGRES_TBP

# Create .env from template
cp .env.example .env

# Edit .env with YOUR API keys (see Security section above)
nano .env  # or use VS Code
```

#### **2. Install Dependencies** (if running locally without Docker)

**Backend:**
```bash
cd project/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend:**
```bash
cd project/frontend
npm install
```

#### **3. Run with Docker** (Recommended)
```bash
cd /path/to/INGRES_TBP
docker-compose up --build

# Wait for both services to start, then:
# Frontend: http://localhost:3000
# Backend: http://localhost:8000/docs
```

#### **4. Test It Works**
```bash
# Open browser to http://localhost:3000
# Register with email → get OTP from console output
# Ask: "Which states are over-exploited?"
# Should get answer with citations ✅
```

### **Development Workflow**

```bash
# Terminal 1: Backend (auto-reloads on code change)
cd project/backend
uvicorn main:app --reload

# Terminal 2: Frontend (auto-reloads on code change)
cd project/frontend
npm run dev

# Terminal 3: Optional - Run ingestion
python -m ingestion.ingestor --source all
```

---

## 9. COMMON TASKS & MODIFICATIONS

### **Task 1: Change the LLM Model**

Currently uses **Gemini 2.5 Flash**. Want to use **GPT-4** instead?

```python
# File: project/backend/rag_engine.py (line ~150)

# BEFORE (Gemini):
response = openai_client.chat.completions.create(
    model="google/gemini-2.5-flash",  # ← Change this
    messages=[...]
)

# AFTER (GPT-4):
response = openai_client.chat.completions.create(
    model="openai/gpt-4",  # ← Now using GPT-4
    messages=[...]
)
```

**Note**: Make sure your OpenRouter account supports the model.

### **Task 2: Add a New Data Source**

Want to add data from a new Excel file?

```python
# File: project/backend/ingestion/column_map.py
# Add new mapping:
COLUMN_MAPPINGS['MyNewDataSource'] = {
    'State': 'state',
    'District Name': 'district',
    'Year': 'assessment_year',
    'Stage %': 'stage_of_extraction_pct',
    # ... map all columns
}

# File: project/backend/ingestion/ingestor.py
# Add to load_data():
if source == 'mynewdata':
    df = pd.read_excel('datasets/mynewdata.xlsx')
    df = transform_data(df, 'MyNewDataSource')
    upsert_to_db(df)

# Run:
python -m ingestion.ingestor --source mynewdata
```

### **Task 3: Modify the Chat Prompt**

Want different response style (more technical? more casual)?

```python
# File: project/backend/rag_engine.py (line ~200)

# Current prompt (factual, cited):
system_prompt = """You are an expert on groundwater resources in India.
Always cite your sources clearly."""

# New prompt (casual, explanatory):
system_prompt = """You are a friendly groundwater expert explaining 
complex data in simple terms. Make it sound conversational but accurate."""
```

### **Task 4: Add New User Roles**

Want to add a **"researcher"** role between "public" and "official"?

```python
# File: database/schema.sql
-- Edit users table:
ALTER TABLE users ADD CONSTRAINT role_values 
CHECK (role IN ('public', 'researcher', 'official', 'admin'));

# File: project/backend/rag_engine.py
# Update role-based filtering:
def apply_role_filter(role: str):
    if role == 'public':
        return "categorization IN ('Safe')"
    elif role == 'researcher':
        return "categorization IN ('Safe', 'Semi-Critical')"
    elif role == 'official':
        return "categorization IN ('Safe', 'Semi-Critical', 'Critical', 'Over-Exploited')"
    else:
        return ""
```

### **Task 5: Change Email Service**

Currently uses **Gmail SMTP**. Want SendGrid instead?

```python
# File: project/backend/auth_utils.py (line ~80)

# BEFORE (Gmail):
smtp_server = "smtp.gmail.com"

# AFTER (SendGrid):
smtp_server = "smtp.sendgrid.net"
smtp_port = 587
mail_username = "apikey"
mail_password = os.getenv("SENDGRID_API_KEY")
```

### **Task 6: Add Custom Visualization**

Want to show data as a map instead of table?

```typescript
// File: project/frontend/src/pages/Dashboard.tsx
// In chat response rendering:

if (response.chart && response.chart.type === 'map') {
    return <MapVisualization data={response.chart.data} />;
} else if (response.chart && response.chart.type === 'chart') {
    return <BarChart data={response.chart.data} />;
}
```

### **Task 7: Debug: Query Returns No Results**

```bash
# 1. Check backend logs
docker-compose logs backend

# 2. Verify database connection
python -c "from supabase import create_client; 
           client = create_client(SUPABASE_URL, SUPABASE_KEY);
           print(client.table('groundwater_time_series').select('*').limit(1).execute())"

# 3. Check vector indices
# In Supabase SQL editor:
SELECT COUNT(*) FROM groundwater_time_series 
WHERE semantic_vector IS NOT NULL;

# 4. Test retrieval directly
python project/backend/rag_engine.py --test-query "Test query"
```

---

## SUMMARY: Key Takeaways

### **Architecture (Remember This)**

```
User Query → Frontend → Backend RAG Engine 
→ Vector Search (retrieve) → LLM Generation → Answer with Citations
```

### **Tech Stack (Must-Have)**

- **Backend**: FastAPI + Python 3.10
- **DB**: Supabase PostgreSQL + pgvector
- **LLM**: Gemini 2.5 Flash (via OpenRouter)
- **Embeddings**: multilingual-e5-large (1024-dim)
- **Frontend**: React 18 + TypeScript + Vite

### **Most Important Files to Know**

1. `project/backend/main.py` - API endpoints & entry point
2. `project/backend/rag_engine.py` - Core RAG logic
3. `database/schema.sql` - Database design
4. `docker-compose.yml` - Container orchestration
5. `project/frontend/src/pages/Dashboard.tsx` - Main UI

### **What's Optional?**

- ✅ Change LLM model to GPT-4 or others
- ✅ Add new embedding models
- ✅ Add new data sources
- ✅ Customize prompts & responses
- ✅ Add new roles & permissions

### **What's Critical?**

- ❌ Don't skip JWT secret rotation
- ❌ Don't hardcode API keys
- ❌ Don't remove vector indices (breaks search)
- ❌ Don't change column names without updating mappings

---

**Next Steps:**
1. ✅ Read this document completely
2. ✅ Get your own API keys (Supabase, OpenRouter, Gmail)
3. ✅ Run `docker-compose up --build`
4. ✅ Test the chat interface
5. ✅ Explore the codebase using the file navigation above
6. ✅ Make your first modification (change a prompt!)

Good luck taking over the project! 🚀
