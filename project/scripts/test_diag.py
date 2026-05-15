import sys, os, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '.')
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('.env'))
load_dotenv(Path('project/.env'), override=False)

from project.backend.rag_engine import classify_query, QueryType

tests = [
    ('What is AEGR and how is it calculated?', 'manual'),
    ('Which districts in Rajasthan are trending toward Over-Exploited?', 'trend'),
    ('What is the groundwater status of Nalgonda 2022', 'data'),
    ('List over-exploited blocks in Gujarat', 'block'),
]
print('Classification tests:')
passed = 0
for q, expected in tests:
    got = classify_query(q).value
    ok = got == expected
    if ok:
        passed += 1
    status = 'OK' if ok else 'FAIL'
    print('  [%s] Expected=%-15s Got=%-15s | %s' % (status, repr(expected), repr(got), q[:45]))

print('Result: %d/%d passed' % (passed, len(tests)))

import os
from google import genai
api_key = os.getenv('GOOGLE_API_KEY')
print('GOOGLE_API_KEY loaded:', bool(api_key), '(len=%d)' % len(api_key or ''))

if api_key:
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents='Say "INGRES diagnostic OK" in exactly 4 words.'
        )
        print('Gemini SDK test:', response.text.strip())
    except Exception as e:
        print('Gemini SDK test FAILED:', e)
else:
    print('Gemini SDK test SKIPPED: no key found')

supabase_url = os.getenv('SUPABASE_URL')
supabase_anon = os.getenv('SUPABASE_ANON_KEY')
print('SUPABASE_URL:', supabase_url[:30] if supabase_url else 'MISSING')
print('SUPABASE_ANON_KEY:', 'OK' if supabase_anon else 'MISSING')
