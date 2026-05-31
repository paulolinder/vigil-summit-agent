-- 002_security_definer_rpcs.sql
--
-- Make the four guard RPCs SECURITY DEFINER with a pinned search_path.
--
-- Why: these functions are the authoritative concurrency guards (lock acquisition,
-- atomic stage transition, job claim). They were running as SECURITY INVOKER, so their
-- writes depended entirely on the caller's role passing RLS. That works today because the
-- backend uses the service_role key, but it is fragile — if the key were ever the anon key,
-- the UPDATEs inside these functions would silently affect 0 rows and the guards would
-- report wrong outcomes. SECURITY DEFINER makes them role-agnostic.
--
-- `SET search_path = public, pg_temp` is mandatory for SECURITY DEFINER functions: it
-- prevents a caller from shadowing the tables/operators the body references via a malicious
-- search_path.
--
-- Bodies are the exact live definitions (from pg_get_functiondef) — ONLY the
-- SECURITY DEFINER + search_path clauses are added. Idempotent (CREATE OR REPLACE).

CREATE OR REPLACE FUNCTION public.acquire_agent_lock(p_lead_id uuid, p_expires_minutes integer DEFAULT 5)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path = public, pg_temp
AS $function$
DECLARE
  rows_affected int;
BEGIN
  DELETE FROM agent_locks
  WHERE lead_id = p_lead_id AND expires_at < now();

  INSERT INTO agent_locks (lead_id, locked_at, expires_at)
  VALUES (p_lead_id, now(), now() + (p_expires_minutes || ' minutes')::interval)
  ON CONFLICT (lead_id) DO NOTHING;

  GET DIAGNOSTICS rows_affected = ROW_COUNT;
  RETURN rows_affected > 0;
END;
$function$;

CREATE OR REPLACE FUNCTION public.atomic_transition_lead_stage(p_lead_id uuid, p_target_stage text, p_valid_from_stages text[])
 RETURNS text
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path = public, pg_temp
AS $function$
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
$function$;

CREATE OR REPLACE FUNCTION public.claim_scheduled_job(p_job_id uuid)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path = public, pg_temp
AS $function$
DECLARE
  rows_affected int;
BEGIN
  UPDATE scheduled_jobs
  SET status = 'RUNNING', started_at = now()
  WHERE id = p_job_id AND status = 'PENDING';
  GET DIAGNOSTICS rows_affected = ROW_COUNT;
  RETURN rows_affected > 0;
END;
$function$;

CREATE OR REPLACE FUNCTION public.renew_agent_lock(p_lead_id uuid, p_extend_minutes integer DEFAULT 3)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path = public, pg_temp
AS $function$
DECLARE
  rows_affected int;
BEGIN
  UPDATE agent_locks
  SET expires_at = now() + (p_extend_minutes || ' minutes')::interval
  WHERE lead_id = p_lead_id AND expires_at > now();
  GET DIAGNOSTICS rows_affected = ROW_COUNT;
  RETURN rows_affected > 0;
END;
$function$;
