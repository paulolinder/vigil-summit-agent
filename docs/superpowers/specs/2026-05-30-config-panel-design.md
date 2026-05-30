# Config Panel + Run Agent — Spec

**Data:** 2026-05-30
**Projeto:** Case AI Engineer — Pareto × Vigil.AI
**Escopo:** Aba "⚙ Configurações" no dashboard + botão "Rodar Agente" no LeadDrawer

---

## 1. Contexto e Motivação

O dashboard atual é somente visualização. Para a apresentação real do projeto, o avaliador precisa conseguir:
1. Ver que todos os serviços externos estão ativos
2. Disparar o agente manualmente sobre qualquer lead para demo ao vivo
3. Ver a fila de jobs do scheduler em tempo real
4. Editar a data do evento (todos os timings da régua derivam dela)

---

## 2. Layout

O dashboard ganha duas tabs no topo, abaixo da KPI strip:

```
┌─────────────────────────────────────────────┐
│  NAVBAR (sticky)                            │
├─────────────────────────────────────────────┤
│  KPI STRIP (sempre visível)                 │
├─────────────────────────────────────────────┤
│  [📊 Funil de Leads] [⚙ Configurações]      │  ← tab bar
├─────────────────────────────────────────────┤
│  Tab Funil:   FunnelChart + ActivityFeed    │
│               FilterBar + Kanban            │
│                                             │
│  Tab Config:  Configuração do Evento        │
│               Status das Integrações        │
│               Fila do Agente (jobs)         │
└─────────────────────────────────────────────┘
```

**Nota:** A KPI strip fica sempre visível em ambas as tabs — mostra os números do funil mesmo quando o avaliador está na aba de configuração.

---

## 3. Componentes Frontend

### 3.1 Tab state em `FunnelBoard.tsx`

Adicionar estado `activeTab: 'funnel' | 'config'` ao `FunnelBoard`.

Tab bar renderizada entre a KPI strip e o conteúdo atual:
```tsx
<div className="bg-white border-b border-slate-200 px-8 flex gap-0">
  <button
    onClick={() => setActiveTab('funnel')}
    className={`py-3 px-5 text-xs font-semibold border-b-2 transition-colors ${
      activeTab === 'funnel'
        ? 'border-navy-700 text-navy-700'
        : 'border-transparent text-slate-400 hover:text-slate-600'
    }`}
  >
    📊 Funil de Leads
  </button>
  <button
    onClick={() => setActiveTab('config')}
    className={`py-3 px-5 text-xs font-semibold border-b-2 transition-colors ${
      activeTab === 'config'
        ? 'border-navy-700 text-navy-700'
        : 'border-transparent text-slate-400 hover:text-slate-600'
    }`}
  >
    ⚙ Configurações
  </button>
</div>
```

Conteúdo condicional:
```tsx
{activeTab === 'funnel' && (
  <>
    {/* middle row, filter bar, kanban — código atual */}
  </>
)}
{activeTab === 'config' && (
  <ConfigPanel />
)}
```

### 3.2 `components/dashboard/ConfigPanel.tsx` (NOVO)

Componente `'use client'` com três seções:

**Seção 1 — Configuração do Evento**
- Fetcha `GET /api/events/` no mount (endpoint existente)
- Form controlado: nome, data (input type="date"), capacidade (input type="number")
- Barra de progresso: `(total_leads / max_capacity) * 100%`
- Botão "Salvar" → `PUT /api/events/{id}` → toast de sucesso/erro
- Após salvar com sucesso, o dado no estado local é atualizado (sem re-fetch)

**Seção 2 — Status das Integrações**
- Fetcha `GET /api/admin/health` no mount → retorna status de cada serviço baseado em env vars
- 6 cards em grid 3×2: Claude, Resend, Apollo.io, Cal.com, Supabase, WhatsApp
- Badge `✓ Ativo` (green) / `⚠ Não configurado` (amber) / `✗ Erro` (red)
- Botão "🔄 Verificar conexões agora" → `GET /api/admin/health?live=true` → pinga cada API de fato e atualiza os cards
- Estado local `checking: boolean` para mostrar spinner no botão durante a verificação

