# Config Panel + Run Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar aba "⚙ Configurações" ao dashboard com config editável do evento, status dos serviços externos, fila de jobs do agente e botão "Rodar Agente Agora" em cada lead.

**Architecture:** Backend ganha um módulo `admin.py` com 3 novos endpoints + `PUT /events/{id}` + `POST /leads/{id}/run-agent`. Frontend ganha 5 rotas proxy + componente `ConfigPanel.tsx` + tab bar no `FunnelBoard` + botão no `LeadDrawer`. Toda auth usa o padrão `X-API-Key` já existente.

**Tech Stack:** FastAPI (Python) + Next.js 14 App Router + TypeScript + Tailwind + Supabase JS client

**Spec:** `docs/superpowers/specs/2026-05-30-config-panel-design.md`

---

## File Map

| Ação | Arquivo | Responsabilidade |
|---|---|---|
| **Criar** | `backend/app/api/auth.py` | `_api_key_header` + `require_api_key` compartilhados |
| **Criar** | `backend/app/api/admin.py` | health, jobs list, run-job endpoints |
| **Modificar** | `backend/app/api/events.py` | Adicionar PUT endpoint; importar auth de `app.api.auth` |
| **Modificar** | `backend/app/api/leads.py` | Adicionar run-agent endpoint; importar auth de `app.api.auth` |
| **Modificar** | `backend/app/main.py` | Registrar admin router |
| **Modificar** | `frontend/lib/types.ts` | Adicionar `ServiceStatus`, `JobRow`, `EventConfig` |
| **Criar** | `frontend/app/api/events/[id]/route.ts` | Proxy PUT para backend |
| **Criar** | `frontend/app/api/admin/health/route.ts` | Proxy GET para backend |
| **Criar** | `frontend/app/api/admin/jobs/route.ts` | Proxy GET para backend |
| **Criar** | `frontend/app/api/admin/jobs/[id]/run/route.ts` | Proxy POST para backend |
| **Criar** | `frontend/app/api/leads/[id]/run-agent/route.ts` | Proxy POST para backend |
| **Criar** | `frontend/components/dashboard/ConfigPanel.tsx` | Config do evento + status serviços + jobs queue |
| **Modificar** | `frontend/components/dashboard/LeadDrawer.tsx` | Seção "Rodar Agente" antes do perfil enriquecido |
| **Modificar** | `frontend/components/dashboard/FunnelBoard.tsx` | Tab bar + render condicional ConfigPanel/funil |

---

## Task 1: Backend — módulo de auth compartilhado

**Files:**
- Create: `backend/app/api/auth.py`
- Modify: `backend/app/api/leads.py`
- Modify: `backend/app/api/events.py`

- [ ] **1.1 — Criar `backend/app/api/auth.py`**

  ```python
  from fastapi import HTTPException, Security
  from fastapi.security import APIKeyHeader
  from app.config import settings

  _api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


  def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
      if not settings.api_key or api_key != settings.api_key:
          raise HTTPException(status_code=401, detail="API key inválida ou ausente")
  ```

- [ ] **1.2 — Atualizar `backend/app/api/leads.py`: remover definição local e importar de `auth`**

  Remover as duas linhas:
  ```python
  _api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
  ```
  e
  ```python
  def _require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
      if not settings.api_key or api_key != settings.api_key:
          raise HTTPException(status_code=401, detail="API key inválida ou ausente")
  ```

  Adicionar no topo dos imports:
  ```python
  from app.api.auth import require_api_key as _require_api_key
  ```

  Remover também o import `from fastapi.security import APIKeyHeader` (não é mais necessário aqui).

- [ ] **1.3 — Atualizar `backend/app/api/events.py`: adicionar import**

  Adicionar no topo:
  ```python
  import asyncio
  from fastapi import HTTPException, Security
  from app.api.auth import require_api_key as _require_api_key
  ```

- [ ] **1.4 — Verificar backend inicia sem erros**

  ```bash
  cd backend
  uvicorn app.main:app --reload --port 8000
  ```

  Esperado: servidor sobe sem `ImportError`. Pressione Ctrl+C para parar.

- [ ] **1.5 — Commit**

  ```bash
  git add backend/app/api/auth.py backend/app/api/leads.py backend/app/api/events.py
  git commit -m "refactor(api): extract require_api_key to shared auth module"
  ```

---

## Task 2: Backend — `PUT /api/events/{event_id}`

**Files:**
- Modify: `backend/app/api/events.py`

- [ ] **2.1 — Adicionar endpoint PUT em `backend/app/api/events.py`**

  O arquivo atual tem apenas `GET /` e `GET /{event_id}`. Adicionar ao final:

  ```python
  @router.put("/{event_id}", dependencies=[Security(_require_api_key)])
  async def update_event(event_id: str, payload: dict):
      allowed = {"name", "event_date", "max_capacity"}
      update_data = {k: v for k, v in payload.items() if k in allowed and v is not None}
      if not update_data:
          raise HTTPException(status_code=400, detail="Nenhum campo válido para atualizar")
      sb = get_supabase()
      result = await asyncio.to_thread(
          lambda: sb.table("events").update(update_data).eq("id", event_id).execute()
      )
      if not result.data:
          raise HTTPException(status_code=404, detail="Evento não encontrado")
      return result.data[0]
  ```

  Verificar que `asyncio` está importado (foi adicionado no Task 1.3).

