"""
rag_engine.py — Hybrid RAG + JEPA Predictive Search Engine
INGRES ChatBOT | Phase 3 | SIH25066

Architecture:
  1. Query Classification: Determines query type (manual/data/trend/block)
  2. Multilingual Detection: Detects language and translates query to English
  3. Dual Retrieval:
     a. Semantic Search → gec_manual_index (for "What is AEGR?")
     b. Semantic Search → groundwater_time_series (for "Tell me about Nalgonda 2022")
     c. JEPA Trajectory Search → predicts trends ("Which districts worsening?")
     d. Block Risk Search → annexure_block_risk ("OE blocks in Rajasthan?")
  4. Context Assembly: Merges retrieved chunks with source citations
  5. Gemini 2.0 Flash: Generates grounded, citation-enforced answers
  6. Response Packaging: Includes chart JSON when visualization is triggered
"""

import os
import re
import json
import sys
import logging
from typing import Dict, List, Optional, Tuple, Any, Iterator
from pathlib import Path
from enum import Enum

import numpy as np
from dotenv import load_dotenv

# ── Load environment (root .env has OpenRouter key; project/.env has Supabase keys)
root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

load_dotenv(dotenv_path=root_dir / ".env")
# Keep runtime-injected environment variables (e.g., Docker compose) authoritative.
load_dotenv(dotenv_path=root_dir / "project" / ".env", override=False)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL     = os.getenv("SUPABASE_URL")
SUPABASE_KEY     = os.getenv("SUPABASE_ANON_KEY")  # Use anon for reads (service_role for admin)

log = logging.getLogger("rag_engine")


# =============================================================================
# QUERY CLASSIFICATION
# =============================================================================

class QueryType(Enum):
    MANUAL        = "manual"     # Formula/methodology questions
    DATA_LOOKUP   = "data"       # Specific district/year data
    TREND_JEPA    = "trend"      # Worsening/improving trend queries
    BLOCK_RISK    = "block"      # Named block at-risk queries
    COMPARISON    = "comparison" # Year-over-year or state comparison
    GENERAL       = "general"    # Fallback


# Keywords that signal each query type
QUERY_SIGNALS = {
    QueryType.MANUAL: [
        "how is calculated", "how is it calculated", "define", "formula", "explain",
        "method", "gec", "cgwb", "aegr is", "tgwr", "rfif", "wtfm",
        "stage of extraction means", "categorization criterion", "what does aegr",
        "mean by", "definition of", "methodology", "criterion", "threshold for"
    ],
    QueryType.DATA_LOOKUP: [
        "status of", "data for", "in 2017", "in 2020", "in 2022", "in 2023", "in 2024",
        "groundwater in", "extraction in", "recharge in",
        "availability in", "how much water", "stage in",
        "tell me about", "what is the groundwater", "what is the stage",
        "what is the status", "assessment of", "extraction of",
    ],
    QueryType.TREND_JEPA: [
        "trend", "trending", "worsening", "improving", "deteriorating",
        "which district", "which districts", "at risk", "danger", "going to",
        "will become", "predict", "trajectory", "moving toward",
        "likely", "forecast", "future", "projected"
    ],
    QueryType.BLOCK_RISK: [
        "over-exploited block", "critical block", "semi-critical block",
        "blocks in", "mandal", "taluka", "annexure", "list of blocks",
        "which blocks", "name the blocks", "at risk blocks",
        "contaminated", "fluoride", "arsenic", "saline block"
    ],
    QueryType.COMPARISON: [
        "compare", "comparison", "vs", "versus", "difference between",
        "year over year", "2017 vs 2022", "change from", "trend from",
        "better or worse", "graph", "chart", "plot"
    ],
}


def classify_query(query: str) -> QueryType:
    """Rule-based query classifier with priority ordering."""
    q = query.lower().strip()

    # Priority order: DATA and BLOCK first (most specific), then TREND, COMPARISON, MANUAL
    for qtype in [
        QueryType.DATA_LOOKUP,
        QueryType.BLOCK_RISK,
        QueryType.TREND_JEPA,
        QueryType.COMPARISON,
        QueryType.MANUAL,
    ]:
        signals = QUERY_SIGNALS[qtype]
        if any(sig in q for sig in signals):
            return qtype

    return QueryType.GENERAL


# =============================================================================
# ENTITY EXTRACTION (State, District, Year)
# =============================================================================

# Known Indian states (canonical forms)
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli", "Daman and Diu", "Delhi", "Lakshadweep",
    "Puducherry", "Jammu and Kashmir", "Ladakh"
]
STATE_LOWER = {s.lower(): s for s in INDIAN_STATES}

# Lightweight alias map for common city-style references to district names.
DISTRICT_ALIASES = {
    "hyderabad": "Hyderabad",
    "bengaluru": "Bengaluru Urban",
    "bangalore": "Bengaluru Urban",
    "mumbai": "Mumbai",
    "delhi": "New Delhi",
    "chennai": "Chennai",
    "kolkata": "Kolkata",
}


def _normalize_place_name(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip(" ,.?"))
    if not cleaned:
        return ""
    return " ".join(part.capitalize() for part in cleaned.split(" "))


def _sanitize_place_candidate(text: str) -> str:
    candidate = _normalize_place_name(text)
    if not candidate:
        return ""
    tokens = candidate.split(" ")
    bad_leading = {
        "in", "of", "for", "the", "what", "was", "is", "are",
        "groundwater", "extraction", "stage", "status", "aegr", "and",
    }
    while len(tokens) > 1 and tokens[0].lower() in bad_leading:
        tokens = tokens[1:]
    return " ".join(tokens)


