"""
ingestor.py — Deep Ingestion Engine (Main Orchestrator)
INGRES ChatBOT | Phase 2 | SIH25066

Processes ALL GEC datasets and loads them into Supabase:
  1. Attribute Tables (26-col, block-level, 5 years, ~8092 rows each)
  2. Annexure-1 (state-level summary, 5 years)
  3. Annexure-2 (district-level summary, 5 years)
  4. Annexure-4A (named at-risk blocks by category)
  5. Annexure-4B (named blocks with quality contamination)
  6. Central/district reports (153-col, all India district, 6 years)
  7. State reports (153-col, per state block-level, 36 states × 6 years)
  8. GEC Manual (PDF text chunks for semantic search)
  9. JEPA vector computation (multi-year temporal trajectory per district)

Usage:
  cd e:\\INGRES_TBP
  python -m project.backend.ingestion.ingestor --source attribute_table
  python -m project.backend.ingestion.ingestor --source central
  python -m project.backend.ingestion.ingestor --source annexure4
  python -m project.backend.ingestion.ingestor --source gec_manual
  python -m project.backend.ingestion.ingestor --source jepa_build
  python -m project.backend.ingestion.ingestor --source all
"""

import os
import sys
import re
import glob
import json
import logging
import argparse
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# ── Local imports ─────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from project.backend.ingestion.column_map import (
    COLUMN_INDEX_MAP, ATTR_TABLE_MAP, JEPA_KEY_ATTR_FIELDS, JEPA_KEY_INDICES,
    normalize_categorization
)
from project.backend.ingestion.transformer import GECTransformer
from project.backend.ingestion.jepa_encoder import encode_sequence, CATEGORY_SCORE
from project.backend.ingestion.embedder import (
    embed_passages, build_groundwater_narrative, build_block_risk_narrative
)

# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / "project" / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
DATASETS_DIR = Path(__file__).resolve().parents[3] / "datasets"
PROJECT_DIR  = Path(__file__).resolve().parents[3] / "project"

# JEPA requires >= 2 years per district to compute a meaningful vector
JEPA_MIN_YEARS = 2

# Batching
UPSERT_BATCH = 25   # Supabase rows per batch (embedding vectors are large)
EMBED_BATCH  = 16   # Texts per embedding call

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ingestion.log", mode="a", encoding="utf-8")
    ]
)
log = logging.getLogger("ingestor")


# =============================================================================
# DATA INTEGRITY TRACKER
# =============================================================================

class IntegrityReport:
    """Tracks data quality across the ingestion run."""

    def __init__(self):
        self.files_processed = 0
        self.rows_total = 0
        self.rows_inserted = 0
        self.rows_skipped = 0
        self.rows_errored = 0
        self.missing_value_counts: Dict[str, int] = {}
        self.column_drift_log: List[Dict] = []
        self.year_coverage: Dict[str, List[int]] = {}  # state → [years]
        self.errors: List[str] = []
        self.start_time = datetime.now()

    def log_missing(self, field: str, count: int = 1):
        self.missing_value_counts[field] = self.missing_value_counts.get(field, 0) + count

    def log_column_drift(self, file: str, expected: str, found: str):
        self.column_drift_log.append({
            "file": file, "expected": expected, "found": found
        })

    def log_year(self, state: str, year: int):
        if state not in self.year_coverage:
            self.year_coverage[state] = []
        if year not in self.year_coverage[state]:
            self.year_coverage[state].append(year)

    def summary(self) -> str:
        dur = (datetime.now() - self.start_time).seconds
        top_missing = sorted(
            self.missing_value_counts.items(), key=lambda x: -x[1]
        )[:10]

        lines = [
            "",
            "=" * 60,
            "  DATA INTEGRITY REPORT",
            "=" * 60,
            f"  Duration:          {dur}s",
            f"  Files processed:   {self.files_processed}",
            f"  Rows total:        {self.rows_total:,}",
            f"  Rows inserted:     {self.rows_inserted:,}",
            f"  Rows skipped:      {self.rows_skipped:,}",
            f"  Rows errored:      {self.rows_errored:,}",
            f"  Column drift logs: {len(self.column_drift_log)}",
            "",
            "  Top Missing Fields:",
        ]
        for field, count in top_missing:
            lines.append(f"    {field:<40} {count:>6} missing values")

        if self.errors:
            lines.append(f"\n  Errors ({len(self.errors)}):")
            for e in self.errors[:5]:
                lines.append(f"    • {e}")

        lines.append("=" * 60)
        return "\n".join(lines)


report = IntegrityReport()


# =============================================================================
# SUPABASE CLIENT
# =============================================================================

def get_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in project/.env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def upsert_batch(client: Client, table: str, rows: List[Dict]) -> int:
    """Upsert a batch of rows with conflict resolution on 'id'. Returns count inserted."""
    if not rows:
        return 0
    try:
        client.table(table).upsert(rows, on_conflict="id").execute()
        return len(rows)
    except Exception as e:
        log.error(f"  Upsert failed for {table}: {e}")
        report.errors.append(f"Upsert {table}: {str(e)[:100]}")
        return 0


