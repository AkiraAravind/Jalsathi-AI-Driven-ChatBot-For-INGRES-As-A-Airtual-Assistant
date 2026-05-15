-- =============================================================================
-- CLEANUP: Drop old tables that are no longer needed
-- Run this in Supabase SQL Editor AFTER confirming the new schema.sql
-- is fully applied and test_phase1.py passes.
--
-- Project: sypreblpupxxztkophmo (Root .env Supabase)
-- =============================================================================

-- ── Step 1: Drop old RPC function (used old 384-dim vector signature) ─────────
drop function if exists match_district_embeddings(vector(384), float, int);

-- ── Step 2: Drop old vector table (384-dim, replaced by groundwater_time_series) ─
drop table if exists district_embeddings cascade;

-- ── Step 3: Drop old structured data table (replaced by groundwater_time_series) ─
drop table if exists district_data cascade;

-- ── Verification: Confirm old tables are gone ─────────────────────────────────
-- Run this SELECT to confirm — it should return 0 rows for the old tables.
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('district_embeddings', 'district_data')
order by table_name;

-- Expected output: (0 rows)

-- ── Confirm new tables are present ────────────────────────────────────────────
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'gec_manual_index',
    'groundwater_time_series',
    'annexure_block_risk',
    'users',
    'chat_sessions'
  )
order by table_name;

-- Expected output: (5 rows — all 5 new tables)
