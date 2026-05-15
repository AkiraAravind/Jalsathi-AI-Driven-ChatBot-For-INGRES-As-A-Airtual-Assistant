# INGRES: CORS, OAuth2, & Complete Tech Stack Explained

---

## 🔴 PART 1: CORS MIDDLEWARE - Why Are We Using It?

### **What is CORS?**

CORS = **Cross-Origin Resource Sharing**

It's a security mechanism that allows a browser to request resources (data, APIs) from a **different domain/port** than the one currently visiting.

### **In INGRES Context:**

**The Problem:**
```
Frontend runs on:  http://localhost:3000  (or 5173 during development)
Backend runs on:   http://localhost:8000  (different port!)

When frontend tries to call backend API:
Browser says: "BLOCKED! You're calling a different origin!"
Error: "Access to XMLHttpRequest blocked by CORS policy"
```

### **Why We Need CORS:**

```code
// In main.py (line ~65):
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],           # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],           # Allow all headers (including Authorization)
)
```

**Translation:**
- `allow_origins` = "These frontend URLs can talk to our backend"
- `allow_credentials=True` = "Allow cookies/JWT tokens to be sent"
- `allow_methods=["*"]` = "Allow all HTTP methods (GET, POST, etc.)"
- `allow_headers=["*"]` = "Allow all custom headers (especially Authorization header with JWT)"

### **Without CORS:**

```text
Frontend makes request to backend:
POST http://localhost:8000/api/chat
Headers: Authorization: Bearer <JWT_TOKEN>

Browser blocks it:
❌ CORS Error: The server doesn't explicitly allow localhost:3000
No data reaches backend
```

### **With CORS:**

```text
Frontend makes request to backend:
POST http://localhost:8000/api/chat
Headers: Authorization: Bearer <JWT_TOKEN>

Browser checks CORS config:
✅ "localhost:3000" is in allow_origins? YES
✅ Request has Authorization header? That's fine
✅ Request allows credentials? YES

Request goes through!
Backend receives it: ✓ Success
```

### **Real Flow in INGRES:**

```
1. User opens http://localhost:3000 (React frontend)
2. Clicks "Send Message" in chat
3. Frontend JavaScript does:
   fetch("http://localhost:8000/api/chat", {
       method: "POST",
       headers: {
           "Authorization": "Bearer eyJhbGc..." // JWT token
       },
       body: JSON.stringify({message: "Which states are over-exploited?"})
   })

4. Browser sees different origin (port 8000 vs 3000)
   Checks CORS config on backend

5. Backend's CORS says: "allow_origins includes localhost:3000" ✓
   Browser allows request

6. Backend receives chat request
7. Backend responds
8. Frontend displays answer
```

### **CORS for Production:**

In `docker-compose.yml` and production, CORS should be:

```python
# DEVELOPMENT (current setup - allow all localhost)
allow_origins=[
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8000",
]

# PRODUCTION (restrict to actual domain)
allow_origins=[
    "https://ingres.ai",
    "https://www.ingres.ai",
]
```

---

## 🟠 PART 2: OAuth2 & Authentication - Why Are We Using It?

### **Important Note:**
INGRES is **NOT using full OAuth2**. Instead, it uses **OAuth2PasswordBearer + JWT**.

Let me explain the difference:

### **What is OAuth2?**

OAuth2 is an **open authorization standard** for secure user authentication. It has several "flows" (methods).

**Common OAuth2 Flows:**

1. **Authorization Code Flow** (used by Google Sign-In)
   - User clicks "Login with Google"
   - Redirected to Google
   - Google asks: "Allow INGRES to access your email?"
   - User clicks "Yes"
   - Google sends token back to INGRES
   - INGRES uses token to identify user

2. **Password Flow** (what INGRES uses)
   - User enters email in login form
   - Backend generates OTP
   - User enters OTP
   - Backend issues JWT token
   - Frontend stores JWT in localStorage
   - Frontend sends JWT with every API request

### **Why We Chose OAuth2PasswordBearer (not full OAuth2):**

```text
FULL OAuth2 (Google/GitHub login):
✓ Easy for users (one click login)
✓ No password storage
✗ Requires external service integration
✗ More complex setup
✗ Dependent on third party

OAuth2PasswordBearer + JWT (INGRES):
✓ Simple to implement
✓ Works offline (no Google dependency)
✓ Fine for government/enterprise use
✗ Users must enter email manually
✗ OTP must be sent via email
```

---

## 🔐 PART 3: INGRES Authentication Flow (OAuth2PasswordBearer + JWT)

### **Step-by-Step:**

