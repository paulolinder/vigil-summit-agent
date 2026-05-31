# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vigil Summit Agent — a full-stack autonomous AI agent for B2B event lead management. Leads progress through a funnel (REGISTERED → ENRICHED → CONFIRMED → ATTENDED → MEETING_SCHEDULED → CONVERTED) driven by a Claude-powered orchestrator, with APScheduler managing the messaging régua.

**Stack:** FastAPI (Python) + Next.js 14 + Supabase (PostgreSQL) + Claude Sonnet (agent) + Claude Haiku (chatbot) + Resend + Apollo.io + APScheduler

**Deploy:** Backend on Railway, frontend on Vercel.

---

## Commands

### Backend

```bash
cd backend

# First-time setup
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements-dev.txt

# Dev server (port 8000)
uvicorn app.main:app --reload --port 8000

# Tests
pytest                                                    # all tests
pytest tests/test_leads_api.py                            # single file
pytest tests/test_leads_api.py::test_create_lead_success  # single test
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # port 3000 (Turbopack)
npm run build
npm run lint
```

---

## Architecture

### Backend (`backend/app/`)

```
main.py           — FastAPI app: lifespan starts APScheduler, wires rate limiter, registers routers
config.py         — Pydantic Settings; reads all env vars from .env
limiter.py        — Single slowapi Limiter instance. Never instantiate another one — two instances break rate limiting.
api/leads.py      — POST /api/leads (public, 10 req/min), checkin/no-show/deletion endpoints (X-API-Key)
api/webhooks.py   — Resend webhook (svix HMAC) and Cal.com webhook (HMAC-SHA256)
api/events.py     — Events CRUD
db/client.py      — Supabase client singleton
db/models.py      — Pydantic models: LeadCreate, LeadStage enum
agent/orchestrator.py   — run_agent(): acquires lock, calls Claude with tool use in a loop (max 10 iters), saves memory
agent/tools.py          — TOOLS list (Anthropic tool definitions fed to Claude)
agent/tool_executor.py  — Dispatches tool calls to actual implementations
agent/prompts.py        — build_system_prompt(): dynamically builds from lead state, last engagement, memory
agent/memory.py         — Saves entries to lead_memory table
agent/lock_manager.py   — Postgres-backed distributed mutex + heartbeat loop (renews every 2 min)
agent/state_machine.py  — VALID_TRANSITIONS dict; is_valid_transition()
scheduler/runner.py     — AsyncIOScheduler; _reload_pending_jobs() every 5 min; bootstrap on startup
scheduler/jobs.py       — check_and_run_job(): atomic job claim via RPC, condition eval, exponential backoff retry
scheduler/cleanup.py    — Daily cleanup cron (3am)
```

### Frontend (`frontend/`)

```
app/page.tsx                        — Landing page: registration form + embedded chatbot
app/login/page.tsx                  — Supabase Auth login
app/dashboard/page.tsx              — Dashboard with FunnelBoard (force-dynamic)
app/deletion-confirm/page.tsx       — LGPD deletion confirmation flow
app/api/chat/route.ts               — Chatbot SSE stream (claude-haiku-4-5-20251001), in-memory rate limit
app/api/leads/route.ts              — Proxies to backend with X-API-Key (requires Supabase auth session)
app/api/leads/[id]/checkin|no-show  — Operational proxies (authenticated)
lib/supabase.ts                     — Browser Supabase client
```

### Database (Supabase / PostgreSQL)

Tables: `events`, `leads`, `lead_enrichment`, `messages`, `lead_memory`, `scheduled_jobs`, `agent_locks`, `deletion_tokens`

Key Postgres RPCs (defined in `backend/migrations/001_initial.sql`):
- `acquire_agent_lock(p_lead_id, p_expires_minutes)` — atomic lock; returns false if already locked
- `renew_agent_lock(p_lead_id, p_extend_minutes)` — heartbeat renewal
- `claim_scheduled_job(p_job_id)` — PENDING → RUNNING atomically; returns false if another worker got it
- `atomic_transition_lead_stage(p_lead_id, p_target_stage, p_valid_from_stages)` — authoritative guard for concurrent stage writes; returns `"OK"`, `"ALREADY_SET"`, `"INVALID_TRANSITION"`, or `"NOT_FOUND"`

