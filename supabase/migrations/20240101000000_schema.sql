-- =============================================================================
-- INGRES AI ChatBOT — Production Database Schema
-- SIH 2025 | Problem Statement SIH25066
-- Architecture: V-JEPA Temporal Encoding + High-Fidelity RAG
-- Embedding Dimension: 1024 (intfloat/multilingual-e5-large)
-- Supabase/PostgreSQL 15 + pgvector
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- EXTENSIONS
-- ─────────────────────────────────────────────────────────────────────────────

create extension if not exists vector;     -- pgvector: vector similarity search
create extension if not exists "uuid-ossp"; -- UUID generation
create extension if not exists pg_trgm;    -- Trigram index for fuzzy text search


-- =============================================================================
-- TABLE 1: gec_manual_index
-- Purpose: Semantic search over the GEC User Manual and GEC-2015 methodology.
-- Use case: Answering "What is AEGR?", "How is Stage of Extraction calculated?"
-- Embedding: 1024-dim semantic vector from multilingual-e5-large
--            Supports English, Hindi, Telugu queries out-of-the-box.
-- =============================================================================

create table if not exists gec_manual_index (
  id              uuid          primary key default gen_random_uuid(),

  -- Source identification
  source_file     text          not null,  -- e.g. 'GEC_UserManual.pdf'
  source_type     text          not null,  -- 'manual' | 'methodology' | 'annexure_definition'
  section_title   text,                   -- e.g. 'Stage of Ground Water Extraction'
  section_number  text,                   -- e.g. '2.5'
  page_number     int,                    -- Original PDF page

  -- Content
  chunk_index     int           not null default 0,   -- Chunk position within section
  content         text          not null,              -- Raw text chunk (≤512 tokens)
  content_hindi   text,                               -- Optional: translated Hindi content
  content_telugu  text,                               -- Optional: translated Telugu content

  -- Semantic embedding (1024-dim)
  -- Model: intfloat/multilingual-e5-large
  -- This is a STATIC embedding: it represents the meaning of the text chunk.
  -- Used for: "What is the formula for AEGR?" → cosine similarity retrieval
  embedding       vector(1024),

  -- Metadata for filtering before vector search (reduces search space)
  metadata        jsonb         not null default '{}'::jsonb,
  -- Expected metadata keys:
  -- { "keywords": ["AEGR", "recharge", "extraction"],
  --   "formula_present": true,
  --   "category": "methodology" | "glossary" | "formula" | "workflow" }

  language        text          not null default 'en',
  created_at      timestamptz   not null default now()
);

-- Index: Approximate Nearest Neighbor for 1024-dim semantic search
-- IVFFlat: Good for up to ~100K chunks. Use HNSW for millions.
create index if not exists idx_gec_manual_embedding
  on gec_manual_index
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 50);

-- Index: Fast metadata filtering before vector search
create index if not exists idx_gec_manual_metadata
  on gec_manual_index using gin (metadata);

-- Index: Full-text fuzzy search (backup for keyword queries)
create index if not exists idx_gec_manual_content_trgm
  on gec_manual_index using gin (content gin_trgm_ops);


-- =============================================================================
-- TABLE 2: groundwater_time_series
-- Purpose: Stores ALL 153-column GEC assessment data for every assessment unit
--          (Block/Mandal/Taluka) across all years.
--
-- The KEY innovation here is the DUAL VECTOR architecture:
--
--   semantic_vector (1024-dim):
--     → Encodes the TEXT description of a single year's snapshot.
--     → Example: "In 2022, Nalgonda district had Stage of Extraction = 87.3%..."
--     → Used for: "Tell me about Nalgonda's 2022 groundwater status."
--
--   jepa_vector (1024-dim):  ← THE V-JEPA INNOVATION
--     → Does NOT embed text. Encodes the TEMPORAL TRAJECTORY of a unit.
--     → Built by concatenating normalized metric vectors across 5 years
--       and then projecting through a learned linear layer to 1024-dim.
--     → Captures: direction of change, velocity, acceleration, current state.
--     → Example: A district going [45%→58%→72%→88%→101%] has a jepa_vector
--       pointing in the "worsening" direction of the embedding space.
--     → Used for: "Which districts are TRENDING toward Over-Exploited?"
--       → ANN search finds units whose jepa_vectors cluster with known OE units.
-- =============================================================================