```
STEP 1: USER REGISTERS
╔════════════════════════════════════════════╗
│ Frontend: User enters email                │
│ Calls: POST /api/auth/register             │
│ Sends: {email: "user@gov.in"}              │
╚════════════════════════════════════════════╝
        ↓
STEP 2: BACKEND GENERATES OTP
╔════════════════════════════════════════════╗
│ Backend (auth_utils.py):                   │
│ 1. Generate random 6-digit OTP using pyotp│
│ 2. Store in memory: otp_store[email] = otp│
│ 3. Send via Gmail SMTP                     │
│ 4. Response: {status: "OTP sent"}          │
╚════════════════════════════════════════════╝
        ↓
STEP 3: USER ENTERS OTP
╔════════════════════════════════════════════╗
│ Frontend: User receives email with OTP     │
│ User enters: 6-digit code in login form    │
│ Calls: POST /api/auth/verify               │
│ Sends: {email: "user@gov.in", otp: "123456"}
╚════════════════════════════════════════════╝
        ↓
STEP 4: BACKEND VALIDATES & ISSUES JWT
╔════════════════════════════════════════════╗
│ Backend (auth_utils.py):                   │
│ 1. Check: otp_store[email] == "123456" ✓  │
│ 2. Delete OTP from memory (1-time use)     │
│ 3. Create JWT token with payload:          │
│    {                                       │
│        "sub": "user@gov.in",               │
│        "role": "user",                     │
│        "exp": 2026-04-12 (tomorrow),       │
│        "iat": 2026-04-11                   │
│    }                                       │
│ 4. Sign with SECRET_KEY using HS256        │
│ 5. Return: {token: "eyJhbGc..."}           │
╚════════════════════════════════════════════╝
        ↓
STEP 5: FRONTEND STORES JWT & AUTHENTICATES
╔════════════════════════════════════════════╗
│ Frontend:                                  │
│ 1. Save JWT to localStorage                │
│ 2. On next API call, add header:           │
│    Authorization: Bearer eyJhbGc...        │
│                                            │
│ Example:                                   │
│ POST /api/chat                             │
│ Headers: {                                 │
│    Authorization: "Bearer eyJhbGc..."      │
│ }                                          │
│ Body: {message: "..."}                     │
╚════════════════════════════════════════════╝
        ↓
STEP 6: BACKEND VALIDATES JWT FOR EVERY REQUEST
╔════════════════════════════════════════════╗
│ Backend (main.py line ~55):                │
│                                            │
│ oauth2_scheme = OAuth2PasswordBearer(...)  │
│                                            │
│ @app.post("/api/chat")                     │
│ async def chat_endpoint(                   │
│     request,                               │
│     user = Depends(get_current_user)  ← JWT check here
│ ):                                         │
│     # If JWT invalid: 401 Unauthorized     │
│     # If JWT valid: Proceed                │
│     # user = decoded JWT payload           │
│     user_email = user.get("sub")           │
│     user_role = user.get("role")           │
│                                            │
│ Function get_current_user:                 │
│ 1. Extract JWT from Authorization header  │
│ 2. Verify signature using SECRET_KEY       │
│ 3. Check expiry (exp > now?)               │
│ 4. If all pass: return {sub, role, iat...}│
│ 5. If fail: raise HTTPException 401        │
╚════════════════════════════════════════════╝
        ↓
STEP 7: REQUEST PROCESSES WITH USER CONTEXT
╔════════════════════════════════════════════╗
│ Backend now knows:                         │
│ - Who is the user (user.get("sub"))        │
│ - What role they have (user.get("role"))   │
│ - Save chat to chat_history with user_email
│ - Apply role-based access control         │
║                                            │
│ Example (line ~180):                       │
│ user_email = user.get("sub", "unknown")    │
│ db.table("chat_history").insert({          │
│     "session_id": sid,                     │
│     "user_email": user_email,  ← From JWT  │
│     "role": "user",                        │
│     "content": request.message             │
│ })                                         │
╚════════════════════════════════════════════╝
```

### **JWT Token Anatomy:**

```
JWT Format: HEADER.PAYLOAD.SIGNATURE

Example token:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
eyJzdWIiOiJ1c2VyQGdvdi5pbiIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxMzE5MjM5MDIyfQ.
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c

Breaking it down:

HEADER (decoded):
{
  "alg": "HS256",     ← Algorithm: HMAC SHA-256
  "typ": "JWT"        ← Type
}

PAYLOAD (decoded):
{
  "sub": "user@gov.in",           ← Subject (user email)
  "role": "user",                 ← User role
  "exp": 1319239022,              ← Expiry timestamp
  "iat": 1319234622               ← Issued at timestamp
}

SIGNATURE:
HMACSHA256(
  base64(HEADER) + "." + base64(PAYLOAD),
  "ingres_super_secret_key_change_me"  ← SECRET_KEY from .env
)
```

