-- ============================================================
-- Phase 3 Supabase RPC Functions  
-- INGRES ChatBOT | RAG Search Functions
-- Run these in Supabase SQL Editor (Settings > SQL Editor)
-- ============================================================

-- 1. Search GEC Manual Index (semantic similarity search)
--    Used by: RAG Path 1 — methodology/formula questions
CREATE OR REPLACE FUNCTION search_gec_manual(
    query_embedding vector(1024),
    match_threshold float,
    match_count     int
)
RETURNS TABLE (
    id              uuid,
    chunk_index     int,
    section_number  text,
    section_title   text,
    page_number     int,
    content         text,
    language        text,
    metadata        jsonb,
    similarity      float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        g.id,
        g.chunk_index,
        g.section_number,
        g.section_title,
        g.page_number,
        g.content,
        g.language,
        g.metadata,
        1 - (g.semantic_vector <=> query_embedding) AS similarity
    FROM gec_manual_index g
    WHERE g.semantic_vector IS NOT NULL
      AND 1 - (g.semantic_vector <=> query_embedding) > match_threshold
    ORDER BY g.semantic_vector <=> query_embedding
    LIMIT match_count;
$$;

GRANT EXECUTE ON FUNCTION search_gec_manual(vector, float, int) TO anon, authenticated, service_role;

-- ============================================================
-- 2. Search Groundwater Time Series (semantic similarity)
--    Used by: RAG Path 2 — district/year data lookups
--    Supports optional SQL filters for state/district/year/category
CREATE OR REPLACE FUNCTION search_groundwater_semantic(
    query_embedding  vector(1024),
    match_threshold  float,
    match_count      int,
    filter_state     text    DEFAULT NULL,
    filter_district  text    DEFAULT NULL,
    filter_year      int     DEFAULT NULL,
    filter_category  text    DEFAULT NULL
)
RETURNS TABLE (
    id                      uuid,
    state                   text,
    district                text,
    assessment_unit         text,
    assessment_unit_type    text,
    assessment_year         int,
    stage_of_extraction_pct float,
    categorization          text,
    aegr                    float,
    total_extraction        float,
    net_gw_availability     float,
    jepa_trend_direction    text,
    jepa_stage_velocity     float,
    similarity              float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        g.id,
        g.state,
        g.district,
        g.assessment_unit,
        g.assessment_unit_type,
        g.assessment_year,
        g.stage_of_extraction_pct,
        g.categorization,
        g.aegr,
        g.total_extraction,
        g.net_gw_availability,
        g.jepa_trend_direction,
        g.jepa_stage_velocity,
        1 - (g.semantic_vector <=> query_embedding) AS similarity
    FROM groundwater_time_series g
    WHERE g.semantic_vector IS NOT NULL
      AND 1 - (g.semantic_vector <=> query_embedding) > match_threshold
      AND (filter_state    IS NULL OR g.state         ILIKE '%' || filter_state    || '%')
      AND (filter_district IS NULL OR g.district      ILIKE '%' || filter_district || '%')
      AND (filter_year     IS NULL OR g.assessment_year = filter_year)
      AND (filter_category IS NULL OR g.categorization  ILIKE '%' || filter_category || '%')
    ORDER BY g.semantic_vector <=> query_embedding
    LIMIT match_count;
$$;

GRANT EXECUTE ON FUNCTION search_groundwater_semantic(vector, float, int, text, text, int, text) TO anon, authenticated, service_role;

-- ============================================================
-- 3. Search Groundwater JEPA Trajectories
--    Used by: RAG Path 3 — trend/prediction queries
CREATE OR REPLACE FUNCTION search_groundwater_jepa(
    query_jepa_vector  vector(1024),
    match_threshold    float,
    match_count        int,
    filter_state       text    DEFAULT NULL,
    min_velocity       float   DEFAULT 0.0,
    filter_trend       text    DEFAULT NULL
)
RETURNS TABLE (
    id                      uuid,
    state                   text,
    district                text,
    assessment_unit         text,
    assessment_year         int,
    stage_of_extraction_pct float,
    categorization          text,
    jepa_trend_direction    text,
    jepa_stage_velocity     float,
    jepa_sequence_years     jsonb,
    trajectory_similarity   float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        g.id,
        g.state,
        g.district,
        g.assessment_unit,
        g.assessment_year,
        g.stage_of_extraction_pct,
        g.categorization,
        g.jepa_trend_direction,
        g.jepa_stage_velocity,
        g.jepa_sequence_years,
        1 - (g.jepa_vector <=> query_jepa_vector) AS trajectory_similarity
    FROM groundwater_time_series g
    WHERE g.jepa_vector IS NOT NULL
      AND 1 - (g.jepa_vector <=> query_jepa_vector) > match_threshold
      AND (filter_state IS NULL OR g.state ILIKE '%' || filter_state || '%')
      AND (filter_trend  IS NULL OR g.jepa_trend_direction = filter_trend)
      AND (g.jepa_stage_velocity IS NULL OR ABS(g.jepa_stage_velocity) >= min_velocity)
    ORDER BY g.jepa_vector <=> query_jepa_vector
    LIMIT match_count;
$$;

GRANT EXECUTE ON FUNCTION search_groundwater_jepa(vector, float, int, text, float, text) TO anon, authenticated, service_role;

-- ============================================================
-- 4. Search At-Risk Blocks (Annexure 4 — block-level query)
--    Used by: RAG Path 4 — OE/Critical block identification
CREATE OR REPLACE FUNCTION search_at_risk_blocks(
    query_embedding  vector(1024),
    match_threshold  float,
    match_count      int,
    filter_state     text    DEFAULT NULL,
    filter_district  text    DEFAULT NULL,
    filter_category  text    DEFAULT NULL,
    filter_year      int     DEFAULT NULL
)
RETURNS TABLE (
    id               uuid,
    state            text,
    district         text,
    block_name       text,
    categorization   text,
    quality_tag      text,
    annexure_source  text,
    assessment_year  int,
    similarity       float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        a.id,
        a.state,
        a.district,
        a.block_name,
        a.categorization,
        a.quality_tag,
        a.annexure_source,
        a.assessment_year,
        1 - (a.semantic_vector <=> query_embedding) AS similarity
    FROM annexure_block_risk a
    WHERE a.semantic_vector IS NOT NULL
      AND 1 - (a.semantic_vector <=> query_embedding) > match_threshold
      AND (filter_state    IS NULL OR a.state           ILIKE '%' || filter_state    || '%')
      AND (filter_district IS NULL OR a.district        ILIKE '%' || filter_district || '%')
      AND (filter_category IS NULL OR a.categorization  ILIKE '%' || filter_category || '%')
      AND (filter_year     IS NULL OR a.assessment_year = filter_year)
    ORDER BY a.semantic_vector <=> query_embedding
    LIMIT match_count;
$$;

GRANT EXECUTE ON FUNCTION search_at_risk_blocks(vector, float, int, text, text, text, int) TO anon, authenticated, service_role;

-- ============================================================
-- VERIFY: Check all 4 functions were created successfully
SELECT routine_name, routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
    'search_gec_manual',
    'search_groundwater_semantic',
    'search_groundwater_jepa',
    'search_at_risk_blocks',
    'bulk_update_jepa'
  )
ORDER BY routine_name;