def insert_batch(client: Client, table: str, rows: List[Dict]) -> int:
    """Plain insert (for tables with auto-generated UUIDs like gec_manual_index)."""
    if not rows:
        return 0
    try:
        # Use ignore_duplicates to handle re-runs gracefully
        client.table(table).insert(rows, returning="minimal").execute()
        return len(rows)
    except Exception as e:
        # Try inserting one-by-one to isolate bad rows
        inserted = 0
        for row in rows:
            try:
                client.table(table).insert(row, returning="minimal").execute()
                inserted += 1
            except Exception:
                pass
        if inserted < len(rows):
            log.warning(f"  {table}: {len(rows)-inserted} rows failed individual insert")
        return inserted


# =============================================================================
# YEAR EXTRACTION
# =============================================================================

YEAR_PATTERNS = [
    r'(\d{4})-(\d{2,4})',   # 2022-23, 2022-2023
    r'(\d{4})_(\d{2,4})',
    r'Assessment Year.*?(\d{4})',
]

def extract_year_from_file(filepath: str, df_raw: Optional[pd.DataFrame] = None) -> Tuple[int, str]:
    """
    Extract assessment year from filename or file metadata row.
    Returns (canonical_year: int, label: str), e.g. (2022, '2022-23')
    """
    fname = Path(filepath).name

    # Method 1: Check embedded metadata row in Central/State reports
    if df_raw is not None:
        for i in range(6):
            try:
                row = df_raw.iloc[i].dropna()
                for v in row.values:
                    m = re.search(r'(\d{4})-(\d{2,4})', str(v))
                    if m:
                        yr = int(m.group(1))
                        label = f"{m.group(1)}-{m.group(2)}"
                        return yr, label
            except Exception:
                pass

    # Method 2: Parse from filename timestamp (Unix ms embedded in name)
    # Format: attributeReport1774714925640.xlsx → timestamp-based, not year
    # For these, we use the file modification order as proxy

    # Method 3: Try common year patterns in filename
    for pat in YEAR_PATTERNS:
        m = re.search(pat, fname)
        if m:
            yr = int(m.group(1))
            return yr, fname

    # Fallback: use file modification time
    mtime = os.path.getmtime(filepath)
    return 2024, "Unknown_Year"


# =============================================================================
# ATTRIBUTE TABLE INGESTION
# =============================================================================