- [ ] **2.2 — Testar endpoint manualmente**

  Com o servidor rodando:
  ```bash
  curl -X PUT http://localhost:8000/api/events/<event-id> \
    -H "X-API-Key: vigil-secret-key-2026" \
    -H "Content-Type: application/json" \
    -d '{"name": "Vigil Summit 2026"}'
  ```

  Esperado: `{"id": "...", "name": "Vigil Summit 2026", ...}`

- [ ] **2.3 — Commit**

  ```bash
  git add backend/app/api/events.py
  git commit -m "feat(api): add PUT /api/events/{id} endpoint"
  ```

---

## Task 3: Backend — `POST /api/leads/{id}/run-agent`

**Files:**
- Modify: `backend/app/api/leads.py`

- [ ] **3.1 — Adicionar endpoint em `backend/app/api/leads.py`**

  Adicionar após o endpoint `mark_no_show` (por volta da linha 128), antes das funções de deletion:

  ```python
  @router.post("/{lead_id}/run-agent", dependencies=[Security(_require_api_key)])
  async def run_agent_endpoint(
      lead_id: str,
      background_tasks: BackgroundTasks,
      payload: dict = None,
  ):
      from fastapi import Body
      trigger = (payload or {}).get("trigger", "MANUAL_TRIGGER")
      sb = get_supabase()
      lead = await asyncio.to_thread(
          lambda: sb.table("leads").select("id").eq("id", lead_id).single().execute().data
      )
      if not lead:
          raise HTTPException(status_code=404, detail="Lead não encontrado")
      from app.agent.orchestrator import run_agent
      background_tasks.add_task(run_agent, lead_id, trigger)
      return {"status": "started", "lead_id": lead_id, "trigger": trigger}
  ```

  **Nota sobre o payload opcional:** FastAPI não aceita `Body(default={})` direto como parâmetro com `Security`. Usar `Request` para ler o body:

  ```python
  @router.post("/{lead_id}/run-agent", dependencies=[Security(_require_api_key)])
  async def run_agent_endpoint(
      lead_id: str,
      request: Request,
      background_tasks: BackgroundTasks,
  ):
      try:
          payload = await request.json()
      except Exception:
          payload = {}
      trigger = payload.get("trigger", "MANUAL_TRIGGER")
      sb = get_supabase()
      lead = await asyncio.to_thread(
          lambda: sb.table("leads").select("id").eq("id", lead_id).single().execute().data
      )
      if not lead:
          raise HTTPException(status_code=404, detail="Lead não encontrado")
      from app.agent.orchestrator import run_agent
      background_tasks.add_task(run_agent, lead_id, trigger)
      return {"status": "started", "lead_id": lead_id, "trigger": trigger}
  ```

- [ ] **3.2 — Testar endpoint**

  ```bash
  curl -X POST http://localhost:8000/api/leads/<lead-id>/run-agent \
    -H "X-API-Key: vigil-secret-key-2026" \
    -H "Content-Type: application/json" \
    -d '{"trigger": "MANUAL_TRIGGER"}'
  ```

  Esperado: `{"status": "started", "lead_id": "...", "trigger": "MANUAL_TRIGGER"}`

- [ ] **3.3 — Commit**

  ```bash
  git add backend/app/api/leads.py
  git commit -m "feat(api): add POST /api/leads/{id}/run-agent endpoint"
  ```

---

## Task 4: Backend — `admin.py` (health + jobs + run-job)

**Files:**
- Create: `backend/app/api/admin.py`
- Modify: `backend/app/main.py`

