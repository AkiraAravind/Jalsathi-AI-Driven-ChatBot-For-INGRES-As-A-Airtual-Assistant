import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

def execute_sql(sql):
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(sql)
        cursor.close()
        conn.close()
        logging.info("Successfully executed SQL block.")
    except Exception as e:
        logging.error(f"SQL execution failed: {e}")

sql_script = """
-- Ensure normal users can log in
INSERT INTO users (username, email, password_hash, full_name, role) 
VALUES ('official_admin', 'official@ingres.ai', 'not_used_otp', 'Admin Official', 'official')
ON CONFLICT (email) DO NOTHING;

-- Create chat_history table
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    user_email TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    chart_json JSONB,
    citations JSONB,
    language TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""
if __name__ == "__main__":
    execute_sql(sql_script)
