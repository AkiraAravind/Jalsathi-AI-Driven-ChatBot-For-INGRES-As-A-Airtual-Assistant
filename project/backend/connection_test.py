import os
import requests
import logging
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

# Load project env
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("connection_test")

def test_supabase():
    log.info("Testing Supabase connectivity...")
    if not SUPABASE_URL or not SUPABASE_KEY:
        log.error("❌ SUPABASE_URL or KEY missing in project/.env")
        return False
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Try a simple count
        res = supabase.table("groundwater_time_series").select("count", count="exact").limit(1).execute()
        log.info(f"✅ Supabase connected. Row count in GTS: {res.count}")
        
        # Check chat_history table
        try:
            supabase.table("chat_history").select("count", count="exact").limit(1).execute()
            log.info("✅ 'chat_history' table verified.")
        except:
             log.warning("⚠️ 'chat_history' table missing. Run SQL: CREATE TABLE chat_history (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), session_id TEXT, role TEXT, content TEXT, created_at TIMESTAMPTZ DEFAULT now());")
        
        return True
    except Exception as e:
        log.error(f"❌ Supabase connection failed: {e}")
        return False

def test_backend_api():
    log.info("Testing Backend FastAPI connectivity...")
    # This assumes main.py is running on 8000
    try:
        response = requests.get("http://localhost:8000/Health")
        if response.status_code == 200:
            log.info("✅ Backend Health Check passed.")
            return True
        else:
            log.info(f"⚠️  Backend returned status {response.status_code}")
            return False
    except:
        log.warning("⚠️  Backend API not running on localhost:8000 (Expected if not started yet)")
        return False

if __name__ == "__main__":
    s_ok = test_supabase()
    b_ok = test_backend_api()
    print("\n" + "="*30)
    print(f"SUPABASE: {'READY' if s_ok else 'FAILED'}")
    print(f"BACKEND:  {'READY' if b_ok else 'NOT RUNNING'}")
    print("="*30)