def ingest_attribute_tables(client: Client):
    """
    Process the 5 Attribute Table files (most comprehensive block-level data).
    Each file: ~8092 rows × 26 columns.
    """
    log.info("\n[1] Processing Attribute Tables...")
    files = sorted(glob.glob(str(DATASETS_DIR / "Attribute table" / "*.xlsx")))
    log.info(f"  Found {len(files)} files")

    # Assign years by file order (oldest to newest based on filename timestamp)
    # Files are named attributeReport{timestamp}.xlsx — higher timestamp = more recent
    YEAR_SEQUENCE = [2017, 2020, 2022, 2023, 2024]

    all_rows = []

    for idx, fpath in enumerate(files):
        year = YEAR_SEQUENCE[idx] if idx < len(YEAR_SEQUENCE) else 2024
        year_label = f"{year}-{str(year+1)[2:]}"
        report.files_processed += 1

        log.info(f"  → {Path(fpath).name} (year={year})")

        try:
            df = pd.read_excel(fpath, sheet_name="Table", dtype=str)
        except Exception as e:
            log.error(f"    Cannot read {fpath}: {e}")
            report.errors.append(f"Read {Path(fpath).name}: {str(e)[:100]}")
            continue

        log.info(f"    Rows: {len(df)}, Columns: {len(df.columns)}")
        report.rows_total += len(df)

        # Check for column drift
        for col in df.columns:
            if col not in ATTR_TABLE_MAP:
                report.log_column_drift(Path(fpath).name, "Expected ATTR col", col)

        narratives = []
        mapped_rows = []

        for _, row in df.iterrows():
            try:
                r = {}

                # Map all 26 columns
                for col, canonical in ATTR_TABLE_MAP.items():
                    raw_val = row.get(col, None)
                    if pd.isna(raw_val) or str(raw_val).strip().lower() in ("nan", "none", ""):
                        report.log_missing(canonical)
                        r[canonical] = None
                    else:
                        r[canonical] = raw_val

                # Use GECTransformer for deep flattening
                raw_metrics = GECTransformer.flatten_row(row, ATTR_TABLE_MAP)
                state = normalize_categorization(str(raw_metrics.get("state", "")))
                district = str(raw_metrics.get("district", "")).strip()

                if not state or not district or state.lower() in ("nan", ""):
                    report.rows_skipped += 1
                    continue

                # Normalize categorization
                cat_raw = str(r.get("categorization_raw", "") or "")
                categorization = normalize_categorization(cat_raw)

                # Safe-convert numerics
                def safe_num(key: str) -> Optional[float]:
                    v = r.get(key)
                    if v is None:
                        return None
                    try:
                        return float(str(v).replace(",", ""))
                    except (ValueError, TypeError):
                        return None

                stage_pct = safe_num("stage_pct_total")
                aegr = safe_num("aegr_total")
                total_ext = safe_num("total_extraction_total")
                net_avail = safe_num("net_availability_total")
                recharge = safe_num("total_annual_gw_recharge_total")

                if stage_pct is None:
                    report.log_missing("stage_pct_total")
                    report.rows_skipped += 1
                    continue

                record = {
                    "state":                          state,
                    "state_code":                     str(r.get("state_code") or ""),
                    "district":                       district,
                    "district_code":                  str(r.get("district_code") or ""),
                    "assessment_unit":                str(r.get("assessment_unit") or ""),
                    "assessment_unit_code":           str(r.get("assessment_unit_code") or ""),
                    "assessment_unit_type":           str(r.get("assessment_unit_type") or "BLOCK").upper(),
                    "assessment_year":                year,
                    "assessment_year_label":          year_label,
                    "data_source":                    "Attribute_Table",
                    "geographical_area_ha":           safe_num("geo_area_total"),
                    "recharge_worthy_area_ha":        safe_num("geo_area_rwa_total"),
                    "recharge_rainfall_monsoon":      safe_num("recharge_rainfall_monsoon"),
                    "recharge_other_monsoon_total":   safe_num("recharge_other_monsoon_total"),
                    "recharge_rainfall_nonmonsoon":   safe_num("recharge_rainfall_nonmonsoon"),
                    "total_annual_gw_recharge":       recharge,
                    "natural_discharges":             safe_num("natural_discharges_total"),
                    "aegr":                           aegr,
                    "total_extraction_irrigation":    safe_num("extraction_irrigation_total"),
                    "total_extraction_domestic":      safe_num("extraction_domestic_total"),
                    "total_extraction_industrial":    safe_num("extraction_industrial_total"),
                    "total_extraction":               total_ext,
                    "gw_allocation_domestic_2025":    safe_num("allocation_domestic_total"),
                    "net_gw_availability":            net_avail,
                    "stage_of_extraction_pct":        stage_pct,
                    "categorization":                 categorization,
                    "aquifer_code":                   str(r.get("aquifer_code") or ""),
                    "raw_metrics":                    raw_metrics,
                }

                # Build narrative for semantic embedding
                embed_input = {**record, "assessment_year_label": year_label}
                narrative = build_groundwater_narrative(embed_input, source="attribute_table")
                narratives.append(narrative)
                mapped_rows.append(record)

                report.log_year(state, year)

            except Exception as e:
                report.rows_errored += 1
                report.errors.append(f"Row error in {Path(fpath).name}: {str(e)[:80]}")
                continue

        # Batch embed
        log.info(f"    Embedding {len(narratives)} records...")
        if narratives:
            try:
                embeddings = embed_passages(narratives, batch_size=EMBED_BATCH)

                for i, (record, emb) in enumerate(zip(mapped_rows, embeddings)):
                    record["semantic_vector"] = emb.tolist()
                    all_rows.append(record)

            except Exception as e:
                log.error(f"    Embedding failed: {e}")
                report.errors.append(f"Embedding attr {Path(fpath).name}: {str(e)[:100]}")
                # Still add records without semantic_vector
                all_rows.extend(mapped_rows)

    # Bulk upsert
    log.info(f"  Upserting {len(all_rows)} rows to groundwater_time_series...")
    _upsert_gts_rows(client, all_rows)


# =============================================================================
# CENTRAL / STATE REPORT INGESTION (153-col)
# =============================================================================

def _parse_153col_file(fpath: str) -> Tuple[pd.DataFrame, str, int]:
    """
    Parse a 153-column Central or State GEC report.
    Returns (dataframe_with_canonical_cols, year_label, year_int)
    """
    df_raw = pd.read_excel(fpath, header=None, dtype=str)
    year_int, year_label = extract_year_from_file(fpath, df_raw)

    # Data starts at row 10 (after 3-row merged header block)
    # Find exact data start by looking for first row with numeric state/district data
    data_start = 10
    for i in range(7, min(15, len(df_raw))):
        row = df_raw.iloc[i]
        if pd.notna(row.iloc[1]) and str(row.iloc[1]).strip().lower() not in (
            "nan", "state", "states", ""
        ):
            data_start = i
            break

    df_data = df_raw.iloc[data_start:].reset_index(drop=True)
    df_data.columns = range(len(df_data.columns))

    # Rename columns using positional map
    rename = {idx: name for idx, name in COLUMN_INDEX_MAP.items() if idx < len(df_data.columns)}
    df_data = df_data.rename(columns=rename)

    return df_data, year_label, year_int


def ingest_central_reports(client: Client):
    """Process 6 Central/district 153-col reports (all India district level)."""
    log.info("\n[2] Processing Central/District Reports (153-col)...")
    files = sorted(glob.glob(str(DATASETS_DIR / "Central" / "district" / "*.xlsx")))
    log.info(f"  Found {len(files)} files")
    _ingest_153col_files(client, files, source="Central_District")