create table if not exists groundwater_time_series (
  id                      uuid    primary key default gen_random_uuid(),

  -- ── Spatial Hierarchy ──────────────────────────────────────────────────────
  country                 text    not null default 'India',
  state                   text    not null,
  state_code              text,             -- e.g. 'TS', 'KA', 'RJ'
  district                text    not null,
  district_code           text,             -- e.g. 'TS06'
  assessment_unit         text,             -- Block / Mandal / Taluka name
  assessment_unit_code    text,             -- e.g. 'TS0610'
  assessment_unit_type    text,             -- 'BLOCK' | 'MANDAL' | 'TALUKA' | 'DISTRICT'

  -- ── Temporal ───────────────────────────────────────────────────────────────
  assessment_year         int     not null, -- Canonical year: 2017, 2020, 2022, 2023, 2024
  assessment_year_label   text,             -- Display label: '2022-23'
  data_source             text,             -- 'Central/district' | 'state/TELANGANA' | 'Attribute_Table'

  -- ── Area Metrics (Ha) ──────────────────────────────────────────────────────
  geographical_area_ha        float,        -- Total geographical area
  recharge_worthy_area_ha     float,        -- Area suitable for recharge

  -- ── Recharge Components (Ham) — GEC-2015 Water Balance: ΔS = R - GE - T - E - B
  -- Monsoon Season
  recharge_rainfall_monsoon       float,    -- R_RF (monsoon) from GW level fluctuation
  recharge_other_mon_gwirr        float,    -- R_GWI: Groundwater irrigation return flow
  recharge_other_mon_swirr        float,    -- R_SWI: Surface water irrigation return flow
  recharge_other_mon_canal        float,    -- R_C: Canal seepage
  recharge_other_mon_tanks        float,    -- R_TP: Tanks & ponds
  recharge_other_mon_wcs          float,    -- R_WCS: Water conservation structures
  recharge_other_mon_streams      float,    -- R_STR: Stream channels
  recharge_other_mon_pipelines    float,    -- Pipelines (urban)
  recharge_other_mon_sewage       float,    -- Sewage/flash floods
  recharge_other_monsoon_total    float,    -- Sum of all non-rainfall monsoon recharge

  -- Non-Monsoon Season
  recharge_rainfall_nonmonsoon    float,    -- R_RF (non-monsoon) from RFIF method
  recharge_other_nonmonsoon       float,    -- Total non-monsoon other-source recharge

  -- Annual Summary
  total_annual_gw_recharge        float,    -- TGWR = Monsoon + Non-Monsoon total
  natural_discharges              float,    -- ND = Environmental flows (5% or 10% of TGWR)

  -- THE KEY DENOMINATOR
  aegr                            float,    -- AEGR = TGWR - ND (Annual Extractable GW Resource)

  -- ── Extraction / Draft (Ham) — GEC 2015 Sec 2.4 ──────────────────────────
  -- Current Season (C)
  extraction_irrigation_c         float,    -- GE_IRR: Irrigation extraction current season
  extraction_domestic_c           float,    -- GE_DOM: Domestic extraction current
  extraction_industrial_c         float,    -- GE_IND: Industrial extraction current

  -- Non-Current Season (NC)
  extraction_irrigation_nc        float,
  extraction_domestic_nc          float,
  extraction_industrial_nc        float,

  -- Poor Quality Zone (PQ)
  extraction_irrigation_pq        float,
  extraction_domestic_pq          float,
  extraction_industrial_pq        float,

  -- Annual Totals
  total_extraction_irrigation     float,    -- Total GE_IRR
  total_extraction_domestic       float,    -- Total GE_DOM
  total_extraction_industrial     float,    -- Total GE_IND
  total_extraction                float,    -- GE_ALL = GE_IRR + GE_DOM + GE_IND

  -- ── Environmental / Other Flows (Ham) ────────────────────────────────────
  baseflow                        float,    -- B: Stream baseflow
  transpiration                   float,    -- T: Groundwater transpiration
  evaporation                     float,    -- E: Groundwater evaporation
  evapotranspiration              float,    -- ET: Combined ET
  vertical_interaquifer_flow      float,    -- VF: Inter-aquifer vertical flow
  lateral_flow                    float,    -- LF: Throughflow

  -- ── Aquifer Storage Resources (Ham) ──────────────────────────────────────
  instorage_unconfined_fresh      float,    -- Static unconfined aquifer resources
  instorage_unconfined_saline     float,
  dynamic_confined_fresh          float,    -- Dynamic confined aquifer resources
  dynamic_confined_saline         float,
  dynamic_semiconfined_fresh      float,
  dynamic_semiconfined_saline     float,

  -- ── Additional Potential Resources (Ham) ─────────────────────────────────
  additional_spring_discharge     float,
  additional_waterlogged          float,    -- Shallow water table zones
  additional_flood_prone          float,
  coastal_area_resources          float,
  water_depletion_zone            float,

  -- ── Allocation & Availability ─────────────────────────────────────────────
  gw_allocation_domestic_2025     float,    -- Allocation = 22 × N × Lg (mm/yr)
  net_gw_availability             float,    -- AEGR - Current Extraction

  -- ── THE PRIMARY OUTPUT FIELDS ─────────────────────────────────────────────
  stage_of_extraction_pct         float     not null, -- (GE_ALL / AEGR) × 100 — THE KEY METRIC
  categorization                  text      not null, -- 'Safe' | 'Semi-Critical' | 'Critical' | 'Over-Exploited' | 'Saline'

  -- ── Quality Tagging (GEC Sec 2.14) ────────────────────────────────────────
  quality_fluoride                boolean   default false,
  quality_arsenic                 boolean   default false,
  quality_saline                  boolean   default false,
  quality_other                   text,     -- Any other quality parameter

  -- ── Aquifer Info ──────────────────────────────────────────────────────────
  aquifer_type                    text,     -- 'Unconfined' | 'Confined' | 'Semi-Confined'
  aquifer_code                    text,

  -- ── Validation (GEC Sec 2.18) ─────────────────────────────────────────────
  gw_trend_validation             text,     -- 'valid' | 'needs_reassessment' | 'unknown'

  -- ── Raw / Overflow ────────────────────────────────────────────────────────
  raw_metrics                     jsonb     default '{}'::jsonb,
  -- Stores ALL remaining 153-column values not mapped above, ensuring zero data loss.

  -- ══ VECTOR COLUMNS — THE INTELLIGENCE LAYER ══════════════════════════════

  -- Vector A: Semantic Text Embedding (1024-dim)
  -- What it encodes: A human-readable narrative of this unit's data for one year.
  -- Example content embedded: "In Nalgonda district of Telangana (2022), the Annual
  -- Extractable GW Resource is 1,234 Ham. Total extraction is 1,076 Ham giving a
  -- Stage of Extraction of 87.2% → Semi-Critical..."
  -- When to use: "What is the groundwater status of Nalgonda in 2022?"
  semantic_vector                 vector(1024),

  -- Vector B: JEPA Temporal Trajectory Vector (1024-dim) ← THE KEY INNOVATION
  -- What it encodes: NOT text. It's a learned projection of the district's
  -- MULTI-YEAR data sequence into a 1024-dim embedding space.
  --
  -- Construction: For each district, we take the 5-year time series of 8 key metrics:
  --   [stage_pct, aegr, total_extraction, rainfall_recharge,
  --    net_availability, extraction_irrigation, extraction_domestic, categorization_code]
  -- This gives a 5×8 = 40-value matrix (after min-max normalization per state).
  -- We then compute:
  --   1. Delta vector (Δ per year): captures velocity of change
  --   2. Acceleration vector (Δ² per year): captures momentum
  --   3. Current state vector: normalized values for the most recent year
  --   4. Mean + Std Dev over all years: captures central tendency + volatility
  -- These are concatenated → projected linearly to 1024-dim using a fixed
  -- project matrix (W ∈ ℝ^{feature_dim × 1024}) and stored as jepa_vector.
  --
  -- When to use: "Which districts are TRENDING toward Over-Exploited?"
  --   → The query itself is projected ("a district going 70%→100% over 5 years")
  --   → ANN cosine search finds districts with similar trajectory vectors
  --   → This is PREDICTIVE: it answers "who is becoming like the OE clusters?"
  jepa_vector                     vector(1024),

  -- Trajectory metadata (derived from jepa encoding, stored for fast SQL filtering)
  jepa_trend_direction            text,
  -- 'worsening_critical': stage increasing + currently Critical/OE
  -- 'worsening_safe': stage increasing but currently Safe
  -- 'improving': stage decreasing
  -- 'stable': <5% change over all years
  -- 'insufficient_data': <2 years available

  jepa_stage_velocity             float,    -- Avg annual change in stage_of_extraction_pct
  -- Positive = worsening (extraction growing faster than recharge)
  -- Negative = improving

  jepa_years_in_sequence          int,      -- How many years contributed to this JEPA vector
  jepa_sequence_years             int[],    -- Exact years used: e.g. {2017, 2020, 2022, 2023}
  jepa_computed_at                timestamptz,

  -- ── Audit ─────────────────────────────────────────────────────────────────
  metadata                        jsonb     default '{}'::jsonb,
  created_at                      timestamptz not null default now(),
  updated_at                      timestamptz not null default now(),

  -- Uniqueness constraint: one row per spatial unit per year
  unique (state, district, assessment_unit, assessment_year)
);