def extract_entities(query: str) -> Dict[str, Any]:
    """Extract state, district, year from natural language query."""
    q = query.lower()
    entities = {"state": None, "district": None, "year": None, "category": None}

    # Year extraction (2015–2025). If a range/multiple years is requested, keep year unfiltered.
    year_matches = re.findall(r'\b(201[5-9]|202[0-5])\b', q)
    if len(year_matches) == 1:
        entities["year"] = int(year_matches[0])

    # State extraction (fuzzy match)
    for state_lower, state_canonical in STATE_LOWER.items():
        if state_lower in q:
            entities["state"] = state_canonical
            break

    # District extraction (supports patterns like "Nalgonda district", "for Hyderabad", "in Jaipur")
    district = None

    district_matches = re.findall(
        r"\b([a-zA-Z][a-zA-Z&.-]*(?:\s+[a-zA-Z][a-zA-Z&.-]*){0,3})\s+district\b",
        query,
        flags=re.IGNORECASE,
    )
    if district_matches:
        district = _sanitize_place_candidate(district_matches[-1])
    else:
        m = re.search(r"\bblocks?\s+in\s+([a-zA-Z][a-zA-Z .&-]{1,40}?)(?:\s+district)?[?.!,;:]?$", query, flags=re.IGNORECASE)
        if m:
            district = _sanitize_place_candidate(m.group(1))

        # Prefer compact place mention at the end, e.g. "... for Hyderabad".
        if not district:
            m = re.search(r"\bfor\s+([a-zA-Z][a-zA-Z .&-]{1,40}?)(?:\s+district)?[?.!,;:]?$", query, flags=re.IGNORECASE)
        else:
            m = None
        if not m:
            m = re.search(r"\bin\s+([a-zA-Z][a-zA-Z .&-]{1,40}?)\s+district\b", query, flags=re.IGNORECASE)
        if m:
            candidate = _sanitize_place_candidate(m.group(1))
            # Avoid capturing broad nouns instead of places.
            bad_tokens = {"groundwater", "status", "aegr", "water", "resource", "resources", "data"}
            if candidate and candidate.lower() not in bad_tokens:
                district = candidate

    if district:
        entities["district"] = DISTRICT_ALIASES.get(district.lower(), district)

    # Infer state for known aliases when user omits it.
    if not entities.get("state") and entities.get("district") == "Hyderabad":
        entities["state"] = "Telangana"

    # Category extraction
    if "over-exploited" in q or "over exploited" in q or "overexploited" in q:
        entities["category"] = "Over-Exploited"
    elif "critical" in q and "semi" not in q:
        entities["category"] = "Critical"
    elif "semi-critical" in q or "semicritical" in q or "semi critical" in q:
        entities["category"] = "Semi-Critical"
    elif "safe" in q:
        entities["category"] = "Safe"

    return entities


# =============================================================================
# LANGUAGE DETECTION
# =============================================================================

LANG_PATTERNS = {
    "te": [  # Telugu script Unicode range: U+0C00–U+0C7F
        r'[\u0C00-\u0C7F]',
    ],
    "hi": [  # Hindi (Devanagari) Unicode range: U+0900–U+097F
        r'[\u0900-\u097F]',
    ],
}

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "te": "Telugu"}


def detect_language(text: str) -> str:
    """Detect language: returns 'en', 'hi', or 'te'."""
    for lang, patterns in LANG_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text):
                return lang
    return "en"


# =============================================================================
# RETRIEVAL ENGINE
# =============================================================================