def ingest_state_reports(client: Client, state_filter: Optional[str] = None):
    """Process state-level 153-col reports for all (or one) state(s)."""
    state_dirs = sorted(glob.glob(str(DATASETS_DIR / "state" / "*")))
    if state_filter:
        state_dirs = [d for d in state_dirs if state_filter.upper() in d.upper()]

    log.info(f"\n[3] Processing State Reports for {len(state_dirs)} states...")

    for state_dir in state_dirs:
        state_name = Path(state_dir).name
        files = sorted(glob.glob(str(Path(state_dir) / "*.xlsx")))
        if not files:
            continue
        log.info(f"  → {state_name} ({len(files)} files)")
        _ingest_153col_files(client, files, source=f"State_{state_name}")


def _ingest_153col_files(client: Client, files: List[str], source: str):
    """Shared logic for Central and State 153-col files."""
    all_rows = []

    for fpath in files:
        report.files_processed += 1
        log.info(f"    Processing {Path(fpath).name}...")

        try:
            df, year_label, year_int = _parse_153col_file(fpath)
        except Exception as e:
            log.error(f"    Parse error: {e}")
            report.errors.append(f"Parse {Path(fpath).name}: {str(e)[:100]}")
            continue

        log.info(f"    Year: {year_label} | Rows: {len(df)}")
        report.rows_total += len(df)

        narratives = []
        mapped_rows = []

        for _, row in df.iterrows():

            def g(field: str, default=None):
                """Get canonical field value safely."""
                v = row.get(field, default)
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    return default
                if isinstance(v, str) and v.strip().lower() in ("nan", "none", ""):
                    return default
                return v

            def gf(field: str) -> Optional[float]:
                """Get field as float."""
                v = g(field)
                if v is None:
                    return None
                try:
                    return float(str(v).replace(",", "").strip())
                except (ValueError, TypeError):
                    report.log_missing(field)
                    return None

            # Use GECTransformer for 153-col flattening
            raw_metrics = GECTransformer.flatten_row(row, COLUMN_INDEX_MAP)
            state       = normalize_categorization(str(raw_metrics.get("state", "")))
            district    = str(raw_metrics.get("district", "")).strip()

            if not state or not district or state.lower() in ("nan", "s.no", ""):
                report.rows_skipped += 1
                continue

            stage_pct = gf("stage_pct_total")
            if stage_pct is None:
                report.log_missing("stage_pct_total")
                report.rows_skipped += 1
                continue

            aegr = gf("aegr_total")
            total_ext = gf("total_extraction_total")
            recharge = gf("total_annual_gw_recharge_total")

            # Derive categorization from stage (153-col files don't always have it)
            if stage_pct > 100:
                categorization = "Over-Exploited"
            elif stage_pct > 90:
                categorization = "Critical"
            elif stage_pct > 70:
                categorization = "Semi-Critical"
            else:
                categorization = "Safe"

            # Quality flags
            q_f = g("quality_fluoride_c")
            q_a = g("quality_arsenic_c")
            has_fluoride = bool(q_f and str(q_f).lower() not in ("nan", "none", "0", ""))
            has_arsenic = bool(q_a and str(q_a).lower() not in ("nan", "none", "0", ""))
            if has_fluoride or has_arsenic:
                categorization = "Saline"

            record = {
                "state":                         state,
                "district":                      district,
                "assessment_unit":               str(g("assessment_unit") or ""),
                "assessment_unit_type":          "DISTRICT",
                "assessment_year":               year_int,
                "assessment_year_label":         year_label,
                "data_source":                   source,
                # Rainfall
                "recharge_rainfall_monsoon":     gf("recharge_rainfall_c"),
                "recharge_rainfall_nonmonsoon":  gf("recharge_rainfall_nc"),
                # Recharge
                "total_annual_gw_recharge":      recharge,
                "natural_discharges":            gf("natural_discharges_total"),
                "aegr":                          aegr,
                # Extraction breakdown
                "extraction_domestic_c":         gf("extraction_domestic_c"),
                "total_extraction_domestic":     gf("extraction_domestic_total"),
                "total_extraction_industrial":   gf("extraction_industrial_total"),
                "total_extraction_irrigation":   gf("extraction_irrigation_total"),
                "total_extraction":              total_ext,
                # Flows
                "baseflow":                      gf("baseflow_total"),
                "lateral_flow":                  gf("lateral_flow_total"),
                "vertical_interaquifer_flow":    gf("vertical_flow_total"),
                "evaporation":                   gf("evaporation_total"),
                "transpiration":                 gf("transpiration_total"),
                # Outputs
                "gw_allocation_domestic_2025":   gf("allocation_domestic_total"),
                "net_gw_availability":           gf("net_availability_total"),
                "stage_of_extraction_pct":       stage_pct,
                "categorization":                categorization,
                # Quality
                "quality_fluoride":              has_fluoride,
                "quality_arsenic":               has_arsenic,
                # Aquifer
                "instorage_unconfined_fresh":    gf("unconfined_instorage_fresh"),
                "dynamic_confined_fresh":        gf("confined_dynamic_fresh"),
                "dynamic_semiconfined_fresh":    gf("semiconfined_dynamic_fresh"),
                # Additional
                "additional_waterlogged":        gf("additional_waterlogged"),
                "additional_flood_prone":        gf("additional_flood_prone"),
                "additional_spring_discharge":   gf("additional_spring_discharge"),
                "raw_metrics":                   raw_metrics,
            }

            narrative = build_groundwater_narrative(record, source=source)
            narratives.append(narrative)
            mapped_rows.append(record)
            report.log_year(state, year_int)

        # Embed batch
        if narratives:
            try:
                embeddings = embed_passages(narratives, batch_size=EMBED_BATCH)
                for record, emb in zip(mapped_rows, embeddings):
                    record["semantic_vector"] = emb.tolist()
                    all_rows.append(record)
            except Exception as e:
                log.error(f"    Embedding error: {e}")
                all_rows.extend(mapped_rows)

    log.info(f"  Upserting {len(all_rows)} rows...")
    _upsert_gts_rows(client, all_rows)