---

## Key Invariants

**Agent locking:** `run_agent()` acquires a PK-based mutex in `agent_locks` before calling Claude. A heartbeat task renews the lock every 2 min. The `finally` block always releases it. `_reload_pending_jobs()` cleans expired locks on every 5-min cycle.

**`save_memory` is not a Claude tool.** The orchestrator calls it internally after each assistant response. Exposing it as a tool would create duplicate entries in `lead_memory`.

**`AsyncIOScheduler` (not `BackgroundScheduler`):** The FastAPI app runs on uvicorn's asyncio event loop. `BackgroundScheduler` runs in a thread and cannot `await` async jobs, causing `RuntimeError: This event loop is already running`. Jobs must be `async` functions scheduled on the same loop.

**Rate limiter singleton:** `app/limiter.py` exports a single `Limiter` instance. All routes import from there — never instantiate `Limiter()` elsewhere.

**Stage machine:** `state_machine.py` defines valid transitions in Python. For concurrent writes (checkin, no-show), the Postgres RPC `atomic_transition_lead_stage` is the authoritative guard. Never bypass it with a plain `UPDATE` for stage changes.

**Scheduler job recovery on restart:** Jobs overdue by more than `STALE_JOB_THRESHOLD_HOURS` (default 2h) are marked SKIPPED to prevent email bursts after long downtime. Jobs within the threshold are re-registered and run immediately.

**LGPD deletion:** Two-step: `POST /deletion-request` → confirmation email with token → `POST /deletion-request/confirm` with token in body (not URL, to avoid log exposure). Anonymization iterates all `lead_id` rows for the given email (one email may appear in multiple events). The email field is replaced with `gen_random_uuid()::TEXT`, not a hash — SHA-256 of email is reversible by dictionary attack.

**`MEETING_SCHEDULED` semantics:** Stage is set when the Cal.com link is generated (not on confirmed booking). For confirmed-booking tracking, a Cal.com `BOOKING_CREATED` webhook updates stage via `POST /api/webhooks/calcom`.

**WhatsApp opt-in:** `send_whatsapp()` may only be called when `whatsapp_consent_at IS NOT NULL`. The system prompt explicitly instructs the agent. The tool description also includes this constraint.

---

## Environment Variables

### Backend `.env`

```
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
RESEND_API_KEY=
RESEND_FROM_EMAIL=Vigil Summit <noreply@vigil.ai>
RESEND_WEBHOOK_SECRET=          # svix format (whsec_...)
APOLLO_API_KEY=
EVOLUTION_API_URL=
EVOLUTION_API_KEY=
EVOLUTION_INSTANCE_NAME=vigil
CAL_API_KEY=
CAL_EVENT_TYPE_ID=              # numeric ID from Cal.com event type
CAL_WEBHOOK_SECRET=
API_KEY=                        # X-API-Key for operational endpoints
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
STALE_JOB_THRESHOLD_HOURS=2
```

### Frontend `.env.local`

```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
ANTHROPIC_API_KEY=              # runtime only, never NEXT_PUBLIC_
BACKEND_API_URL=
BACKEND_API_KEY=
```

---

## API Security Model

| Endpoint | Auth |
|---|---|
| `POST /api/leads/` | Public (rate-limited 10 req/min/IP via slowapi) |
| `POST /api/leads/deletion-request` | Public (rate-limited 5 req/min/IP) |
| `POST /api/leads/deletion-request/confirm` | Public (rate-limited 10 req/min/IP) |
| `GET /api/leads/` | `X-API-Key` header |
| `POST /api/leads/{id}/checkin` | `X-API-Key` header |
| `POST /api/leads/{id}/no-show` | `X-API-Key` header |
| `POST /api/webhooks/resend` | svix HMAC signature (503 if secret not configured) |
| `POST /api/webhooks/calcom` | HMAC-SHA256 `X-Cal-Signature-256` (503 if secret not configured) |