class INGRESRetriever:
    """Handles all 4 retrieval paths: Manual, Semantic, JEPA, Block-Risk."""

    def __init__(self):
        from supabase import create_client
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self._embedder = None

    def _get_embedder(self):
        if self._embedder is None:
            from project.backend.ingestion.embedder import embed_query
            self._embedder = embed_query
        return self._embedder

    def _embed_query(self, text: str) -> List[float]:
        """Embed query text to 1024-dim vector."""
        embed_fn = self._get_embedder()
        vec = embed_fn(text)
        return vec.tolist()

    # ── Path 1: GEC Manual / Methodology ──────────────────────────────────────
    def search_manual(
        self, query: str, k: int = 5, threshold: float = 0.55
    ) -> List[Dict]:
        """
        Semantic search over GEC Manual.
        Use for: formula questions, methodology, glossary.
        """
        vec = self._embed_query(f"query: {query}")
        try:
            result = self.client.rpc("search_gec_manual", {
                "query_embedding": vec,
                "match_threshold": threshold,
                "match_count": k,
            }).execute()
            return result.data or []
        except Exception as e:
            log.error(f"Manual search error: {e}")
            return []

    # ── Path 2: Groundwater Data — Semantic ───────────────────────────────────
    def search_data(
        self,
        query: str,
        state: Optional[str] = None,
        district: Optional[str] = None,
        year: Optional[int] = None,
        category: Optional[str] = None,
        k: int = 6,
        threshold: float = 0.50,
    ) -> List[Dict]:
        """
        Semantic search over groundwater data records.
        Supports SQL pre-filters by state/district/year/category.
        """
        vec = self._embed_query(f"query: {query}")
        try:
            result = self.client.rpc("search_groundwater_semantic", {
                "query_embedding": vec,
                "match_threshold": threshold,
                "match_count": k,
                "filter_state":    state,
                "filter_district": district,
                "filter_year":     year,
                "filter_category": category,
            }).execute()
            return result.data or []
        except Exception as e:
            log.error(f"Data search error: {e}")
            return []

    # ── Path 3: JEPA Predictive Trajectory Search ─────────────────────────────
    def search_trends(
        self,
        target_trajectory: str = "Over-Exploited",
        state: Optional[str] = None,
        min_velocity: float = 3.0,
        k: int = 10,
        threshold: float = 0.25,
    ) -> List[Dict]:
        """
        V-JEPA Trajectory Search — finds districts with similar temporal patterns.

        Args:
            target_trajectory: "Over-Exploited", "improving", or "Safe"
            min_velocity: Minimum stage change per year (% per year)
            state: Optional state filter

        Returns districts whose trajectory vectors cluster near the target.
        """
        from project.backend.ingestion.jepa_encoder import build_prototype_vector
        prototype = build_prototype_vector(target_trajectory)

        try:
            result = self.client.rpc("search_groundwater_jepa", {
                "query_jepa_vector": prototype.tolist(),
                "match_threshold":   threshold,
                "match_count":       k,
                "filter_state":      state,
                "min_velocity":      min_velocity,
                "filter_trend":      None,
            }).execute()
            return result.data or []
        except Exception as e:
            log.error(f"JEPA search error: {e}")
            return []

    # ── Path 4: Named Block Risk Search ───────────────────────────────────────
    def search_blocks(
        self,
        query: str,
        state: Optional[str] = None,
        district: Optional[str] = None,
        category: Optional[str] = None,
        year: Optional[int] = None,
        k: int = 10,
        threshold: float = 0.30,
    ) -> List[Dict]:
        """
        Named block at-risk lookup (Annexure 4A/4B).
        Use for: "Which blocks in Nalgonda are Over-Exploited?"
        """
        vec = self._embed_query(f"query: {query}")
        try:
            result = self.client.rpc("search_at_risk_blocks", {
                "query_embedding":  vec,
                "match_threshold":  threshold,
                "match_count":      k,
                "filter_state":     state,
                "filter_district":  district,
                "filter_category":  category,
                "filter_year":      year,
            }).execute()
            return result.data or []
        except Exception as e:
            log.error(f"Block search error: {e}")
            return []

    # ── Orchestrated retrieval ─────────────────────────────────────────────────
    def retrieve(
        self,
        query: str,
        query_type: QueryType,
        entities: Dict[str, Any],
    ) -> Dict[str, List[Dict]]:
        """
        Run the appropriate retrieval path(s) for a given query.
        Returns dict with results from each active path.
        """
        results = {
            "manual": [],
            "data": [],
            "jepa": [],
            "blocks": [],
        }

        state    = entities.get("state")
        district = entities.get("district")
        year     = entities.get("year")
        category = entities.get("category")

        if query_type == QueryType.MANUAL:
            results["manual"] = self.search_manual(query, k=5)

        elif query_type == QueryType.DATA_LOOKUP:
            results["data"] = self.search_data(
                query, state=state, district=district, year=year, k=8
            )
            # Also pull manual context for formula definitions
            results["manual"] = self.search_manual(query, k=2, threshold=0.5)

        elif query_type == QueryType.TREND_JEPA:
            trajectory = "Over-Exploited" if "over" in query.lower() else \
                         "improving" if "improv" in query.lower() else "Over-Exploited"
            results["jepa"] = self.search_trends(
                target_trajectory=trajectory,
                state=state,
                min_velocity=3.0,
                k=10,
            )
            # Also semantic search for context
            results["data"] = self.search_data(query, state=state, k=5)

            ql = query.lower()
            if "improv" in ql:
                filtered = [d for d in results["jepa"] if "improv" in (d.get("jepa_trend_direction") or "").lower()]
                results["jepa"] = filtered
            elif any(x in ql for x in ["worsen", "deterior", "toward over", "towards over", "over-exploited"]):
                filtered = [
                    d for d in results["jepa"]
                    if "wors" in (d.get("jepa_trend_direction") or "").lower()
                    or (d.get("jepa_stage_velocity") is not None and d.get("jepa_stage_velocity") > 0)
                ]
                results["jepa"] = filtered

        elif query_type == QueryType.BLOCK_RISK:
            results["blocks"] = self.search_blocks(
                query, state=state, district=district,
                category=category, year=year, k=15
            )
            results["data"] = self.search_data(
                query, state=state, district=district,
                year=year, category=category, k=4
            )
            
            # If no blocks match the strict category filter, fetch general district data 
            # so the LLM knows the district exists and can answer that no blocks match the category.
            if not results["blocks"] and not results["data"] and category:
                results["data"] = self.search_data(
                    query, state=state, district=district, year=year, k=5
                )

        elif query_type == QueryType.COMPARISON:
            results["data"] = self.search_data(
                query, state=state, district=district, year=year, k=10
            )
            results["jepa"] = self.search_trends(state=state, k=8)

        else:  # GENERAL
            results["manual"] = self.search_manual(query, k=3, threshold=0.30)
            results["data"]   = self.search_data(query, state=state, k=5)

        return results


# =============================================================================
# CONTEXT ASSEMBLER
# =============================================================================

