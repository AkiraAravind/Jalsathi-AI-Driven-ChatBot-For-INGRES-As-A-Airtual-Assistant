"""
column_map.py — 153-Column Canonical Mapping for GEC Central/State Reports
INGRES ChatBOT | Phase 2 | SIH25066

The 153-column GEC reports use a 3-row merged header structure:
  Row 7:  Section headers (e.g. 'Ground Water Recharge (ham)')
  Row 8:  Sub-section headers (e.g. 'Rainfall Recharge', 'Canals')
  Row 9:  Leaf headers: C / NC / PQ / Total (Current/Non-Current/Poor Quality/Total)

This file provides:
  1. COLUMN_INDEX_MAP: Exact positional mapping of col index → canonical field name
  2. ATTR_TABLE_MAP: Attribute Table (26-col) column name → canonical field name
  3. normalize_col(): fuzzy match for column names that vary across years
"""

from typing import Optional
import re

# ─────────────────────────────────────────────────────────────────────────────
# 153-COLUMN POSITIONAL MAP
# Built from direct inspection of CentralReport*.xlsx (row 7 + row 8 + row 9)
# Format: col_index → canonical_field_name
# ─────────────────────────────────────────────────────────────────────────────

COLUMN_INDEX_MAP = {
    # ── Identity ──────────────────────────────────────────────────────────────
    0:   "sl_no",
    1:   "state",
    2:   "district",
    3:   "assessment_unit",

    # ── Rainfall (mm) ─────────────────────────────────────────────────────────
    # Section: "Rainfall (mm)" | Sub: C / NC / PQ / Total
    4:   "rainfall_mm_c",           # Current season
    5:   "rainfall_mm_nc",          # Non-current season
    6:   "rainfall_mm_pq",          # Poor quality zone
    7:   "rainfall_mm_total",       # Total annual rainfall

    # ── Geographical Area (ha) ────────────────────────────────────────────────
    # Section: "Total Geographical Area (ha)" | Sub: Recharge Worthy Area
    8:   "geo_area_rwa_c",          # Recharge Worthy Area - Current
    9:   "geo_area_rwa_nc",
    10:  "geo_area_rwa_pq",
    11:  "geo_area_rwa_total",      # ← USE THIS as recharge_worthy_area_ha
    12:  "geo_area_hilly_c",        # Hilly Area - Current
    13:  "geo_area_total",          # Total Geographical Area

    # ── GW Recharge (ham) — Section starts col 14 ────────────────────────────
    # Sub-section: Rainfall Recharge
    14:  "recharge_rainfall_c",
    15:  "recharge_rainfall_nc",
    16:  "recharge_rainfall_pq",
    17:  "recharge_rainfall_total",

    # Sub-section: Canals
    18:  "recharge_canal_c",
    19:  "recharge_canal_nc",
    20:  "recharge_canal_pq",
    21:  "recharge_canal_total",

    # Sub-section: Surface Water Irrigation
    22:  "recharge_swi_c",
    23:  "recharge_swi_nc",
    24:  "recharge_swi_pq",
    25:  "recharge_swi_total",

    # Sub-section: Ground Water Irrigation
    26:  "recharge_gwi_c",
    27:  "recharge_gwi_nc",
    28:  "recharge_gwi_pq",
    29:  "recharge_gwi_total",

    # Sub-section: Tanks and Ponds
    30:  "recharge_tanks_c",
    31:  "recharge_tanks_nc",
    32:  "recharge_tanks_pq",
    33:  "recharge_tanks_total",

    # Sub-section: Water Conservation Structures
    34:  "recharge_wcs_c",
    35:  "recharge_wcs_nc",
    36:  "recharge_wcs_pq",
    37:  "recharge_wcs_total",

    # Sub-section: Pipelines
    38:  "recharge_pipelines_c",
    39:  "recharge_pipelines_nc",
    40:  "recharge_pipelines_pq",
    41:  "recharge_pipelines_total",

    # Sub-section: Sewages and Flash Flood Channels
    42:  "recharge_sewage_c",
    43:  "recharge_sewage_nc",
    44:  "recharge_sewage_pq",
    45:  "recharge_sewage_total",

    # Other Sources (Stream Channels etc.) subtotal
    46:  "recharge_other_c",
    47:  "recharge_other_nc",
    48:  "recharge_other_pq",
    49:  "recharge_other_total",

    # ── Inflows and Outflows (ham) — Section col 50 ───────────────────────────
    # Sub-section: Base Flow
    50:  "baseflow_c",
    51:  "baseflow_nc",
    52:  "baseflow_pq",
    53:  "baseflow_total",

    # Sub-section: Stream Recharges
    54:  "stream_recharge_c",
    55:  "stream_recharge_nc",
    56:  "stream_recharge_pq",
    57:  "stream_recharge_total",

    # Sub-section: Lateral Flows
    58:  "lateral_flow_c",
    59:  "lateral_flow_nc",
    60:  "lateral_flow_pq",
    61:  "lateral_flow_total",

    # Sub-section: Vertical Flows
    62:  "vertical_flow_c",
    63:  "vertical_flow_nc",
    64:  "vertical_flow_pq",
    65:  "vertical_flow_total",

    # Sub-section: Evaporation
    66:  "evaporation_c",
    67:  "evaporation_nc",
    68:  "evaporation_pq",
    69:  "evaporation_total",

    # Sub-section: Transpiration
    70:  "transpiration_c",
    71:  "transpiration_nc",
    72:  "transpiration_pq",
    73:  "transpiration_total",

    # Sub-section: Evapotranspiration
    74:  "evapotranspiration_c",
    75:  "evapotranspiration_nc",
    76:  "evapotranspiration_pq",
    77:  "evapotranspiration_total",

    # Inflows subtotal
    78:  "inflows_outflows_c",
    79:  "inflows_outflows_nc",
    80:  "inflows_outflows_pq",
    81:  "inflows_outflows_total",

    # ── Annual GW Recharge total (ham) — col 82 ───────────────────────────────
    82:  "total_annual_gw_recharge_c",
    83:  "total_annual_gw_recharge_nc",
    84:  "total_annual_gw_recharge_pq",
    85:  "total_annual_gw_recharge_total",  # ← TGWR: USE THIS

    # ── Environmental Flows / Natural Discharges (ham) — col 86 ─────────────
    86:  "natural_discharges_c",
    87:  "natural_discharges_nc",
    88:  "natural_discharges_pq",
    89:  "natural_discharges_total",        # ← ND: USE THIS

    # ── Annual Extractable GW Resource (ham) — col 90 ────────────────────────
    # AEGR = TGWR - ND (GEC-2015 Sec 2.3)
    90:  "aegr_c",
    91:  "aegr_nc",
    92:  "aegr_pq",
    93:  "aegr_total",                      # ← AEGR: USE THIS

    # ── GW Extraction for all uses (ham) — col 94 ────────────────────────────
    # Sub-section: Domestic
    94:  "extraction_domestic_c",
    95:  "extraction_domestic_nc",
    96:  "extraction_domestic_pq",
    97:  "extraction_domestic_total",       # ← GE_DOM

    # Sub-section: Industrial
    98:  "extraction_industrial_c",
    99:  "extraction_industrial_nc",
    100: "extraction_industrial_pq",
    101: "extraction_industrial_total",     # ← GE_IND

    # Sub-section: Irrigation
    102: "extraction_irrigation_c",
    103: "extraction_irrigation_nc",
    104: "extraction_irrigation_pq",
    105: "extraction_irrigation_total",     # ← GE_IRR

    # Total Extraction subtotal
    106: "total_extraction_c",
    107: "total_extraction_nc",
    108: "total_extraction_pq",
    109: "total_extraction_total",          # ← GE_ALL: USE THIS

    # ── Stage of GW Extraction (%) — col 110 ─────────────────────────────────
    # Stage = (GE_ALL / AEGR) × 100
    110: "stage_pct_c",
    111: "stage_pct_nc",
    112: "stage_pct_pq",
    113: "stage_pct_total",                # ← PRIMARY KEY METRIC

    # ── Allocation for Domestic Use — col 114 ────────────────────────────────
    114: "allocation_domestic_c",
    115: "allocation_domestic_nc",
    116: "allocation_domestic_pq",
    117: "allocation_domestic_total",       # ← Alloc 2025

    # ── Net Annual GW Availability (ham) — col 118 ───────────────────────────
    118: "net_availability_c",
    119: "net_availability_nc",
    120: "net_availability_pq",
    121: "net_availability_total",          # ← Net Avail: USE THIS

    # ── Quality Tagging — col 122 ────────────────────────────────────────────
    122: "quality_fluoride_c",
    123: "quality_fluoride_nc",
    124: "quality_fluoride_pq",
    125: "quality_arsenic_c",
    126: "quality_arsenic_nc",
    127: "quality_arsenic_pq",

    # ── Additional Potential Resources (ham) — col 128 ───────────────────────
    128: "additional_waterlogged",
    129: "additional_flood_prone",
    130: "additional_spring_discharge",

    # ── Coastal Areas (ham) — col 131 ────────────────────────────────────────
    131: "coastal_c",
    132: "coastal_nc",
    133: "coastal_pq",
    134: "coastal_total",

    # ── In-Storage Unconfined GW Resources (ham) — col 135 ───────────────────
    135: "unconfined_instorage_fresh",
    136: "unconfined_instorage_saline",
    137: "unconfined_total_fresh",
    138: "unconfined_total_saline",

    # ── Dynamic Confined GW Resources (ham) — col 139 ────────────────────────
    139: "confined_dynamic_fresh",
    140: "confined_dynamic_saline",
    141: "confined_instorage_fresh",
    142: "confined_instorage_saline",
    143: "confined_total_fresh",
    144: "confined_total_saline",

    # ── Dynamic Semi-Confined GW Resources (ham) — col 145 ───────────────────
    145: "semiconfined_dynamic_fresh",
    146: "semiconfined_dynamic_saline",
    147: "semiconfined_instorage_fresh",
    148: "semiconfined_instorage_saline",
    149: "semiconfined_total_fresh",
    150: "semiconfined_total_saline",

    # ── Total GW Availability in area (ham) — col 151 ────────────────────────
    151: "total_gw_availability_fresh",
    152: "total_gw_availability_saline",
}

