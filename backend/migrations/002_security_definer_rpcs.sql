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
-- search_path. Bodies are otherwise byte-for-byte the live definitions.
--
-- Idempotent (CREATE OR REPLACE). Safe to re-run.

CREATE OR REPLACE FUNCTION public.acquire_agent_lock(p_lead_id uuid, p_expires_minutes integer DEFAULT 10)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path = public, pg_temp
AS $function$
BEGIN
  -- Limpa locks expirados
  DELETE FROM agent_locks WHERE expires_at < NOW();

  -- Tenta inserir lock (PK garante atomicidade)
  INSERT INTO agent_locks (lead_id, expires_at)
  VALUES (p_lead_id, NOW() + (p_expires_minutes || ' minutes')::INTERVAL);

  RETURN TRUE;
EXCEPTION
  WHEN unique_violation THEN
    RETURN FALSE;
END;
$function$;

CREATE OR REPLACE FUNCTION public.atomic_transition_lead_stage(p_lead_id uuid, p_target_stage text, p_valid_from_stages text[])
 RETURNS text
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path = public, pg_temp
AS $function$
DECLARE
  v_current_stage TEXT;
  v_rows_affected INT;
BEGIN
  SELECT stage INTO v_current_stage FROM leads WHERE id = p_lead_id FOR UPDATE;

  IF NOT FOUND THEN
    RETURN 'NOT_FOUND';
  END IF;

  IF v_current_stage = p_target_stage THEN
    RETURN 'ALREADY_SET';
  END IF;

  IF NOT (v_current_stage = ANY(p_valid_from_stages)) THEN
    RETURN 'INVALID_TRANSITION';
  END IF;

  UPDATE leads SET stage = p_target_stage, updated_at = NOW() WHERE id = p_lead_id;
  GET DIAGNOSTICS v_rows_affected = ROW_COUNT;

  IF v_rows_affected = 1 THEN
    RETURN 'OK';
  ELSE
    RETURN 'INVALID_TRANSITION';
  END IF;
END;
$function$;

CREATE OR REPLACE FUNCTION public.claim_scheduled_job(p_job_id uuid)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path = public, pg_temp
AS $function$
BEGIN
  UPDATE scheduled_jobs
  SET status = 'RUNNING', updated_at = NOW()
  WHERE id = p_job_id AND status = 'PENDING';

  RETURN FOUND;
END;
$function$;

CREATE OR REPLACE FUNCTION public.renew_agent_lock(p_lead_id uuid, p_extend_minutes integer DEFAULT 10)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path = public, pg_temp
AS $function$
BEGIN
  UPDATE agent_locks SET expires_at = NOW() + (p_extend_minutes || ' minutes')::INTERVAL WHERE lead_id = p_lead_id;
  RETURN FOUND;
END;
$function$;