def assemble_context(
    results: Dict[str, List[Dict]],
    query_type: QueryType,
) -> Tuple[str, List[str]]:
    """
    Build the RAG context string and citation list from retrieval results.

    Returns:
        (context_text: str, citations: List[str])
    """
    context_parts = []
    citations = []

    # ── Manual / Methodology Context ──────────────────────────────────────────
    for i, doc in enumerate(results.get("manual", [])):
        section = doc.get("section_title", "GEC Manual")
        page    = doc.get("page_number", "?")
        content = doc.get("content", "")
        sim     = doc.get("similarity", 0)

        if content and sim > 0.3:
            cite = f"GEC User Manual, Section {doc.get('section_number', '?')} ({section}), Page {page}"
            citations.append(cite)
            context_parts.append(
                f"[MANUAL SOURCE: {cite}]\n{content}"
            )

    # ── Groundwater Data Context ───────────────────────────────────────────────
    for doc in results.get("data", []):
        state    = doc.get("state", "?")
        district = doc.get("district", "?")
        unit     = doc.get("assessment_unit", "")
        year     = doc.get("assessment_year", "?")
        stage    = doc.get("stage_of_extraction_pct")
        cat      = doc.get("categorization", "?")
        aegr     = doc.get("aegr", doc.get("aegr_total"))
        total_e  = doc.get("total_extraction", doc.get("total_extraction_total"))
        net_av   = doc.get("net_gw_availability", doc.get("net_availability_total"))
        trend    = doc.get("jepa_trend_direction", "")
        velocity = doc.get("jepa_stage_velocity")

        unit_str = f"{unit}, " if unit else ""
        cite = f"INGRES Assessment Data, {state} — {unit_str}{district} District, Year {year}"
        citations.append(cite)

        data_str = (
            f"[DATA SOURCE: {cite}]\n"
            f"Assessment Unit: {unit_str}{district} | State: {state} | Year: {year}\n"
            f"Stage of Extraction: {stage:.1f}% → {cat}\n"
        )
        if aegr is not None:
            data_str += f"AEGR (Annual Extractable GW Resource): {aegr:.2f} Ham\n"
        if total_e is not None:
            data_str += f"Total Extraction: {total_e:.2f} Ham\n"
        if net_av is not None:
            data_str += f"Net GW Availability for Future Use: {net_av:.2f} Ham\n"
        if trend:
            data_str += f"Trend (JEPA): {trend}"
            if velocity is not None:
                data_str += f" ({velocity:+.1f}%/year)"
            data_str += "\n"

        context_parts.append(data_str)

    # ── JEPA Trend Context ─────────────────────────────────────────────────────
    jepa_docs = results.get("jepa", [])
    if jepa_docs:
        context_parts.append("[TREND ANALYSIS — JEPA Trajectory Search]")
        for doc in jepa_docs:
            state    = doc.get("state", "?")
            district = doc.get("district", "?")
            unit     = doc.get("assessment_unit", "")
            year     = doc.get("assessment_year", "?")
            stage    = doc.get("stage_of_extraction_pct")
            trend    = doc.get("jepa_trend_direction", "")
            velocity = doc.get("jepa_stage_velocity")
            seq_yrs  = doc.get("jepa_sequence_years") or []
            traj_sim = doc.get("trajectory_similarity", 0)

            unit_str = f"{unit} / " if unit else ""
            cite = f"INGRES JEPA Trend Data, {unit_str}{district}, {state}"
            citations.append(cite)

            trend_str = (
                f"  • {unit_str}{district}, {state}: "
                f"Stage={stage:.1f}% ({doc.get('categorization', '?')}) | "
                f"Trend={trend} | Velocity={velocity:+.1f}%/yr | "
                f"Years: {seq_yrs} | Trajectory match: {traj_sim:.2f}\n"
            )
            context_parts.append(trend_str)

    # ── Block Risk Context ─────────────────────────────────────────────────────
    block_docs = results.get("blocks", [])
    if block_docs:
        context_parts.append("[AT-RISK BLOCK DATA — Annexure 4]")
        for doc in block_docs:
            state   = doc.get("state", "?")
            dist    = doc.get("district", "?")
            block   = doc.get("block_name", "?")
            cat     = doc.get("categorization", "?")
            quality = doc.get("quality_tag")
            source  = doc.get("annexure_source", "Annexure4A")
            year    = doc.get("assessment_year", "?")

            cite = f"{source}, {state} — {dist} District, Year {year}"
            citations.append(cite)

            q_str = f" (Quality: {quality})" if quality else ""
            context_parts.append(
                f"  • {block} block, {dist}, {state}: {cat}{q_str} [SOURCE: {cite}]"
            )

    context_text = "\n\n".join(context_parts)

    # Truncate to avoid Gemini context limit (keep most relevant at top)
    MAX_CONTEXT_CHARS = 18000
    if len(context_text) > MAX_CONTEXT_CHARS:
        context_text = context_text[:MAX_CONTEXT_CHARS] + "\n... [Context truncated for length]"

    return context_text, list(dict.fromkeys(citations))  # deduplicate citations


# =============================================================================
# VISUALIZATION TRIGGER
# =============================================================================

def should_generate_chart(query: str, query_type: QueryType) -> bool:
    """Detect if user wants a chart/graph/visualization."""
    q = query.lower()
    CHART_KEYWORDS = [
        "chart", "graph", "plot", "visualize", "show me", "trend",
        "compare", "over the years", "year by year", "bar", "line",
        "percentage over", "how has", "change in"
    ]
    return any(kw in q for kw in CHART_KEYWORDS)