- [ ] **4.1 — Criar `backend/app/api/admin.py`**

  ```python
  import asyncio
  import httpx
  from fastapi import APIRouter, BackgroundTasks, HTTPException, Security
  from app.api.auth import require_api_key as _require_api_key
  from app.config import settings
  from app.db.client import get_supabase

  router = APIRouter(prefix="/admin", tags=["admin"])


  async def _db(fn):
      return await asyncio.to_thread(fn)


  # ── Health check ────────────────────────────────────────────────────────────

  def _env_status(key: str) -> str:
      return "ok" if key else "warn"


  async def _ping_anthropic() -> str:
      try:
          import anthropic
          client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
          await client.models.list()
          return "ok"
      except Exception:
          return "error"


  async def _ping_resend() -> str:
      try:
          async with httpx.AsyncClient(timeout=5) as c:
              r = await c.get(
                  "https://api.resend.com/domains",
                  headers={"Authorization": f"Bearer {settings.resend_api_key}"},
              )
              return "ok" if r.status_code in (200, 404) else "error"
      except Exception:
          return "error"


  async def _ping_apollo() -> str:
      if not settings.apollo_api_key:
          return "warn"
      try:
          async with httpx.AsyncClient(timeout=5) as c:
              r = await c.get(
                  "https://api.apollo.io/api/v1/auth/health",
                  headers={"x-api-key": settings.apollo_api_key},
              )
              return "ok" if r.status_code == 200 else "error"
      except Exception:
          return "error"


  async def _ping_cal() -> str:
      if not settings.cal_api_key:
          return "warn"
      try:
          async with httpx.AsyncClient(timeout=5) as c:
              r = await c.get(
                  "https://api.cal.com/v1/event-types",
                  headers={"Authorization": f"Bearer {settings.cal_api_key}"},
              )
              return "ok" if r.status_code in (200, 401) else "error"
      except Exception:
          return "error"


  async def _ping_evolution() -> str:
      if not settings.evolution_api_url or not settings.evolution_api_key:
          return "warn"
      try:
          async with httpx.AsyncClient(timeout=5) as c:
              r = await c.get(
                  f"{settings.evolution_api_url}/instance/fetchInstances",
                  headers={"apikey": settings.evolution_api_key},
              )
              return "ok" if r.status_code == 200 else "error"
      except Exception:
          return "error"


  def _build_services_config_only() -> list[dict]:
      return [
          {
              "name": "Claude (Anthropic)",
              "role": "Orquestrador do agente",
              "status": _env_status(settings.anthropic_api_key),
              "detail": "claude-sonnet-4-6" if settings.anthropic_api_key else "ANTHROPIC_API_KEY ausente",
          },
          {
              "name": "Resend",
              "role": "Envio de emails",
              "status": _env_status(settings.resend_api_key),
              "detail": settings.resend_from_email if settings.resend_api_key else "RESEND_API_KEY ausente",
          },
          {
              "name": "Apollo.io",
              "role": "Enriquecimento de leads",
              "status": _env_status(settings.apollo_api_key),
              "detail": "people/match API" if settings.apollo_api_key else "APOLLO_API_KEY ausente",
          },
          {
              "name": "Cal.com",
              "role": "Agendamento de reuniões",
              "status": _env_status(settings.cal_api_key),
              "detail": f"event type {settings.cal_event_type_id}" if settings.cal_api_key else "CAL_API_KEY ausente",
          },
          {
              "name": "Supabase",
              "role": "Banco de dados + Realtime",
              "status": "ok",
              "detail": "PostgreSQL · RLS ativo",
          },
          {
              "name": "WhatsApp (Evolution)",
              "role": "Mensagens WhatsApp",
              "status": _env_status(settings.evolution_api_url),
              "detail": settings.evolution_instance_name if settings.evolution_api_url else "EVOLUTION_API_URL ausente",
          },
      ]


  async def _build_services_live() -> list[dict]:
      anthropic_s, resend_s, apollo_s, cal_s, evolution_s = await asyncio.gather(
          _ping_anthropic(),
          _ping_resend(),
          _ping_apollo(),
          _ping_cal(),
          _ping_evolution(),
      )
      return [
          {"name": "Claude (Anthropic)", "role": "Orquestrador do agente", "status": anthropic_s, "detail": "claude-sonnet-4-6"},
          {"name": "Resend", "role": "Envio de emails", "status": resend_s, "detail": settings.resend_from_email},
          {"name": "Apollo.io", "role": "Enriquecimento de leads", "status": apollo_s, "detail": "people/match API"},
          {"name": "Cal.com", "role": "Agendamento de reuniões", "status": cal_s, "detail": f"event type {settings.cal_event_type_id}"},
          {"name": "Supabase", "role": "Banco de dados + Realtime", "status": "ok", "detail": "PostgreSQL · RLS ativo"},
          {"name": "WhatsApp (Evolution)", "role": "Mensagens WhatsApp", "status": evolution_s, "detail": settings.evolution_instance_name or "não configurado"},
      ]


  @router.get("/health", dependencies=[Security(_require_api_key)])
  async def health_check(live: bool = False):
      if live:
          services = await _build_services_live()
      else:
          services = _build_services_config_only()
      return {"services": services}


  # ── Jobs queue ───────────────────────────────────────────────────────────────

  @router.get("/jobs", dependencies=[Security(_require_api_key)])
  async def list_jobs(limit: int = 20):
      if limit > 100:
          limit = 100
      sb = get_supabase()
      rows = await _db(lambda: (
          sb.table("scheduled_jobs")
          .select("*, leads(name, company, role)")
          .order("created_at", desc=True)
          .limit(limit)
          .execute()
          .data
      ))
      return {"data": rows or []}


  @router.post("/jobs/{job_id}/run", dependencies=[Security(_require_api_key)])
  async def run_job_now(job_id: str, background_tasks: BackgroundTasks):
      sb = get_supabase()
      job = await _db(
          lambda: sb.table("scheduled_jobs").select("id, status").eq("id", job_id).single().execute().data
      )
      if not job:
          raise HTTPException(status_code=404, detail="Job não encontrado")
      if job["status"] not in ("PENDING", "FAILED"):
          raise HTTPException(
              status_code=409,
              detail=f"Job está em status '{job['status']}' — só PENDING ou FAILED podem ser re-executados",
          )
      if job["status"] == "FAILED":
          await _db(lambda: (
              sb.table("scheduled_jobs")
              .update({"status": "PENDING", "error": None})
              .eq("id", job_id)
              .execute()
          ))
      from app.scheduler.jobs import check_and_run_job
      background_tasks.add_task(check_and_run_job, job_id)
      return {"status": "triggered", "job_id": job_id}
  ```

