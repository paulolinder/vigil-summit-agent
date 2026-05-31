-- 004_fix_stage_transition_enum_cast.sql
--
-- BUG (pré-existente, desde a criação da função em backend/migrations/002_security_definer_rpcs.sql):
-- a coluna leads.stage é o ENUM `lead_stage`, mas atomic_transition_lead_stage comparava e
-- atribuía o stage contra text / text[] sem cast. As checagens iniciais usavam a variável
-- `current_stage text` (cast implícito no SELECT INTO, OK), mas o UPDATE comparava a COLUNA enum
-- direto com text[]:
--     UPDATE leads SET stage = p_target_stage WHERE ... stage = ANY(p_valid_from_stages)
-- → ERROR: operator does not exist: lead_stage = text
--
-- Efeito: a função SEMPRE lançava exceção ao tentar mover um stage. Nenhuma transição
-- (REGISTERED→ENRICHED, →ATTENDED, →MEETING_SCHEDULED, etc.) jamais ocorreu em produção —
-- todo lead ficava preso em REGISTERED. O enrichment gravava a linha em lead_enrichment, mas a
-- transição subsequente explodia (silenciosamente, pois tool_executor não checa o retorno da RPC).
--
-- FIX: corpo exato do pg_get_functiondef + os casts mínimos:
--   - SELECT stage::text INTO current_stage  (explícito; já funcionava por cast implícito)
--   - SET stage = p_target_stage::lead_stage
--   - WHERE ... stage::text = ANY(p_valid_from_stages)
-- Idempotente (CREATE OR REPLACE). Supersede o corpo de atomic_transition_lead_stage em
-- backend/migrations/002_security_definer_rpcs.sql. As demais 3 RPCs daquele arquivo não tocam
-- a coluna enum e permanecem corretas.

CREATE OR REPLACE FUNCTION public.atomic_transition_lead_stage(p_lead_id uuid, p_target_stage text, p_valid_from_stages text[])
 RETURNS text
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
  rows_affected int;
  current_stage text;
BEGIN
  SELECT stage::text INTO current_stage FROM leads WHERE id = p_lead_id;
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
  SET stage = p_target_stage::lead_stage
  WHERE id = p_lead_id AND stage::text = ANY(p_valid_from_stages);
  GET DIAGNOSTICS rows_affected = ROW_COUNT;
  IF rows_affected = 0 THEN
    RETURN 'ALREADY_SET';
  END IF;
  RETURN 'OK';
END;
$function$;