def build_chart_json(
    results: Dict[str, List[Dict]],
    query: str,
    entities: Dict[str, Any],
) -> Optional[Dict]:
    """
    Build Chart.js-compatible JSON for the frontend.
    """
    data_rows = results.get("data", []) + results.get("jepa", [])
    if not data_rows:
        return None

    districts_present = list(set([r.get("district") for r in data_rows if r.get("district")]))
    years_present = list(set([r.get("assessment_year") for r in data_rows if r.get("assessment_year")]))
    q = query.lower()

    # Case 1: Line chart for a single district over years
    if len(years_present) > 1 and len(districts_present) > 0 and any(w in q for w in ["trend", "year", "change", "line", "over time", "progress", "plot"]):
        target_district = districts_present[0]
        d_rows = [r for r in data_rows if r.get("district") == target_district and r.get("assessment_year")]
        d_rows.sort(key=lambda r: r["assessment_year"])
        
        seen_years = set()
        clean_rows = []
        for r in d_rows:
            if r["assessment_year"] not in seen_years:
                seen_years.add(r["assessment_year"])
                clean_rows.append(r)
                
        if len(clean_rows) > 1:
            return {
                "type": "line",
                "title": f"Stage of Extraction Trend — {target_district}",
                "x_label": "Assessment Year",
                "y_label": "Stage of Extraction (%)",
                "threshold_lines": [
                    {"value": 70,  "label": "Semi-Critical",  "color": "#f59e0b"},
                    {"value": 90,  "label": "Critical",        "color": "#ef4444"},
                    {"value": 100, "label": "Over-Exploited",  "color": "#991b1b"},
                ],
                "datasets": [{
                    "label": target_district,
                    "data": [{"x": r["assessment_year"], "y": r.get("stage_of_extraction_pct", 0)} for r in clean_rows],
                    "borderColor": "#3b82f6",
                    "backgroundColor": "rgba(59,130,246,0.1)",
                    "fill": True,
                }],
                "source": "INGRES Assessment Data (GEC 2015)",
                "generated_at": str(__import__("datetime").datetime.utcnow()),
            }

    # Case 2: Bar chart comparison across districts for a single year
    if len(districts_present) > 1:
        years_present.sort(reverse=True)
        target_year = years_present[0] if years_present else None
        
        if target_year:
            c_rows = []
            seen_districts = set()
            for r in data_rows:
                d = r.get("district")
                if d and d not in seen_districts and r.get("assessment_year") == target_year:
                    seen_districts.add(d)
                    c_rows.append(r)
            
            c_rows.sort(key=lambda r: r.get("stage_of_extraction_pct", 0), reverse=True)
            c_rows = c_rows[:10]
            
            if len(c_rows) > 1:
                stages = [r.get("stage_of_extraction_pct", 0) for r in c_rows]
                return {
                    "type":    "bar",
                    "title":   f"Stage of GW Extraction Comparison — {target_year}",
                    "x_label": "District",
                    "y_label": "Stage of Extraction (%)",
                    "threshold_lines": [
                        {"value": 70,  "label": "Semi-Critical",  "color": "#f59e0b"},
                        {"value": 90,  "label": "Critical",        "color": "#ef4444"},
                        {"value": 100, "label": "Over-Exploited",  "color": "#991b1b"},
                    ],
                    "datasets": [{
                        "label":           f"Stage % ({target_year})",
                        "data":            stages,
                        "labels":          [r["district"] for r in c_rows],
                        "backgroundColor": ["#ef4444" if s > 100 else "#f97316" if s > 90 else "#f59e0b" if s > 70 else "#22c55e" for s in stages],
                    }],
                    "source": f"INGRES Assessment Data {target_year} (GEC 2015)",
                    "generated_at": str(__import__("datetime").datetime.utcnow()),
                }

    return None


# =============================================================================
# OPENROUTER — LLM CLIENT
# =============================================================================

def get_openrouter_client():
    """Initialize OpenRouter client with primary+fallback model routing."""
    try:
        from openai import OpenAI
    except Exception as exc:
        raise RuntimeError("OpenAI client library is not installed in backend environment") from exc

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("No OPENROUTER_API_KEY configured!")

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    return _OpenRouterClientWrapper(client)


class _OpenRouterClientWrapper:
    """OpenRouter wrapper with Gemini primary and LLaMA fallback."""

    PRIMARY_MODEL = "google/gemini-2.5-flash"
    FALLBACK_MODELS = [
        "meta-llama/llama-3-8b-instruct:free",
    ]

    def __init__(self, client: Any):
        self._client = client

    def _completion_text(self, response: Any) -> str:
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        return (getattr(message, "content", "") or "").strip()

    def generate_content(self, prompt: str):
        models = [self.PRIMARY_MODEL] + self.FALLBACK_MODELS
        last_error = None

        for model in models:
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    top_p=0.8,
                    max_tokens=2048,
                )
                text = self._completion_text(response)
                if not text:
                    raise RuntimeError(f"Empty completion from model {model}")
                return type("LLMResponse", (), {"text": text})()
            except Exception as e:
                last_error = e
                log.warning(f"Model {model} failed via OpenRouter, trying fallback: {e}")

        raise RuntimeError(f"All OpenRouter models failed. Last error: {last_error}")

    def generate_content_stream(self, prompt: str) -> Iterator[str]:
        """Stream partial tokens from OpenRouter with model fallback."""
        models = [self.PRIMARY_MODEL] + self.FALLBACK_MODELS
        last_error = None

        for model in models:
            try:
                stream = self._client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    top_p=0.8,
                    max_tokens=2048,
                    stream=True,
                )
                emitted = False
                for chunk in stream:
                    choices = getattr(chunk, "choices", None) or []
                    if not choices:
                        continue
                    delta = getattr(choices[0], "delta", None)
                    token = getattr(delta, "content", None) if delta else None
                    if token:
                        emitted = True
                        yield token
                if emitted:
                    return
                raise RuntimeError(f"Empty stream from model {model}")
            except Exception as e:
                last_error = e
                log.warning(f"Model {model} stream failed via OpenRouter, trying fallback: {e}")

        raise RuntimeError(f"All OpenRouter streaming models failed. Last error: {last_error}")


