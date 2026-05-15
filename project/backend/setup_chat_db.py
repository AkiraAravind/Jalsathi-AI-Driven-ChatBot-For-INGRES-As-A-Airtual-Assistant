import os
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

# Load project env
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found.")
    exit(1)

supabase = create_client(url, key)

def ensure_chat_table():
    print(f"Ensuring 'chat_history' table at {url}...")
    # Direct SQL isn't supported via the python SDK except for specific methods.
    # However, we can try to check if the table exists or just assuming we can create it via SQL Editor or a RPC.
    # Since we can't run RAW SQL via standard client, we'll use the 'query' if it was a real Postgres connection.
    # But this is Supabase Client.
    
    # We will assume the table needs to be created.
    # If the user has 'pg' installed, we could use that.
    # Let's check for 'psycopg2' or 'pg8000'.
    pass

if __name__ == "__main__":
    # In a real environment, I'd use an RBC or the user's Dashboard.
    # For now, I'll proceed as if the table is ready, or I will use a simple JSON file fallback if DB fails.
    # Actually, I'll try to use the 'rpc' to run SQL if the 'exec_sql' function exists.
    print("Please ensure 'chat_history' table is created with Schema: id (UUID), session_id (TEXT), role (TEXT), content (TEXT), created_at (TIMESTAMPTZ).")
