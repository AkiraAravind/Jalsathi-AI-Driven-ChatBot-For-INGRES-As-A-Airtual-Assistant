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

def check_schema():
    print(f"Checking schema for 'groundwater_time_series' at {url}...")
    try:
        # We can't directly get schema via client, but we can try a dummy select
        res = supabase.table("groundwater_time_series").select("*").limit(1).execute()
        if res.data:
            columns = list(res.data[0].keys())
            print(f"Columns found: {columns}")
            if "raw_metrics" in columns:
                print("✅ 'raw_metrics' column exists.")
            else:
                print("❌ 'raw_metrics' column is MISSING.")
        else:
            print("Table is empty, cannot infer columns from data.")
    except Exception as e:
        print(f"Error checking schema: {e}")

if __name__ == "__main__":
    check_schema()
