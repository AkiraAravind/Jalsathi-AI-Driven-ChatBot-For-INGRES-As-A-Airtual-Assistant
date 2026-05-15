"""Quick summary check for Phase 3 test results."""
import sys, os, logging
logging.disable(logging.CRITICAL)
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, '.')
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('.env'))
load_dotenv(Path('project/.env'), override=False)

from project.backend.rag_engine import (
    classify_query, extract_entities, detect_language, QueryType,
    INGRESRetriever, INGRESChatEngine
)

print("=" * 55)
print("  PHASE 3 VERIFICATION SUMMARY")
print("=" * 55)

results = []

# T1: Classifier (4 tests)
cls_tests = [
    ("What is AEGR and how is it calculated?", "manual"),
    ("Which districts in Rajasthan are trending toward Over-Exploited?", "trend"),
    ("What is the groundwater status of Nalgonda 2022", "data"),
    ("List over-exploited blocks in Gujarat", "block"),
]
all_ok = True
for q, exp in cls_tests:
    got = classify_query(q).value
    ok = got == exp
    if not ok: all_ok = False
    print("[%s] %-6s => %s" % ("OK" if ok else "FAIL", exp, q[:45]))
results.append(("T1 Query Classifier (4/4)", all_ok))

# T2: Language
ld_ok = (detect_language("भूजल क्या है?") == "hi" and
         detect_language("What is AEGR?") == "en")
print("[%s] Language detection" % ("OK" if ld_ok else "FAIL"))
results.append(("T2 Language Detection", ld_ok))

# T3: Entities
ent = extract_entities("Nalgonda district Telangana 2022 over-exploited")
e_ok = ent.get("state") == "Telangana" and ent.get("year") == 2022 and ent.get("category") == "Over-Exploited"
print("[%s] Entity extraction: %s" % ("OK" if e_ok else "FAIL", ent))
results.append(("T3 Entity Extraction", e_ok))

# T4: Manual retrieval
try:
    r = INGRESRetriever()
    m = r.search_manual("What is AEGR? How is Annual Extractable Ground Water Resource derived?", k=3)
    m_ok = len(m) > 0
    print("[%s] GEC Manual retrieved %d chunks (top sim=%.3f)" % (
        "OK" if m_ok else "FAIL", len(m),
        max((d.get("similarity",0) for d in m), default=0)
    ))
    results.append(("T4 GEC Manual Retrieval", m_ok))
except Exception as e:
    print("[FAIL] GEC Manual: %s" % str(e)[:60])
    results.append(("T4 GEC Manual Retrieval", False))
    r = None

# T5: Data retrieval
try:
    if r is None: r = INGRESRetriever()
    d = r.search_data("groundwater Telangana mandal", state="TELANGANA", k=3)
    d_ok = len(d) > 0
    print("[%s] Data retrieval: %d records" % ("OK" if d_ok else "FAIL", len(d)))
    if d:
        row = d[0]
        print("    Sample: %s/%s Year=%s Stage=%s" % (
            row.get("state","?"), row.get("district","?"),
            row.get("assessment_year","?"), row.get("stage_of_extraction_pct","?")
        ))
    results.append(("T5 Data Retrieval", d_ok))
except Exception as e:
    print("[FAIL] Data retrieval: %s" % str(e)[:60])
    results.append(("T5 Data Retrieval", False))

# T6: Gemini RAG
try:
    engine = INGRESChatEngine()
    resp = engine.chat("What is AEGR and how is it derived from Total Annual Ground Water Recharge?")
    ans = resp.get("answer", "")
    g_ok = len(ans) > 50 and "technical error" not in ans.lower()
    print("[%s] Gemini response (%d chars, %d citations)" % (
        "OK" if g_ok else "WARN", len(ans), len(resp.get("citations", []))
    ))
    print("    Excerpt: %s" % ans[:120].replace("\n"," "))
    results.append(("T6 Gemini RAG Answer", g_ok))
except Exception as e:
    print("[FAIL] Gemini: %s" % str(e)[:80])
    results.append(("T6 Gemini RAG Answer", False))

# T7: Hindi
try:
    hi_resp = engine.chat("भारत में भूजल की स्थिति क्या है?")
    h_ok = hi_resp.get("language") == "hi"
    print("[%s] Hindi query: lang=%s" % ("OK" if h_ok else "FAIL", hi_resp.get("language")))
    results.append(("T7 Multilingual Hindi", h_ok))
except Exception as e:
    print("[FAIL] Hindi: %s" % str(e)[:60])
    results.append(("T7 Multilingual Hindi", False))

# Summary
passed = sum(1 for _, ok in results if ok)
print("=" * 55)
print("  RESULTS: %d/%d PASSED" % (passed, len(results)))
print("=" * 55)
for name, ok in results:
    print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