# =============================================================================
# ANNEXURE 4 INGESTION (Named At-Risk Blocks)
# =============================================================================

def ingest_annexure4(client: Client):
    """
    Process Annexure-4A (categorized blocks) and 4B (quality blocks).
    Links named blocks to their parent districts.
    """
    log.info("\n[4] Processing Annexure-4 (At-Risk Block Names)...")
    files = sorted(glob.glob(str(DATASETS_DIR / "Annexure-4" / "*.xlsx")))
    YEAR_SEQ = [2017, 2020, 2022, 2023, 2024]

    all_rows = []

    for idx, fpath in enumerate(files):
        year = YEAR_SEQ[idx] if idx < len(YEAR_SEQ) else 2024
        report.files_processed += 1
        log.info(f"  → {Path(fpath).name} (year={year})")

        try:
            xl = pd.ExcelFile(fpath)
        except Exception as e:
            log.error(f"    Cannot open: {e}")
            continue

        # Process Annexure 4A — categorized blocks
        if "Annexure 4A" in xl.sheet_names:
            try:
                df4a = pd.read_excel(fpath, sheet_name="Annexure 4A", header=None, dtype=str)
                rows = _parse_annexure4a(df4a, year, "Annexure4A")
                all_rows.extend(rows)
                log.info(f"    4A: {len(rows)} blocks found")
            except Exception as e:
                log.error(f"    4A parse error: {e}")
                report.errors.append(f"Ann4A {Path(fpath).name}: {str(e)[:80]}")

        # Process Annexure 4B — quality blocks
        if "Annexure 4B" in xl.sheet_names:
            try:
                df4b = pd.read_excel(fpath, sheet_name="Annexure 4B", header=None, dtype=str)
                rows = _parse_annexure4b(df4b, year, "Annexure4B")
                all_rows.extend(rows)
                log.info(f"    4B: {len(rows)} blocks found")
            except Exception as e:
                log.error(f"    4B parse error: {e}")
                report.errors.append(f"Ann4B {Path(fpath).name}: {str(e)[:80]}")

    # Embed narratives
    if all_rows:
        log.info(f"  Building narratives and embeddings for {len(all_rows)} blocks...")
        narratives = [build_block_risk_narrative(r) for r in all_rows]
        try:
            embeddings = embed_passages(narratives, batch_size=EMBED_BATCH)
            for row, emb in zip(all_rows, embeddings):
                row["embedding"] = emb.tolist()
        except Exception as e:
            log.error(f"  Embedding error: {e}")

        log.info(f"  Upserting {len(all_rows)} block-risk rows...")
        for i in range(0, len(all_rows), UPSERT_BATCH):
            batch = all_rows[i:i + UPSERT_BATCH]
            n = upsert_batch(client, "annexure_block_risk", batch)
            report.rows_inserted += n

    report.rows_total += len(all_rows)


def _find_data_start(df: pd.DataFrame) -> int:
    """Scan rows to find where actual data begins (skip merged headers)."""
    for i in range(min(10, len(df))):
        row = df.iloc[i].dropna()
        # Data rows have many non-null values with state/district text
        if len(row) >= 3:
            vals = [str(v).strip().lower() for v in row.values[:4]]
            if any(v not in ("nan", "", "s.no", "sl.no", "state", "district")
                   for v in vals):
                return i
    return 3


