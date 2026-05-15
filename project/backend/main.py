import sys
import json
import logging
import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[2]
sys.path.append(str(root_dir))

from project.backend.rag_engine import INGRESChatEngine
from project.backend.auth_utils import (
    send_otp_email, send_feedback_email, generate_otp, 
    otp_store, create_access_token, verify_access_token
)

import os
from supabase import create_client
from project.backend.mock_supabase import create_mock_client

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingres_api")

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Try to create real Supabase client, fall back to mock if unavailable
try:
    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
        logger.info("✓ Supabase client initialized (real)")
        using_mock_db = False
    else:
        raise Exception("Missing Supabase credentials")
except Exception as e:
    logger.warning(f"⚠ Supabase unavailable ({str(e)}), using mock client for development")
    supabase = create_mock_client()
    using_mock_db = True


def db_execute(operation):
    """Execute DB operations and switch to mock DB if real Supabase is unreachable."""
    global supabase, using_mock_db
    try:
        return operation(supabase)
    except Exception as exc:
        if not using_mock_db:
            logger.warning(f"Supabase query failed, switching to mock DB: {exc}")
            supabase = create_mock_client()
            using_mock_db = True
            return operation(supabase)
        raise


def run_db_query(query_obj):
    """Execute Supabase-style query builders, or return immediate mock responses as-is."""
    return query_obj.execute() if hasattr(query_obj, "execute") else query_obj

app = FastAPI(title="INGRES AI ChatBOT API", version="1.0.0")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return payload

async def get_current_official_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "official":
        raise HTTPException(status_code=403, detail="Insufficient permissions. Official role required.")
    return current_user

# Enable CORS for React frontend (Vite range for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG Engine
chat_engine = INGRESChatEngine()

@app.on_event("startup")
async def startup_event():
    """Optionally pre-load embeddings at startup; auth endpoints should not be blocked by model warmup."""
    preload_model = os.getenv("PRELOAD_EMBEDDINGS_ON_STARTUP", "1").lower() in ("1", "true", "yes", "on")
    if not preload_model:
        logger.info("Skipping embedding preload at startup (set PRELOAD_EMBEDDINGS_ON_STARTUP=1 to enable).")
        return

    logger.info("Initializing HuggingFace Embedding Model...")
    try:
        from project.backend.ingestion.embedder import _get_model
        _get_model()
        logger.info("Embedding Model loaded successfully. Server is ready for fast queries.")
    except Exception as exc:
        # Keep API alive even if model warmup fails; model can be loaded lazily on first chat request.
        logger.warning(f"Embedding preload failed during startup: {exc}")

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    uploaded_context: Optional[str] = None
    stream: Optional[bool] = False

class ChatResponse(BaseModel):
    answer: str
    citations: List[str]
    chart: Optional[Dict[str, Any]] = None
    language: str
    query_type: str

class AuthRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = "user"

class VerifyRequest(BaseModel):
    email: EmailStr
    otp: str

class FeedbackRequest(BaseModel):
    email: str
    message: str