- [ ] **4.2 — Registrar admin router em `backend/app/main.py`**

  Adicionar import após os outros routers:
  ```python
  from app.api.admin import router as admin_router
  ```

  Adicionar após `app.include_router(events_router, prefix="/api")`:
  ```python
  app.include_router(admin_router, prefix="/api")
  ```

- [ ] **4.3 — Verificar todos os endpoints**

  ```bash
  curl http://localhost:8000/api/admin/health \
    -H "X-API-Key: vigil-secret-key-2026"
  ```

  Esperado: `{"services": [...]}` com 6 serviços.

  ```bash
  curl http://localhost:8000/api/admin/jobs \
    -H "X-API-Key: vigil-secret-key-2026"
  ```

  Esperado: `{"data": [...]}` com jobs do banco.

- [ ] **4.4 — Commit**

  ```bash
  git add backend/app/api/admin.py backend/app/main.py
  git commit -m "feat(api): add admin router — health check, jobs queue, run-job endpoint"
  ```

---

## Task 5: Frontend — tipos e rotas proxy

**Files:**
- Modify: `frontend/lib/types.ts`
- Create: `frontend/app/api/events/[id]/route.ts`
- Create: `frontend/app/api/admin/health/route.ts`
- Create: `frontend/app/api/admin/jobs/route.ts`
- Create: `frontend/app/api/admin/jobs/[id]/run/route.ts`
- Create: `frontend/app/api/leads/[id]/run-agent/route.ts`

- [ ] **5.1 — Adicionar tipos em `frontend/lib/types.ts`**

  Adicionar ao final do arquivo:

  ```ts
  export type ServiceStatus = {
    name: string
    role: string
    status: 'ok' | 'warn' | 'error' | 'checking'
    detail: string
  }

  export type JobRow = {
    id: string
    lead_id: string
    job_type: string
    run_at: string
    status: 'PENDING' | 'RUNNING' | 'DONE' | 'FAILED' | 'SKIPPED'
    error: string | null
    created_at: string
    leads: { name: string | null; company: string | null; role: string | null } | null
  }

  export type EventConfig = {
    id: string
    name: string
    event_date: string
    max_capacity: number | null
  }
  ```

- [ ] **5.2 — Criar `frontend/app/api/events/[id]/route.ts`**

  ```ts
  import { NextRequest, NextResponse } from 'next/server'
  import { createSupabaseServerClient } from '@/lib/supabase-server'

  export async function PUT(
    request: NextRequest,
    { params }: { params: { id: string } }
  ) {
    const supabase = await createSupabaseServerClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 })

    const backendUrl = process.env.BACKEND_API_URL
    const backendKey = process.env.BACKEND_API_KEY
    if (!backendUrl || !backendKey) return NextResponse.json({ error: 'Configuração ausente' }, { status: 500 })

    const body = await request.json()
    const res = await fetch(`${backendUrl}/api/events/${params.id}`, {
      method: 'PUT',
      headers: { 'X-API-Key': backendKey, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  }
  ```

- [ ] **5.3 — Criar `frontend/app/api/admin/health/route.ts`**

  ```ts
  import { NextRequest, NextResponse } from 'next/server'
  import { createSupabaseServerClient } from '@/lib/supabase-server'

  export async function GET(request: NextRequest) {
    const supabase = await createSupabaseServerClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 })

    const backendUrl = process.env.BACKEND_API_URL
    const backendKey = process.env.BACKEND_API_KEY
    if (!backendUrl || !backendKey) return NextResponse.json({ error: 'Configuração ausente' }, { status: 500 })

    const live = request.nextUrl.searchParams.get('live') === 'true'
    const url = `${backendUrl}/api/admin/health${live ? '?live=true' : ''}`
    const res = await fetch(url, { headers: { 'X-API-Key': backendKey }, cache: 'no-store' })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  }
  ```

- [ ] **5.4 — Criar `frontend/app/api/admin/jobs/route.ts`**

  ```ts
  import { NextRequest, NextResponse } from 'next/server'
  import { createSupabaseServerClient } from '@/lib/supabase-server'

  export async function GET(request: NextRequest) {
    const supabase = await createSupabaseServerClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 })

    const backendUrl = process.env.BACKEND_API_URL
    const backendKey = process.env.BACKEND_API_KEY
    if (!backendUrl || !backendKey) return NextResponse.json({ error: 'Configuração ausente' }, { status: 500 })

    const limit = request.nextUrl.searchParams.get('limit') ?? '20'
    const res = await fetch(`${backendUrl}/api/admin/jobs?limit=${limit}`, {
      headers: { 'X-API-Key': backendKey },
      cache: 'no-store',
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  }
  ```

- [ ] **5.5 — Criar `frontend/app/api/admin/jobs/[id]/run/route.ts`**

  ```ts
  import { NextRequest, NextResponse } from 'next/server'
  import { createSupabaseServerClient } from '@/lib/supabase-server'

  export async function POST(
    _request: NextRequest,
    { params }: { params: { id: string } }
  ) {
    const supabase = await createSupabaseServerClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 })

    const backendUrl = process.env.BACKEND_API_URL
    const backendKey = process.env.BACKEND_API_KEY
    if (!backendUrl || !backendKey) return NextResponse.json({ error: 'Configuração ausente' }, { status: 500 })

    const res = await fetch(`${backendUrl}/api/admin/jobs/${params.id}/run`, {
      method: 'POST',
      headers: { 'X-API-Key': backendKey },
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  }
  ```

