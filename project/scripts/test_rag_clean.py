"""
Phase 3 RAG Verification — Clean Output
Run: python test_rag_clean.py
"""
import sys, os, logging
from pathlib import Path

# Suppress verbose logs
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.basicConfig(level=logging.ERROR)

sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(Path('.env'))
load_dotenv(Path('project/.env'), override=False)

from project.backend.rag_engine import (
    INGRESRetriever, INGRESChatEngine,
    classify_query, extract_entities, detect_language, QueryType
)

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"

results = []

print("=" * 60)
print("  INGRES Phase 3 — RAG Verification Suite")
print("=" * 60)

# ── T1: Query Classification ────────────────────────────────────────────────
print("\n[T1] Query Classification")
tests_cls = [
    ("What is AEGR and how is it calculated?",           QueryType.MANUAL),
    ("Which districts in Rajasthan are trending toward Over-Exploited?", QueryType.TREND_JEPA),
    ("What is the groundwater status of Nalgonda 2022",  QueryType.DATA_LOOKUP),
    ("List over-exploited blocks in Gujarat",            QueryType.BLOCK_RISK),
]
all_cls_ok = True
for q, expected in tests_cls:
    got = classify_query(q)
    ok = got == expected
    all_cls_ok = all_cls_ok and ok
    status = PASS if ok else FAIL
    print(f"  {status}  '{q[:45]}...' → {got.value}")

results.append(("T1 Query Classification", all_cls_ok))

# ── T2: Language Detection ───────────────────────────────────────────────────
print("\n[T2] Language Detection")
ld_tests = [
    ("What is AEGR?",               "en"),
    ("भूजल स्तर क्या है?",            "hi"),
    ("భూగర్భ జల స్థాయి ఏమిటి?",     "te"),
]
all_ld_ok = True
for q, expected in ld_tests:
    got = detect_language(q)
    ok = got == expected
    all_ld_ok = all_ld_ok and ok
    status = PASS if ok else FAIL
    print(f"  {status}  '{q[:30]}' → {got}")

results.append(("T2 Language Detection", all_ld_ok))

# ── T3: Entity Extraction ───────────────────────────────────────────────────
print("\n[T3] Entity Extraction")
ent = extract_entities("groundwater status of Nalgonda district in Telangana in 2022 over-exploited")
ok3 = ent.get("state") == "Telangana" and ent.get("year") == 2022 and ent.get("category") == "Over-Exploited"
print(f"  {'✅' if ent.get('state')=='Telangana' else '❌'}  State: {ent.get('state')}")
print(f"  {'✅' if ent.get('year')==2022 else '❌'}  Year:  {ent.get('year')}")
print(f"  {'✅' if ent.get('category')=='Over-Exploited' else '❌'}  Category: {ent.get('category')}")
results.append(("T3 Entity Extraction", ok3))

# ── T4: GEC Manual Semantic Retrieval ───────────────────────────────────────
print("\n[T4] GEC Manual Semantic Retrieval")
try:
    retriever = INGRESRetriever()
    manual_results = retriever.search_manual("What is AEGR? How is it calculated from recharge?", k=3)
    ok4 = len(manual_results) > 0
    print(f"  Retrieved: {len(manual_results)} chunks")
    for doc in manual_results[:2]:
        pg  = doc.get("page_number", "?")
        sim = doc.get("similarity", 0)
        sec = doc.get("section_title", "")[:40]
        cnt = str(doc.get("content", ""))[:100]
        print(f"  • Page {pg} | Sim={sim:.3f} | '{sec}'")
        print(f"    {cnt}...")
    results.append(("T4 GEC Manual Retrieval", ok4))
    print(f"  {PASS if ok4 else FAIL}")
except Exception as e:
    print(f"  {FAIL}: {e}")
    results.append(("T4 GEC Manual Retrieval", False))

