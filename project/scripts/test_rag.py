"""
Phase 3 RAG Retrieval Test
Run: python test_rag.py
"""
import sys, os
from pathlib import Path
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(Path('.env'))                           # GOOGLE_API_KEY
load_dotenv(Path('project/.env'), override=False)   # SUPABASE_URL, SUPABASE_ANON_KEY

from project.backend.rag_engine import INGRESRetriever, INGRESChatEngine

print("=" * 60)
print("  Phase 3 - RAG Retrieval Test")
print("=" * 60)

r = INGRESRetriever()

# Test 1: GEC Manual search
print("\n[T1] GEC Manual Search — 'What is AEGR?'")
try:
    results = r.search_manual("What is AEGR? How is it calculated?", k=3)
    print(f"  Retrieved: {len(results)} chunks")
    for doc in results:
        pg   = doc.get("page_number", "?")
        sim  = doc.get("similarity", 0)
        sec  = doc.get("section_title", "?")
        cont = str(doc.get("content", ""))[:120]
        print(f"  Section: {sec} | Page: {pg} | Similarity: {sim:.3f}")
        print(f"  Content: {cont}...")
        print()
    print("  T1 STATUS:", "PASS" if results else "FAIL (no results)")
except Exception as e:
    print(f"  T1 ERROR: {e}")

# Test 2: Data search
print("\n[T2] Groundwater Data Search — 'Telangana 2022'")
try:
    results2 = r.search_data("groundwater status Telangana 2022", state="TELANGANA", k=3)
    print(f"  Retrieved: {len(results2)} records")
    for doc in results2:
        st   = doc.get("state", "?")
        dist = doc.get("district", "?")
        unit = doc.get("assessment_unit", "")
        stg  = doc.get("stage_of_extraction_pct", "?")
        cat  = doc.get("categorization", "?")
        yr   = doc.get("assessment_year", "?")
        print(f"  {st}/{dist}/{unit} | Year={yr} | Stage={stg}% | Cat={cat}")
    print("  T2 STATUS:", "PASS" if results2 else "WARN (check state filter)")
except Exception as e:
    print(f"  T2 ERROR: {e}")

# Test 3: Full chat with Gemini
print("\n[T3] Full RAG Chat — 'What is AEGR and how is it calculated?'")
try:
    engine = INGRESChatEngine()
    response = engine.chat("What is AEGR and how is it calculated?")
    print(f"  Language:   {response['language']}")
    print(f"  Query type: {response['query_type']}")
    print(f"  Citations:  {len(response['citations'])}")
    print(f"  Answer excerpt:")
    print("  " + response["answer"][:400].replace("\n", "\n  "))
    print()
    print("  T3 STATUS: PASS")
except Exception as e:
    print(f"  T3 ERROR: {e}")

# Test 4: Refusal trigger
print("\n[T4] Refusal Trigger — data not in INGRES")
try:
    engine2 = INGRESChatEngine()
    response2 = engine2.chat("What is the groundwater status of Mars Colony, Pune in 2099?")
    answer = response2["answer"].lower()
    has_refusal = "not available in ingres" in answer or "cannot find" in answer or "no data" in answer
    print(f"  Has refusal message: {has_refusal}")
    print(f"  Answer excerpt: {response2['answer'][:200]}")
    print("  T4 STATUS:", "PASS" if has_refusal else "WARN (check refusal trigger)")
except Exception as e:
    print(f"  T4 ERROR: {e}")

print("\n" + "=" * 60)
print("  Phase 3 Tests Complete")
print("=" * 60)