# =============================================================================
# SYSTEM PROMPT — THE INTELLIGENCE CONTRACT
# =============================================================================

SYSTEM_PROMPT = """You are INGRES-AI, an official AI assistant for the India Ground Water Resource Estimation System (INGRES), developed under the GEC-2015 methodology by CGWB and IIT Hyderabad for the Ministry of Jal Shakti, Government of India.

## YOUR ROLE
You answer questions about groundwater resources across India, including:
- GEC-2015 methodology, formulas, and scientific definitions
- District-wise groundwater assessment data (Stage of Extraction, AEGR, Recharge, Extraction)
- At-risk block identification (Over-Exploited, Critical, Semi-Critical)
- Temporal trends and predictions based on multi-year data
- Multilingual support (English, Hindi हिंदी, Telugu తెలుగు)

## CORE SCIENTIFIC RULES (NEVER VIOLATE)
1. Stage of Extraction = (Total Annual GW Extraction / AEGR) × 100
2. AEGR = Total Annual GW Recharge (TGWR) − Natural Discharges (ND)
3. Categorization rules:
   - 0−70%: SAFE
   - 70−90%: SEMI-CRITICAL
   - 90−100%: CRITICAL
   - >100%: OVER-EXPLOITED
   - Quality-based (Fluoride/Arsenic/Salinity): SALINE (independent of stage %)
4. Units: Recharge/Extraction in Ham (Hectare Meters); National totals in BCM
5. Natural Discharges = 5% of TGWR (if WTFM method) or 10% of TGWR (if RIFM method)

## MANDATORY CITATION RULE
EVERY factual claim you make MUST include a citation in this exact format:
  [SOURCE: <source name>]
Example:
  "Nalgonda district has a Stage of Extraction of 87.3% (Semi-Critical) [SOURCE: INGRES Assessment Data, Telangana — Nalgonda District, Year 2022]"

## REFUSAL TRIGGER (CRITICAL — DO NOT HALLUCINATE)
If the provided context does NOT contain the information needed to answer:
  → Always respond: "This information is **not available in INGRES** for the requested parameters. Please check the INGRES portal directly at https://ingres.iith.ac.in for the latest data or contact CGWB."
  → NEVER guess, estimate, or fabricate data values.
  → NEVER cite sources you did not receive in the context.

## UNRELATED DATA TRIGGER
If the question is completely unrelated to India groundwater, INGRESS, hydrology, or CGWB data, you MUST politely decline by exactly stating:
"Sorry for that, but I can help you only in understanding the INGRES platform and groundwater data."
Do not answer the unrelated question.

## RESPONSE FORMAT RULES
1. Always start with a direct answer to the question.
2. Make answers sufficiently detailed by default: include context, key values, and brief interpretation.
3. Use bullet points for lists of districts or blocks.
4. For data answers, include at least 3-5 informative bullets when data is available.
5. Use bold for key metrics (Stage %, Category, AEGR values).
6. If a chart was generated, mention: "📊 A chart has been generated to visualize this data."
7. End every response with: "📚 Sources: [list all citations]"
8. For Hindi/Telugu queries: respond in the SAME language as the query.

## WHAT YOU MUST NEVER DO
- Do NOT make up district names, block names, or numerical values.
- Do NOT cite documents not provided in the context.
- Do NOT claim data for years not in the context (available years: 2017, 2020, 2022, 2023, 2024).
- Do NOT override the GEC-2015 categorization thresholds.
- Do NOT provide medical or legal advice.
"""


HINDI_SUFFIX = """

## हिंदी में उत्तर देने के निर्देश
- यदि प्रश्न हिंदी में है, तो उत्तर भी हिंदी में दें।
- तकनीकी शब्द (AEGR, Stage of Extraction, Ham) अंग्रेजी में रखें।
- उद्धरण अंग्रेजी में दें।
"""

TELUGU_SUFFIX = """

## తెలుగులో సమాధానం ఇవ్వడానికి సూచనలు
- ప్రశ్న తెలుగులో ఉంటే, సమాధానం కూడా తెలుగులో ఇవ్వండి.
- సాంకేతిక పదాలు (AEGR, Stage of Extraction, Ham) ఆంగ్లంలో ఉంచండి.
- అనుల్లేఖాలు ఆంగ్లంలో ఇవ్వండి.
"""


def build_system_prompt(language: str) -> str:
    """Build the system prompt with language-specific suffix."""
    base = SYSTEM_PROMPT
    if language == "hi":
        base += HINDI_SUFFIX
    elif language == "te":
        base += TELUGU_SUFFIX
    return base


# =============================================================================
# MAIN RAG PIPELINE
# =============================================================================