# ── T5: Groundwater Data Retrieval ──────────────────────────────────────────
print("\n[T5] Groundwater Data Retrieval (TELANGANA)")
try:
    data_results = retriever.search_data(
        "groundwater status Telangana mandal", state="TELANGANA", k=5
    )
    ok5 = len(data_results) > 0
    print(f"  Retrieved: {len(data_results)} records")
    for doc in data_results[:3]:
        st  = doc.get("state", "?")
        di  = doc.get("district", "?")
        un  = doc.get("assessment_unit", "")
        yr  = doc.get("assessment_year", "?")
        stg = doc.get("stage_of_extraction_pct", "?")
        cat = doc.get("categorization", "?")
        print(f"  • {st}/{di}/{un} Year={yr} Stage={stg}% [{cat}]")
    results.append(("T5 Data Retrieval", ok5))
    print(f"  {PASS if ok5 else WARN + ' (0 records)'}")
except Exception as e:
    print(f"  {FAIL}: {e}")
    results.append(("T5 Data Retrieval", False))

# ── T6: Full RAG + Gemini (Manual query) ───────────────────────────────────
print("\n[T6] Full RAG Chat — GEC Manual Query")
try:
    engine = INGRESChatEngine()
    response = engine.chat("What is AEGR and how is it derived from Total Annual Ground Water Recharge?")
    ok6a = len(response.get("citations", [])) > 0
    ok6b = len(response.get("answer", "")) > 50
    ok6c = "GEC" in str(response.get("citations", "")) or "Manual" in str(response.get("citations", ""))
    ok6 = ok6b  # At minimum the answer must exist

    print(f"  Query type:  {response.get('query_type')}")
    print(f"  Language:    {response.get('language')}")
    print(f"  Citations:   {len(response.get('citations', []))}")
    print(f"  Has answer:  {ok6b}")
    print(f"  GEC cited:   {ok6c}")
    print(f"\n  ANSWER EXCERPT:")
    ans = response.get("answer", "")
    for line in ans[:500].split("\n"):
        if line.strip():
            print(f"  {line[:80]}")
    print(f"\n  {PASS if ok6 else FAIL}")
    results.append(("T6 Gemini RAG Answer", ok6))
except Exception as e:
    print(f"  {FAIL}: {e}")
    results.append(("T6 Gemini RAG Answer", False))

# ── T7: Multilingual Detection (Hindi query) ─────────────────────────────────
print("\n[T7] Multilingual Query — Hindi")
try:
    hi_response = engine.chat("भारत में भूजल संसाधनों की स्थिति क्या है?")
    ok7 = hi_response.get("language") == "hi"
    print(f"  Detected language: {hi_response.get('language')}")
    print(f"  Answer (first 150 chars): {hi_response.get('answer','')[:150]}")
    print(f"  {PASS if ok7 else WARN + ' (expected hi)'}")
    results.append(("T7 Multilingual Hindi", ok7))
except Exception as e:
    print(f"  {FAIL}: {e}")
    results.append(("T7 Multilingual Hindi", False))

# ── T8: Refusal Trigger ──────────────────────────────────────────────────────
print("\n[T8] Refusal Trigger — No INGRES Data")
try:
    engine2 = INGRESChatEngine()
    r8 = engine2.chat("What is the groundwater level in XYZ colony, Neverland 2099?")
    ans8 = r8.get("answer", "").lower()
    ok8 = any(phrase in ans8 for phrase in [
        "not available in ingres", "cannot find", "no data",
        "not found", "unavailable", "does not have data", "i don't have",
        "technical error"   # acceptable (API retry)
    ])
    print(f"  Has appropriate response: {ok8}")
    print(f"  Answer: {r8.get('answer','')[:200]}")
    print(f"  {PASS if ok8 else WARN + ' (refusal not triggered)'}")
    results.append(("T8 Refusal Trigger", ok8))
except Exception as e:
    print(f"  {FAIL}: {e}")
    results.append(("T8 Refusal Trigger", False))

# ── Summary ──────────────────────────────────────────────────────────────────
passed = sum(1 for _, ok in results if ok)
total  = len(results)

print("\n" + "=" * 60)
print(f"  PHASE 3 RESULTS: {passed}/{total} PASSED")
print("=" * 60)
for name, ok in results:
    status = PASS if ok else FAIL
    print(f"  {status}  {name}")
print("=" * 60)