### **Why JWT?**

✅ **Stateless** - Backend doesn't need to store sessions
✅ **Secure** - Can't be forged without SECRET_KEY
✅ **Expiring** - Token automatically becomes invalid after 1 day
✅ **Contains user info** - No database lookup needed on every request

---

## 🟢 PART 4: Role-Based Access Control (RBAC)

INGRES implements role-based protection:

```python
# In main.py (line ~61):
async def get_current_official_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "official":
        raise HTTPException(status_code=403, detail="Insufficient permissions. Official role required.")
    return current_user
```

**Roles in INGRES:**

```
1. PUBLIC (default users)
   ✓ Can ask questions
   ✓ Can export chat
   ✗ Cannot see admin dashboard

2. OFFICIAL (government officials)
   ✓ Can ask questions
   ✓ Can export chat
   ✓ Can see admin dashboard
   ✓ Can upload data
   ✓ Can manage users

3. ADMIN (system administrators)
   ✓ Full access
   ✓ Can modify system settings
   ✓ Can manage roles
```

**Example: Admin-only endpoint**

```python
@app.get("/api/portal/dashboard-data")
async def get_dashboard_data(official_user: dict = Depends(get_current_official_user)):
    # This endpoint REQUIRES "official" role
    # If public user calls it:
    # Response: 403 Forbidden "Insufficient permissions. Official role required."
    return {...dashboard data...}
```

---

## 🔵 PART 5: Complete Tech Stack & Purpose

### **Backend Tech Stack:**

| Package | Version | Purpose | Used In |
|---------|---------|---------|---------|
| **fastapi** | Latest | Async web framework, API routing | main.py, all endpoints |
| **uvicorn** | Latest | ASGI server, runs FastAPI app | `uvicorn main:app` |
| **pydantic** | Latest | Data validation, request models | ChatRequest, AuthRequest classes |
| **supabase** | Latest | PostgreSQL + Auth client | Database operations, chat_history, users |
| **python-dotenv** | Latest | Load .env file, manage secrets | JWT_SECRET, MAIL_PASSWORD, API keys |
| **numpy** | Latest | Numerical operations | JEPA encoder, vector math |
| **pandas** | Latest | Data manipulation, CSV/Excel | Ingestion pipeline, data transformation |
| **openpyxl** | Latest | Read/write Excel files | Loading GEC dataset columns |
| **requests** | Latest | HTTP library | API calls (fallback) |
| **openai** | Latest | OpenAI client (if needed) | Alternative to OpenRouter |
| **sentence-transformers** | Latest | Embedding model wrapper | Loads multilingual-e5-large |
| **torch** | Latest | Deep learning framework | Powers sentence-transformers |
| **fastapi-mail** | Latest | Email sending | OTP delivery via SMTP |
| **pyotp** | Latest | OTP generation | 6-digit codes, TOTP |
| **python-multipart** | Latest | Form data parsing | File uploads in requests |
| **python-jose[cryptography]** | Latest | JWT token handling | JWT create, verify, sign |
| **passlib[bcrypt]** | Latest | Password hashing | User password storage |
| **psycopg2-binary** | Latest | PostgreSQL driver | Database connection |
| **reportlab** | Latest | PDF generation | Chat export to PDF |
| **PyMuPDF** | Latest | PDF manipulation | PDF reading/parsing |

### **External Services:**

| Service | Purpose | Configuration |
|---------|---------|----------------|
| **OpenRouter API** | LLM provider (Gemini 2.5 Flash) | OPENROUTER_API_KEY in .env |
| **Gmail SMTP** | Send OTP emails | MAIL_USERNAME, MAIL_PASSWORD in .env |
| **HuggingFace Models** | Embedding model (multilingual-e5-large) | Auto-downloaded on first use |
| **Supabase PostgreSQL** | Main database, pgvector extension | SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY in .env |

### **Frontend Tech Stack:**

| Package | Purpose | Used In |
|---------|---------|----------|
| **React 18** | UI framework | All Pages, Components |
| **TypeScript** | Type-safe JavaScript | .tsx files, type definitions |
| **Vite** | Fast build tool and dev server | Dev server, production build |
| **Tailwind CSS** | Styling | All CSS classes |
| **nginx** | Reverse proxy, static serving | Docker container, proxies to FastAPI |

### **Database Tech Stack:**

| Component | Purpose |
|-----------|---------|
| **PostgreSQL 15** | Relational database, stores all data |
| **pgvector** | Vector extension, stores embeddings (1024-dim) |
| **IVFFlat** | Vector index type, fast ANN search |

---

## 📊 COMPLETE DATA FLOW WITH AUTHENTICATION