class INGRESChatEngine:
    """Main conversational RAG engine. Maintains session history."""

    def __init__(self):
        self.retriever = INGRESRetriever()
        self._llm = None
        self.session_history: List[Dict] = []

    def _get_llm(self):
        if self._llm is None:
            self._llm = get_openrouter_client()
        return self._llm

    def _load_session_history(self, session_id: str):
        """Fetch persistent history from Supabase."""
        try:
            res = self.retriever.client.table("chat_history")\
                .select("role, content")\
                .eq("session_id", session_id)\
                .order("created_at", desc=False)\
                .limit(10)\
                .execute()
            return res.data or []
        except:
            return []

    def _save_session_turn(self, session_id: str, role: str, content: str):
        """Persist a single turn to Supabase."""
        try:
            self.retriever.client.table("chat_history").insert({
                "session_id": session_id,
                "role":       role,
                "content":    content
            }).execute()
        except:
            pass

    def _prepare_chat_payload(
        self,
        user_message: str,
        session_id: Optional[str] = "default_session",
        uploaded_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build all retrieval and prompt artifacts used by sync and stream modes."""
        session_id = session_id or "default_session"
        history = self._load_session_history(session_id)

        language = detect_language(user_message)
        query_type = classify_query(user_message)

        last_user_query = ""
        for turn in reversed(history[-4:]):
            if turn["role"] == "user":
                last_user_query = turn["content"]
                break

        entities = extract_entities(user_message)
        if not entities.get("state") and not entities.get("year"):
            entities.update({k: v for k, v in extract_entities(last_user_query).items() if v and not entities.get(k)})

        results = self.retriever.retrieve(user_message, query_type, entities)
        if not any(results.values()):
            log.info("Agentic Loop: Zero results, widening threshold...")
            results = self.retriever.retrieve(user_message, query_type, entities)

        context, citations = assemble_context(results, query_type)

        sys_prompt = build_system_prompt(language)
        history_str = ""
        for turn in history:
            role = "User" if turn["role"] == "user" else "Assistant"
            history_str += f"{role}: {turn['content'][:200]}\n"

        if uploaded_context:
            full_prompt = f"""{sys_prompt}
---
## CONVERSATION HISTORY
{history_str if history_str else "(New conversation)"}
---
## PRIMARY DOCUMENT (USER UPLOADED — treat this as the authoritative source)
{uploaded_context}
---
## SUPPLEMENTAL INGRES DATABASE CONTEXT
{context if context else "No additional database records matched this query."}
---
## USER QUESTION
{user_message}
---
## INSTRUCTIONS FOR THIS RESPONSE
- Answer the question based primarily on the uploaded document above.
- Quote or reference specific sections of the document where possible.
- If the user asks about accuracy or correctness, summarize what the document says on that topic — do NOT refuse.
- Supplement with INGRES database context only if it adds useful information.
---
## YOUR ANSWER
"""
        else:
            full_prompt = f"""{sys_prompt}
---
## CONVERSATION HISTORY (PERSISTED)
{history_str if history_str else "(New conversation)"}
---
## RETRIEVED CONTEXT
{context if context else "[REFUSAL TRIGGER: This information is not available in INGRES]"}
---
## USER QUESTION
{user_message}
---
## YOUR ANSWER
"""

        chart = None
        if should_generate_chart(user_message, query_type):
            log.info("Agentic Loop: Triggering chart generation...")
            chart = build_chart_json(results, user_message, entities)

        return {
            "session_id": session_id,
            "user_message": user_message,
            "language": language,
            "query_type": query_type,
            "entities": entities,
            "citations": citations,
            "chart": chart,
            "context": context,
            "results": results,
            "full_prompt": full_prompt,
        }

    def _fallback_answer_from_results(self, payload: Dict[str, Any]) -> Optional[str]:
        """Generate a deterministic answer when LLM refuses despite having retrieved records."""
        results = payload.get("results") or {}
        qtype = payload.get("query_type")
        citations = payload.get("citations") or []
        chart = payload.get("chart")
        question = (payload.get("user_message") or "").lower()

        def sources_block() -> str:
            if not citations:
                return ""
            unique = list(dict.fromkeys(citations))[:8]
            return "\n\n📚 Sources: " + "; ".join(unique)

        if qtype in (QueryType.DATA_LOOKUP, QueryType.COMPARISON, QueryType.GENERAL):
            rows = results.get("data") or []
            if rows:
                lines = []
                for d in rows[:8]:
                    dist = d.get("district", "?")
                    state = d.get("state", "?")
                    year = d.get("assessment_year", "?")
                    stage = d.get("stage_of_extraction_pct")
                    aegr = d.get("aegr", d.get("aegr_total"))
                    cat = d.get("categorization", "?")
                    stage_text = f"{stage:.1f}%" if stage is not None else "N/A"
                    aegr_text = f"{aegr:.2f} Ham" if aegr is not None else "N/A"
                    lines.append(f"• {dist}, {state} ({year}): Stage {stage_text} ({cat}), AEGR {aegr_text}")
                msg = "Here are the retrieved groundwater records:\n" + "\n".join(lines)
                if chart:
                    msg += "\n\n📊 A chart has been generated to visualize this data."
                return msg + sources_block()
            return "I could not find matching groundwater records for the exact filters in your query. Please try adding or adjusting state/district/year." + sources_block()

        if qtype == QueryType.TREND_JEPA:
            rows = results.get("jepa") or []
            if rows:
                lines = []
                for d in rows[:10]:
                    dist = d.get("district", "?")
                    state = d.get("state", "?")
                    trend = d.get("jepa_trend_direction", "?")
                    vel = d.get("jepa_stage_velocity")
                    vel_text = f"{vel:+.1f}%/yr" if vel is not None else "N/A"
                    lines.append(f"• {dist}, {state}: trend={trend}, velocity={vel_text}")
                msg = "These districts were retrieved from the JEPA trend engine:\n" + "\n".join(lines)
                if chart:
                    msg += "\n\n📊 A chart has been generated to visualize this data."
                return msg + sources_block()
            return "No matching JEPA trend records were found for the requested trend direction and filters." + sources_block()

        if qtype == QueryType.BLOCK_RISK:
            rows = results.get("blocks") or []
            if rows:
                lines = []
                for b in rows[:15]:
                    block = b.get("block_name", "?")
                    dist = b.get("district", "?")
                    state = b.get("state", "?")
                    cat = b.get("categorization", "?")
                    quality = b.get("quality_tag")
                    q_text = f", quality={quality}" if quality else ""
                    lines.append(f"• {block} ({dist}, {state}): {cat}{q_text}")
                return "Here are the retrieved at-risk blocks:\n" + "\n".join(lines) + sources_block()
            return "No matching block-level risk records were found for the requested state/district/category/quality filters." + sources_block()

        if qtype == QueryType.MANUAL:
            rows = results.get("manual") or []
            if rows:
                snippet = (rows[0].get("content") or "").strip()[:500]
                if snippet:
                    return f"According to the retrieved GEC manual section:\n\n{snippet}" + sources_block()

        return None

    def chat(
        self,
        user_message: str,
        session_id: Optional[str] = "default_session",
        uploaded_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Improvised RAG Pipeline with Agentic Reflection & Persistent Memory.
        """
        payload = self._prepare_chat_payload(
            user_message=user_message,
            session_id=session_id,
            uploaded_context=uploaded_context,
        )

        # ── Step 5: Generate LLM response ─────────────────────────────────────
        try:
            model    = self._get_llm()
            response = model.generate_content(payload["full_prompt"])
            answer   = response.text.strip()
        except Exception as e:
            log.error(f"Generate Content Error: {e}")
            answer = "I'm experiencing high traffic right now. Please try your search again in a moment."

        if "not available in ingres" in answer.lower():
            fallback = self._fallback_answer_from_results(payload)
            if fallback:
                answer = fallback

        # ── Step 5: Persist chat turns ────────────────────────────────────────
        self._save_session_turn(payload["session_id"], "user", user_message)
        self._save_session_turn(payload["session_id"], "assistant", answer)

        return {
            "answer":       answer,
            "citations":    payload["citations"],
            "chart":        payload["chart"],
            "language":     payload["language"],
            "query_type":   payload["query_type"].value,
            "entities":     payload["entities"],
            "context_used": payload["context"][:300] + "..." if payload["context"] else ""
        }

    def chat_stream(
        self,
        user_message: str,
        session_id: Optional[str] = "default_session",
        uploaded_context: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Stream response tokens while preserving the same RAG/retrieval workflow."""
        payload = self._prepare_chat_payload(
            user_message=user_message,
            session_id=session_id,
            uploaded_context=uploaded_context,
        )

        chunks: List[str] = []
        try:
            model = self._get_llm()
            for token in model.generate_content_stream(payload["full_prompt"]):
                chunks.append(token)
                yield {"type": "token", "content": token}
            answer = "".join(chunks).strip()
            if not answer:
                answer = "I'm experiencing high traffic right now. Please try your search again in a moment."
        except Exception as e:
            log.error(f"Generate Content Stream Error: {e}")
            answer = "I'm experiencing high traffic right now. Please try your search again in a moment."
            yield {"type": "token", "content": answer}

        self._save_session_turn(payload["session_id"], "user", user_message)
        self._save_session_turn(payload["session_id"], "assistant", answer)

        yield {
            "type": "final",
            "answer": answer,
            "citations": payload["citations"],
            "chart": payload["chart"],
            "language": payload["language"],
            "query_type": payload["query_type"].value,
            "entities": payload["entities"],
        }


# =============================================================================
# PHASE 3 TEST QUERIES
# =============================================================================

def run_test_queries():
    """
    Phase 3 verification — run 5 test queries covering all retrieval paths.
    Run this after Phase 2 data ingestion is complete.
    """
    engine = INGRESChatEngine()

    TEST_QUERIES = [
        # T1: Manual / Formula query
        {
            "query": "What is AEGR and how is it calculated?",
            "expected_type": "manual",
            "expected_citation_contains": "GEC",
        },
        # T2: Data lookup query
        {
            "query": "What is the groundwater status of Nalgonda district in Telangana?",
            "expected_type": "data",
            "expected_citation_contains": "INGRES",
        },
        # T3: JEPA trend query
        {
            "query": "Which districts in Rajasthan are trending toward Over-Exploited?",
            "expected_type": "trend",
            "expected_citation_contains": "JEPA",
        },
        # T4: Block risk query
        {
            "query": "List the Over-Exploited blocks in Gujarat",
            "expected_type": "block",
            "expected_citation_contains": "Annexure",
        },
        # T5: Refusal trigger (no data)
        {
            "query": "What is the groundwater level in Mars colony, Pune for 2099?",
            "expected_type": "general",
            "expected_answer_contains": "not available in INGRES",
        },
    ]

    print("\n" + "="*60)
    print("  PHASE 3 — RAG Engine Test Queries")
    print("="*60)

    passed = 0
    for i, test in enumerate(TEST_QUERIES, 1):
        print(f"\n[T{i}] Query: {test['query']}")
        try:
            result = engine.chat(test["query"])
            print(f"     Type:     {result['query_type']}")
            print(f"     Language: {result['language']}")
            print(f"     Answer:   {result['answer'][:200]}...")
            if result["citations"]:
                print(f"     Citations ({len(result['citations'])}): {result['citations'][0][:80]}")
            if result["chart"]:
                print(f"     Chart:    {result['chart']['type']} — {result['chart']['title']}")

            # Verify
            if test["expected_type"] == result["query_type"]:
                print(f"     ✅ Query type correct")
                passed += 1
            else:
                print(f"     ⚠️  Expected type '{test['expected_type']}', got '{result['query_type']}'")

        except Exception as e:
            print(f"     ❌ ERROR: {e}")

    print(f"\n{'='*60}")
    print(f"  PHASE 3 RESULTS: {passed}/{len(TEST_QUERIES)} passed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_test_queries()