-- Index A: Semantic vector search
create index if not exists idx_gts_semantic_vector
  on groundwater_time_series
  using ivfflat (semantic_vector vector_cosine_ops)
  with (lists = 150);

-- Index B: JEPA temporal trajectory search
create index if not exists idx_gts_jepa_vector
  on groundwater_time_series
  using ivfflat (jepa_vector vector_cosine_ops)
  with (lists = 150);

-- Index C: Fast SQL pre-filters (avoid full scan before vector search)
create index if not exists idx_gts_state_district
  on groundwater_time_series (state, district, assessment_year);

create index if not exists idx_gts_categorization
  on groundwater_time_series (categorization, assessment_year);

create index if not exists idx_gts_stage_pct
  on groundwater_time_series (stage_of_extraction_pct);

create index if not exists idx_gts_trend
  on groundwater_time_series (jepa_trend_direction, jepa_stage_velocity);

create index if not exists idx_gts_metadata
  on groundwater_time_series using gin (metadata);


-- =============================================================================
-- TABLE 3: annexure_block_risk
-- Purpose: Named block-level at-risk lists from Annexure 4A (categorization) and
--          Annexure 4B (quality contamination). Links blocks to parent districts.
--          Answers: "Which specific mandals in Rajasthan are Over-Exploited?"
-- =============================================================================

