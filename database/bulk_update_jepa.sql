-- ============================================================
-- JEPA Batch Update RPC Function
-- INGRES ChatBOT | Phase 2 Optimization
-- Run this in Supabase SQL Editor to enable bulk JEPA updates
-- ============================================================

-- Function: bulk_update_jepa
-- Updates multiple rows' JEPA vectors in one SQL call
-- Args: updates JSONB array of {id, jepa_vector, jepa_trend_direction, jepa_stage_velocity, jepa_years_in_sequence, jepa_sequence_years}

CREATE OR REPLACE FUNCTION bulk_update_jepa(updates JSONB)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  upd JSONB;
  updated_count INTEGER := 0;
BEGIN
  FOR upd IN SELECT jsonb_array_elements(updates)
  LOOP
    UPDATE groundwater_time_series
    SET
      jepa_vector           = (upd->>'jepa_vector')::vector,
      jepa_trend_direction  = upd->>'jepa_trend_direction',
      jepa_stage_velocity   = (upd->>'jepa_stage_velocity')::float,
      jepa_years_in_sequence = (upd->>'jepa_years_in_sequence')::int,
      jepa_sequence_years   = (upd->'jepa_sequence_years')::jsonb,
      jepa_computed_at      = NOW(),
      updated_at            = NOW()
    WHERE id = (upd->>'id')::uuid;

    updated_count := updated_count + 1;
  END LOOP;

  RETURN updated_count;
END;
$$;

-- Grant execute to service role
GRANT EXECUTE ON FUNCTION bulk_update_jepa(JSONB) TO service_role;

-- Comments
COMMENT ON FUNCTION bulk_update_jepa(JSONB) IS
'Bulk updates JEPA temporal trajectory vectors for groundwater_time_series rows.
Used by ingestor.py Phase 2 to avoid N+1 PATCH requests.
Input: JSONB array of update objects with id and JEPA fields.';