Frontend API routes at `/api/leads/*` proxy to the backend and require an active Supabase Auth session.

---

## Simulating the Messaging Régua

To test time-based jobs without waiting, insert `scheduled_jobs` rows with `run_at` in the past. On the next `_reload_pending_jobs()` cycle (every 5 min, or on restart), overdue jobs within the stale threshold are re-registered and run immediately.

```sql
INSERT INTO scheduled_jobs (lead_id, job_type, run_at, condition, status)
VALUES (
  '<lead-uuid>',
  'CONFIRMATION_T14',
  NOW() - INTERVAL '1 minute',
  '{}',
  'PENDING'
);
```

Alternatively, call `check_and_run_job(job_id)` directly from a test script. See `backend/scripts/seed_personas.py` for synthetic test personas.

**LLM provider auto-detection (multi-provider):** `backend/app/llm/provider.py` `detect_provider()` picks the LLM by env key — `ANTHROPIC_API_KEY` wins if both are set, else `OPENAI_API_KEY`, else a clear boot error (also enforced by the `config.py` `@model_validator`). The orchestrator drives its tool-use loop through `get_adapter()` (an `LLMAdapter`), created ONCE per run and reused across iterations, so the loop is provider-agnostic; each adapter owns its native `messages` format and returns normalized `Turn`/`ToolCall`. `ToolCall` fields (`name`/`input`/`id`) are load-bearing — `agent/memory.py` reads them directly. The health check (`api/admin.py` `_ping_llm`) and the frontend chatbot (`app/api/chat/route.ts`) each detect the provider with the same rule; the chatbot emits an identical SSE shape regardless of provider, so `ChatbotWidget.tsx` is untouched. OpenAI model ids come from `OPENAI_AGENT_MODEL` / `OPENAI_CHAT_MODEL` (defaults `gpt-4.1` / `gpt-4.1-mini`).

**Demo mode (mocks por ausência de chave):** Apollo, Cal.com e WhatsApp/Evolution degradam para mock quando a chave correspondente está vazia — mesmo padrão de `detect_provider()`. As fronteiras vivem em `app/services/` (`enrichment.py`, `whatsapp.py`, `meeting.py`); o `tool_executor` só orquestra (não importa mais `httpx`). O enriquecimento mock (`services/mocks.py`) é determinístico por email e "Apollo-shaped" (o `sector` é uma chave de `_APOLLO_TO_SECTOR`, validado por teste anti-drift). WhatsApp simulado grava `messages` com `status="SIMULATED"`. O funil fecha via `apply_booking_created` — o MESMO núcleo do webhook real do Cal.com — disparado por um job `SIMULATED_BOOKING` (`generate_meeting_link` mock o agenda; `scheduler/jobs.py` o roteia direto pra `apply_booking_created`, sem o agente). Email e LLM são sempre reais.

**Régua acelerada (`DEMO_FAST_FORWARD`):** quando `true`, `_build_regua` (em `prompts.py`) troca as âncoras de datas-calendário por `now + N min` (passo de 2 min, folga sobre o lock de agente); a lógica/condições/ordem/templates não mudam. `settings` é importado dentro da função (sem mudar a assinatura). Na janela comprimida o webhook de abertura/clique do Resend não chega a tempo — use `POST /leads/{id}/simulate-engagement` (e os botões do `LeadDrawer`) para escrever `opened_at`/`clicked_at` na última mensagem e dirigir o branching por engajamento.

**Resiliência de lock do scheduler:** `run_agent` retorna o sentinela `LOCK_BUSY` (não uma string livre) quando o lock do lead está ocupado; `check_and_run_job` re-enfileira o job (`status=PENDING`, `run_at`+30s, incrementa `contention_count` — NÃO `retry_count`) com teto `MAX_CONTENTION=5` → `FAILED` se exceder. Isso corrige a perda silenciosa de jobs (antes marcados `DONE` sem rodar) e evita loop infinito se o lock ficar preso. Pré-requisito de schema: `scripts/migrations/003_demo_mode.sql` adiciona `scheduled_jobs.contention_count` e garante `'RUNNING'` no CHECK de status.