- [ ] **5.6 — Criar `frontend/app/api/leads/[id]/run-agent/route.ts`**

  ```ts
  import { NextRequest, NextResponse } from 'next/server'
  import { createSupabaseServerClient } from '@/lib/supabase-server'

  export async function POST(
    request: NextRequest,
    { params }: { params: { id: string } }
  ) {
    const supabase = await createSupabaseServerClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 })

    const backendUrl = process.env.BACKEND_API_URL
    const backendKey = process.env.BACKEND_API_KEY
    if (!backendUrl || !backendKey) return NextResponse.json({ error: 'Configuração ausente' }, { status: 500 })

    let body = {}
    try { body = await request.json() } catch { /* empty body is fine */ }

    const res = await fetch(`${backendUrl}/api/leads/${params.id}/run-agent`, {
      method: 'POST',
      headers: { 'X-API-Key': backendKey, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  }
  ```

- [ ] **5.7 — Verificar TypeScript**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

  Esperado: zero erros.

- [ ] **5.8 — Commit**

  ```bash
  git add frontend/lib/types.ts \
    frontend/app/api/events/[id]/route.ts \
    frontend/app/api/admin/health/route.ts \
    frontend/app/api/admin/jobs/route.ts \
    "frontend/app/api/admin/jobs/[id]/run/route.ts" \
    "frontend/app/api/leads/[id]/run-agent/route.ts"
  git commit -m "feat(frontend): add types + proxy routes for config panel and run-agent"
  ```

---

## Task 6: Frontend — `ConfigPanel.tsx`

**Files:**
- Create: `frontend/components/dashboard/ConfigPanel.tsx`