create table if not exists annexure_block_risk (
  id              uuid      primary key default gen_random_uuid(),

  -- Spatial
  state           text      not null,
  district        text      not null,
  block_name      text      not null,

  -- Risk classification
  categorization  text      not null,  -- 'Semi-Critical' | 'Critical' | 'Over-Exploited'
  quality_tag     text,                -- 'Fluoride' | 'Arsenic' | 'Saline' | null
  annexure_source text      not null,  -- 'Annexure4A' | 'Annexure4B'

  -- Temporal
  assessment_year int       not null,

  -- Embedding: "Nalgonda Mattampalli block is Over-Exploited in 2022 (Annexure 4A)"
  -- Used for: named block queries and source citation
  embedding       vector(1024),

  metadata        jsonb     default '{}'::jsonb,
  created_at      timestamptz not null default now(),

  unique (state, district, block_name, assessment_year, annexure_source)
);

create index if not exists idx_abr_embedding
  on annexure_block_risk
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 50);

create index if not exists idx_abr_state_district
  on annexure_block_risk (state, district, assessment_year);

create index if not exists idx_abr_categorization
  on annexure_block_risk (categorization, quality_tag);


-- =============================================================================
-- TABLE 4: users
-- Purpose: JWT authentication. Roles gate which data layers are accessible.
-- =============================================================================

