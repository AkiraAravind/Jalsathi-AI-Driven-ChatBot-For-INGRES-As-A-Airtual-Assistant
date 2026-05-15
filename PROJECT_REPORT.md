# INGRES ChatBOT — Complete Project Report
### AI-Powered Groundwater Intelligence Platform (SIH 2025 — Problem Statement SIH25066)

---

## Table of Contents

1. [Project Identity](#1-project-identity)
2. [Problem Statement — SIH25066](#2-problem-statement--sih25066)
3. [Project Objectives](#3-project-objectives)
4. [Solution Overview](#4-solution-overview)
5. [System Architecture](#5-system-architecture)
6. [Dataset Analysis](#6-dataset-analysis)
7. [Data Ingestion Pipeline](#7-data-ingestion-pipeline-the-engine)
8. [RAG System](#8-rag-system--retrieval-augmented-generation)
9. [Backend — FastAPI Server](#9-backend--fastapi-server)
10. [Database Design — Supabase + pgvector](#10-database-design--supabase--pgvector)
11. [Frontend — React + Vite + TypeScript](#11-frontend--react--vite--typescript)
12. [Security Architecture](#12-security-architecture)
13. [Technology Stack](#13-technology-stack)
14. [Project File Structure](#14-project-file-structure)
15. [End-to-End Flow](#15-how-everything-works-together--end-to-end-flow)
16. [Current State](#16-current-state--what-has-been-built)
17. [Next Steps](#17-what-needs-to-be-done-next-upcoming-steps)
18. [Glossary](#18-glossary)

---

## 1. Project Identity

| Property | Value |
|----------|-------|
| **Project Name** | INGRES ChatBOT (India National Groundwater Resources Expert System) |
| **Competition** | Smart India Hackathon 2025 (SIH 2025) |
| **Problem Statement ID** | SIH25066 |
| **Theme** | Smart Water Management / e-Governance |
| **Organization** | Ministry of Jal Shakti / Central Ground Water Board (CGWB) |
| **Team** | TBP (Team Building Project) Iteration 2 |
| **App Name** | INGRES |
| **API Version** | v1.0.0 |

---

## 2. Problem Statement — SIH25066

India faces a **critical groundwater crisis**. According to CGWB (Central Ground Water Board), over **17% of India's administrative assessment units** are classified as **Over-Exploited**, meaning groundwater is being extracted faster than it is being replenished. States like Haryana (63.64% Over-Exploited blocks), Delhi (29.41%), and Rajasthan have reached alarming levels.

### The Core Problem

The Ministry of Jal Shakti generates massive amounts of groundwater assessment reports every 2–3 years through the **GEC (Ground Water Estimation Committee)** framework. These reports contain:
- Block/Mandal/Taluka level recharge and extraction data
- District and State level summaries
- Categorization of assessment units (Safe / Semi-Critical / Critical / Over-Exploited / Saline)
- Quality contamination data (Fluoride, Arsenic, Salinity)

**However**, this data is:
1. Locked in **dense Excel files and PDFs** that are hard to navigate
2. Not easily queryable — officials must manually search thousands of rows
3. Not accessible to policymakers or the general public in a usable form
4. Spread across **36 states/UTs**, **hundreds of districts**, and **thousands of blocks**

### The Ask

Build an **AI-powered intelligent chatbot** that can:
- Answer natural-language questions about groundwater resources
- Provide district-wise, state-wise, and national-level insights
- Surface trends across multiple assessment years
- Be secure, reliable, and scalable for government use

---

## 3. Project Objectives

### Primary Objective
Build a **Retrieval-Augmented Generation (RAG)** based AI chatbot that allows users to ask natural language questions about India's groundwater data and receive **accurate, data-grounded answers** without hallucination.

### Secondary Objectives
1. **Ingest and Index** all GEC report data (Annexures 1-4, Attribute Tables, Central and State reports) into a searchable vector database
2. **Normalize and Standardize** messy, multi-format Excel data into a clean, queryable schema
3. **Build a secure API** with JWT authentication for enterprise use by government officials
4. **Create a clean, modern UI** that allows both experts and non-technical users to query the system
5. **Support temporal querying** — allow comparisons across assessment years (2017, 2020, 2022, 2023, 2025)
6. **Expand coverage** from Telangana (current) to all 36 States/UTs of India

---

## 4. Solution Overview

INGRES is a full-stack AI application structured as follows:

```
User Types Natural Language Question
        |
React Frontend (Chat Interface)
        |
FastAPI Backend (REST API)
        |
[Security Layer] - JWT Auth + Input Sanitization
        |
[RAG Engine]
    |- Embed Query via SentenceTransformer (all-MiniLM-L6-v2)
    |- Vector Search via Supabase pgvector (cosine similarity)
    |- Generate Answer via Gemini 2.0 Flash (OpenRouter)
        |
Grounded Answer Returned to User
```

The key innovation is the **RAG approach** — unlike a generic LLM that might hallucinate numbers, INGRES:
1. **Retrieves** the actual data chunks from the database matching the user query
2. **Passes them as context** to the LLM
3. **Instructs the LLM** to answer ONLY from that context
4. Returns a **source-cited, factual answer**

---

## 5. System Architecture

```
INGRES SYSTEM
=============

FRONTEND (React+Vite+TS)  <--HTTP/REST-->  BACKEND (FastAPI)
                                              |
                                         /auth/register
                                         /auth/token
                                         /chat/ask
                                              |
                                         [RAG Engine]
                                           |- Embedder (MiniLM)
                                           |- Retriever (pgvector RPC)
                                           |- Generator (Gemini Flash)
                                              |
SUPABASE (PostgreSQL)  <--supabase-py-->  [DB Layer]
  |- district_embeddings (vector 384)
  |- district_data (structured jsonb)
  |- users (auth + roles)

OFFLINE INGESTION PIPELINE (runs separately)
  Excel/JSON Files
    -> parser.py
    -> normalizer.py
    -> transformer.py
    -> chunker.py
    -> embedder.py
    -> store.py
    -> Supabase
```

---

## 6. Dataset Analysis

The datasets uploaded in `TBP/datasets/` come directly from the **Ministry of Jal Shakti's GEC Assessment Reports**. They are the ground truth for all groundwater intelligence.

### Dataset Hierarchy

```
Nation (India)
  -> State/UT (36 States/UTs)
       -> District (750+ districts)
            -> Assessment Unit / Block / Mandal / Taluka (8000+ units)
```

### 6.1 Annexure-1 — National State Summary (BCM)

- **5 files** representing 5 different assessment years
- One row per State/UT (36 rows per file)
- Unit: **BCM (Billion Cubic Meters)**

**Key Columns (16 total):**

| Column | Meaning |
|--------|---------|
| States / Union Territories | State name |
| Recharge from Rainfall (Monsoon) | GW recharged by rain in monsoon |
| Recharge from Other Sources (Monsoon) | GW recharged from canals/tanks in monsoon |
| Recharge from Rainfall (Non-Monsoon) | Rain recharge in winter/summer |
| Recharge from Other Sources (Non-Monsoon) | Other source recharge in non-monsoon |
| **Total Annual GW Recharge** | Total water recharged per year |
| Total Natural Discharges | Groundwater naturally leaving system |
| **Annual Extractable GW Resource** | Max water that can be extracted |
| Irrigation Use | GW extracted for farming |
| Industrial Use | GW extracted for factories |
| Domestic Use | GW extracted for drinking/household |
| **Total Extraction** | All uses combined |
| Annual GW Allocation for Domestic use 2025 | Future planned domestic allocation |
| **Net GW Availability for future use** | Extractable minus Currently extracted |
| **Stage of GW Extraction (%)** | (Total Extraction / Extractable) x 100 — THE KEY METRIC |

---

### 6.2 Annexure-2 — District-Level Summary (Ham)

- **5 files** for 5 assessment years
- ~892 rows per file (one per district across all states)
- Unit: **Ham (Hectare Meters)** — 1 BCM = 100,000 Ham
- Same 16 columns as Annexure-1 but at **district granularity**

---

### 6.3 Annexure-3 — Block/Mandal Categorization Counts

- **6 sub-sheets**: 3A (State), 3B (District), 3C-3F (finer levels)
- Counts and percentages of blocks in each category

**Key Columns:**

| Column | Meaning |
|--------|---------|
| Total No. of Assessed Units | Total blocks evaluated |
| Safe (Nos. + %) | Units where Stage of Extraction < 70% |
| Semi-Critical (Nos. + %) | Units where Stage 70-90% |
| Critical (Nos. + %) | Units where Stage 90-100% |
| Over-Exploited (Nos. + %) | Units where Stage > 100% (DANGER ZONE) |
| Saline (Nos. + %) | Units with water quality issues |

**Classification Rules:**
- Safe: Stage of Extraction < 70%
- Semi-Critical: 70% to 90%
- Critical: 90% to 100%
- Over-Exploited: Stage > 100% (extraction exceeds recharge - UNSUSTAINABLE)
- Saline: Quality-based (fluoride/arsenic/salinity contamination)

---

### 6.4 Annexure-4 — Named Assessment Units by Category

- **Annexure 4A**: Lists specific block names classified as Semi-Critical, Critical, and Over-Exploited per district
- **Annexure 4B**: Lists blocks contaminated by Fluoride, Arsenic, or Salinity

---

### 6.5 Attribute Table — THE MASTER DATASET (Most Important)

- **5 files**, each with ~8092 rows (one per assessment unit across India)
- Unit: Ham (Hectare Meters) + Ha (Hectares) for area
- **26 comprehensive columns** — the most ML/AI-ready dataset

**Complete Column List:**

| Column | Purpose |
|--------|---------|
| Sl.No | Row identifier |
| State_code | State abbreviation (e.g., TS=Telangana, KA=Karnataka) |
| State_District_Code | District code (e.g., TS06) |
| State_District_Block_Code | Full block code (e.g., TS0610) |
| State | State name |
| District | District name |
| Assessment Unit Name | Block/Mandal/Taluka name |
| Assessment Unit Type | BLOCK / MANDAL / TALUKA |
| Total Geographical Area | Total land area in Ha |
| Recharge Worthy Area | Area suitable for recharge in Ha |
| Recharge from Rainfall-MON | Monsoon rainfall recharge (Ham) |
| Recharge from Other Sources-MON | Other monsoon recharge (Ham) |
| Recharge from Rainfall-NM | Non-monsoon rainfall recharge (Ham) |
| Recharge from Other Sources-NM | Other non-monsoon recharge (Ham) |
| Total Annual GW Recharge | Total annual recharge (Ham) |
| Total Natural Discharges | Natural outflow (Ham) |
| Annual Extractable GW Resource | Net supply (Ham) |
| Irrigation Use | Farming extraction (Ham) |
| Industrial Use | Industry extraction (Ham) |
| Domestic Use | Household extraction (Ham) |
| Total Extraction | All uses (Ham) |
| Annual GW Allocation for Domestic Use 2025 | Future domestic allocation (Ham) |
| Net GW Availability for future use | Remaining supply (Ham) |
| **Stage of GW Extraction (%)** | **Primary classification metric** |
| **Categorization** | **Safe / Semi-Critical / Critical / OE / Saline** — TARGET LABEL |
| Bo_Aquifer | Aquifer type indicator |

---

### 6.6 Central Reports — Full 153-Column GEC Reports

- **Central/district/**: 6 files, 6 assessment years, district-level for all of India
- **Central/states/**: 7 files, 7 assessment years, state-level India-wide

**153 columns include:**
- Rainfall breakdown: Current (C) / Non-Current (NC) / Poor Quality (PQ) / Total
- All recharge sources: Rainfall, Canals, Surface Irrigation, GW Irrigation, Tanks, Water Conservation Structures, Pipelines, Sewage/Flash Flood Channels
- Inflows and Outflows: Base Flow, Stream Recharges, Lateral Flows, Vertical Flows, Evaporation, Transpiration, Evapotranspiration
- Extraction by sector: Domestic / Industrial / Irrigation (each with C/NC/PQ/Total)
- Environmental Flows, Stage of Extraction, Quality tagging (Fluoride, Arsenic, Salinity)
- Aquifer data: Unconfined, Confined, Semi-Confined (Fresh + Saline volumes)
- Additional resources: Waterlogged areas, Flood Prone Zones, Coastal Areas, Spring Discharge

---

### 6.7 State Reports — Per-State Block Level Data

- **36 subdirectories** under `state/` — one per State/UT
- Each has 6 files (6 assessment years)
- Same 153-column format as Central/district but filtered to one state
- Data at **Block/Mandal/Taluka level** — most granular

---

### Dataset Scale Summary

| Dataset | Files | Rows per File | Granularity | Unit |
|---------|-------|---------------|-------------|------|
| Annexure-1 | 5 | 36 | State | BCM |
| Annexure-2 | 5 | ~800 | District | Ham |
| Annexure-3 | 5 | ~1000 | State/District/Block | Count/% |
| Annexure-4 | 5 | ~3000 | Block names | Named |
| Attribute Table | 5 | ~8092 | Block | Ham/Ha |
| Central/District | 6 | ~750 | District | Ham |
| Central/States | 7 | 36 | State | Ham |
| State Reports | 36×6=216 | ~200 | Block | Ham |

---

## 7. Data Ingestion Pipeline (The Engine)

The ingestion pipeline is a series of Python modules that process raw data files and load them into Supabase. It runs **offline** (as a one-time or periodic job) and feeds the vector database that powers RAG.

### Pipeline Flow

```
Raw Data Files (TXT/JSON/Excel)
          |
    parser.py     -- Reads and parses file content
          |
    normalizer.py -- Cleans text, validates district names
          |
    transformer.py -- Maps raw JSON keys to flat schema
          |
    chunker.py    -- Splits into RAG chunks
          |
    embedder.py   -- Text -> 384-dim float vector
          |
    store.py      -- Upserts into Supabase
          |
    Supabase: district_embeddings + district_data
```

### 7.1 Parser (`parser.py`)
- Reads `.txt` and `.json` files from `project/data/` directory
- Strictly parses JSON content (structured pipeline)
- Returns either `List[Dict]` (multiple records) or `Dict` (single record)
- Extracts assessment year from filename (e.g., `telangana_2022-23.txt` -> 2022)

### 7.2 Normalizer (`normalizer.py`)
- Maintains a **canonical list of 33 official Telangana districts**
- Case-insensitive lookup with strict validation
- Raises `ValueError` for unknown districts — no Unknown fallback
- Cleans text: removes excessive whitespace, normalizes encoding

**The 33 Telangana Districts hardcoded:**
Adilabad, Bhadradri Kothagudem, Hanumakonda, Hyderabad, Jagtial, Jangaon, Jayashankar Bhupalpally, Jogulamba Gadwal, Kamareddy, Karimnagar, Khammam, Komaram Bheem Asifabad, Mahabubabad, Mahabubnagar, Mancherial, Medak, Medchal-Malkajgiri, Mulugu, Nagarkurnool, Nalgonda, Narayanpet, Nirmal, Nizamabad, Peddapalli, Rajanna Sircilla, Ranga Reddy, Sangareddy, Siddipet, Suryapet, Vikarabad, Wanaparthy, Warangal, Yadadri Bhuvanagiri

### 7.3 Transformer (`transformer.py`)
Maps raw INGRES portal JSON keys to the flat canonical schema.

**Input (INGRES API format):**
```json
{
  "locationName": "Hyderabad",
  "rechargeData": { "total": { "total": 1234.56 } },
  "stageOfExtraction": { "total": 87.5 },
  "category": { "total": "Semi-Critical" }
}
```

**Output (flat schema):**
```json
{
  "country": "India",
  "state": "Telangana",
  "district": "Hyderabad",
  "assessment_year": 2022,
  "recharge_total": 1234.56,
  "stage_of_extraction_percent": 87.5,
  "category": "Semi-Critical"
}
```

### 7.4 Chunker (`chunker.py`)

**For JSON/Structured Data:**
- One chunk per district record
- Creates human-readable sentence format:
```
In **Hyderabad** district for the year **2022**:
- The Total Annual GW Recharge is 1,234.56.
- The Stage of GW Extraction is 87.50%.
- The Categorization is Semi-Critical.
```
- Chunk ID format: `{District}_{Year}_{Index}` (e.g., `Hyderabad_2022_0`)

**For Raw Text:**
- 1000-character windows with 100-character overlap
- Splits at sentence boundaries (last period before size limit)

### 7.5 Embedder (`embedder.py`)
- Model: **`all-MiniLM-L6-v2`** from HuggingFace SentenceTransformers
- Output: **384-dimensional float vector**
- Loaded globally once (not per request) for efficiency

### 7.6 Store (`store.py`)
- **`district_embeddings` table**: Stores `(id, content, embedding, metadata)` — upsert by primary key
- **`district_data` table**: Stores structured flat records — upsert by `(district, year)` unique constraint
- Both tables have Row Level Security (RLS) enabled

---

## 8. RAG System — Retrieval-Augmented Generation

The RAG system is the core intelligence of INGRES. It lives in `backend/rag.py`.

### RAG Flow in Detail

```
User Query: "What is the stage of extraction in Nalgonda for 2022?"
                            |
                       embedder.py
                    all-MiniLM-L6-v2
                            |
               384-dimensional query vector
                            |
               Supabase RPC: match_district_embeddings
                  threshold: 0.1, top-k: 5
                            |
              Top 5 most similar text chunks
              with similarity scores
                            |
              Context string (real data from DB)
                            |
                 Gemini 2.0 Flash LLM (OpenRouter)
                 System: "Answer ONLY from context.
                          Do NOT make up numbers."
                            |
              Grounded, factual answer returned
```

### Why RAG Instead of Direct LLM?

| Approach | Problem |
|----------|---------|
| Pure LLM (ChatGPT/Gemini directly) | Hallucinates groundwater numbers, may use outdated training data |
| Direct SQL query | Cannot handle natural language; needs exact column names |
| **RAG (our approach)** | Retrieves real data, feeds to LLM, grounded factual answer |

### Retrieval: Cosine Similarity Search
The database function `match_district_embeddings` uses **cosine similarity** on pgvector:
```sql
1 - (district_embeddings.embedding <=> query_embedding) as similarity
```
- `<=>` is the cosine distance operator in pgvector
- Results filtered by `similarity > threshold`
- Returns top-k most similar chunks with metadata and content

### Generation: Gemini 2.0 Flash
- **Model**: `google/gemini-2.0-flash-001` via OpenRouter API
- **Temperature**: 0.3 (low = factual, less creative)
- **System Role**: Expert Groundwater Analyst for Telangana State Government
- **Key instruction**: Answer ONLY from provided context; do NOT make up numbers

---

## 9. Backend — FastAPI Server

Built with **FastAPI** (Python) — production-grade async REST API framework.

### API Endpoints

| Method | Endpoint | Auth Required | Purpose |
|--------|----------|---------------|---------|
| GET | `/` | No | Root health check |
| GET | `/health` | No | System status check |
| POST | `/auth/register` | No | Create new user account |
| POST | `/auth/token` | No | Login and get JWT token |
| POST | `/chat/ask` | JWT Required | Ask groundwater question (RAG) |

### `/chat/ask` Request/Response Example

```json
// Request Header:
Authorization: Bearer eyJ...

// Request Body:
{ "query": "What is the groundwater situation in Karimnagar?" }

// Response:
{
  "answer": "Based on the 2022 assessment data for Karimnagar district: The stage of extraction is 68.3%, placing it in the Safe category...",
  "context_used": "- In Karimnagar district for the year 2022: The Total Annual GW Recharge is 2,340.00 ..."
}
```

### Rate Limiting
- `/chat/ask` is limited to **5 requests per minute** per IP using SlowAPI
- Prevents abuse of the AI API (OpenRouter charges per token)

### Middleware Stack
1. **Global Exception Handler** — Catches all unhandled exceptions, returns 500 with safe message
2. **CORS Middleware** — Allows requests from localhost:3000, localhost:5173, localhost:8000
3. **Rate Limiter** — SlowAPI with fixed-window strategy

---

## 10. Database Design — Supabase + pgvector

**Supabase** is a managed PostgreSQL platform. We use it with the **pgvector** extension for vector similarity search.

### Tables

**`users`** (Authentication)
```sql
id            UUID (PK, auto)
username      TEXT (unique)
password_hash TEXT (bcrypt hashed)
role          TEXT ('user' | 'admin')
created_at    TIMESTAMP
```

**`district_data`** (Structured Groundwater Data)
```sql
id         UUID (PK, auto)
state      TEXT (default 'Telangana')
district   TEXT
year       INTEGER
metrics    JSONB  -- Full flat schema stored as JSON
created_at TIMESTAMP
UNIQUE(district, year)
```

**`district_embeddings`** (Vector Store for RAG)
```sql
id         TEXT (PK, format: "Hyderabad_2022_0")
content    TEXT   -- Human-readable chunk text
embedding  vector(384)  -- 384-dim float vector from MiniLM
metadata   JSONB  -- { district, year, source_file }
created_at TIMESTAMP
```

### Vector Search Function (SQL)
```sql
CREATE OR REPLACE FUNCTION match_district_embeddings(
  query_embedding vector(384),
  match_threshold float,
  match_count int
)
RETURNS TABLE(id text, content text, metadata jsonb, similarity float)
AS $$
  SELECT id, content, metadata,
    1 - (embedding <=> query_embedding) as similarity
  FROM district_embeddings
  WHERE 1 - (embedding <=> query_embedding) > match_threshold
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$ LANGUAGE plpgsql;
```

### Row Level Security (RLS)
- Both `district_data` and `district_embeddings` have RLS **enabled**
- Authenticated users can **read** but not write
- Service role key (backend) bypasses RLS for write operations
- All secrets are in `.env` — never committed to git

---

## 11. Frontend — React + Vite + TypeScript

Built with **React 18 + TypeScript + Vite** for a fast, type-safe development experience.

### Pages

**Home Page (`/`)**
- Landing page with animated hero section
- Gradient headline: "Chat with your Data Securely"
- Feature highlights: RAG Powered, Enterprise Security, Lightning Fast, AI Analysis
- Framer Motion animations for smooth entrance effects
- Links to Login / Get Started → routes to Chat page

**Chat Page (`/chat`)**
- Full-featured chat interface
- JWT-based login form (before authenticated)
- Message history with user / AI differentiation
- Loading states during API calls
- Source context display (shows what data was retrieved)
- Responsive design using TailwindCSS

### Tech Stack (Frontend)
- React 18 — Component-based UI
- TypeScript — Type safety
- Vite — Ultra-fast dev server and build tool
- React Router DOM — Client-side routing
- TailwindCSS — Utility-first CSS
- shadcn/ui — Pre-built accessible UI components (Button, Card, etc.)
- Framer Motion — Animation library
- Lucide React — Icon library

---

## 12. Security Architecture

### Authentication — JWT (JSON Web Tokens)
```
User Login -> Backend verifies credentials from Supabase users table
           -> Creates JWT with { sub: username, role: "user" }
           -> Signs with SECRET_KEY using HS256 algorithm
           -> Token expires in 30 minutes
           -> Frontend sends in Authorization: Bearer header
           -> Backend validates on every protected request
```

**Libraries**: `python-jose[cryptography]` for JWT, `passlib[bcrypt]` for password hashing

### Input Security (`security.py`)
- Input validation: Checks query length and rejects malicious patterns
- Input sanitization: Strips dangerous characters before passing to LLM or DB
- Prevents prompt injection attacks

### Password Security
- All passwords hashed with **bcrypt** (industry standard, salted, adaptive)
- Plain text passwords are NEVER stored
- Password verification uses constant-time comparison to prevent timing attacks

### CORS Policy
- Only allowed origins: localhost:3000, localhost:5173, localhost:8000
- All credentials allowed (for JWT cookie support)

### Rate Limiting
- 5 requests/minute on `/chat/ask`
- Fixed-window strategy via SlowAPI

---

## 13. Technology Stack

### Backend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Framework | FastAPI | REST API server |
| Server | Uvicorn | ASGI web server |
| DB Client | supabase-py | Supabase/PostgreSQL client |
| Embedding Model | SentenceTransformer (all-MiniLM-L6-v2) | Text to vector |
| LLM | Gemini 2.0 Flash via OpenRouter | Answer generation |
| Authentication | python-jose + passlib | JWT + bcrypt |
| Rate Limiting | SlowAPI | Request throttling |
| Settings | pydantic-settings | Type-safe env config |
| Logging | Python logging | Structured application logs |
| PDF Parser | pdfplumber | PDF text extraction (planned) |

### Database

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Database | Supabase (PostgreSQL 15) | Primary data store |
| Vector Extension | pgvector | 384-dim vector storage + search |
| Vector Index | IVFFlat (cosine) | Fast ANN search |
| Security | Row Level Security | Data access control |

### Frontend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | React 18 | UI rendering |
| Language | TypeScript | Type safety |
| Build Tool | Vite | Development + production bundling |
| Styling | TailwindCSS | Utility-first CSS |
| Components | shadcn/ui | Pre-built UI components |
| Animations | Framer Motion | Smooth UI animations |
| Icons | Lucide React | Vector icon set |
| Routing | React Router DOM | Client-side navigation |

### AI / ML

| Component | Technology | Details |
|-----------|-----------|---------|
| Embedding Model | all-MiniLM-L6-v2 | 384-dim, 6-layer transformer, ~22M params |
| LLM | Google Gemini 2.0 Flash | Fast, accurate, low hallucination |
| LLM Access | OpenRouter API | Unified API for multiple LLMs |
| RAG Pattern | Custom implementation | No LangChain dependency |

---

## 14. Project File Structure

```
TBP/
|-- datasets/                    <- Raw GEC datasets (Excel files)
|   |-- Annexure-1/              <- 5 files, state-level summary (BCM)
|   |-- Annexure-2/              <- 5 files, district-level summary (Ham)
|   |-- Annexure-3/              <- 5 files, block categorization counts
|   |-- Annexure-4/              <- 5 files, block names by category
|   |-- Attribute table/         <- 5 files, master 26-col block dataset
|   |-- Central/
|   |   |-- district/            <- 6 files, 153-col district GEC reports
|   |   |-- states/              <- 7 files, 153-col state GEC reports
|   |-- state/                   <- 36 dirs, one per State/UT
|   |   |-- KARNATAKA/           <- 6 files per state
|   |   |-- TELEANGANA/
|   |   |-- ... (34 more states)
|   |-- GEC User_manual.pdf      <- Official GEC methodology manual
|
|-- project/
    |-- .env                     <- Secret keys (Supabase, OpenRouter, JWT)
    |-- requirements.txt         <- Python dependencies
    |-- complete_setup.sql       <- Full Supabase schema setup SQL
    |-- run_server.bat           <- Start FastAPI server
    |-- run_ingestion.bat        <- Run data pipeline
    |-- run_frontend.bat         <- Start React dev server
    |
    |-- data/                    <- Processed input files for ingestion
    |   |-- telangana_2021-22.txt
    |   |-- telangana_2022-23.txt
    |   |-- telangana_2023-24.txt
    |   |-- telangana_2024-25.txt
    |
    |-- backend/
    |   |-- main.py              <- FastAPI app factory, middleware, routers
    |   |-- config.py            <- Pydantic settings (reads .env)
    |   |-- db.py                <- Supabase client initialization
    |   |-- auth.py              <- JWT token creation/validation
    |   |-- security.py          <- Input validation/sanitization
    |   |-- rag.py               <- RAG: retrieve_context + generate_answer
    |   |-- logger.py            <- Logging configuration
    |   |-- limiter.py           <- SlowAPI rate limiter instance
    |   |-- routers/
    |   |   |-- auth.py          <- /auth/register + /auth/token endpoints
    |   |   |-- chat.py          <- /chat/ask endpoint
    |   |-- ingestion/
    |       |-- ingest.py        <- Main pipeline orchestrator
    |       |-- parser.py        <- File reader/JSON parser
    |       |-- normalizer.py    <- Text cleaner + district validator
    |       |-- transformer.py   <- Raw JSON to flat schema mapper
    |       |-- chunker.py       <- Text/JSON to RAG chunks
    |       |-- embedder.py      <- Text to 384-dim vector
    |       |-- store.py         <- Supabase write operations
    |       |-- key_map.py       <- Allowed fields for RAG chunking
    |
    |-- frontend/
        |-- package.json         <- Node dependencies
        |-- vite.config.ts       <- Vite configuration
        |-- tailwind.config.js   <- TailwindCSS config
        |-- index.html           <- HTML entry point
        |-- src/
            |-- main.tsx         <- React root render
            |-- App.tsx          <- Router setup
            |-- pages/
            |   |-- Home.tsx     <- Landing page
            |   |-- Chat.tsx     <- Chat interface
            |-- components/
                |-- ui/          <- shadcn/ui components
```

---

## 15. How Everything Works Together — End-to-End Flow

### Phase 1: Data Preparation (Offline / One-Time Job)

```
Step 1: Export data from INGRES portal as JSON/TXT files
        -> Place in TBP/project/data/

Step 2: Run ingestion:
        python -m project.backend.ingestion.ingest

Step 3: For each file:
        a) parser.py reads and parses JSON content
        b) transformer.py maps raw keys to flat schema
        c) store.py saves structured record to district_data table
        d) chunker.py creates human-readable text chunks per district
        e) embedder.py converts each chunk to 384-dim vector
        f) store.py upserts (chunk_id, content, embedding, metadata)
           into district_embeddings table

Step 4: Supabase now has all data vectorized and indexed
```

### Phase 2: Runtime User Query

```
Step 1: User opens browser -> localhost:5173 (React frontend)

Step 2: User clicks Login -> enters username/password
        -> POST /auth/token
        -> FastAPI verifies against Supabase users table
        -> Returns JWT token

Step 3: React stores JWT, includes in all future requests

Step 4: User types: "Is Hyderabad over-exploited?"
        -> POST /chat/ask { "query": "Is Hyderabad over-exploited?" }
           with Authorization: Bearer <JWT>

Step 5: FastAPI validates JWT -> extracts user role -> allows request

Step 6: SecurityUtils.validate_input() checks query
        SecurityUtils.sanitize_input() cleans it

Step 7: retrieve_context() is called:
        a) get_embedding("Is Hyderabad over-exploited?")
           -> [0.234, -0.521, ...] (384 floats)
        b) supabase.rpc("match_district_embeddings", {
             query_embedding: [...],
             match_threshold: 0.1,
             match_count: 5
           })
        c) Returns top 5 most semantically similar chunks
        d) Formats as context string with source citations

Step 8: generate_answer(query, context) is called:
        -> Sends to Gemini 2.0 Flash via OpenRouter:
           System: "Answer ONLY from context. Don't make up numbers."
           User: context_data + query
        -> Gemini responds with factual, grounded answer

Step 9: Response returned to frontend:
        {
          "answer": "Based on 2022 data, Hyderabad has a Stage of GW Extraction of 92.1%, placing it in the Critical category...",
          "context_used": "- In Hyderabad district for the year 2022: ..."
        }

Step 10: React renders the answer in the chat interface
         User can see both the answer and the source context used
```

---

## 16. Current State — What Has Been Built

### Completed Components
- Full backend FastAPI server with auth + chat routers
- JWT authentication system (register, login, token validation)
- Complete data ingestion pipeline (parser, normalizer, transformer, chunker, embedder, store)
- RAG engine with Supabase pgvector retrieval + Gemini generation
- Supabase database schema (all tables, indexes, RLS, match function)
- React + Vite + TypeScript frontend (Home page + Chat page)
- Rate limiting (5 req/min on /chat/ask)
- Input validation and sanitization
- Row Level Security on all database tables
- **Data ingested for Telangana (4 assessment years: 2021-22 to 2024-25)**
- **Datasets uploaded: All Annexures, Attribute Tables, Central and State Reports**

### Partially Complete
- District coverage: Currently only **Telangana** is in the pipeline — 36 states' Excel files need processing
- Text files (telangana_*.txt) — parser currently returns None for pure text (needs JSON format)
- RAG match threshold (0.1) is very low — may sometimes return less relevant chunks

### Not Yet Started
- Excel -> JSON converter for the 36-state GEC datasets
- Admin panel for data management
- User dashboard and analytics
- Export functionality (PDF/CSV of chat answers)
- Multi-language support (Hindi, Telugu, etc.)

---

## 17. What Needs To Be Done Next (Upcoming Steps)

### Priority 1 — Data Pipeline (Critical)

The biggest gap: the **Excel datasets are uploaded but not ingested** into Supabase yet.

**Step A**: Build Excel to JSON converter for each dataset type:
- Read `attributeReport*.xlsx` Table sheet (8092 rows, 26 columns)
- Map each row to standard schema
- Write as JSON to `project/data/` for ingestion pipeline

**Step B**: Update `normalizer.py` to support all 36 states (currently only Telangana's 33 districts)

**Step C**: Run full ingestion for all 36 x 6 = 216 state report files

### Priority 2 — Fix Text File Parsing

The 4 existing Telangana .txt files need to be either:
- Converted to proper JSON format that the parser can handle, OR
- Parser updated to handle text with structured extraction

### Priority 3 — Improve RAG Retrieval

Once all data is ingested:
- Increase `match_count` from 5 to 10 for better context coverage
- Test and tune `match_threshold` (0.1 is very permissive)
- Add metadata pre-filtering (filter by state or year before vector search)

### Priority 4 — Production Deployment

- Deploy backend to Railway / Render (cloud)
- Deploy frontend to Vercel
- Configure environment variables in cloud
- Add HTTPS + custom domain
- Add continuous data ingestion pipeline (scheduled job)

---

## 18. Glossary

| Term | Definition |
|------|-----------|
| **GEC** | Ground Water Estimation Committee — India's official body that defines groundwater assessment methodology |
| **CGWB** | Central Ground Water Board — Government organization under Ministry of Jal Shakti |
| **INGRES** | India National Groundwater Resources Expert System — project name |
| **RAG** | Retrieval-Augmented Generation — AI pattern that retrieves relevant data before generating an answer |
| **BCM** | Billion Cubic Meters — unit for national/state-level water volumes |
| **Ham** | Hectare Meters — unit for district/block level water volumes (1 BCM = 100,000 Ham) |
| **Ha** | Hectares — unit for land area |
| **pgvector** | PostgreSQL extension for storing and searching vector embeddings |
| **IVFFlat** | Inverted File with Flat index — approximate nearest neighbor search algorithm |
| **Cosine Similarity** | Measure of similarity between two vectors based on angle between them |
| **384-dimensional** | The embedding vector size from all-MiniLM-L6-v2 — each text becomes 384 numbers |
| **Stage of Extraction** | (Total Extraction / Extractable Resource) x 100% — primary groundwater health metric |
| **Assessment Unit** | Smallest unit assessed — Block (North India), Mandal (South India), Taluka (West India) |
| **Over-Exploited (OE)** | Stage > 100% — extraction exceeds natural recharge — critical crisis indicator |
| **JWT** | JSON Web Token — a signed, encrypted token used for stateless authentication |
| **bcrypt** | Password hashing algorithm — secure, salted, computationally expensive to prevent brute force |
| **RLS** | Row Level Security — PostgreSQL feature to restrict data access per row per user |
| **CORS** | Cross-Origin Resource Sharing — browser security policy for cross-domain requests |
| **OpenRouter** | API gateway that provides unified access to multiple AI models (Gemini, GPT, Claude) |
| **SentenceTransformer** | Python library for generating semantic text embeddings using transformer models |
| **Supabase** | Open-source Firebase alternative — managed PostgreSQL with auth, storage, realtime |
| **C / NC / PQ** | Current season / Non-Current season / Poor Quality — data classification in GEC reports |

---

*Report Generated: 2026-03-28*
*Project: INGRES ChatBOT — SIH25066*
*Version: 1.0*
*Authors: TBP Team, Iteration 2*