- [ ] **6.1 — Criar `frontend/components/dashboard/ConfigPanel.tsx`**

  ```tsx
  'use client'
  import { useState, useEffect, useCallback } from 'react'
  import type { EventConfig, ServiceStatus, JobRow } from '@/lib/types'

  const STATUS_BADGE: Record<string, { cls: string; label: string }> = {
    ok:       { cls: 'bg-green-50 text-green-700',  label: '✓ Ativo' },
    warn:     { cls: 'bg-amber-50 text-amber-700',  label: '⚠ Não configurado' },
    error:    { cls: 'bg-red-50 text-red-600',      label: '✗ Erro' },
    checking: { cls: 'bg-slate-100 text-slate-500', label: '⏳ Verificando…' },
  }

  const JOB_STATUS_BADGE: Record<string, string> = {
    DONE:    'bg-green-50 text-green-700',
    PENDING: 'bg-blue-50 text-blue-700',
    RUNNING: 'bg-amber-50 text-amber-700',
    FAILED:  'bg-red-50 text-red-600',
    SKIPPED: 'bg-slate-100 text-slate-500',
  }

  export default function ConfigPanel({ totalLeads }: { totalLeads: number }) {
    const [event, setEvent]           = useState<EventConfig | null>(null)
    const [form, setForm]             = useState<Partial<EventConfig>>({})
    const [saving, setSaving]         = useState(false)
    const [saveMsg, setSaveMsg]       = useState<string | null>(null)

    const [services, setServices]     = useState<ServiceStatus[]>([])
    const [checking, setChecking]     = useState(false)

    const [jobs, setJobs]             = useState<JobRow[]>([])
    const [runningJobs, setRunningJobs] = useState<Set<string>>(new Set())

    // ── Load event ───────────────────────────────────────────────────────────
    useEffect(() => {
      fetch('/api/events')
        .then(r => r.json())
        .then((data: EventConfig[]) => {
          if (data.length > 0) {
            setEvent(data[0])
            setForm({
              name: data[0].name,
              event_date: data[0].event_date?.slice(0, 10) ?? '',
              max_capacity: data[0].max_capacity ?? 120,
            })
          }
        })
        .catch(() => {/* non-fatal */})
    }, [])

    // ── Load services (env-var check) ────────────────────────────────────────
    useEffect(() => {
      fetch('/api/admin/health', { cache: 'no-store' })
        .then(r => r.json())
        .then(data => setServices(data.services ?? []))
        .catch(() => {/* non-fatal */})
    }, [])

    // ── Load + poll jobs ─────────────────────────────────────────────────────
    const loadJobs = useCallback(() => {
      fetch('/api/admin/jobs?limit=20', { cache: 'no-store' })
        .then(r => r.json())
        .then(data => setJobs(data.data ?? []))
        .catch(() => {/* non-fatal */})
    }, [])

    useEffect(() => {
      loadJobs()
      const id = setInterval(loadJobs, 30_000)
      return () => clearInterval(id)
    }, [loadJobs])

    // ── Save event ───────────────────────────────────────────────────────────
    async function handleSave() {
      if (!event) return
      setSaving(true)
      setSaveMsg(null)
      try {
        const res = await fetch(`/api/events/${event.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: form.name,
            event_date: form.event_date ? `${form.event_date}T09:00:00-03:00` : undefined,
            max_capacity: form.max_capacity,
          }),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const updated: EventConfig = await res.json()
        setEvent(updated)
        setSaveMsg('✓ Salvo com sucesso')
      } catch {
        setSaveMsg('✗ Falha ao salvar')
      } finally {
        setSaving(false)
        setTimeout(() => setSaveMsg(null), 3000)
      }
    }

    // ── Live health check ────────────────────────────────────────────────────
    async function handleCheckLive() {
      setChecking(true)
      setServices(prev => prev.map(s => ({ ...s, status: 'checking' as const })))
      try {
        const res = await fetch('/api/admin/health?live=true', { cache: 'no-store' })
        const data = await res.json()
        setServices(data.services ?? [])
      } catch {
        setServices(prev => prev.map(s => ({ ...s, status: 'error' as const })))
      } finally {
        setChecking(false)
      }
    }

    // ── Run job ──────────────────────────────────────────────────────────────
    async function handleRunJob(jobId: string) {
      setRunningJobs(prev => new Set(prev).add(jobId))
      setJobs(prev => prev.map(j => j.id === jobId ? { ...j, status: 'RUNNING' } : j))
      try {
        await fetch(`/api/admin/jobs/${jobId}/run`, { method: 'POST' })
      } catch {/* will refresh on next poll */}
      setTimeout(() => {
        setRunningJobs(prev => { const s = new Set(prev); s.delete(jobId); return s })
        loadJobs()
      }, 3000)
    }

    const capacity = form.max_capacity ?? 120
    const pct = capacity > 0 ? Math.min(Math.round((totalLeads / capacity) * 100), 100) : 0

    return (
      <div className="px-8 py-6 space-y-6">

        {/* ── Event Config ─────────────────────────────────────────────────── */}
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-400 mb-3">
            Configuração do Evento
          </p>
          <div className="bg-white border border-slate-200 border-t-[3px] border-t-navy-700 rounded-lg p-5">
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div>
                <label className="block text-[10px] font-semibold text-slate-400 mb-1.5">Nome</label>
                <input
                  type="text"
                  value={form.name ?? ''}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full border border-slate-200 rounded-md px-3 py-2 text-xs focus:outline-none focus:border-navy-700"
                />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-slate-400 mb-1.5">Data do evento</label>
                <input
                  type="date"
                  value={form.event_date ?? ''}
                  onChange={e => setForm(f => ({ ...f, event_date: e.target.value }))}
                  className="w-full border border-slate-200 rounded-md px-3 py-2 text-xs focus:outline-none focus:border-navy-700"
                />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-slate-400 mb-1.5">Capacidade máxima</label>
                <input
                  type="number"
                  value={form.max_capacity ?? 120}
                  onChange={e => setForm(f => ({ ...f, max_capacity: Number(e.target.value) }))}
                  className="w-full border border-slate-200 rounded-md px-3 py-2 text-xs focus:outline-none focus:border-navy-700"
                />
              </div>
            </div>
            <div className="mb-4">
              <div className="flex justify-between text-[10px] text-slate-500 mb-1">
                <span>Vagas ocupadas: <strong>{totalLeads} de {capacity}</strong> ({pct}%)</span>
                <span>{capacity - totalLeads} vagas disponíveis</span>
              </div>
              <div className="bg-slate-100 rounded-full h-1.5">
                <div
                  className="bg-navy-700 rounded-full h-full transition-all duration-500"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleSave}
                disabled={saving}
                className="bg-navy-950 text-white text-xs font-bold px-5 py-2 rounded-md hover:bg-navy-700 disabled:opacity-50 transition-colors"
              >
                {saving ? 'Salvando…' : 'Salvar alterações'}
              </button>
              {saveMsg && (
                <span className={`text-xs font-semibold ${saveMsg.startsWith('✓') ? 'text-green-600' : 'text-red-500'}`}>
                  {saveMsg}
                </span>
              )}
              <span className="text-[10px] text-slate-400 ml-1">
                Atualiza a data usada pelo agente para calcular os timings da régua
              </span>
            </div>
          </div>
        </div>

        {/* ── Service Status ───────────────────────────────────────────────── */}
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-400 mb-3">
            Status das Integrações
          </p>
          <div className="grid grid-cols-3 gap-3 mb-3">
            {services.map(svc => {
              const badge = STATUS_BADGE[svc.status] ?? STATUS_BADGE.warn
              return (
                <div key={svc.name} className="bg-white border border-slate-200 rounded-lg p-3">
                  <div className="flex justify-between items-start mb-1.5">
                    <span className="text-xs font-bold text-navy-950">{svc.name}</span>
                    <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${badge.cls}`}>
                      {badge.label}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500">{svc.role}</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">{svc.detail}</p>
                </div>
              )
            })}
          </div>
          <button
            onClick={handleCheckLive}
            disabled={checking}
            className="border border-slate-200 bg-white text-xs font-semibold text-slate-500 px-4 py-2 rounded-md hover:border-navy-700 hover:text-navy-700 disabled:opacity-50 transition-colors"
          >
            {checking ? '⏳ Verificando conexões…' : '🔄 Verificar conexões agora'}
          </button>
        </div>

        {/* ── Jobs Queue ───────────────────────────────────────────────────── */}
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-400 mb-3">
            Fila do Agente — Jobs Recentes
          </p>
          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="flex justify-between items-center px-4 py-3 border-b border-slate-100">
              <span className="text-xs font-semibold text-navy-950">Últimos 20 jobs</span>
              <span className="text-[10px] text-slate-400">Atualiza a cada 30s</span>
            </div>
            {jobs.length === 0 ? (
              <p className="text-xs text-slate-300 text-center py-8">Nenhum job encontrado</p>
            ) : (
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-100">
                    <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Lead</th>
                    <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Job</th>
                    <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Agendado para</th>
                    <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Status</th>
                    <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map(job => {
                    const canRun = job.status === 'PENDING' || job.status === 'FAILED'
                    const isRunning = runningJobs.has(job.id)
                    const leadName = job.leads?.name ?? job.lead_id.slice(0, 8) + '…'
                    const leadCompany = job.leads?.company ?? ''
                    const runAt = new Date(job.run_at).toLocaleString('pt-BR', {
                      day: '2-digit', month: 'short', year: 'numeric',
                      hour: '2-digit', minute: '2-digit',
                    })
                    return (
                      <tr key={job.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                        <td className="px-4 py-2.5">
                          <div className="font-semibold text-navy-950 text-[11px]">{leadName}</div>
                          {leadCompany && <div className="text-[10px] text-slate-400">{leadCompany}</div>}
                        </td>
                        <td className="px-4 py-2.5">
                          <code className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-[10px]">
                            {job.job_type}
                          </code>
                        </td>
                        <td className="px-4 py-2.5 text-[10px] text-slate-500">{runAt}</td>
                        <td className="px-4 py-2.5">
                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${JOB_STATUS_BADGE[job.status] ?? 'bg-slate-100 text-slate-500'}`}>
                            {job.status}
                          </span>
                        </td>
                        <td className="px-4 py-2.5">
                          {canRun ? (
                            <button
                              onClick={() => handleRunJob(job.id)}
                              disabled={isRunning}
                              className="border border-slate-200 text-[10px] font-semibold text-navy-700 px-2 py-1 rounded hover:border-navy-700 disabled:opacity-50 transition-colors"
                            >
                              {isRunning ? '⏳' : job.status === 'FAILED' ? '↻ Retry' : '▶ Rodar agora'}
                            </button>
                          ) : (
                            <span className="text-[10px] text-slate-300">—</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

      </div>
    )
  }
  ```

- [ ] **6.2 — Verificar TypeScript**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

  Esperado: zero erros.

- [ ] **6.3 — Commit**

  ```bash
  git add frontend/components/dashboard/ConfigPanel.tsx
  git commit -m "feat(dashboard): add ConfigPanel — event config, service status, jobs queue"
  ```

---

## Task 7: Frontend — botão "Rodar Agente" no `LeadDrawer`

**Files:**
- Modify: `frontend/components/dashboard/LeadDrawer.tsx`

- [ ] **7.1 — Adicionar estado e handler no `LeadDrawer`**

  Após a linha `const [onClose]` da interface `LeadDrawerProps`, adicionar dois estados no início da função `LeadDrawer`:

  ```tsx
  const [agentRunning, setAgentRunning] = useState(false)
  const [agentResult, setAgentResult] = useState<{ ok: boolean; message: string } | null>(null)

  async function handleRunAgent() {
    setAgentRunning(true)
    setAgentResult(null)
    try {
      const res = await fetch(`/api/leads/${lead.id}/run-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trigger: 'MANUAL_TRIGGER' }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setAgentResult({ ok: true, message: 'Agente iniciado — aguarde o Realtime atualizar o lead' })
    } catch {
      setAgentResult({ ok: false, message: 'Falha ao iniciar o agente' })
    } finally {
      setAgentRunning(false)
    }
  }
  ```

- [ ] **7.2 — Inserir seção "Rodar Agente" no JSX**

  Localizar o bloco `{/* Stage bar */}` no JSX. Inserir a nova seção APÓS o stage bar e ANTES da seção de enriquecimento (`{/* Enrichment grid */}`):

  ```tsx
  {/* Run Agent */}
  <div className="px-5 py-3 border-b border-slate-100 bg-slate-50">
    <p className="text-[10px] font-bold uppercase tracking-[0.06em] text-slate-400 mb-2">
      Ação do Agente
    </p>
    <button
      onClick={handleRunAgent}
      disabled={agentRunning}
      className="w-full bg-navy-950 text-white text-[11px] font-bold py-2 rounded-md
                 hover:bg-navy-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
    >
      {agentRunning ? '⏳ Executando…' : '▶ Rodar Agente Agora'}
    </button>
    {agentResult && (
      <p className={`text-[10px] mt-1.5 text-center font-semibold ${
        agentResult.ok ? 'text-green-600' : 'text-red-500'
      }`}>
        {agentResult.message}
      </p>
    )}
  </div>
  ```

- [ ] **7.3 — Verificar TypeScript**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

  Esperado: zero erros.

- [ ] **7.4 — Commit**

  ```bash
  git add frontend/components/dashboard/LeadDrawer.tsx
  git commit -m "feat(dashboard): add Run Agent button to LeadDrawer"
  ```

---

## Task 8: Frontend — tab bar no `FunnelBoard`

**Files:**
- Modify: `frontend/components/dashboard/FunnelBoard.tsx`

- [ ] **8.1 — Adicionar import e estado de tab**

  No topo de `FunnelBoard.tsx`, adicionar o import do `ConfigPanel`:
  ```tsx
  import ConfigPanel from './ConfigPanel'
  ```

  No corpo do componente `FunnelBoard`, adicionar estado após os estados existentes (após `selectedLeadId`):
  ```tsx
  const [activeTab, setActiveTab] = useState<'funnel' | 'config'>('funnel')
  ```

- [ ] **8.2 — Inserir tab bar e render condicional**

  Localizar o bloco `{/* MIDDLE ROW: Funnel Chart + Activity Feed */}` no JSX do return.

  Inserir ANTES desse bloco (após o KPI strip, que termina com `</div>`):

  ```tsx
  {/* TAB BAR */}
  <div className="bg-white border-b border-slate-200 px-8 flex gap-0">
    <button
      onClick={() => setActiveTab('funnel')}
      className={`py-3 px-5 text-xs font-semibold border-b-2 transition-colors -mb-px ${
        activeTab === 'funnel'
          ? 'border-navy-700 text-navy-700'
          : 'border-transparent text-slate-400 hover:text-slate-600'
      }`}
    >
      📊 Funil de Leads
    </button>
    <button
      onClick={() => setActiveTab('config')}
      className={`py-3 px-5 text-xs font-semibold border-b-2 transition-colors -mb-px ${
        activeTab === 'config'
          ? 'border-navy-700 text-navy-700'
          : 'border-transparent text-slate-400 hover:text-slate-600'
      }`}
    >
      ⚙ Configurações
    </button>
  </div>
  ```

  Depois, envolver todo o conteúdo abaixo da tab bar (middle row, filter bar, kanban, drawer) com:

  ```tsx
  {activeTab === 'funnel' && (
    <>
      {/* MIDDLE ROW: Funnel Chart + Activity Feed */}
      ...

      {/* FILTER BAR */}
      ...

      {/* KANBAN */}
      ...

      {/* LEAD DRAWER */}
      ...
    </>
  )}

  {activeTab === 'config' && (
    <ConfigPanel totalLeads={leads.length} />
  )}
  ```

- [ ] **8.3 — Verificar build completo**

  ```bash
  cd frontend && npm run build 2>&1 | tail -20
  ```

  Esperado: build sem erros. Dashboard em `/dashboard` com as duas tabs.

- [ ] **8.4 — Verificar fluxo no browser**

  ```bash
  cd frontend && npm run dev
  ```

  Acessar `http://localhost:3000/dashboard` e verificar:
  - [ ] Tab "📊 Funil de Leads" mostra o kanban normal
  - [ ] Tab "⚙ Configurações" mostra event config + service status + jobs table
  - [ ] Botão "Salvar alterações" salva o evento (checar resposta 200 no Network)
  - [ ] Botão "🔄 Verificar conexões" mostra spinner e atualiza badges
  - [ ] Clicar num lead card → drawer abre → seção "Ação do Agente" aparece com botão
  - [ ] Botão "▶ Rodar Agente Agora" mostra "⏳ Executando…" e depois mensagem de sucesso

- [ ] **8.5 — Commit**

  ```bash
  git add frontend/components/dashboard/FunnelBoard.tsx
  git commit -m "feat(dashboard): add config tab bar to FunnelBoard"
  ```

- [ ] **8.6 — Push**

  ```bash
  git push origin master
  ```

---

## Self-Review

**Spec coverage:**
- ✅ Tab bar com "Funil" e "Configurações" — Task 8
- ✅ KPI strip sempre visível — a tab bar fica APÓS o KPI strip, que sempre renderiza
- ✅ Config do evento editável (nome, data, capacidade) — Task 6 + PUT endpoint Task 2
- ✅ Barra de progresso de vagas — Task 6 (usa `totalLeads` prop + `max_capacity`)
- ✅ 6 cards de status de serviços — Task 4 (health) + Task 6 (render)
- ✅ Verificação real sob demanda (`?live=true`) — Task 4 + Task 6 botão
- ✅ Fila de jobs com polling 30s — Task 6
- ✅ "▶ Rodar agora" para PENDING e "↻ Retry" para FAILED — Task 6
- ✅ Botão "Rodar Agente Agora" no LeadDrawer — Task 7
- ✅ Auth em todas as rotas proxy (Supabase session) — Task 5
- ✅ X-API-Key em todos os endpoints backend — Tasks 1, 2, 3, 4
- ✅ `require_api_key` extraído para módulo compartilhado — Task 1

**Tipos consistentes em todos os tasks:**
- `EventConfig`, `ServiceStatus`, `JobRow` definidos em Task 5 e usados em Task 6 ✅
- `totalLeads: number` prop passada de `FunnelBoard` para `ConfigPanel` via `leads.length` ✅