create table if not exists users (
  id              uuid      primary key default gen_random_uuid(),
  username        text      not null unique,
  email           text      unique,
  password_hash   text      not null,
  role            text      not null default 'public',
  -- Role hierarchy:
  -- 'public'    → can query Safe/Semi-Critical data, all formulas
  -- 'official'  → can query all categories including OE, Quality tags
  -- 'admin'     → full access including ingestion status and user management
  full_name       text,
  language_pref   text      default 'en',  -- 'en' | 'hi' | 'te'
  created_at      timestamptz not null default now(),
  last_login      timestamptz
);


-- =============================================================================
-- TABLE 5: chat_sessions (Audit + Context Memory)
-- Purpose: Stores conversation history for multi-turn context and analytics.
-- =============================================================================

create table if not exists chat_sessions (
  id              uuid      primary key default gen_random_uuid(),
  user_id         uuid      references users(id) on delete set null,
  session_token   text      not null unique,
  language        text      default 'en',

  -- Turn-by-turn history stored as JSONB array
  history         jsonb     not null default '[]'::jsonb,
  -- Format: [{"role": "user", "content": "...", "ts": "..."}, ...]

  -- Source citations used in this session (for analytics)
  citations_used  jsonb     default '[]'::jsonb,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);


-- =============================================================================
-- RPC FUNCTION 1: search_gec_manual
-- Purpose: Semantic similarity search on the GEC Manual / methodology text.
-- Called by: RAG engine when query is about formulas, definitions, GEC process.
-- Example: "What is AEGR?" → returns top-k manual chunks explaining AEGR.
-- =============================================================================

create or replace function search_gec_manual(
  query_embedding   vector(1024),
  match_threshold   float       default 0.4,
  match_count       int         default 6,
  filter_metadata   jsonb       default null
)
returns table (
  id            uuid,
  content       text,
  source_file   text,
  section_title text,
  section_number text,
  page_number   int,
  metadata      jsonb,
  similarity    float
)
language plpgsql
as $$
begin
  return query
  select
    m.id,
    m.content,
    m.source_file,
    m.section_title,
    m.section_number,
    m.page_number,
    m.metadata,
    1 - (m.embedding <=> query_embedding) as similarity
  from gec_manual_index m
  where
    -- Apply metadata pre-filter if provided
    (filter_metadata is null or m.metadata @> filter_metadata)
    and
    -- Similarity threshold gate
    1 - (m.embedding <=> query_embedding) > match_threshold
  order by m.embedding <=> query_embedding
  limit match_count;
end;
$$;


-- =============================================================================
-- RPC FUNCTION 2: search_groundwater_semantic
-- Purpose: Single-year semantic search on groundwater data.
-- Called by: RAG engine for factual data queries about a specific district/year.
-- Example: "What is the situation in Karimnagar for 2022?"
-- =============================================================================