**Seção 3 — Fila do Agente**
- Fetcha `GET /api/admin/jobs?limit=20` no mount e a cada 30s via `setInterval`
- Tabela com colunas: Lead (nome + empresa), Job Type, Agendado para, Status, Ação
- Status badges: `DONE` (green), `PENDING` (blue), `RUNNING` (amber), `FAILED` (red), `SKIPPED` (slate)
- Coluna "Ação":
  - `PENDING` → botão "▶ Rodar agora" → `POST /api/admin/jobs/{id}/run`
  - `FAILED` → botão "↻ Retry" → `POST /api/admin/jobs/{id}/run`
  - Outros → "—"
- Após clicar "Rodar agora" / "Retry", atualiza o status do job na tabela imediatamente para `RUNNING`

### 3.3 `components/dashboard/LeadDrawer.tsx` — adicionar seção "Rodar Agente"

Nova seção entre o Stage bar e o Perfil enriquecido:

```tsx
{/* Seção: Ação do Agente */}
<div className="px-5 py-3 border-b border-slate-100">
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
    <p className={`text-[10px] mt-1.5 text-center ${
      agentResult.ok ? 'text-green-600' : 'text-red-500'
    }`}>
      {agentResult.message}
    </p>
  )}
</div>
```

Estado local no `LeadDrawer`:
```ts
const [agentRunning, setAgentRunning] = useState(false)
const [agentResult, setAgentResult] = useState<{ ok: boolean; message: string } | null>(null)
```

`handleRunAgent`:
```ts
async function handleRunAgent() {
  setAgentRunning(true)
  setAgentResult(null)
  try {
    const res = await fetch(`/api/leads/${lead.id}/run-agent`, { method: 'POST' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    setAgentResult({ ok: true, message: 'Agente iniciado — aguarde Realtime atualizar o lead' })
  } catch {
    setAgentResult({ ok: false, message: 'Falha ao iniciar o agente' })
  } finally {
    setAgentRunning(false)
  }
}
```

---

## 4. Frontend API Proxy Routes (NOVAS)

| Arquivo | Método | Proxies para |
|---|---|---|
| `app/api/events/[id]/route.ts` | PUT | `PUT {BACKEND_URL}/api/events/{id}` |
| `app/api/admin/health/route.ts` | GET | `GET {BACKEND_URL}/api/admin/health` |
| `app/api/admin/jobs/route.ts` | GET | `GET {BACKEND_URL}/api/admin/jobs` |
| `app/api/admin/jobs/[id]/run/route.ts` | POST | `POST {BACKEND_URL}/api/admin/jobs/{id}/run` |
| `app/api/leads/[id]/run-agent/route.ts` | POST | `POST {BACKEND_URL}/api/leads/{id}/run-agent` |

Todas as rotas:
- Verificam sessão Supabase Auth (`createSupabaseServerClient`)
- Retornam 401 se não autenticado
- Passam `X-API-Key: BACKEND_API_KEY` para o backend

---

## 5. Backend — Novos Endpoints

### 5.1 `backend/app/api/events.py` — adicionar PUT

```python
@router.put("/{event_id}", dependencies=[Security(_require_api_key)])
async def update_event(event_id: str, payload: dict):
    allowed = {"name", "event_date", "max_capacity"}
    update_data = {k: v for k, v in payload.items() if k in allowed}
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

Precisa importar `_require_api_key` de `app.api.leads` (ou mover para um módulo compartilhado `app.api.auth`).

### 5.2 `backend/app/api/admin.py` (NOVO)

```python
router = APIRouter(prefix="/admin", tags=["admin"])
```

**`GET /api/admin/health`**

- Sem `?live=true`: retorna apenas se cada env var está configurada (`"configured"` ou `"not_configured"`)
- Com `?live=true`: executa verificações reais em cada serviço externo

Verificações reais:
- **Claude**: `anthropic.AsyncAnthropic().models.list()` — lista modelos (rápido, ~200ms)
- **Resend**: `resend.Domains.list()` — verifica API key
- **Apollo.io**: GET `https://api.apollo.io/v1/auth/health` com header `x-api-key`
- **Cal.com**: GET `https://api.cal.com/v1/event-types` com `Authorization: Bearer {key}`
- **Supabase**: `sb.table("events").select("id").limit(1).execute()` — já está conectado
- **WhatsApp**: GET `{EVOLUTION_API_URL}/instance/fetchInstances` com `apikey: {key}`

