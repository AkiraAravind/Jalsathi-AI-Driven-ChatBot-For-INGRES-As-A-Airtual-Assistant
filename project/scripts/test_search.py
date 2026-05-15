"""Test search_groundwater_semantic with real query embedding."""
import sys, os, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '.')
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('.env'))
load_dotenv(Path('project/.env'), override=False)

from supabase import create_client
from project.backend.ingestion.embedder import embed_query

c_anon = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
c_svc = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print("Embedding query...")
vec = embed_query("query: groundwater status Telangana district 2022")
print(f"Vector dim: {len(vec.tolist())}, norm: {float((vec**2).sum()**0.5):.4f}")

print("\nTesting search_groundwater_semantic (anon key, threshold=0.1)...")
try:
    r = c_anon.rpc('search_groundwater_semantic', {
        'query_embedding': vec.tolist(),
        'match_threshold': 0.1,
        'match_count': 5,
        'filter_state': None,
        'filter_district': None,
        'filter_year': None,
        'filter_category': None
    }).execute()
    print(f"Results (anon): {len(r.data)}")
    for row in r.data[:3]:
        print(f"  {row.get('state')}/{row.get('district')} Year={row.get('assessment_year')} Stage={row.get('stage_of_extraction_pct')} Sim={row.get('similarity',0):.3f}")
except Exception as e:
    print(f"ERROR (anon): {e}")

print("\nTesting with service role key, threshold=0.1...")
try:
    r2 = c_svc.rpc('search_groundwater_semantic', {
        'query_embedding': vec.tolist(),
        'match_threshold': 0.1,
        'match_count': 5,
        'filter_state': None,
        'filter_district': None,
        'filter_year': None,
        'filter_category': None
    }).execute()
    print(f"Results (svc): {len(r2.data)}")
    for row in r2.data[:3]:
        print(f"  {row.get('state')}/{row.get('district')} Year={row.get('assessment_year')} Stage={row.get('stage_of_extraction_pct')} Sim={row.get('similarity',0):.3f}")
except Exception as e:
    print(f"ERROR (svc): {e}")

print("\nCheck: How many rows have semantic_vector?")
cnt = c_svc.table('groundwater_time_series').select('id', count='exact').not_.is_('semantic_vector','null').execute()
print(f"  Rows with vector: {cnt.count}")