```
┌──────────────────────────────────────┐
│ User Opens Browser                   │
│ http://localhost:3000                │
└──────────────────┬───────────────────┘
                   ↓
        ┌──────────────────────┐
        │ Login Page Appears   │
        │ (no JWT in storage)  │
        └──────────┬───────────┘
                   ↓
        ┌──────────────────────────────────┐
        │ User enters email                 │
        │ POST /api/auth/register          │
        │ Body: {email: "user@gov.in"}     │
        └──────────┬───────────────────────┘
                   ↓
        ┌──────────────────────────────────┐
        │ Backend (auth_utils.py):         │
        │ 1. Generate OTP: 5G2K8L          │
        │ 2. Store: otp_store[email] = OTP │
        │ 3. Gmail: Send OTP               │
        │ 4. Response: {status: "sent"}    │
        └──────────┬───────────────────────┘
                   ↓
        ┌──────────────────────────────────┐
        │ User receives email with OTP     │
        │ Enters OTP in form               │
        │ POST /api/auth/verify            │
        │ Body: {email, otp: "5G2K8L"}     │
        └──────────┬───────────────────────┘
                   ↓
        ┌──────────────────────────────────┐
        │ Backend Verifies OTP:            │
        │ ✓ otp_store[email] == "5G2K8L"   │
        │ ✓ Delete OTP (1-time use)        │
        │ ✓ Create JWT token               │
        │   Payload: {sub: email, role}    │
        │   Signed: HS256 + SECRET_KEY     │
        │   Expire: 24 hours               │
        │ Response: {token: "eyJhbGc..."}  │
        └──────────┬───────────────────────┘
                   ↓
        ┌──────────────────────────────────┐
        │ Frontend:                        │
        │ 1. Save token to localStorage    │
        │ 2. Redirect to Dashboard         │
        │ 3. Set header on all requests:   │
        │    Authorization: Bearer ...     │
        └──────────┬───────────────────────┘
                   ↓
        ┌──────────────────────────────────┐
        │ User on Dashboard (protected)    │
        │ Asks: "Over-exploited states?"   │
        │ POST /api/chat                   │
        │ Headers: {                       │
        │   Authorization: Bearer eyJ...   │
        │ }                                │
        │ Body: {message: "..."}           │
        └──────────┬───────────────────────┘
                   ↓
        ┌──────────────────────────────────┐
        │ Backend Route Handler:           │
        │ @app.post("/api/chat")           │
        │ async def chat_endpoint(         │
        │   request,                       │
        │   user = Depends(                │
        │     get_current_user  ← JWT check
        │   )                              │
        │ )                                │
        │                                  │
        │ get_current_user function:       │
        │ 1. Extract JWT from header       │
        │ 2. Verify signature (SECRET_KEY) │
        │ 3. Check expiry (exp > now)      │
        │ 4. Decode payload                │
        │ → user = {sub, role, exp, iat}   │
        │                                  │
        │ If invalid: 401 Unauthorized     │
        │ If valid: Continue ✓             │
        └──────────┬───────────────────────┘
                   ↓
        ┌──────────────────────────────────┐
        │ Process Chat Request:            │
        │ 1. user_email = user["sub"]      │
        │ 2. Call RAG Engine               │
        │ 3. Generate answer               │
        │ 4. Save to chat_history:         │
        │    - session_id: sid             │
        │    - user_email: (from JWT)      │
        │    - content: answer             │
        │ 5. Return answer to frontend     │
        └──────────┬───────────────────────┘
                   ↓
        ┌──────────────────────────────────┐
        │ Frontend Receives Response       │
        │ Displays answer in chat UI       │
        └──────────────────────────────────┘
```

---

## 🛡️ Security Summary

| Layer | Mechanism | Protection |
|-------|-----------|-----------|
| **Transport** | HTTPS (should use in prod) | Data in transit encrypted |
| **CORS** | Allow specific origins | Prevents unauthorized cross-origin requests |
| **Authentication** | OTP + JWT | Only verified users get tokens |
| **Authorization** | Role-based (public/official/admin) | Users only access allowed endpoints |
| **Token Expiry** | 24-hour JWT expiration | Tokens automatically become invalid |
| **Secrets** | .env file (not in git) | API keys/SECRET_KEY protected |
| **Database** | Role-based query filtering | Users only see their own data |

---

## 📝 Key Takeaways

✅ **CORS enabled different ports to talk to each other**
✅ **OAuth2PasswordBearer + JWT instead of full OAuth2 for simplicity**
✅ **OTP + Email for passwordless registration**
✅ **JWT tokens include user info, expire after 24 hours**
✅ **Role-based access control (RBAC) for admin/public separation**
✅ **20+ packages handling frontend, backend, ML, database, email, and more**
