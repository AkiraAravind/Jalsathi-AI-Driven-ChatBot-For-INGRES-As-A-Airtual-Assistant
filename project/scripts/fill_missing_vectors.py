import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv(Path('project/.env'))

from supabase import create_client
from project.backend.ingestion.embedder import build_groundwater_narrative, embed_passages

c = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print("Fetching records with NULL semantic_vector...")
batch_size = 500
total_updated = 0

while True:
    print(f"Fetching next batch of {batch_size}...")
    res = c.table('groundwater_time_series').select('*').is_('semantic_vector', 'null').limit(batch_size).execute()
    rows = res.data
    
    if not rows:
        print("No more missing rows found.")
        break
        
    print(f"Generating narratives for {len(rows)} rows...")
    narratives = [build_groundwater_narrative(r, source=r.get('data_source', 'attribute_table')) for r in rows]
    
    print("Embedding passages (this might take a moment)...")
    embeddings = embed_passages(narratives, batch_size=16)
    
    print("Updating vectors back into Supabase...")
    for r, emb in zip(rows, embeddings):
        c.table('groundwater_time_series').update({'semantic_vector': emb.tolist()}).eq('id', r['id']).execute()
        total_updated += 1

    print(f"--> Total vectors updated so far: {total_updated}")

print(f"Data push complete! Processed {total_updated} missing records.")
