CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS events (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  event_date  TIMESTAMPTZ NOT NULL,
  capacity    INT DEFAULT 120,
  sector      TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

DO $$ BEGIN
  CREATE TYPE lead_stage AS ENUM (
    'REGISTERED', 'ENRICHED', 'CONFIRMED', 'ATTENDED',
    'NO_SHOW', 'MEETING_SCHEDULED', 'CONVERTED', 'OPTED_OUT'
  );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS leads (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id         UUID REFERENCES events(id) ON DELETE CASCADE,
  name             TEXT,
  email            TEXT NOT NULL,
  phone            TEXT,
  company          TEXT,
  role             TEXT,
  stage            lead_stage DEFAULT 'REGISTERED',
  has_companion    BOOL DEFAULT false,
  companion_name   TEXT,
  consent_at           TIMESTAMPTZ NOT NULL,
  consent_ip           TEXT NOT NULL,
  whatsapp_consent_at  TIMESTAMPTZ,   -- NULL = não optou; agente só usa send_whatsapp() se preenchido
  deletion_req_at      TIMESTAMPTZ,
  created_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lead_enrichment (
  lead_id           UUID PRIMARY KEY REFERENCES leads(id) ON DELETE CASCADE,
  real_role         TEXT,
  company           TEXT,
  sector            TEXT,
  company_size      TEXT,
  linkedin_url      TEXT,
  security_signals  TEXT,
  is_decision_maker BOOL DEFAULT false,
  enrichment_summary TEXT,
  source            TEXT DEFAULT 'apollo',
  enriched_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id      UUID REFERENCES leads(id) ON DELETE CASCADE,
  event_id     UUID REFERENCES events(id) ON DELETE SET NULL,
  channel      TEXT CHECK (channel IN ('EMAIL','WHATSAPP','CHAT')),
  direction    TEXT CHECK (direction IN ('IN','OUT')),
  subject      TEXT,
  body         TEXT,
  funnel_stage lead_stage,
  resend_id    TEXT,
  opened_at    TIMESTAMPTZ,
  clicked_at   TIMESTAMPTZ,
  sent_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lead_memory (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id     UUID REFERENCES leads(id) ON DELETE CASCADE,
  role        TEXT CHECK (role IN ('user','assistant')),
  content     TEXT,
  tool_use    JSONB,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- CORRIGIDO: adicionado status FAILED e coluna error para rastreamento de falhas
CREATE TABLE IF NOT EXISTS scheduled_jobs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id     UUID REFERENCES leads(id) ON DELETE CASCADE,
  event_id    UUID REFERENCES events(id) ON DELETE SET NULL,
  job_type    TEXT NOT NULL,
  run_at      TIMESTAMPTZ NOT NULL,
  condition   JSONB DEFAULT '{}',
  status       TEXT DEFAULT 'PENDING'
               CHECK (status IN ('PENDING','DONE','SKIPPED','FAILED')),
  error        TEXT,
  retry_count  INT DEFAULT 0,
  max_retries  INT DEFAULT 3,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Mutex de execução por lead: impede que background task D+0 e APScheduler processem o mesmo lead simultaneamente.
-- run_agent() faz INSERT aqui no início; se já existe uma entrada válida, abort silencioso.
-- expires_at evita deadlock permanente em caso de crash do processo.
CREATE TABLE IF NOT EXISTS agent_locks (
  lead_id    UUID PRIMARY KEY REFERENCES leads(id) ON DELETE CASCADE,
  locked_at  TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL
);

-- Previne duplo registro do mesmo email no mesmo evento
CREATE UNIQUE INDEX IF NOT EXISTS leads_email_event_unique ON leads(email, event_id);
CREATE INDEX IF NOT EXISTS idx_leads_event_id ON leads(event_id);
CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
CREATE INDEX IF NOT EXISTS idx_messages_lead_id ON messages(lead_id);
-- Índice composto para check_engagement: busca do último email sem full scan por lead
CREATE INDEX IF NOT EXISTS idx_messages_lead_sent ON messages(lead_id, sent_at DESC) WHERE direction = 'OUT';
CREATE INDEX IF NOT EXISTS idx_messages_resend_id ON messages(resend_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_run_at ON scheduled_jobs(run_at) WHERE status = 'PENDING';
CREATE INDEX IF NOT EXISTS idx_lead_memory_lead_id ON lead_memory(lead_id);
CREATE INDEX IF NOT EXISTS idx_agent_locks_expires ON agent_locks(expires_at);

INSERT INTO events (name, event_date, capacity, sector)
VALUES (
  'Vigil Summit — Segurança para a Era da IA',
  NOW() + INTERVAL '30 days',
  120,
  'cybersecurity'
) ON CONFLICT DO NOTHING;
