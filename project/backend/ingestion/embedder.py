"""
embedder.py — 1024-dim Multilingual Text Embedder
INGRES ChatBOT | Phase 2 | SIH25066

Model: intfloat/multilingual-e5-large
  - 1024-dimensional output ✓
  - Multilingual: English, Hindi (हिंदी), Telugu (తెలుగు), and 100+ languages ✓
  - Open source, HuggingFace, free via local inference ✓
  - Requires prefix: "passage: {text}" for documents, "query: {text}" for queries

Memory: Model is ~560MB. Loaded ONCE globally and reused.
"""

import os
from typing import List, Union
import numpy as np

_model = None
MODEL_NAME = "intfloat/multilingual-e5-large"


def _get_model():
    """Lazy-load: ensure model is loaded only once."""
    global _model
    if _model is None:
        print(f"  [Embedder] Loading {MODEL_NAME} (first time ~30s)...")

        # Set HF token from environment
        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            os.environ["HUGGING_FACE_HUB_TOKEN"] = hf_token

        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
        print(f"  [Embedder] [SUCCESS] Model loaded. Embedding dim: {_model.get_sentence_embedding_dimension()}")

    return _model


def embed_passages(texts: List[str], batch_size: int = 16) -> np.ndarray:
    """
    Embed document chunks (GEC manual sections, groundwater data narratives).
    Uses "passage: {text}" prefix as required by multilingual-e5-large.

    Args:
        texts: List of text strings to embed
        batch_size: Process in batches to avoid OOM (default: 16)

    Returns:
        np.ndarray of shape (len(texts), 1024), dtype float32
    """
    model = _get_model()
    prefixed = [f"passage: {t}" for t in texts]
    embeddings = model.encode(
        prefixed,
        batch_size=batch_size,
        normalize_embeddings=True,    # L2 normalize → cosine similarity = dot product
        show_progress_bar=len(texts) > 50,
        convert_to_numpy=True
    )
    return embeddings.astype(np.float32)


def embed_query(text: str) -> np.ndarray:
    """
    Embed a single user query for retrieval.
    Uses "query: {text}" prefix.

    Args:
        text: User query string (can be English, Hindi, or Telugu)

    Returns:
        np.ndarray of shape (1024,), dtype float32
    """
    model = _get_model()
    prefixed = f"query: {text}"
    embedding = model.encode(
        [prefixed],
        normalize_embeddings=True,
        convert_to_numpy=True
    )
    return embedding[0].astype(np.float32)


def build_groundwater_narrative(row: dict, source: str = "attribute_table") -> str:
    """
    Build a human-readable narrative from a groundwater data row.
    This text is what gets embedded as the semantic_vector for each record.

    Args:
        row: Dict with canonical field names and values
        source: Source dataset type for context

    Returns:
        A rich, information-dense text string for embedding
    """
    state = row.get("state", "Unknown State")
    district = row.get("district", "Unknown District")
    unit = row.get("assessment_unit", "")
    year = row.get("assessment_year", "Unknown")
    year_label = row.get("assessment_year_label", str(year))
    unit_type = row.get("assessment_unit_type", "Assessment Unit")

    stage = row.get("stage_pct_total", row.get("stage_of_extraction_pct", None))
    cat = row.get("categorization", row.get("categorization_raw", "Unknown"))
    aegr = row.get("aegr_total", None)
    total_ext = row.get("total_extraction_total", None)
    net_avail = row.get("net_availability_total", None)
    recharge = row.get("total_annual_gw_recharge_total", None)
    nat_disc = row.get("natural_discharges_total", None)
    irr_ext = row.get("extraction_irrigation_total", None)
    dom_ext = row.get("extraction_domestic_total", None)
    ind_ext = row.get("extraction_industrial_total", None)
    quality_f = row.get("quality_fluoride_c", None)
    quality_a = row.get("quality_arsenic_c", None)

    unit_str = f"{unit} {unit_type}" if unit else f"{district} district"

    parts = [
        f"Groundwater assessment for {unit_str} in {district} district, "
        f"{state}, India. Assessment year: {year_label} ({year})."
    ]

    if stage is not None:
        parts.append(
            f"The Stage of Ground Water Extraction is {stage:.1f}%, "
            f"categorizing this unit as {cat}."
        )
        if stage > 100:
            parts.append(
                "CRITICAL: This unit is Over-Exploited — extraction exceeds "
                "annual recharge capacity. Urgent intervention required."
            )
        elif stage > 90:
            parts.append(
                "WARNING: This unit is Critical — approaching depletion. "
                "Extraction is 90-100% of extractable resource."
            )
        elif stage > 70:
            parts.append(
                "CAUTION: This unit is Semi-Critical — stage between 70-90%. "
                "Groundwater stress is significant."
            )

    if aegr is not None:
        parts.append(
            f"Annual Extractable Ground Water Resource (AEGR): {aegr:.2f} Ham "
            f"(Hectare Meters). This is the maximum sustainable annual extraction."
        )

    if recharge is not None:
        parts.append(
            f"Total Annual Ground Water Recharge (TGWR): {recharge:.2f} Ham."
        )

    if nat_disc is not None:
        parts.append(
            f"Natural Discharges (ecological flow): {nat_disc:.2f} Ham. "
            f"AEGR = TGWR - Natural Discharges = {recharge:.2f} - {nat_disc:.2f}."
            if recharge else f"Natural Discharges: {nat_disc:.2f} Ham."
        )

    if total_ext is not None:
        parts.append(f"Total Ground Water Extraction: {total_ext:.2f} Ham.")

    extracts = []
    if irr_ext is not None:
        extracts.append(f"Irrigation: {irr_ext:.2f} Ham")
    if dom_ext is not None:
        extracts.append(f"Domestic: {dom_ext:.2f} Ham")
    if ind_ext is not None:
        extracts.append(f"Industrial: {ind_ext:.2f} Ham")
    if extracts:
        parts.append(f"Extraction breakdown — {'; '.join(extracts)}.")

    if net_avail is not None:
        parts.append(
            f"Net Ground Water Availability for future use: {net_avail:.2f} Ham."
        )

    aquifer = row.get("aquifer_code", row.get("aquifer_type", ""))
    if aquifer:
        parts.append(f"Aquifer type: {aquifer}.")

    quality_issues = []
    if quality_f and str(quality_f).lower() not in ("nan", "none", "0", "false", ""):
        quality_issues.append("Fluoride contamination")
    if quality_a and str(quality_a).lower() not in ("nan", "none", "0", "false", ""):
        quality_issues.append("Arsenic contamination")
    if quality_issues:
        parts.append(f"Quality issues: {', '.join(quality_issues)} detected.")

    return " ".join(parts)


def build_block_risk_narrative(row: dict) -> str:
    """Build narrative for an Annexure 4A/4B at-risk block record."""
    cat = row.get("categorization", "Unknown")
    quality = row.get("quality_tag", "")
    block = row.get("block_name", "Unknown Block")
    district = row.get("district", "Unknown District")
    state = row.get("state", "Unknown State")
    year = row.get("assessment_year", "Unknown")
    source = row.get("annexure_source", "Annexure4")

    if quality:
        return (
            f"{block} block in {district} district, {state} has groundwater "
            f"quality contamination: {quality}. Source: {source}, Year: {year}. "
            f"This block requires water quality intervention."
        )
    else:
        return (
            f"{block} block in {district} district, {state} is classified as "
            f"{cat} in the {year} GEC assessment. "
            f"Source: {source} (Annexure 4A - At-Risk Block List)."
        )
