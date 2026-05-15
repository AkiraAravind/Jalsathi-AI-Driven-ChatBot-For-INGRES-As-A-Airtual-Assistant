"""
jepa_encoder.py — V-JEPA inspired Temporal Trajectory Encoder
INGRES ChatBOT | Phase 2 | SIH25066

Implements a JEPA-inspired (Joint Embedding Predictive Architecture) encoder
for groundwater time-series data. Instead of encoding video frames, we encode
sequences of annual groundwater assessment metrics.

Architecture:
  Input:  N × 8 matrix (N years × 8 key metrics)
  Output: 1024-dim float vector (jepa_vector)

How the temporal trajectory is captured:
  1. current_state   (8 dims)  → Latest year's normalized metric values
  2. delta_vector    (8 dims)  → Avg annual change (velocity) per metric
  3. delta2_vector   (8 dims)  → Avg change in delta (acceleration)
  4. trend_slopes    (8 dims)  → Linear regression slope over all years
  5. mean_vector     (8 dims)  → Mean across years
  6. std_vector      (8 dims)  → Std deviation (volatility)
  7. min_vector      (8 dims)  → Minimum across years
  8. max_vector      (8 dims)  → Maximum across years
  9. range_vector    (8 dims)  → max - min (total excursion)
  10. norm_time_vec  (8 dims)  → Values normalized to [0,1] time axis

  → Concatenated feature vector: 80 dims
  → Projected to 1024-dim via fixed seed random projection matrix W (80 × 1024)
  → L2-normalized → jepa_vector

Why random projection works:
  Johnson-Lindenstrauss lemma guarantees approximate distance preservation
  in the projected space. Since W is FIXED (seeded), the same input always
  produces the same output. This is the "encoder" in our JEPA-inspired approach.

Predictive capability:
  Districts with similar trajectories (e.g., Safe→Critical→OE over 5 years)
  will have jepa_vectors that cluster in the 1024-dim space.
  A "query trajectory" (synthetic or from known OE districts) can be embedded
  and nearest neighbors found via ANN search in Supabase.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Categorization → numeric score for JEPA encoding
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_SCORE = {
    "Safe":           0.25,
    "Semi-Critical":  0.50,
    "Critical":       0.75,
    "Over-Exploited": 1.00,
    "Saline":         0.60,
    "Unknown":        0.50,
}

# Fixed random projection matrix (seed=42 for reproducibility)
# Shape: (80, 1024) — projects 80-dim feature vector to 1024-dim
_PROJECTION_MATRIX: Optional[np.ndarray] = None

def _get_projection_matrix() -> np.ndarray:
    """Get or create the fixed random projection matrix."""
    global _PROJECTION_MATRIX
    if _PROJECTION_MATRIX is None:
        rng = np.random.RandomState(seed=42)  # Fixed seed — NEVER change
        _PROJECTION_MATRIX = rng.randn(80, 1024).astype(np.float32)
        # Normalize columns for stable projection
        _PROJECTION_MATRIX /= np.linalg.norm(
            _PROJECTION_MATRIX, axis=0, keepdims=True
        ) + 1e-8
    return _PROJECTION_MATRIX


def _safe_float(v) -> float:
    """Convert any value to float safely, return 0.0 on failure."""
    try:
        f = float(v)
        return 0.0 if (np.isnan(f) or np.isinf(f)) else f
    except (TypeError, ValueError):
        return 0.0


def encode_sequence(
    yearly_metrics: List[Dict[str, float]],
    categorizations: List[str],
    state_stats: Optional[Dict[str, Tuple[float, float]]] = None
) -> Tuple[np.ndarray, Dict]:
    """
    Encode a multi-year sequence of groundwater metrics into a 1024-dim JEPA vector.

    Args:
        yearly_metrics: List of dicts, one per year, each with 8 key metric values.
                        Keys: stage_pct, aegr, total_extraction, recharge_rainfall,
                              net_availability, extraction_irrigation,
                              extraction_domestic, extraction_industrial
        categorizations: List of category strings matching each year's entry.
        state_stats: Optional dict of {field: (min_val, max_val)} for normalization.
                     If None, uses the sequence's own min/max (less stable).

    Returns:
        Tuple of (jepa_vector: np.ndarray shape [1024], trajectory_metadata: dict)
    """

    METRICS = [
        "stage_pct", "aegr", "total_extraction", "recharge_rainfall",
        "net_availability", "extraction_irrigation", "extraction_domestic",
        "extraction_industrial"
    ]

    n = len(yearly_metrics)

    if n == 0:
        return np.zeros(1024, dtype=np.float32), {
            "jepa_trend_direction": "insufficient_data",
            "jepa_stage_velocity": 0.0,
            "jepa_years_in_sequence": 0
        }

    # ── Step 1: Build raw matrix (n × 9) — 8 metrics + categorization score ──
    raw = np.zeros((n, 9), dtype=np.float32)
    for i, (metrics, cat) in enumerate(zip(yearly_metrics, categorizations)):
        for j, field in enumerate(METRICS):
            raw[i, j] = _safe_float(metrics.get(field, 0.0))
        raw[i, 8] = CATEGORY_SCORE.get(cat, 0.5)

    # ── Step 2: Normalize each metric to [0, 1] ───────────────────────────────
    normed = np.zeros_like(raw)
    scale_info = []

    for j in range(9):
        col = raw[:, j]
        field = METRICS[j] if j < 8 else "category_score"

        if state_stats and field in state_stats:
            lo, hi = state_stats[field]
        else:
            lo, hi = col.min(), col.max()

        rang = hi - lo
        if rang < 1e-6:
            normed[:, j] = 0.5  # All same value → center
        else:
            normed[:, j] = np.clip((col - lo) / rang, 0.0, 1.0)

        scale_info.append((lo, hi))

    # ── Step 3: Compute temporal features ────────────────────────────────────
    # 3a. Current state (latest year)
    current_state = normed[-1, :]                           # shape: (9,)

    # 3b. Delta (velocity) per year
    if n >= 2:
        deltas = np.diff(normed, axis=0)                    # shape: (n-1, 9)
        delta_vector = deltas.mean(axis=0)                  # avg annual change
    else:
        delta_vector = np.zeros(9, dtype=np.float32)

    # 3c. Acceleration (delta of delta)
    if n >= 3:
        delta2_vector = np.diff(deltas, axis=0).mean(axis=0)
    else:
        delta2_vector = np.zeros(9, dtype=np.float32)

    # 3d. Linear trend slope (OLS) for each metric
    if n >= 2:
        x = np.arange(n, dtype=np.float32)
        x -= x.mean()
        x_var = (x ** 2).sum() + 1e-8
        slopes = np.array([
            (x * normed[:, j]).sum() / x_var for j in range(9)
        ], dtype=np.float32)
    else:
        slopes = np.zeros(9, dtype=np.float32)

    # 3e. Statistical moments
    mean_vec = normed.mean(axis=0)                          # shape: (9,)
    std_vec  = normed.std(axis=0)
    min_vec  = normed.min(axis=0)
    max_vec  = normed.max(axis=0)
    range_vec = max_vec - min_vec

    # ── Step 4: Build 80-dim feature vector ──────────────────────────────────
    # [current_state(9) | delta(9) | delta2(9) | slopes(9) |
    #  mean(9) | std(9) | min(9) | max(9) | range(9) - 1 dim padding]
    # Total: 9×8 = 72 dims + 8 padding = 80 dims

    feature = np.concatenate([
        current_state,     # 9
        delta_vector,      # 9
        delta2_vector,     # 9
        slopes,            # 9
        mean_vec,          # 9
        std_vec,           # 9
        min_vec,           # 9
        max_vec,           # 9
    ])                     # 72 dims total

    # Pad to exactly 80 dims
    if len(feature) < 80:
        feature = np.concatenate([feature, np.zeros(80 - len(feature))])
    feature = feature[:80].astype(np.float32)

    # ── Step 5: Project to 1024-dim ──────────────────────────────────────────
    W = _get_projection_matrix()                            # shape: (80, 1024)
    projected = feature @ W                                 # shape: (1024,)

    # ── Step 6: L2 normalize ──────────────────────────────────────────────────
    norm = np.linalg.norm(projected) + 1e-8
    jepa_vector = (projected / norm).astype(np.float32)

    # ── Step 7: Compute trajectory metadata ───────────────────────────────────
    # Stage % velocity (raw, not normalized) for human-readable metadata
    stage_raw = raw[:, 0]  # stage_pct column, raw values
    if n >= 2:
        stage_velocity = float(np.diff(stage_raw).mean())
    else:
        stage_velocity = 0.0

    latest_stage = float(stage_raw[-1]) if n > 0 else 0.0
    latest_cat = categorizations[-1] if categorizations else "Unknown"

    # Determine trend direction
    if n < 2:
        trend_direction = "insufficient_data"
    elif abs(stage_velocity) < 2.0:
        trend_direction = "stable"
    elif stage_velocity > 0:
        if latest_cat in ("Critical", "Over-Exploited"):
            trend_direction = "worsening_critical"
        else:
            trend_direction = "worsening_safe"
    else:
        trend_direction = "improving"

    metadata = {
        "jepa_trend_direction": trend_direction,
        "jepa_stage_velocity":  round(stage_velocity, 3),
        "jepa_years_in_sequence": n,
    }

    return jepa_vector, metadata


def build_prototype_vector(category: str = "Over-Exploited") -> np.ndarray:
    """
    Build a prototype JEPA query vector for a target trajectory.
    Use for: "Which districts are trending toward Over-Exploited?"

    Args:
        category: The target end-state (e.g. "Over-Exploited")

    Returns:
        1024-dim prototype JEPA vector for ANN search
    """

    # Simulate a district going from Safe → Semi-Critical → Critical → OE
    if category == "Over-Exploited":
        stages     = [45.0, 62.0, 78.0, 92.0, 107.0]    # 5-year worsening
        aegrs      = [2000, 1900, 1850, 1800, 1750]
        extracts   = [900, 1180, 1443, 1656, 1872]        # steadily rising
        recharges  = [1800, 1750, 1700, 1680, 1650]       # declining
        cats       = ["Safe", "Semi-Critical", "Critical", "Critical", "Over-Exploited"]

    elif category == "improving":
        stages     = [105.0, 98.0, 88.0, 75.0, 60.0]
        aegrs      = [1500, 1520, 1550, 1570, 1600]
        extracts   = [1575, 1490, 1364, 1178, 960]
        recharges  = [1800, 1820, 1840, 1860, 1880]
        cats       = ["Over-Exploited", "Critical", "Semi-Critical", "Semi-Critical", "Safe"]

    else:  # Safe / stable
        stages     = [30.0, 32.0, 31.0, 33.0, 30.0]
        aegrs      = [2000, 2010, 2005, 2008, 2012]
        extracts   = [600, 643, 620, 663, 604]
        recharges  = [2200, 2210, 2200, 2208, 2215]
        cats       = ["Safe"] * 5

    n = len(stages)
    yearly = [
        {
            "stage_pct":              stages[i],
            "aegr":                   aegrs[i],
            "total_extraction":       extracts[i],
            "recharge_rainfall":      recharges[i],
            "net_availability":       aegrs[i] - extracts[i],
            "extraction_irrigation":  extracts[i] * 0.75,
            "extraction_domestic":    extracts[i] * 0.15,
            "extraction_industrial":  extracts[i] * 0.10,
        }
        for i in range(n)
    ]

    vec, _ = encode_sequence(yearly, cats)
    return vec