def _parse_annexure4a(df: pd.DataFrame, year: int, source: str) -> List[Dict]:
    """
    Parse Annexure 4A: State | District | Semi-Critical Blocks | Critical Blocks | OE Blocks
    Structure varies by year — use positional scanning.
    """
    rows = []
    state, district = "", ""

    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values]
        non_null = [v for v in vals if v.lower() not in ("nan", "none", "")]

        if not non_null:
            continue

        # Detect state/district header rows vs data rows
        # Heuristic: if first value is a known state name pattern
        first = non_null[0] if non_null else ""

        # State row: single prominent non-null value
        if len(non_null) == 1 and len(first) > 3 and first.upper() == first:
            state = first.title()
            continue

        # District + block row: at least 2 values, first is district
        if len(non_null) >= 2:
            potential_district = non_null[0]
            # If looks like a district (not a block name)
            if len(potential_district) > 2 and not re.match(r'^\d+', potential_district):
                district = potential_district
                block_vals = non_null[1:]
            else:
                block_vals = non_null

            # Categories: Semi-Critical, Critical, Over-Exploited
            for cat_idx, cat in enumerate(["Semi-Critical", "Critical", "Over-Exploited"]):
                if cat_idx < len(block_vals):
                    # Block names may be comma-separated or in separate cells
                    block_names = [b.strip() for b in block_vals[cat_idx].split(",")
                                   if b.strip() and b.strip().lower() not in ("nil", "none", "nan", "-")]
                    for block in block_names:
                        if block and state and district:
                            rows.append({
                                "state":           state,
                                "district":        district,
                                "block_name":      block,
                                "categorization":  cat,
                                "quality_tag":     None,
                                "annexure_source": source,
                                "assessment_year": year,
                                "metadata":        {"year": year},
                            })

    return rows


def _parse_annexure4b(df: pd.DataFrame, year: int, source: str) -> List[Dict]:
    """
    Parse Annexure 4B: State | District | Fluoride Blocks | Arsenic Blocks | Saline Blocks
    """
    rows = []
    state, district = "", ""

    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values]
        non_null = [v for v in vals if v.lower() not in ("nan", "none", "")]

        if not non_null:
            continue

        first = non_null[0] if non_null else ""

        if len(non_null) == 1 and len(first) > 3:
            state = first.title()
            continue

        if len(non_null) >= 2:
            potential_district = non_null[0]
            if len(potential_district) > 2 and not re.match(r'^\d+', potential_district):
                district = potential_district
                block_vals = non_null[1:]
            else:
                block_vals = non_null

            for qual_idx, quality in enumerate(["Fluoride", "Arsenic", "Saline"]):
                if qual_idx < len(block_vals):
                    block_names = [b.strip() for b in block_vals[qual_idx].split(",")
                                   if b.strip() and b.strip().lower() not in ("nil", "none", "nan", "-")]
                    for block in block_names:
                        if block and state and district:
                            rows.append({
                                "state":           state,
                                "district":        district,
                                "block_name":      block,
                                "categorization":  "Saline",
                                "quality_tag":     quality,
                                "annexure_source": source,
                                "assessment_year": year,
                                "metadata":        {"year": year, "quality": quality},
                            })

    return rows


# =============================================================================
# GEC MANUAL INGESTION
# =============================================================================

def ingest_gec_manual(client: Client):
    """
    Chunk and embed the GEC User Manual text for semantic search.
    Source: gec_extracted.txt (pre-extracted from GEC User_manual.pdf)
    """
    log.info("\n[5] Processing GEC Manual...")

    txt_path = DATASETS_DIR.parent / "gec_extracted.txt"
    if not txt_path.exists():
        log.warning("  gec_extracted.txt not found. Run extraction first.")
        return

    with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
        full_text = f.read()

    # Split by page markers
    pages = re.split(r'--- PAGE (\d+) ---', full_text)

    chunks = []
    CHUNK_SIZE = 800     # characters per chunk
    CHUNK_OVERLAP = 100

    current_page = 0
    for i in range(1, len(pages), 2):
        try:
            page_num = int(pages[i])
            page_text = pages[i + 1].strip() if i + 1 < len(pages) else ""
        except (ValueError, IndexError):
            continue

        current_page = page_num

        # Detect section header
        section_match = re.search(r'(\d+\.\d*)\s+([A-Z][^\n]{5,60})', page_text)
        section_title = section_match.group(2).strip() if section_match else ""
        section_number = section_match.group(1) if section_match else ""

        # Chunk the page text
        text = re.sub(r'\s+', ' ', page_text).strip()
        if len(text) < 50:
            continue

        start = 0
        chunk_idx = 0
        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))
            # Try to break at sentence boundary
            if end < len(text):
                last_period = text.rfind('.', start, end)
                if last_period > start + CHUNK_SIZE // 2:
                    end = last_period + 1

            chunk_text = text[start:end].strip()
            if len(chunk_text) > 50:
                chunks.append({
                    "source_file":    "GEC_UserManual.pdf",
                    "source_type":    "manual",
                    "section_title":  section_title,
                    "section_number": section_number,
                    "page_number":    page_num,
                    "chunk_index":    chunk_idx,
                    "content":        chunk_text,
                    "language":       "en",
                    "metadata": {
                        "keywords": _extract_keywords(chunk_text),
                        "formula_present": bool(re.search(r'[A-Z_]+\s*=\s*[\w\s\+\-\*\/\(\)]+', chunk_text)),
                    }
                })
                chunk_idx += 1

            start = end - CHUNK_OVERLAP if end < len(text) else len(text)

    log.info(f"  Created {len(chunks)} chunks from manual")
    report.rows_total += len(chunks)

    # Embed
    texts = [c["content"] for c in chunks]
    log.info(f"  Embedding {len(texts)} chunks...")
    try:
        embeddings = embed_passages(texts, batch_size=EMBED_BATCH)
        for chunk, emb in zip(chunks, embeddings):
            chunk["embedding"] = emb.tolist()
    except Exception as e:
        log.error(f"  Manual embedding error: {e}")

    # Insert (gec_manual_index has auto-UUID, no manual id)
    # First clear existing manual entries to allow re-run
    try:
        client.table("gec_manual_index").delete().eq("source_file", "GEC_UserManual.pdf").execute()
        log.info("  Cleared existing GEC manual entries for clean re-insert")
    except Exception:
        pass

    for i in range(0, len(chunks), UPSERT_BATCH):
        batch = chunks[i:i + UPSERT_BATCH]
        n = insert_batch(client, "gec_manual_index", batch)
        report.rows_inserted += n

    log.info(f"  ✅ GEC Manual ingested: {len(chunks)} chunks")


