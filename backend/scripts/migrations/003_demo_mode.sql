-- 003_demo_mode.sql — suporte de schema ao modo demo
-- Aplicar via Supabase SQL editor ou MCP apply_migration. Idempotente.

-- 1. Contador de contenção de lock para o teto de re-enfileiramento do scheduler (spec §8).
ALTER TABLE scheduled_jobs
  ADD COLUMN IF NOT EXISTS contention_count INTEGER NOT NULL DEFAULT 0;

-- 2. Garante que scheduled_jobs.status aceita 'RUNNING' — claim_scheduled_job seta esse
--    valor, mas o CHECK de 001_initial.sql o omitia. Recria idempotente (spec §12).
ALTER TABLE scheduled_jobs DROP CONSTRAINT IF EXISTS scheduled_jobs_status_check;
ALTER TABLE scheduled_jobs
  ADD CONSTRAINT scheduled_jobs_status_check
  CHECK (status IN ('PENDING','RUNNING','DONE','SKIPPED','FAILED'));