Resposta:
```json
{
  "services": [
    {"name": "Claude (Anthropic)", "role": "Orquestrador do agente", "status": "ok", "detail": "claude-sonnet-4-6 · chave configurada"},
    {"name": "Resend", "role": "Envio de emails", "status": "ok", "detail": "noreply@vigil.ai · webhook ativo"},
    {"name": "Apollo.io", "role": "Enriquecimento de leads", "status": "ok", "detail": "people/match API · chave configurada"},
    {"name": "Cal.com", "role": "Agendamento de reuniões", "status": "ok", "detail": "event type configurado"},
    {"name": "Supabase", "role": "Banco de dados + Realtime", "status": "ok", "detail": "PostgreSQL · RLS ativo"},
    {"name": "WhatsApp (Evolution)", "role": "Mensagens WhatsApp", "status": "warn", "detail": "EVOLUTION_API_URL ausente"}
  ]
}
```

Status values: `"ok"` | `"warn"` | `"error"`

**`GET /api/admin/jobs?limit=20`**

```python
@router.get("/jobs", dependencies=[Security(_require_api_key)])
async def list_jobs(limit: int = 20):
    sb = get_supabase()
    rows = await asyncio.to_thread(lambda: (
        sb.table("scheduled_jobs")
        .select("*, leads(name, company, role)")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    ))
    return {"data": rows}
```

**`POST /api/admin/jobs/{job_id}/run`**

```python
@router.post("/jobs/{job_id}/run", dependencies=[Security(_require_api_key)])
async def run_job_now(job_id: str, background_tasks: BackgroundTasks):
    sb = get_supabase()
    # Reset FAILED or leave PENDING — then trigger
    job = await asyncio.to_thread(
        lambda: sb.table("scheduled_jobs").select("status").eq("id", job_id).single().execute().data
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job["status"] == "FAILED":
        await asyncio.to_thread(lambda: (
            sb.table("scheduled_jobs").update({"status": "PENDING", "error": None}).eq("id", job_id).execute()
        ))
    background_tasks.add_task(check_and_run_job, job_id)
    return {"status": "triggered", "job_id": job_id}
```

### 5.3 `backend/app/api/leads.py` — adicionar run-agent endpoint

```python
@router.post("/{lead_id}/run-agent", dependencies=[Security(_require_api_key)])
async def run_agent_endpoint(lead_id: str, background_tasks: BackgroundTasks, payload: dict = Body(default={})):
    sb = get_supabase()
    lead = await asyncio.to_thread(
        lambda: sb.table("leads").select("id").eq("id", lead_id).single().execute().data
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    trigger = payload.get("trigger", "MANUAL_TRIGGER")
    background_tasks.add_task(run_agent, lead_id, trigger)
    return {"status": "started", "lead_id": lead_id, "trigger": trigger}
```

### 5.4 `backend/app/main.py` — registrar admin router

```python
from app.api.admin import router as admin_router
app.include_router(admin_router, prefix="/api")
```

---

## 6. Arquivo de Auth Compartilhado

`_require_api_key` está atualmente definido em `app/api/leads.py`. Como `admin.py` e `events.py` também precisam dele, extrair para `app/api/auth.py`:

```python
# app/api/auth.py
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    if not settings.api_key or api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="API key inválida ou ausente")
```

`leads.py` e `events.py` passam a importar de `app.api.auth`.

---

## 7. Tipos TypeScript (frontend)

Adicionar em `frontend/lib/types.ts`:

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
  leads: { name: string | null; company: string | null; role: string | null } | null
}

export type EventConfig = {
  id: string
  name: string
  event_date: string
  max_capacity: number
}
```

---

## 8. Restrições e Decisões

- **Auth em todos os endpoints admin**: todos usam `X-API-Key` — igual ao padrão existente. Nenhuma nova mecanismo de auth.
- **Health check lazy por padrão**: na carga inicial, apenas verifica env vars (rápido). Verificação real (`?live=true`) só sob demanda via botão.
- **Jobs queue com polling**: `setInterval(30_000)` no ConfigPanel para atualizar a tabela. Não usa Realtime para a tabela `scheduled_jobs` (evita configurar subscriptions extras).
- **Sem edição de jobs**: a tabela de jobs é read-only + run/retry. Cancelamento de jobs não está no escopo.
- **Tab state não persiste**: trocar de tab e recarregar a página volta para "Funil". Não há necessidade de persistir no URL para o MVP.
- **`max_capacity` na tabela `events`**: se a coluna não existir, o PUT omite esse campo silenciosamente. A barra de progresso usa `120` como fallback hardcoded.

---

*Documento gerado em 2026-05-30 — aprovado em sessão de brainstorming com o usuário*