create or replace function search_groundwater_semantic(
  query_embedding   vector(1024),
  match_threshold   float       default 0.35,
  match_count       int         default 8,
  filter_state      text        default null,
  filter_district   text        default null,
  filter_year       int         default null,
  filter_category   text        default null
)
returns table (
  id                      uuid,
  state                   text,
  district                text,
  assessment_unit         text,
  assessment_year         int,
  stage_of_extraction_pct float,
  categorization          text,
  aegr                    float,
  total_extraction        float,
  net_gw_availability     float,
  jepa_trend_direction    text,
  jepa_stage_velocity     float,
  similarity              float,
  raw_metrics             jsonb
)
language plpgsql
as $$
begin
  return query
  select
    g.id,
    g.state,
    g.district,
    g.assessment_unit,
    g.assessment_year,
    g.stage_of_extraction_pct,
    g.categorization,
    g.aegr,
    g.total_extraction,
    g.net_gw_availability,
    g.jepa_trend_direction,
    g.jepa_stage_velocity,
    1 - (g.semantic_vector <=> query_embedding) as similarity,
    g.raw_metrics
  from groundwater_time_series g
  where
    (filter_state    is null or lower(g.state)    = lower(filter_state))
    and (filter_district is null or lower(g.district) = lower(filter_district))
    and (filter_year     is null or g.assessment_year = filter_year)
    and (filter_category is null or lower(g.categorization) = lower(filter_category))
    and 1 - (g.semantic_vector <=> query_embedding) > match_threshold
  order by g.semantic_vector <=> query_embedding
  limit match_count;
end;
$$;


-- =============================================================================
-- RPC FUNCTION 3: search_groundwater_jepa  ← THE PREDICTIVE FUNCTION
-- Purpose: V-JEPA trajectory search. Finds districts with SIMILAR TEMPORAL
--          TRAJECTORIES to a target query pattern.
-- Called by: RAG engine for trend/prediction queries.
-- Example: "Which districts are trending toward Over-Exploited?"
--   → Backend generates a "prototype OE-trajectory vector"
--     (built from districts that went from Safe to OE over 5 years)
--   → This function finds districts whose jepa_vectors are closest to it.
-- =============================================================================

create or replace function search_groundwater_jepa(
  query_jepa_vector  vector(1024),
  match_threshold    float        default 0.30,
  match_count        int          default 10,
  filter_state       text         default null,
  min_velocity       float        default null,   -- e.g. 3.0 = worsening >3%/year
  filter_trend       text         default null    -- e.g. 'worsening_critical'
)
returns table (
  id                      uuid,
  state                   text,
  district                text,
  assessment_unit         text,
  assessment_year         int,
  stage_of_extraction_pct float,
  categorization          text,
  jepa_trend_direction    text,
  jepa_stage_velocity     float,
  jepa_years_in_sequence  int,
  jepa_sequence_years     int[],
  trajectory_similarity   float
)
language plpgsql
as $$
begin
  return query
  select
    g.id,
    g.state,
    g.district,
    g.assessment_unit,
    g.assessment_year,
    g.stage_of_extraction_pct,
    g.categorization,
    g.jepa_trend_direction,
    g.jepa_stage_velocity,
    g.jepa_years_in_sequence,
    g.jepa_sequence_years,
    1 - (g.jepa_vector <=> query_jepa_vector) as trajectory_similarity
  from groundwater_time_series g
  where
    g.jepa_vector is not null
    and (filter_state  is null or lower(g.state) = lower(filter_state))
    and (min_velocity  is null or g.jepa_stage_velocity >= min_velocity)
    and (filter_trend  is null or g.jepa_trend_direction = filter_trend)
    and 1 - (g.jepa_vector <=> query_jepa_vector) > match_threshold
  order by g.jepa_vector <=> query_jepa_vector
  limit match_count;
end;
$$;


-- =============================================================================
-- RPC FUNCTION 4: search_at_risk_blocks
-- Purpose: Named-block risk lookup. Answers "Which blocks in district X are OE?"
--          Powered by Annexure 4A/4B data.
-- =============================================================================

