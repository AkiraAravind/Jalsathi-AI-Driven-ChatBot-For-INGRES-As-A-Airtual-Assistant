"""Check vector population in database."""
from supabase import create_client
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path('project/.env'))
c = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

# Total rows
r_total = c.table('groundwater_time_series').select('id', count='exact').execute()
print('groundwater_time_series total:', r_total.count)

# With semantic vector
r_vec = c.table('groundwater_time_series').select('id,state,assessment_year').not_.is_('semantic_vector', 'null').limit(5).execute()
print('Rows with semantic_vector (sample 5):', len(r_vec.data))
for row in r_vec.data:
    print(' ', row.get('state'), row.get('assessment_year'))

# GEC manual
r_manual = c.table('gec_manual_index').select('id', count='exact').not_.is_('embedding', 'null').execute()
print('gec_manual_index with vector:', r_manual.count)

# Check sample with actual vector value type
sample = c.table('gec_manual_index').select('id,content,embedding').limit(1).execute()
if sample.data:
    row = sample.data[0]
    vec = row.get('embedding')
    print('Manual chunk has vector:', vec is not None, 'type:', type(vec).__name__, 'len:', len(vec) if vec else 0)