def _extract_keywords(text: str) -> List[str]:
    """Extract domain-specific keywords from a text chunk."""
    keywords = []
    DOMAIN_TERMS = [
        "AEGR", "Stage of Extraction", "Over-Exploited", "Semi-Critical",
        "Critical", "Safe", "recharge", "extraction", "aquifer", "baseflow",
        "RFIF", "WTFM", "transpiration", "evaporation", "canal", "monsoon",
        "Ham", "BCM", "GEC", "CGWB", "groundwater", "GW level", "Saline",
        "Fluoride", "Arsenic", "piezometric", "confined", "unconfined"
    ]
    for term in DOMAIN_TERMS:
        if term.lower() in text.lower():
            keywords.append(term)
    return keywords[:10]


# =============================================================================
# JEPA VECTOR BUILD (POST-INGESTION)
# =============================================================================

def build_jepa_vectors(client: Client, state_filter: Optional[str] = None):
    """
    After all data is ingested, iterate through every unique district/unit and
    compute the JEPA temporal trajectory vector from multi-year data.

    This is run AFTER all semantic data is loaded.
    """
    log.info("\n[6] Building JEPA Temporal Vectors...")

    # Paginated fetch — Supabase defaults to max 1000 rows per call
    PAGE_SIZE = 1000
    all_records = []
    page = 0

    log.info("  Fetching all records with pagination...")
    while True:
        q = client.table("groundwater_time_series").select(
            "id, state, district, assessment_unit, assessment_year, "
            "stage_of_extraction_pct, aegr, total_extraction, "
            "recharge_rainfall_monsoon, net_gw_availability, "
            "total_extraction_irrigation, total_extraction_domestic, "
            "total_extraction_industrial, categorization"
        ).range(page * PAGE_SIZE, (page + 1) * PAGE_SIZE - 1)

        if state_filter:
            q = q.ilike("state", f"%{state_filter}%")

        batch_result = q.execute()
        if not batch_result.data:
            break

        all_records.extend(batch_result.data)
        log.info(f"  ... fetched {len(all_records)} records so far")

        if len(batch_result.data) < PAGE_SIZE:
            break  # Last page
        page += 1

    if not all_records:
        log.warning("  No data found for JEPA building.")
        return

    log.info(f"  Loaded {len(all_records)} records for JEPA computation")

    # Group by (state, district, assessment_unit)
    groups: Dict[str, List[Dict]] = {}
    for row in all_records:
        key = f"{row['state']}|{row['district']}|{row.get('assessment_unit', '')}"
        if key not in groups:
            groups[key] = []
        groups[key].append(row)

    log.info(f"  Found {len(groups)} unique assessment units")

    updated = 0
    skipped_insufficient = 0
    pending_jepa_updates: List[Dict] = []
    JEPA_BATCH = 50  # rows per upsert call

    for key, records in groups.items():
        if len(records) < JEPA_MIN_YEARS:
            skipped_insufficient += 1
            continue

        # Sort by year
        records.sort(key=lambda r: r["assessment_year"])

        yearly_metrics = []
        categorizations = []

        for r in records:
            def sf(field: str) -> float:
                v = r.get(field)
                try:
                    return float(v or 0)
                except (TypeError, ValueError):
                    return 0.0

            yearly_metrics.append({
                "stage_pct":              sf("stage_of_extraction_pct"),
                "aegr":                   sf("aegr"),
                "total_extraction":       sf("total_extraction"),
                "recharge_rainfall":      sf("recharge_rainfall_monsoon"),
                "net_availability":       sf("net_gw_availability"),
                "extraction_irrigation":  sf("total_extraction_irrigation"),
                "extraction_domestic":    sf("total_extraction_domestic"),
                "extraction_industrial":  sf("total_extraction_industrial"),
            })
            categorizations.append(r.get("categorization", "Unknown"))

        # Compute JEPA vector
        jepa_vec, meta = encode_sequence(yearly_metrics, categorizations)
        years_used = [r["assessment_year"] for r in records]

        for r in records:
            pending_jepa_updates.append({
                "id":                     r["id"],
                "jepa_vector":            jepa_vec.tolist(),
                "jepa_trend_direction":   meta["jepa_trend_direction"],
                "jepa_stage_velocity":    meta["jepa_stage_velocity"],
                "jepa_years_in_sequence": meta["jepa_years_in_sequence"],
                "jepa_sequence_years":    years_used,
                "jepa_computed_at":       datetime.utcnow().isoformat(),
            })
            updated += 1

        # Flush batch every JEPA_BATCH rows
        if len(pending_jepa_updates) >= JEPA_BATCH:
            _flush_jepa_updates(client, pending_jepa_updates)
            pending_jepa_updates.clear()

    # Final flush for remaining rows
    if pending_jepa_updates:
        _flush_jepa_updates(client, pending_jepa_updates)

    log.info(f"  ✅ JEPA vectors staged: {updated} records")
    log.info(f"     Skipped (insufficient years): {skipped_insufficient}")