@app.get("/")
@app.get("/Health")
async def root():
    return {"status": "online", "message": "INGRES AI Backend is operational"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, user: dict = Depends(get_current_user)):
    try:
        logger.info(f"Received query: {request.message}")

        # Determine actual session id (engine might create one or we default)
        sid = request.session_id or "default_session"
        user_email = user.get("sub", "unknown")
        engine_sid = f"{user_email}:{sid}"

        if request.stream:
            def stream_events():
                final_payload = None
                try:
                    for event in chat_engine.chat_stream(
                        request.message,
                        session_id=engine_sid,
                        uploaded_context=request.uploaded_context,
                    ):
                        if event.get("type") == "final":
                            final_payload = event
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except Exception as exc:
                    err = {"type": "error", "message": str(exc)}
                    yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"
                    return

                if final_payload and supabase:
                    try:
                        db_execute(lambda db: run_db_query(db.table("chat_history").insert({
                            "session_id": sid,
                            "user_email": user_email,
                            "role": "user",
                            "content": request.message
                        })))

                        db_execute(lambda db: run_db_query(db.table("chat_history").insert({
                            "session_id": sid,
                            "user_email": user_email,
                            "role": "assistant",
                            "content": final_payload.get("answer", ""),
                            "citations": final_payload.get("citations", []),
                            "chart_json": final_payload.get("chart", None),
                            "language": final_payload.get("language", "en")
                        })))
                    except Exception as e:
                        logger.error(f"Failed to persist streamed chat history: {e}")

            return StreamingResponse(stream_events(), media_type="text/event-stream")

        result = chat_engine.chat(request.message, session_id=engine_sid, uploaded_context=request.uploaded_context)
        
        if supabase:
            try:
                # Save User Message
                db_execute(lambda db: run_db_query(db.table("chat_history").insert({
                    "session_id": sid,
                    "user_email": user_email,
                    "role": "user",
                    "content": request.message
                })))
                
                # Save Assistant Message
                db_execute(lambda db: run_db_query(db.table("chat_history").insert({
                    "session_id": sid,
                    "user_email": user_email,
                    "role": "assistant",
                    "content": result["answer"],
                    "citations": result.get("citations", []),
                    "chart_json": result.get("chart", None),
                    "language": result.get("language", "en")
                })))
            except Exception as e:
                logger.error(f"Failed to persist chat history: {e}")
        
        return ChatResponse(
            answer=result["answer"],
            citations=result["citations"],
            chart=result["chart"],
            language=result["language"],
            query_type=result["query_type"]
        )
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history")
async def get_chat_history(user: dict = Depends(get_current_user)):
    # Fetch distinct sessions for the user, ordered by latest
    # Since Supabase python client doesn't support complex distinct easily, we fetch all and group
    user_email = user.get("sub")
    res = db_execute(lambda db: run_db_query(db.table("chat_history").select("*").eq("user_email", user_email).order("created_at", desc=True)))
    
    # Group by session
    sessions_map = {}
    for idx, row in enumerate(res.data or []):
        sid = row["session_id"]
        if sid not in sessions_map:
            # Try to construct a title from the first user message we see (which is the most recent, so maybe not first)
            sessions_map[sid] = {
                "id": sid,
                "title": f"Session {sid[:6]}...",
                "date": row["created_at"][:10],
                "messages": []
            }
        
        # Optionally, reverse order later so oldest is first
        sessions_map[sid]["messages"].append({
            "id": row.get("id", f"{sid}-{idx}"),
            "role": row["role"],
            "content": row["content"],
            "citations": row.get("citations"),
            "chart": row.get("chart_json"),
            "language": row.get("language")
        })
    
    # Reverse messages in each session so they are chronological
    for sid in sessions_map:
        sessions_map[sid]["messages"] = sessions_map[sid]["messages"][::-1]
        
    return {"status": "success", "sessions": list(sessions_map.values())}

class ExportRequest(BaseModel):
    session_id: str
    messages: Optional[List[Dict[str, Any]]] = None


def _resolve_export_messages(request: ExportRequest, user_email: str) -> List[Dict[str, Any]]:
    """Resolve messages for export with DB lookup and safe fallbacks."""
    res = db_execute(lambda db: run_db_query(
        db.table("chat_history")
        .select("*")
        .eq("session_id", request.session_id)
        .eq("user_email", user_email)
        .order("created_at")
    ))
    rows = res.data or []
    if rows:
        return rows

    # Fallback: use client-provided messages for export when DB is unavailable
    # or session history is not yet persisted.
    if request.messages:
        normalized = []
        for m in request.messages:
            normalized.append({
                "role": m.get("role", "assistant"),
                "content": m.get("content", ""),
                "citations": m.get("citations", []),
            })
        return normalized

    # Last fallback: export latest user conversation rows if session-specific lookup is empty.
    latest = db_execute(lambda db: run_db_query(
        db.table("chat_history")
        .select("*")
        .eq("user_email", user_email)
        .order("created_at", desc=True)
        .limit(100)
    ))
    latest_rows = latest.data or []
    if latest_rows:
        return list(reversed(latest_rows))

    return []

@app.post("/api/chat/export")
async def export_chat(request: ExportRequest, user: dict = Depends(get_current_user)):
        
    user_email = user.get("sub")
    export_messages = _resolve_export_messages(request, user_email)

    if not export_messages:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Import locally to avoid cyclic or missing deps at startup if reportlab breaks
    from project.backend.pdf_utils import generate_chat_pdf
    pdf_path = generate_chat_pdf(export_messages, request.session_id)
    
    # Send email with attachment
    from project.backend.auth_utils import send_pdf_email
    try:
        await send_pdf_email(user_email, pdf_path)
        return {"status": "success", "message": "Chat exported and emailed"}
    except Exception as e:
        logger.error(f"Export email error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email")