# ─────────────────────────────────────────────────────────────────────────────
# ATTRIBUTE TABLE MAP (26 columns)
# Maps exact pandas column names → canonical schema field names
# ─────────────────────────────────────────────────────────────────────────────

ATTR_TABLE_MAP = {
    "Sl.No":                                              "sl_no",
    "State_code":                                         "state_code",
    "State_District_Code":                                "district_code",
    "State_District_Block_Code":                          "assessment_unit_code",
    "State":                                              "state",
    "District":                                           "district",
    "Assessment Unit  Name":                              "assessment_unit",
    "Assessment Unit Type":                               "assessment_unit_type",
    "Total Geographical Area":                            "geo_area_total",
    "Recharge Worthy Area":                               "geo_area_rwa_total",
    "Recharge from Rainfall-MON":                         "recharge_rainfall_monsoon",
    "Recharge from Other Sources-MON":                    "recharge_other_monsoon_total",
    "Recharge from Rainfall-NM":                          "recharge_rainfall_nonmonsoon",
    "Recharge from Other Sources-NM":                     "recharge_other_nonmonsoon",
    "Total Annual  Ground Water (Ham) Recharge":          "total_annual_gw_recharge_total",
    "Total Natural Discharges (Ham)":                     "natural_discharges_total",
    "Annual Extractable Ground Water Resource  (Ham)":    "aegr_total",
    "Irrigation Use  (Ham)":                              "extraction_irrigation_total",
    "Industrial Use (Ham)":                               "extraction_industrial_total",
    "Domestic Use (Ham)":                                 "extraction_domestic_total",
    "Total Extraction  (Ham)":                            "total_extraction_total",
    "Annual GW Allocation for  for Domestic Use  as on 2025  (Ham)": "allocation_domestic_total",
    "Net Ground Water Availability for future  use  (Ham)": "net_availability_total",
    "Stage of Ground Water  Extraction (%)":              "stage_pct_total",
    "Categorization (OE/Critical/Semicritical/Safe)":     "categorization_raw",
    "Bo_Aquifer":                                         "aquifer_code",
}

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORIZATION NORMALIZER
# Handles all known variants across years and formats
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIZATION_MAP = {
    # Over-Exploited variants
    "over exploited":   "Over-Exploited",
    "over-exploited":   "Over-Exploited",
    "overexploited":    "Over-Exploited",
    "oe":               "Over-Exploited",
    "o.e":              "Over-Exploited",
    "o.e.":             "Over-Exploited",
    "over exp":         "Over-Exploited",

    # Critical variants
    "critical":         "Critical",

    # Semi-Critical variants
    "semi critical":    "Semi-Critical",
    "semi-critical":    "Semi-Critical",
    "semicritical":     "Semi-Critical",
    "semi_critical":    "Semi-Critical",
    "s.c":              "Semi-Critical",
    "sc":               "Semi-Critical",

    # Safe variants
    "safe":             "Safe",

    # Saline variants
    "saline":           "Saline",
}


