import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv(Path('project/.env'))

from supabase import create_client
from project.backend.ingestion.embedder import embed_passages

c = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

try:
    print("Fetching records from gec_manual_index with NULL embedding...")
    res = c.table('gec_manual_index').select('id, content, section_title').is_('embedding', 'null').execute()
    rows = res.data

    if not rows:
        print("No missing manual embeddings found!")
        sys.exit(0)

    print(f"Generating embeddings for {len(rows)} manual chunks...")
    
    # We enrich the embed text slightly with the section title for better search
    valid_rows = [r for r in rows if r.get('content')]
    valid_texts = [f"{r.get('section_title', 'GEC Manual')}: {r['content']}" for r in valid_rows]

    embeddings = embed_passages(valid_texts, batch_size=16)

    print("Updating vectors back into Supabase gec_manual_index...")
    total_updated = 0
    for r, emb in zip(valid_rows, embeddings):
        c.table('gec_manual_index').update({'embedding': emb.tolist()}).eq('id', r['id']).execute()
        total_updated += 1
        
    print(f"[SUCCESS] Data push complete! Processed {total_updated} manual records.")

except Exception as e:
    print(f"Error occurred: {e}")