@app.post("/api/chat/export/download")
async def export_chat_download(request: ExportRequest, user: dict = Depends(get_current_user)):
    user_email = user.get("sub")
    export_messages = _resolve_export_messages(request, user_email)

    if not export_messages:
        raise HTTPException(status_code=404, detail="Session not found")

    from project.backend.pdf_utils import generate_chat_pdf
    pdf_path = generate_chat_pdf(export_messages, request.session_id)
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="Failed to generate PDF")

    filename = f"ingres-chat-{request.session_id}.pdf"
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename,
    )

from fastapi import UploadFile, File
import fitz # PyMuPDF
import io

@app.post("/api/chat/upload")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not file.filename.lower().endswith(('.pdf', '.txt')):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported.")
    try:
        content = await file.read()
        extracted_text = ""
        
        if file.filename.lower().endswith('.pdf'):
            doc = fitz.open(stream=content, filetype="pdf")
            for page in doc:
                extracted_text += page.get_text() + "\n"
        else:
            extracted_text = content.decode('utf-8', errors='ignore')
            
        return {"status": "success", "extracted_context": extracted_text[:20000]} # Limit size
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=400, detail="Failed to extract text from file")

@app.post("/api/auth/register")
async def register(request: AuthRequest):
    # Check if user already exists
    response = db_execute(lambda db: run_db_query(db.table("users").select("email").eq("email", request.email)))
    if response.data and len(response.data) > 0:
        raise HTTPException(status_code=400, detail="User already registered. Please log in.")

    code = generate_otp()
    # Store temporary registration data
    otp_store[request.email] = {
        "otp": code, 
        "role": request.role or "user", 
        "name": request.name or "Citizen",
        "is_register": True
    }
    await send_otp_email(request.email, code)
    return {"status": "success", "message": f"OTP sent to {request.email} (Mock OTP: {code})"}

@app.post("/api/auth/login")
async def login(request: AuthRequest):
    # Strictly check if user exists before sending OTP
    response = db_execute(lambda db: run_db_query(db.table("users").select("*").eq("email", request.email)))
    if not response.data or len(response.data) == 0:
        raise HTTPException(status_code=404, detail="Email not registered in the system.")
    
    user_data = response.data[0]
    
    code = generate_otp()
    # Pull role and name from DB to prevent privilege escalation via request
    otp_store[request.email] = {
        "otp": code, 
        "role": user_data.get("role", "user"),
        "name": user_data.get("full_name", "Citizen"),
        "is_register": False
    }
    await send_otp_email(request.email, code)
    return {"status": "success", "message": f"OTP sent to {request.email} (Mock OTP: {code})"}

@app.post("/api/auth/verify")
async def verify(request: VerifyRequest):
    if request.email in otp_store:
        record = otp_store[request.email]
        if record["otp"] == request.otp:
            # If this is a new registration, commit it to the DB now that it's verified
            if record.get("is_register"):
                if supabase:
                    username = request.email.split('@')[0]
                    db_execute(lambda db: run_db_query(db.table("users").insert({
                        "email": request.email,
                        "full_name": record["name"],
                        "role": record["role"],
                        "username": username,
                        "password_hash": "not_used_otp"
                    })))
            
            # Generate JWT with email and role
            access_token = create_access_token(data={
                "sub": request.email,
                "role": record["role"],
                "name": record.get("name", "Citizen")
            })
            
            # Cleanup OTP
            del otp_store[request.email]
            
            return {
                "status": "success", 
                "token": access_token,
                "role": record["role"],
                "name": record.get("name", "Citizen"),
                "message": "Authorized"
            }
    
    raise HTTPException(status_code=401, detail="Invalid or expired OTP")

class ResendOTPRequest(BaseModel):
    email: EmailStr

@app.post("/api/auth/resend-otp")
async def resend_otp(request: ResendOTPRequest):
    if request.email not in otp_store:
        raise HTTPException(status_code=400, detail="No active registration/login session found.")
    
    code = generate_otp()
    otp_store[request.email]["otp"] = code
    await send_otp_email(request.email, code)
    return {"status": "success", "message": f"OTP resent to {request.email} (Mock OTP: {code})"}

