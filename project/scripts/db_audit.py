"""
Full database audit — checks what's in Supabase and what SQL functions exist.
"""
import sys, os, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '.')
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('project/.env'))

from supabase import create_client
c = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print("=" * 60)
print("  SUPABASE DATABASE AUDIT")
print("=" * 60)

# ── 1. Table row counts ─────────────────────────────────────
print("\n[1] TABLE ROW COUNTS")
tables = [
    'groundwater_time_series',
    'gec_manual_index',
    'annexure_block_risk',
]
for t in tables:
    try:
        r = c.table(t).select('id', count='exact').execute()
        print("  %-35s : %d rows" % (t, r.count))
    except Exception as e:
        print("  %-35s : ERROR - %s" % (t, str(e)[:60]))

# ── 2. Vector coverage ─────────────────────────────────────
print("\n[2] VECTOR COVERAGE")
try:
    r_gts_total = c.table('groundwater_time_series').select('id', count='exact').execute()
    r_gts_sem   = c.table('groundwater_time_series').select('id', count='exact').not_.is_('semantic_vector','null').execute()
    r_gts_jepa  = c.table('groundwater_time_series').select('id', count='exact').not_.is_('jepa_vector','null').execute()
    print("  groundwater_time_series:")
    print("    Total rows          : %d" % r_gts_total.count)
    print("    With semantic_vector: %d (%.1f%%)" % (r_gts_sem.count, 100*r_gts_sem.count/max(r_gts_total.count,1)))
    print("    With jepa_vector    : %d (%.1f%%)" % (r_gts_jepa.count, 100*r_gts_jepa.count/max(r_gts_total.count,1)))
except Exception as e:
    print("  ERROR: %s" % e)

try:
    r_gec_sem = c.table('gec_manual_index').select('id', count='exact').not_.is_('embedding','null').execute()
    print("  gec_manual_index with embedding: %d" % r_gec_sem.count)
except Exception as e:
    print("  gec_manual_index ERROR: %s" % e)

# ── 3. Data breakdown by year ───────────────────────────────
print("\n[3] GROUNDWATER DATA - BREAKDOWN BY YEAR")
try:
    r_yr = c.table('groundwater_time_series').select('assessment_year', count='exact').execute()
    from collections import Counter
    yrs = Counter(x.get('assessment_year') for x in r_yr.data)
    for yr, cnt in sorted(yrs.items()):
        print("    Year %s : %d rows" % (yr, cnt))
except Exception as e:
    print("  ERROR: %s" % e)

# ── 4. By data source ───────────────────────────────────────
print("\n[4] GROUNDWATER DATA - BY SOURCE")
try:
    r_src = c.table('groundwater_time_series').select('data_source').execute()
    srcs = Counter(x.get('data_source') for x in r_src.data)
    for src, cnt in srcs.most_common():
        print("    %-30s : %d" % (src or 'None', cnt))
except Exception as e:
    print("  ERROR: %s" % e)

# ── 5. By state ─────────────────────────────────────────────
print("\n[5] GROUNDWATER DATA - STATES COVERED")
try:
    r_st = c.table('groundwater_time_series').select('state').execute()
    states = sorted(set(x.get('state','?') for x in r_st.data if x.get('state')))
    print("    Total unique states: %d" % len(states))
    for s in states:
        cnt = sum(1 for x in r_st.data if x.get('state') == s)
        print("      %-30s : %d rows" % (s, cnt))
except Exception as e:
    print("  ERROR: %s" % e)

# ── 6. RPC Functions ────────────────────────────────────────
print("\n[6] SUPABASE RPC FUNCTIONS (checking via test calls)")
import numpy as np
test_vec = np.random.randn(1024).astype(np.float32)
test_vec /= np.linalg.norm(test_vec)

rpc_tests = [
    ('search_gec_manual',           {'query_embedding': test_vec.tolist(), 'match_threshold': 0.01, 'match_count': 1}),
    ('search_groundwater_semantic', {'query_embedding': test_vec.tolist(), 'match_threshold': 0.01, 'match_count': 1, 'filter_state': None, 'filter_district': None, 'filter_year': None, 'filter_category': None}),
    ('search_groundwater_jepa',     {'query_jepa_vector': test_vec.tolist(), 'match_threshold': 0.01, 'match_count': 1, 'filter_state': None, 'min_velocity': 0.0, 'filter_trend': None}),
    ('search_at_risk_blocks',       {'query_embedding': test_vec.tolist(), 'match_threshold': 0.01, 'match_count': 1, 'filter_state': None, 'filter_district': None, 'filter_category': None, 'filter_year': None}),
    ('bulk_update_jepa',            None),  # Skip call test for this one
]
for fn_name, params in rpc_tests:
    if params is None:
        print("  %-35s : NOT TESTED (write function)" % fn_name)
        continue
    try:
        r = c.rpc(fn_name, params).execute()
        print("  %-35s : EXISTS [SUCCESS] (returned %d rows)" % (fn_name, len(r.data)))
    except Exception as e:
        err = str(e)
        if 'PGRST202' in err or 'function' in err.lower() or 'does not exist' in err.lower():
            print("  %-35s : MISSING [FAIL] - needs to be created" % fn_name)
        else:
            print("  %-35s : ERROR - %s" % (fn_name, err[:80]))

print("\n" + "=" * 60)
print("  AUDIT COMPLETE")
print("=" * 60)