create or replace function search_at_risk_blocks(
  query_embedding   vector(1024),
  match_threshold   float       default 0.35,
  match_count       int         default 10,
  filter_state      text        default null,
  filter_district   text        default null,
  filter_category   text        default null,
  filter_year       int         default null
)
returns table (
  id              uuid,
  state           text,
  district        text,
  block_name      text,
  categorization  text,
  quality_tag     text,
  annexure_source text,
  assessment_year int,
  similarity      float
)
language plpgsql
as $$
begin
  return query
  select
    a.id,
    a.state,
    a.district,
    a.block_name,
    a.categorization,
    a.quality_tag,
    a.annexure_source,
    a.assessment_year,
    1 - (a.embedding <=> query_embedding) as similarity
  from annexure_block_risk a
  where
    (filter_state    is null or lower(a.state)    = lower(filter_state))
    and (filter_district is null or lower(a.district) = lower(filter_district))
    and (filter_category is null or lower(a.categorization) = lower(filter_category))
    and (filter_year     is null or a.assessment_year = filter_year)
    and 1 - (a.embedding <=> query_embedding) > match_threshold
  order by a.embedding <=> query_embedding
  limit match_count;
end;
$$;


-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- Purpose: Ensure public users cannot write, admins can ingest.
-- =============================================================================

alter table gec_manual_index         enable row level security;
alter table groundwater_time_series  enable row level security;
alter table annexure_block_risk      enable row level security;
alter table users                    enable row level security;
alter table chat_sessions            enable row level security;

-- POLICY: Anyone (anon) can READ groundwater and manual data
create policy "Public can read gec manual"
  on gec_manual_index for select
  to anon, authenticated
  using (true);

create policy "Public can read groundwater data"
  on groundwater_time_series for select
  to anon, authenticated
  using (true);

create policy "Public can read block risk data"
  on annexure_block_risk for select
  to anon, authenticated
  using (true);

-- POLICY: Only service_role (backend ingestion) can write
create policy "Service role can insert gec manual"
  on gec_manual_index for insert
  to service_role
  with check (true);

create policy "Service role can insert groundwater"
  on groundwater_time_series for insert
  to service_role
  with check (true);

create policy "Service role can upsert groundwater"
  on groundwater_time_series for update
  to service_role
  using (true);

create policy "Service role can insert block risk"
  on annexure_block_risk for insert
  to service_role
  with check (true);

-- Users can only see their own sessions
create policy "Users see own sessions"
  on chat_sessions for select
  to authenticated
  using (user_id = auth.uid()::uuid);

create policy "Users manage own sessions"
  on chat_sessions for all
  to authenticated
  using (user_id = auth.uid()::uuid);


-- =============================================================================
-- HELPER VIEWS
-- =============================================================================

-- View: Latest assessment year per district (for dashboard "current status")
create or replace view v_district_latest as
select distinct on (state, district)
  state,
  district,
  assessment_year,
  stage_of_extraction_pct,
  categorization,
  aegr,
  total_extraction,
  net_gw_availability,
  jepa_trend_direction,
  jepa_stage_velocity
from groundwater_time_series
where assessment_unit_type in ('DISTRICT', null)
   or assessment_unit is null
order by state, district, assessment_year desc;


-- View: National categorization summary per year (for Annexure-1 style queries)
create or replace view v_national_summary as
select
  assessment_year,
  categorization,
  count(*) as unit_count,
  round(avg(stage_of_extraction_pct)::numeric, 2) as avg_stage_pct,
  round(sum(total_extraction)::numeric, 2) as total_extraction_ham,
  round(sum(aegr)::numeric, 2) as total_aegr_ham
from groundwater_time_series
group by assessment_year, categorization
order by assessment_year, categorization;


-- View: Worsening districts (jepa_velocity > 5% per year) for alert surfacing
create or replace view v_worsening_districts as
select
  state,
  district,
  assessment_year,
  stage_of_extraction_pct,
  categorization,
  jepa_trend_direction,
  jepa_stage_velocity,
  jepa_sequence_years
from groundwater_time_series
where jepa_stage_velocity > 5.0
  and jepa_trend_direction like 'worsening%'
order by jepa_stage_velocity desc;


-- =============================================================================
-- MIGRATION NOTE
-- =============================================================================
-- This schema REPLACES the old schema (district_data + district_embeddings).
-- Old tables can be dropped after data is re-ingested:
--   DROP TABLE IF EXISTS district_embeddings;
--   DROP TABLE IF EXISTS district_data;
-- =============================================================================