class ProfileUpdateRequest(BaseModel):
    name: str

@app.post("/api/auth/profile")
async def update_profile(request: ProfileUpdateRequest, user: dict = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        db_execute(lambda db: run_db_query(db.table("users").update({"full_name": request.name}).eq("email", user.get("sub"))))
        return {"status": "success", "message": "Profile updated"}
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")

@app.post("/api/feedback")
async def feedback(request: FeedbackRequest):
    await send_feedback_email(request.email, request.message)
    return {"status": "success", "message": "Feedback relayed"}

@app.get("/api/verify-gemini")
@app.get("/api/verify-openrouter")
async def verify_openrouter():
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return {"status": "warning", "key_provided": False, "message": "OPENROUTER_API_KEY is missing"}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        response = client.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": "Reply with the single word: OK"}],
            max_tokens=10,
        )
        text = (response.choices[0].message.content or "").strip()
        return {"status": "online", "key_provided": True, "message": "Verified OpenRouter Link", "sample": text[:32]}
    except Exception as e:
        return {
            "status": "warning",
            "key_provided": True,
            "message": "OpenRouter verification failed",
            "detail": str(e)
        }

@app.get("/api/portal/dashboard-data")
async def get_portal_dashboard_data(user: dict = Depends(get_current_official_user)):
    try:
        res = db_execute(lambda db: run_db_query(
            db.table("groundwater_time_series")
            .select("state,assessment_year,stage_of_extraction_pct,assessment_unit,district")
            .order("assessment_year", desc=True)
        ))

        rows = res.data or []
        if not rows:
            return {
                "status": "success",
                "data": {
                    "summary": {
                        "extraction_avg": 0.0,
                        "at_risk_blocks": 0,
                        "monitored_states": 0,
                        "latest_year": None,
                    },
                    "state_levels": [],
                    "critical_states": [],
                    "healthy_states": [],
                    "source": "live",
                },
            }

        state_agg: Dict[str, Dict[str, Any]] = {}
        global_latest_year = None

        for row in rows:
            state = row.get("state")
            year = row.get("assessment_year")
            stage = row.get("stage_of_extraction_pct")
            if not state or year is None or stage is None:
                continue
            try:
                stage_f = float(stage)
                year_i = int(year)
            except (TypeError, ValueError):
                continue

            if global_latest_year is None or year_i > global_latest_year:
                global_latest_year = year_i

            bucket = state_agg.get(state)
            if not bucket or year_i > bucket["year"]:
                state_agg[state] = {
                    "year": year_i,
                    "sum": stage_f,
                    "count": 1,
                }
            elif year_i == bucket["year"]:
                bucket["sum"] += stage_f
                bucket["count"] += 1

        state_levels = []
        for state, bucket in state_agg.items():
            if bucket["count"] <= 0:
                continue
            avg_stage = round(bucket["sum"] / bucket["count"], 2)
            state_levels.append({
                "state": state,
                "level": avg_stage,
                "year": bucket["year"],
            })

        state_levels.sort(key=lambda x: x["state"])

        extraction_avg = round(sum(x["level"] for x in state_levels) / len(state_levels), 2) if state_levels else 0.0
        critical_states = sorted(state_levels, key=lambda x: x["level"], reverse=True)[:5]
        healthy_states = sorted(state_levels, key=lambda x: x["level"])[:5]

        at_risk_blocks = 0
        if global_latest_year is not None:
            for row in rows:
                year = row.get("assessment_year")
                stage = row.get("stage_of_extraction_pct")
                try:
                    if int(year) == global_latest_year and float(stage) >= 100.0:
                        at_risk_blocks += 1
                except (TypeError, ValueError):
                    continue

        return {
            "status": "success",
            "data": {
                "summary": {
                    "extraction_avg": extraction_avg,
                    "at_risk_blocks": at_risk_blocks,
                    "monitored_states": len(state_levels),
                    "latest_year": global_latest_year,
                },
                "state_levels": state_levels,
                "critical_states": critical_states,
                "healthy_states": healthy_states,
                "source": "live",
            },
        }
    except Exception as e:
        logger.error(f"Portal dashboard live data fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load portal dashboard data")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
