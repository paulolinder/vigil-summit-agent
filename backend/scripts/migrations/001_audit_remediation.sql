-- backend/scripts/migrations/001_audit_remediation.sql
-- Run as Supabase service_role or via Supabase Dashboard SQL editor

-- 1. UNIQUE constraint on agent_locks to make INSERT ON CONFLICT work atomically
ALTER TABLE agent_locks
  ADD CONSTRAINT IF NOT EXISTS agent_locks_lead_id_unique UNIQUE (lead_id);

-- 2. Column started_at in scheduled_jobs to track when job began execution
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS started_at timestamptz;

-- 3. Atomic claim function for scheduled_job
CREATE OR REPLACE FUNCTION claim_scheduled_job(p_job_id uuid)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
  rows_affected int;
BEGIN
  UPDATE scheduled_jobs
  SET status = 'RUNNING', started_at = now()
  WHERE id = p_job_id AND status = 'PENDING';
  GET DIAGNOSTICS rows_affected = ROW_COUNT;
  RETURN rows_affected > 0;
END;
$$;

-- 4. Atomic acquisition function for agent_lock
CREATE OR REPLACE FUNCTION acquire_agent_lock(p_lead_id uuid, p_expires_minutes int DEFAULT 5)
RETURNS boolean
LANGUAGE plpgsql
AS $$
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
$$;

-- 5. Heartbeat renewal function for agent_lock
CREATE OR REPLACE FUNCTION renew_agent_lock(p_lead_id uuid, p_extend_minutes int DEFAULT 3)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
  rows_affected int;
BEGIN
  UPDATE agent_locks
  SET expires_at = now() + (p_extend_minutes || ' minutes')::interval
  WHERE lead_id = p_lead_id AND expires_at > now();
  GET DIAGNOSTICS rows_affected = ROW_COUNT;
  RETURN rows_affected > 0;
END;
$$;

-- 6. Table for LGPD deletion tokens (used by Task 5)
CREATE TABLE IF NOT EXISTS deletion_tokens (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email      text NOT NULL,
  token      text UNIQUE NOT NULL,
  expires_at timestamptz NOT NULL,
  used_at    timestamptz,
  created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_deletion_tokens_token ON deletion_tokens(token);
CREATE INDEX IF NOT EXISTS idx_deletion_tokens_email ON deletion_tokens(email);

-- 7. Status column in messages for transactional outbox (used by Task 9)
ALTER TABLE messages ADD COLUMN IF NOT EXISTS status text DEFAULT 'SENT';
CREATE INDEX IF NOT EXISTS idx_messages_resend_id ON messages(resend_id);

-- 8. Consent version column for LGPD audit (used by Task 11)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS consent_version text DEFAULT 'v1.0';