def normalize_categorization(raw: str) -> str:
    """Convert any raw categorization string to canonical form."""
    if not raw or str(raw).strip().lower() in ("nan", "none", ""):
        return "Unknown"
    key = str(raw).strip().lower()
    return CATEGORIZATION_MAP.get(key, raw.strip().title())


def normalize_col_name(name: str) -> Optional[str]:
    """
    Fuzzy-normalize a column name to its canonical form.
    Used for columns that drift slightly between assessment years.
    Returns None if no match found.
    """
    if not name:
        return None
    n = str(name).strip().lower()
    n = re.sub(r'\s+', ' ', n)          # collapse whitespace
    n = re.sub(r'[().,\-]', '', n)      # remove punctuation
    n = re.sub(r'\bham\b', '', n)       # remove unit labels
    n = re.sub(r'\bha\b', '', n)
    n = re.sub(r'\bpercent\b', '', n)
    n = n.strip()

    # Pattern-based extraction
    if 'stage of ground water extraction' in n or 'stage of gw extraction' in n:
        return 'stage_pct_total'
    if 'total extraction' in n and 'annual' not in n:
        return 'total_extraction_total'
    if 'annual extractable' in n or 'aegr' in n:
        return 'aegr_total'
    if 'total annual ground water recharge' in n or 'tgwr' in n:
        return 'total_annual_gw_recharge_total'
    if 'natural discharge' in n:
        return 'natural_discharges_total'
    if 'net ground water availability' in n or 'net annual ground water' in n:
        return 'net_availability_total'
    if 'categorization' in n:
        return 'categorization_raw'
    if 'total geographical area' in n:
        return 'geo_area_total'
    if 'recharge worthy area' in n:
        return 'geo_area_rwa_total'

    return None


# ── Priority "Total" column indices (for JEPA vector construction) ────────────
# These are the 8 key metrics used to build the JEPA temporal vector.
JEPA_KEY_INDICES = {
    "stage_pct":              113,  # Stage of extraction (%) - TOTAL
    "aegr":                    93,  # Annual Extractable GW Resource - TOTAL
    "total_extraction":       109,  # Total extraction all uses - TOTAL
    "recharge_rainfall":       17,  # Rainfall recharge - TOTAL
    "net_availability":       121,  # Net GW availability - TOTAL
    "extraction_irrigation":  105,  # Irrigation draft - TOTAL
    "extraction_domestic":     97,  # Domestic draft - TOTAL
    "extraction_industrial":  101,  # Industrial draft - TOTAL
}

# The same metrics for Attribute Table (column names after mapping)
JEPA_KEY_ATTR_FIELDS = [
    "stage_pct_total",
    "aegr_total",
    "total_extraction_total",
    "recharge_rainfall_monsoon",
    "net_availability_total",
    "extraction_irrigation_total",
    "extraction_domestic_total",
    "extraction_industrial_total",
]
