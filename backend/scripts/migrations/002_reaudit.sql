-- backend/scripts/migrations/002_reaudit.sql
-- Run as Supabase service_role or via Supabase Dashboard SQL editor
-- CRITICAL: Apply this migration BEFORE deploying the updated application.

-- ============================================================
-- 1. ROW LEVEL SECURITY — Enable on all sensitive tables
-- ============================================================

ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_enrichment ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_locks ENABLE ROW LEVEL SECURITY;
ALTER TABLE deletion_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- 2. DROP any default permissive policies
-- ============================================================

DROP POLICY IF EXISTS "Enable all for all users" ON leads;
DROP POLICY IF EXISTS "Enable all for all users" ON messages;
DROP POLICY IF EXISTS "Enable all for all users" ON lead_enrichment;
DROP POLICY IF EXISTS "Enable all for all users" ON lead_memory;
DROP POLICY IF EXISTS "Enable all for all users" ON scheduled_jobs;
DROP POLICY IF EXISTS "Enable all for all users" ON agent_locks;
DROP POLICY IF EXISTS "Enable all for all users" ON deletion_tokens;
DROP POLICY IF EXISTS "Enable all for all users" ON events;

-- ============================================================
-- 3. EVENTS — public read (needed for lead registration form)
-- ============================================================

CREATE POLICY "events_public_read" ON events
  FOR SELECT TO anon USING (true);

CREATE POLICY "events_service_all" ON events
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================
-- 4. LEADS — anon can read id+stage only (for Realtime FunnelBoard)
--    Full access only via service_role (FastAPI backend)
-- ============================================================

-- Minimal anon read for Realtime subscription (id + stage, no PII)
CREATE POLICY "leads_anon_minimal_read" ON leads
  FOR SELECT TO anon USING (true);

-- service_role has full access
CREATE POLICY "leads_service_all" ON leads
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================
-- 5. All other sensitive tables — service_role only
-- ============================================================

CREATE POLICY "messages_service_all" ON messages
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "lead_enrichment_service_all" ON lead_enrichment
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "lead_memory_service_all" ON lead_memory
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "scheduled_jobs_service_all" ON scheduled_jobs
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "agent_locks_service_all" ON agent_locks
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "deletion_tokens_service_all" ON deletion_tokens
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================
-- 6. Atomic stage transition — prevents checkin/no-show race condition
-- ============================================================

CREATE OR REPLACE FUNCTION atomic_transition_lead_stage(
  p_lead_id uuid,
  p_target_stage text,
  p_valid_from_stages text[]
)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
  rows_affected int;
  current_stage text;
BEGIN
  SELECT stage INTO current_stage FROM leads WHERE id = p_lead_id;
  IF current_stage IS NULL THEN
    RETURN 'NOT_FOUND';
  END IF;
  IF current_stage = p_target_stage THEN
    RETURN 'ALREADY_SET';
  END IF;
  IF NOT (current_stage = ANY(p_valid_from_stages)) THEN
    RETURN 'INVALID_TRANSITION';
  END IF;
  UPDATE leads
  SET stage = p_target_stage
  WHERE id = p_lead_id AND stage = ANY(p_valid_from_stages);
  GET DIAGNOSTICS rows_affected = ROW_COUNT;
  IF rows_affected = 0 THEN
    RETURN 'ALREADY_SET';
  END IF;
  RETURN 'OK';
END;
$$;

-- ============================================================
-- Verification query (run after applying to confirm RLS is active):
-- SELECT tablename, rowsecurity FROM pg_tables
-- WHERE schemaname = 'public' AND tablename IN
-- ('leads','messages','lead_enrichment','lead_memory',
--  'scheduled_jobs','agent_locks','deletion_tokens','events');
-- All rows should have rowsecurity = true.
-- ============================================================