# =============================================================================
# JEPA BATCH FLUSH HELPER
# =============================================================================

def _flush_jepa_updates(client: Client, updates: List[Dict]):
    """Batch-upsert JEPA vectors for a list of rows by UUID id."""
    try:
        client.table("groundwater_time_series").upsert(
            updates, on_conflict="id"
        ).execute()
        log.info(f"  JEPA flush: {len(updates)} rows updated")
    except Exception as e:
        log.error(f"  JEPA flush failed: {str(e)[:120]}")
        for upd in updates:
            try:
                upd_data = {k: v for k, v in upd.items() if k != "id"}
                client.table("groundwater_time_series").update(upd_data).eq("id", upd["id"]).execute()
            except Exception:
                report.errors.append(f"JEPA single fail: {upd.get('id','?')[:20]}")


# =============================================================================
# UPSERT HELPER FOR GTS TABLE
# =============================================================================

def _upsert_gts_rows(client: Client, rows: List[Dict]):
    """Insert groundwater_time_series rows (ignoring duplicates for idempotency)."""
    # Remove manually set IDs — let Supabase generate UUIDs
    for row in rows:
        row.pop("id", None)

    for i in range(0, len(rows), UPSERT_BATCH):
        batch = rows[i:i + UPSERT_BATCH]
        if not batch:
            continue
        try:
            # ignore_duplicates=True skips rows that violate the unique constraint
            # This makes the ingestion idempotent (safe to re-run)
            client.table("groundwater_time_series").insert(
                batch, returning="minimal"
            ).execute()
            report.rows_inserted += len(batch)
        except Exception as e:
            err_str = str(e)
            # If it's a duplicate key violation, try row-by-row
            if "duplicate" in err_str.lower() or "unique" in err_str.lower() or "23505" in err_str:
                inserted_this_batch = 0
                for row in batch:
                    try:
                        client.table("groundwater_time_series").insert(
                            row, returning="minimal"
                        ).execute()
                        inserted_this_batch += 1
                    except Exception:
                        pass  # Skip duplicates silently
                report.rows_inserted += inserted_this_batch
            else:
                log.error(f"  GTS insert batch failed: {err_str[:120]}")
                report.errors.append(f"GTS insert: {err_str[:100]}")
                report.rows_errored += len(batch)

    report.rows_total += len(rows)


# =============================================================================
# MAIN ENTRYPOINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="INGRES Deep Ingestion Engine")
    parser.add_argument(
        "--source", default="all",
        choices=["attribute_table", "central", "state", "annexure4",
                 "gec_manual", "jepa_build", "all"],
        help="Which dataset to ingest"
    )
    parser.add_argument("--state", default=None, help="Filter to specific state (e.g. TELANGANA)")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("  INGRES Deep Ingestion Engine — Phase 2")
    log.info(f"  Source: {args.source} | State filter: {args.state or 'All'}")
    log.info("=" * 60)

    client = get_client()

    src = args.source

    if src in ("attribute_table", "all"):
        ingest_attribute_tables(client)

    if src in ("central", "all"):
        ingest_central_reports(client)

    if src in ("state", "all"):
        ingest_state_reports(client, state_filter=args.state)

    if src in ("annexure4", "all"):
        ingest_annexure4(client)

    if src in ("gec_manual", "all"):
        ingest_gec_manual(client)

    if src in ("jepa_build", "all"):
        build_jepa_vectors(client, state_filter=args.state)

    # Print integrity report
    print(report.summary())

    # Save report to file
    report_path = Path(__file__).parent / "ingestion_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "files_processed": report.files_processed,
            "rows_total": report.rows_total,
            "rows_inserted": report.rows_inserted,
            "rows_skipped": report.rows_skipped,
            "rows_errored": report.rows_errored,
            "top_missing": [
                {"field": k, "count": v}
                for k, v in sorted(
                    report.missing_value_counts.items(), key=lambda x: -x[1]
                )[:20]
            ],
            "column_drift_count": len(report.column_drift_log),
            "states_covered": list(report.year_coverage.keys()),
            "errors_sample": report.errors[:10],
        }, f, indent=2)

    log.info(f"\n  Report saved to {report_path}")


if __name__ == "__main__":
    main()
