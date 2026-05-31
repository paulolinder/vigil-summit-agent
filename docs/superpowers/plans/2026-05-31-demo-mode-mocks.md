# Modo Demo & Mocks de Integrações Externas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que o funil inteiro (captação → enriquecimento → régua → reunião) rode sem chaves de APIs pagas — Apollo, Cal.com e WhatsApp/Evolution degradam para mock na ausência da chave; email (Resend) e LLM (Claude) seguem reais.

**Architecture:** Extrair as chamadas externas do `tool_executor.py` para uma camada `services/` onde cada função de fronteira decide real-vs-mock pela presença da chave (espelhando `llm/provider.py::detect_provider`). Um gerador determinístico (`mocks.py`) fabrica enrichment "Apollo-shaped". O funil fecha via webhook simulado que reusa o mesmo caminho de transição da produção. Uma flag `DEMO_FAST_FORWARD` comprime a régua (dias→minutos), e controles no dashboard (check-in/no-show + simular abertura/clique) deixam o avaliador dirigir o funil.

**Tech Stack:** FastAPI (Python), pytest, APScheduler, Supabase (PostgreSQL), Next.js 14 (TypeScript), Supabase Realtime.

**Spec:** `docs/superpowers/specs/2026-05-31-demo-mode-mocks-design.md`

---

## Estrutura de arquivos

**Criar (backend):**
- `backend/app/services/mocks.py` — gerador determinístico de enrichment
- `backend/app/services/enrichment.py` — `enrich_lead_data(lead)` (real Apollo vs mock)
- `backend/app/services/whatsapp.py` — `send_whatsapp_message(lead, text, sb)` (Evolution vs simulado)
- `backend/app/services/meeting.py` — `generate_meeting_link(lead)` + `apply_booking_created(email)`
- `backend/scripts/migrations/003_demo_mode.sql` — coluna `contention_count` + relaxa CHECK de status
- `backend/tests/test_services_mocks.py`, `test_services_enrichment.py`, `test_services_whatsapp.py`, `test_services_meeting.py`

**Modificar (backend):**
- `backend/app/agent/tool_executor.py` — `_enrich_lead`, `_send_whatsapp`, `_schedule_meeting` chamam os serviços (sem `httpx`)
- `backend/app/api/webhooks.py` — extrai núcleo para `apply_booking_created`
- `backend/app/api/leads.py` — novo `POST /{id}/simulate-engagement`
- `backend/app/scheduler/jobs.py` — branch `SIMULATED_BOOKING` + re-enfileiramento por contenção de lock
- `backend/app/agent/orchestrator.py` — sentinela `LOCK_BUSY`
- `backend/app/agent/prompts.py` — fast-forward em `_build_regua`
- `backend/app/config.py` — flag `demo_fast_forward`
- `backend/.env.example` — bloco modo demo

**Modificar (frontend):**
- `frontend/lib/api.ts` — `simulateEngagement(...)`
- `frontend/lib/types.ts` — `Message` ganha `channel`/`status`
- `frontend/app/api/leads/[id]/simulate-engagement/route.ts` (NOVO proxy)
- `frontend/components/dashboard/LeadDrawer.tsx` — botões + badge SIMULATED/WhatsApp
- `frontend/components/dashboard/FunnelBoard.tsx` — select de mensagens inclui channel/status

**Docs:**
- `CLAUDE.md`

---

## Task 1: Migração — coluna `contention_count` + CHECK de status

**Files:**
- Create: `backend/scripts/migrations/003_demo_mode.sql`

- [ ] **Step 1: Escrever a migração**

```sql
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
```

- [ ] **Step 2: Aplicar a migração ao banco**

Aplique via Supabase (MCP `apply_migration` com name `003_demo_mode`, ou cole no SQL editor do projeto). O sandbox não alcança o Supabase — esta etapa roda contra o projeto real.

- [ ] **Step 3: Verificar a coluna**

Run (Supabase SQL editor ou MCP `execute_sql`):
```sql
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'scheduled_jobs' AND column_name = 'contention_count';
```
Expected: 1 linha, `integer`, default `0`.

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/migrations/003_demo_mode.sql
git commit -m "feat(db): contention_count + status CHECK para modo demo"
```

---

## Task 2: `services/mocks.py` — gerador determinístico de enrichment

**Files:**
- Create: `backend/app/services/mocks.py`
- Test: `backend/tests/test_services_mocks.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# backend/tests/test_services_mocks.py
from app.services.mocks import generate_enrichment
from app.services.resend_service import _APOLLO_TO_SECTOR


def test_deterministic_same_email_same_output():
    lead = {"email": "ciso@bigbank.com.br", "name": "Maria", "company": None, "role": None}
    a = generate_enrichment(lead)
    b = generate_enrichment(dict(lead))
    assert a == b


def test_sector_is_apollo_shaped():
    """sector DEVE ser uma chave de _APOLLO_TO_SECTOR — senão a personalização por setor degrada."""
    for local in ("a@x.com", "b@y.com.br", "c@z.io", "ciso@bank.com", "cto@health.org"):
        out = generate_enrichment({"email": local, "name": "X", "company": None, "role": None})
        assert out["sector"] in _APOLLO_TO_SECTOR, f"setor fora do mapa: {out['sector']}"


def test_role_keyword_implies_decision_maker():
    out = generate_enrichment({"email": "p@empresa.com", "name": "P", "company": "Empresa", "role": "CISO"})
    assert out["is_decision_maker"] is True


def test_generic_domain_gets_synthetic_company():
    out = generate_enrichment({"email": "alguem@gmail.com", "name": "A", "company": None, "role": None})
    assert out["company"] and out["company"].lower() != "gmail"


def test_output_has_parity_fields_no_security_signals():
    out = generate_enrichment({"email": "x@y.com", "name": "X", "company": None, "role": None})
    assert set(out.keys()) == {
        "real_role", "company", "sector", "company_size",
        "linkedin_url", "is_decision_maker", "enrichment_summary", "source",
    }
    assert out["source"] == "mock"
    # paridade: o Apollo real NÃO grava security_signals; o mock também não
    assert "security_signals" not in out
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

Run: `cd backend && pytest tests/test_services_mocks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.mocks'`

- [ ] **Step 3: Implementar `mocks.py`**

```python
# backend/app/services/mocks.py
"""Geradores determinísticos para o modo demo (sem chaves de API pagas).

O enrichment é uma função pura de `email`: o mesmo email sempre produz o mesmo
perfil. O campo `sector` sai no vocabulário de indústria do Apollo (chaves de
`_APOLLO_TO_SECTOR` em resend_service.py) para casar com a personalização por setor.
"""
import hashlib

# Setores: subconjunto EXPLÍCITO das chaves de _APOLLO_TO_SECTOR (resend_service.py).
# Teste anti-drift garante que todos pertencem ao mapa.
_SECTOR_POOL = [
    "financial services",
    "computer software",
    "hospital & health care",
    "manufacturing",
    "government administration",
    "telecommunications",
    "retail",
    "oil & energy",
]

_DM_TITLES = [
    "Chief Information Security Officer",
    "Chief Technology Officer",
    "VP of Information Security",
    "Diretor de Tecnologia da Informação",
    "Head of Cybersecurity",
]
_NON_DM_TITLES = [
    "Security Analyst",
    "IT Manager",
    "Infrastructure Engineer",
    "Risk & Compliance Analyst",
]
_COMPANY_SIZE_POOL = ["180", "650", "1200", "3400", "8000"]
_SECURITY_SIGNALS_POOL = [
    "pesquisou soluções de Zero Trust nos últimos 30 dias",
    "baixou um whitepaper sobre conformidade LGPD",
    "participou de um webinar sobre detecção de ameaças com IA",
    "visitou páginas sobre resposta a incidentes",
]

_GENERIC_DOMAINS = {
    "gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "live.com",
}
_SYNTHETIC_COMPANIES = ["Acme Security", "Nimbus Tech", "Fortaleza Digital", "Vértice Sistemas"]
_DM_KEYWORDS = ("ciso", "cto", "cio", "diretor", "head", "vp", "chief", "gerente de risco")


def _seed(email: str) -> int:
    return int(hashlib.sha256(email.lower().encode()).hexdigest(), 16)


def _pick(pool: list, seed: int, shift: int):
    """Índice determinístico decorrelacionado por deslocamento de bits do seed."""
    return pool[(seed >> shift) % len(pool)]


def generate_enrichment(lead: dict) -> dict:
    email = (lead.get("email") or "").lower()
    seed = _seed(email)
    domain = email.split("@")[1] if "@" in email else "exemplo.com"

    company = lead.get("company")
    if not company:
        if domain in _GENERIC_DOMAINS:
            company = _pick(_SYNTHETIC_COMPANIES, seed, 0)
        else:
            company = domain.split(".")[0].capitalize()

    role = (lead.get("role") or "").lower()
    if role:
        is_dm = any(k in role for k in _DM_KEYWORDS)
    else:
        is_dm = ((seed >> 4) % 2) == 0
    title = _pick(_DM_TITLES if is_dm else _NON_DM_TITLES, seed, 8)

    sector = _pick(_SECTOR_POOL, seed, 16)
    company_size = _pick(_COMPANY_SIZE_POOL, seed, 24)
    signal = _pick(_SECURITY_SIGNALS_POOL, seed, 32)

    slug = (email.split("@")[0] or "lead").replace(".", "-")
    linkedin_url = f"https://linkedin.com/in/{slug}"

    summary = (
        f"{title} na {company}. Setor: {sector}. "
        f"Porte: {company_size} funcionários. "
        f"Sinal de interesse em segurança: {signal}."
    )

    return {
        "real_role": title,
        "company": company,
        "sector": sector,
        "company_size": company_size,
        "linkedin_url": linkedin_url,
        "is_decision_maker": is_dm,
        "enrichment_summary": summary,
        "source": "mock",
    }
```

- [ ] **Step 4: Rodar o teste para confirmar que passa**

Run: `cd backend && pytest tests/test_services_mocks.py -v`
Expected: PASS (5 testes)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/mocks.py backend/tests/test_services_mocks.py
git commit -m "feat(services): gerador determinístico de enrichment Apollo-shaped"
```

---

## Task 3: `services/enrichment.py` — fronteira real-vs-mock

**Files:**
- Create: `backend/app/services/enrichment.py`
- Test: `backend/tests/test_services_enrichment.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# backend/tests/test_services_enrichment.py
import pytest
from unittest.mock import patch, MagicMock


async def test_uses_mock_when_no_apollo_key():
    from app.config import settings
    from app.services.enrichment import enrich_lead_data
    with patch.object(settings, "apollo_api_key", ""):
        out = await enrich_lead_data({"email": "ciso@bank.com", "company": None, "role": "CISO"})
    assert out["source"] == "mock"
    assert out["is_decision_maker"] is True


async def test_uses_apollo_when_key_present():
    from app.config import settings
    from app.services.enrichment import enrich_lead_data

    apollo_json = {
        "person": {
            "title": "CISO",
            "seniority": "c_suite",
            "linkedin_url": "https://linkedin.com/in/real",
            "organization": {"name": "RealBank", "industry": "banking", "estimated_num_employees": 5000},
        }
    }
    fake_resp = MagicMock()
    fake_resp.json.return_value = apollo_json
    fake_resp.raise_for_status.return_value = None

    class _FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return fake_resp

    with patch.object(settings, "apollo_api_key", "real-key"), \
         patch("app.services.enrichment.httpx.AsyncClient", return_value=_FakeClient()):
        out = await enrich_lead_data({"email": "ciso@realbank.com", "company": "RealBank"})

    assert out["source"] == "apollo"
    assert out["real_role"] == "CISO"
    assert out["is_decision_maker"] is True
    assert out["company"] == "RealBank"
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

Run: `cd backend && pytest tests/test_services_enrichment.py -v`
Expected: FAIL — `No module named 'app.services.enrichment'`

- [ ] **Step 3: Implementar `enrichment.py`**

```python
# backend/app/services/enrichment.py
"""Fronteira de enriquecimento: Apollo real se a chave existir, senão mock determinístico.
Retorna um dict normalizado (SEM lead_id) — quem persiste/transita é o tool_executor."""
import httpx
from app.config import settings
from app.services.mocks import generate_enrichment

_DM_SENIORITIES = {"director", "vp", "c_suite", "owner", "partner", "founder"}


async def enrich_lead_data(lead: dict) -> dict:
    if settings.apollo_api_key:
        return await _enrich_via_apollo(lead)
    return generate_enrichment(lead)


async def _enrich_via_apollo(lead: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.apollo.io/api/v1/people/match",
            headers={"x-api-key": settings.apollo_api_key, "Content-Type": "application/json"},
            params={"email": lead["email"], "organization_name": lead.get("company")},
        )
        resp.raise_for_status()
        data = resp.json()

    person = data.get("person") or {}
    org = person.get("organization") or {}
    is_dm = person.get("seniority", "") in _DM_SENIORITIES

    return {
        "real_role": person.get("title"),
        "company": org.get("name") or lead.get("company"),
        "sector": org.get("industry"),
        "company_size": str(org.get("estimated_num_employees", "")),
        "linkedin_url": person.get("linkedin_url"),
        "is_decision_maker": is_dm,
        "enrichment_summary": (
            f"{person.get('title', 'profissional')} na {org.get('name', lead.get('company', ''))}. "
            f"Setor: {org.get('industry', 'N/A')}. "
            f"Tamanho: {org.get('estimated_num_employees', 'N/A')} funcionários."
        ),
        "source": "apollo",
    }
```

- [ ] **Step 4: Rodar o teste para confirmar que passa**

Run: `cd backend && pytest tests/test_services_enrichment.py -v`
Expected: PASS (2 testes)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/enrichment.py backend/tests/test_services_enrichment.py
git commit -m "feat(services): enrich_lead_data com fronteira Apollo/mock"
```

---

## Task 4: Wire `enrichment` em `tool_executor._enrich_lead`

**Files:**
- Modify: `backend/app/agent/tool_executor.py:50-101`
- Test: `backend/tests/test_services_enrichment.py` (adiciona um teste de wiring)

- [ ] **Step 1: Escrever o teste que falha**

Adicione ao final de `backend/tests/test_services_enrichment.py`:

```python
async def test_tool_executor_enrich_persists_and_transitions():
    """_enrich_lead chama o serviço, faz upsert e tenta a transição REGISTERED->ENRICHED."""
    from app.config import settings
    tables = {}

    def get_table(name):
        tables.setdefault(name, MagicMock())
        return tables[name]

    sb = MagicMock()
    sb.table.side_effect = get_table
    sb.rpc = MagicMock(return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data="OK"))))
    tables_lead = get_table("leads")
    tables_lead.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "email": "ciso@bank.com", "name": "Maria", "company": None,
    }
    get_table("lead_enrichment").upsert.return_value.execute.return_value = MagicMock()

    from app.agent.tool_executor import _enrich_lead
    with patch.object(settings, "apollo_api_key", ""):
        result = await _enrich_lead("lead-001", sb)

    assert "enriquecido" in result.lower()
    get_table("lead_enrichment").upsert.assert_called_once()
    sb.rpc.assert_called()  # atomic_transition_lead_stage
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && pytest tests/test_services_enrichment.py::test_tool_executor_enrich_persists_and_transitions -v`
Expected: FAIL — o `_enrich_lead` atual ainda contém a chamada `httpx` direta e o dead-end de `apollo_api_key`.

- [ ] **Step 3: Substituir `_enrich_lead`**

Em `backend/app/agent/tool_executor.py`, substitua TODA a função `_enrich_lead` (linhas 50-101) por:

```python
async def _enrich_lead(lead_id: str, sb) -> str:
    lead = await _db(lambda: sb.table("leads").select("email, name, company").eq("id", lead_id).single().execute().data)
    if not lead:
        return "Lead não encontrado"

    try:
        from app.services.enrichment import enrich_lead_data
        data = await enrich_lead_data(lead)
        enrichment = {**data, "lead_id": lead_id}

        await _db(lambda: sb.table("lead_enrichment").upsert(enrichment).execute())
        # Marca ENRICHED via o guard atômico (nunca UPDATE plano). Só REGISTERED→ENRICHED
        # é válido; se o lead já avançou, o RPC retorna ALREADY_SET/INVALID_TRANSITION
        # e o stage é corretamente preservado.
        await _db(lambda: sb.rpc("atomic_transition_lead_stage", {
            "p_lead_id": lead_id,
            "p_target_stage": "ENRICHED",
            "p_valid_from_stages": ["REGISTERED"],
        }).execute())

        return f"Lead enriquecido: {enrichment['enrichment_summary']}"
    except Exception as e:
        return f"Erro no enriquecimento: {e}"
```

Também remova o `import httpx` do topo do arquivo SE nenhuma outra função o usar após as Tasks 5 e 7 (deixe por enquanto; a Task 7 remove em definitivo).

- [ ] **Step 4: Rodar o teste e a suíte de agente**

Run: `cd backend && pytest tests/test_services_enrichment.py tests/test_agent.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/tool_executor.py backend/tests/test_services_enrichment.py
git commit -m "refactor(agent): _enrich_lead usa o serviço de enrichment (sem dead-end)"
```

---

## Task 5: `services/whatsapp.py` + wire em `tool_executor._send_whatsapp`

**Files:**
- Create: `backend/app/services/whatsapp.py`
- Modify: `backend/app/agent/tool_executor.py:148-184`
- Test: `backend/tests/test_services_whatsapp.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# backend/tests/test_services_whatsapp.py
from unittest.mock import patch, MagicMock


async def test_simulated_when_no_evolution_key():
    from app.config import settings
    from app.services.whatsapp import send_whatsapp_message

    sb = MagicMock()
    inserted = {}
    def capture_insert(row):
        inserted.update(row)
        return MagicMock(execute=MagicMock(return_value=MagicMock()))
    sb.table.return_value.insert.side_effect = capture_insert

    with patch.object(settings, "evolution_api_url", ""), \
         patch.object(settings, "evolution_api_key", ""):
        out = await send_whatsapp_message({"id": "lead-001", "phone": "+5511999"}, "Olá!", sb)

    assert out == {"simulated": True}
    assert inserted["channel"] == "WHATSAPP"
    assert inserted["status"] == "SIMULATED"
    assert inserted["body"] == "Olá!"
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && pytest tests/test_services_whatsapp.py -v`
Expected: FAIL — `No module named 'app.services.whatsapp'`

- [ ] **Step 3: Implementar `whatsapp.py`**

```python
# backend/app/services/whatsapp.py
"""Fronteira de WhatsApp: Evolution real se a chave existir, senão grava uma mensagem
SIMULATED visível no dashboard. A trava de consentimento LGPD fica no tool_executor."""
import asyncio
import httpx
from datetime import datetime, timezone
from app.config import settings


async def _db(fn):
    return await asyncio.to_thread(fn)


async def send_whatsapp_message(lead: dict, text: str, sb) -> dict:
    lead_id = lead["id"]
    now = datetime.now(timezone.utc).isoformat()

    if not settings.evolution_api_url or not settings.evolution_api_key:
        # MOCK — registra mensagem simulada (visível no dashboard como WhatsApp enviado)
        await _db(lambda: sb.table("messages").insert({
            "lead_id": lead_id,
            "channel": "WHATSAPP",
            "direction": "OUT",
            "body": text,
            "status": "SIMULATED",
            "sent_at": now,
        }).execute())
        return {"simulated": True}

    # REAL — Evolution API
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{settings.evolution_api_url}/message/sendText/{settings.evolution_instance_name}",
            headers={"apikey": settings.evolution_api_key},
            json={"number": lead["phone"], "text": text},
        )
        resp.raise_for_status()

    await _db(lambda: sb.table("messages").insert({
        "lead_id": lead_id,
        "channel": "WHATSAPP",
        "direction": "OUT",
        "body": text,
        "status": "SENT",
        "sent_at": now,
    }).execute())
    return {"sent": True}
```

- [ ] **Step 4: Substituir `_send_whatsapp` no tool_executor**

Em `backend/app/agent/tool_executor.py`, substitua a função `_send_whatsapp` (linhas 148-184) por:

```python
async def _send_whatsapp(tool_input: dict, sb) -> str:
    lead_id = tool_input["lead_id"]
    text = tool_input.get("text", "")

    lead = await _db(lambda: sb.table("leads").select("id, phone, whatsapp_consent_at").eq("id", lead_id).single().execute().data)
    if not lead:
        return "Lead não encontrado"

    # Trava de consentimento LGPD — permanece no tool_executor, antes do serviço.
    if not lead.get("whatsapp_consent_at"):
        return "Lead não optou por WhatsApp — mensagem não enviada"
    if not lead.get("phone"):
        return "Telefone não cadastrado — mensagem não enviada"

    try:
        from app.services.whatsapp import send_whatsapp_message
        result = await send_whatsapp_message(lead, text, sb)
        if result.get("simulated"):
            return f"WhatsApp SIMULADO registrado para {lead['phone']}"
        return f"WhatsApp enviado para {lead['phone']}"
    except Exception as e:
        return f"Erro WhatsApp: {e}"
```

- [ ] **Step 5: Rodar os testes**

Run: `cd backend && pytest tests/test_services_whatsapp.py tests/test_agent.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/whatsapp.py backend/app/agent/tool_executor.py backend/tests/test_services_whatsapp.py
git commit -m "feat(services): WhatsApp com mock visível (status SIMULATED)"
```

---

## Task 6: `services/meeting.py::apply_booking_created` + refactor do webhook

**Files:**
- Create: `backend/app/services/meeting.py`
- Modify: `backend/app/api/webhooks.py:71-121`
- Test: `backend/tests/test_services_meeting.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# backend/tests/test_services_meeting.py
from unittest.mock import patch, MagicMock


async def test_apply_booking_created_transitions_each_lead():
    from app.services.meeting import apply_booking_created

    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "lead-1"}, {"id": "lead-2"},
    ]
    rpc_calls = []
    def rpc(fn, params):
        rpc_calls.append((fn, params))
        return MagicMock(execute=MagicMock(return_value=MagicMock(data="OK")))
    sb.rpc = MagicMock(side_effect=rpc)

    with patch("app.services.meeting.get_supabase", return_value=sb):
        await apply_booking_created("ciso@bank.com")

    assert len(rpc_calls) == 2
    for fn, params in rpc_calls:
        assert fn == "atomic_transition_lead_stage"
        assert params["p_target_stage"] == "MEETING_SCHEDULED"
        assert params["p_valid_from_stages"] == ["ATTENDED", "NO_SHOW"]
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && pytest tests/test_services_meeting.py -v`
Expected: FAIL — `No module named 'app.services.meeting'`

- [ ] **Step 3: Implementar `apply_booking_created` em `meeting.py`**

```python
# backend/app/services/meeting.py
"""Fronteira de agendamento: Cal.com real se a chave existir, senão link simulado +
booking simulado. apply_booking_created é o núcleo de transição compartilhado com o
webhook real do Cal.com."""
import asyncio
from app.db.client import get_supabase


async def _db(fn):
    return await asyncio.to_thread(fn)


async def apply_booking_created(email: str) -> None:
    """Transita cada lead deste email ATTENDED/NO_SHOW -> MEETING_SCHEDULED.
    Núcleo compartilhado: usado pelo webhook real do Cal.com E pelo booking simulado."""
    sb = get_supabase()
    rows = await _db(lambda: sb.table("leads").select("id").eq("email", email).execute().data)
    for row in rows or []:
        await _db(lambda lid=row["id"]: sb.rpc("atomic_transition_lead_stage", {
            "p_lead_id": lid,
            "p_target_stage": "MEETING_SCHEDULED",
            "p_valid_from_stages": ["ATTENDED", "NO_SHOW"],
        }).execute())
```

- [ ] **Step 4: Refatorar o webhook para usar a função**

Em `backend/app/api/webhooks.py`, substitua o corpo do handler `calcom_webhook` a partir do parse do payload (linhas 94-121) — mantendo HMAC e 503 intactos (linhas 77-92) — por:

```python
    data = json.loads(payload)
    event_type = data.get("triggerEvent", "")

    if event_type != "BOOKING_CREATED":
        return {"received": True}

    booking = data.get("payload", {})
    attendees = booking.get("attendees") or []
    attendee_email = attendees[0].get("email", "") if attendees else ""

    if not attendee_email:
        return {"received": True}

    from app.services.meeting import apply_booking_created
    await apply_booking_created(attendee_email)
    return {"received": True}
```

Remova o `from app.db.client import get_supabase` do `calcom_webhook` se não for mais usado nesse handler (o `resend_webhook` ainda usa — verifique antes de remover o import do topo).

- [ ] **Step 5: Rodar os testes (inclui regressão do webhook)**

Run: `cd backend && pytest tests/test_services_meeting.py -v`
Expected: PASS

Verifique também que nada quebrou nos webhooks (se houver teste):
Run: `cd backend && pytest -k webhook -v`
Expected: PASS (ou "no tests ran" se não existir — aceitável)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/meeting.py backend/app/api/webhooks.py backend/tests/test_services_meeting.py
git commit -m "refactor(webhook): extrai apply_booking_created (núcleo compartilhado)"
```

---

## Task 7: `meeting.generate_meeting_link` + wire em `_schedule_meeting`

**Files:**
- Modify: `backend/app/services/meeting.py`
- Modify: `backend/app/agent/tool_executor.py:264-301` (e remove `import httpx`/`urlencode` se não usados)
- Test: `backend/tests/test_services_meeting.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicione a `backend/tests/test_services_meeting.py`:

```python
async def test_generate_meeting_link_mock_inserts_simulated_booking():
    from app.config import settings
    from app.services.meeting import generate_meeting_link

    sb = MagicMock()
    inserted = {}
    def capture_insert(row):
        inserted.update(row)
        return MagicMock(execute=MagicMock(return_value=MagicMock(data=[{"id": "job-xyz"}])))
    sb.table.return_value.insert.side_effect = capture_insert

    with patch.object(settings, "cal_api_key", ""), \
         patch.object(settings, "cal_event_type_id", ""), \
         patch("app.services.meeting.get_supabase", return_value=sb), \
         patch("app.scheduler.runner.add_job_to_scheduler") as mock_add:
        out = await generate_meeting_link({"id": "lead-1", "name": "Ana", "email": "ana@x.com"})

    assert "SIMULADO" in out["note"]
    assert out["booking_link"].startswith("https://cal.com/")
    assert inserted["job_type"] == "SIMULATED_BOOKING"
    assert inserted["status"] == "PENDING"
    mock_add.assert_called_once()
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && pytest tests/test_services_meeting.py::test_generate_meeting_link_mock_inserts_simulated_booking -v`
Expected: FAIL — `generate_meeting_link` não existe.

- [ ] **Step 3: Implementar `generate_meeting_link`**

Adicione a `backend/app/services/meeting.py` (no topo, ajuste imports):

```python
import httpx
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from app.config import settings

# Atraso curto do booking simulado — o New #4 do review confirma que não colide
# com o lock do run_agent que o criou (apply_booking_created não adquire lock).
_SIMULATED_BOOKING_DELAY_SECONDS = 30


async def generate_meeting_link(lead: dict) -> dict:
    if settings.cal_api_key and settings.cal_event_type_id:
        return await _real_meeting_link(lead)
    return await _mock_meeting_link(lead)


async def _real_meeting_link(lead: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"https://api.cal.com/v1/event-types/{settings.cal_event_type_id}",
            headers={"Authorization": f"Bearer {settings.cal_api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
    event_type = data.get("event_type", {})
    slug = event_type.get("slug", "demo-vigil")
    username = (event_type.get("team") or {}).get("slug", "vigil")
    booking_link = (
        f"https://cal.com/{username}/{slug}"
        f"?{urlencode({'name': lead['name'], 'email': lead['email']})}"
    )
    return {"booking_link": booking_link, "note": "Link real do Cal.com gerado."}


async def _mock_meeting_link(lead: dict) -> dict:
    booking_link = (
        f"https://cal.com/vigil/demo-vigil"
        f"?{urlencode({'name': lead['name'], 'email': lead['email']})}"
    )
    run_at = datetime.now(timezone.utc) + timedelta(seconds=_SIMULATED_BOOKING_DELAY_SECONDS)
    sb = get_supabase()
    result = await _db(lambda: sb.table("scheduled_jobs").insert({
        "lead_id": lead["id"],
        "job_type": "SIMULATED_BOOKING",
        "run_at": run_at.isoformat(),
        "condition": {},
        "status": "PENDING",
        "event_id": lead.get("event_id"),  # anulável; preenche p/ views por-evento do dashboard
    }).execute())
    job_id = result.data[0]["id"]
    from app.scheduler.runner import add_job_to_scheduler
    add_job_to_scheduler(job_id, run_at)
    return {
        "booking_link": booking_link,
        "note": "[SIMULADO] reunião será confirmada automaticamente em segundos.",
    }
```

- [ ] **Step 4: Substituir `_schedule_meeting` no tool_executor**

Em `backend/app/agent/tool_executor.py`, substitua a função `_schedule_meeting` (linhas 264-301) por:

```python
async def _schedule_meeting(tool_input: dict, sb) -> str:
    lead_id = tool_input["lead_id"]

    lead = await _db(lambda: sb.table("leads").select("id, name, email, stage, event_id").eq("id", lead_id).single().execute().data)
    if not lead:
        return "Lead não encontrado"

    try:
        from app.services.meeting import generate_meeting_link
        result = await generate_meeting_link(lead)
        # Stage NÃO é alterado aqui. MEETING_SCHEDULED é setado por apply_booking_created
        # (webhook real do Cal.com OU booking simulado), origens ATTENDED/NO_SHOW.
        return (
            f"Link de agendamento gerado: {result['booking_link']}. {result['note']} "
            f"Stage permanece '{lead['stage']}' até a confirmação."
        )
    except Exception as e:
        return f"Erro ao gerar link de agendamento: {e}"
```

Agora remova do topo de `tool_executor.py` os imports não mais usados: `import httpx` e `from urllib.parse import urlencode` (todas as chamadas externas migraram para `services/`). Mantenha `import asyncio`, `import json`, `from datetime import ...`.

- [ ] **Step 5: Rodar os testes**

Run: `cd backend && pytest tests/test_services_meeting.py tests/test_agent.py -v`
Expected: PASS

Confirme que `httpx` não é mais referenciado no tool_executor:
Run: `cd backend && python -c "import app.agent.tool_executor"`
Expected: sem erro de import.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/meeting.py backend/app/agent/tool_executor.py backend/tests/test_services_meeting.py
git commit -m "feat(services): meeting link com booking simulado; tool_executor sem httpx"
```

---

## Task 8: Branch `SIMULATED_BOOKING` em `scheduler/jobs.py`

**Files:**
- Modify: `backend/app/scheduler/jobs.py:34-36` (inserir branch após obter `lead_id`)
- Test: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicione a `backend/tests/test_scheduler.py`:

```python
async def test_simulated_booking_calls_apply_and_skips_agent():
    """Job SIMULATED_BOOKING transita via apply_booking_created e NÃO chama o agente."""
    job = {**_JOB, "job_type": "SIMULATED_BOOKING"}
    mock_sb = _make_sb(job=job, lead_stage="ATTENDED")
    # leads.email lookup para resolver o email do lead
    mock_sb.table("leads").select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "stage": "ATTENDED", "email": "ana@x.com",
    }

    mock_run_agent = AsyncMock()
    mock_apply = AsyncMock()
    with patch("app.scheduler.jobs.get_supabase", return_value=mock_sb), \
         patch("app.scheduler.jobs.run_agent", mock_run_agent), \
         patch("app.services.meeting.apply_booking_created", mock_apply):
        from app.scheduler.jobs import check_and_run_job
        await check_and_run_job("job-001")

    mock_apply.assert_called_once_with("ana@x.com")
    mock_run_agent.assert_not_called()
    update_calls = str(mock_sb.table("scheduled_jobs").update.call_args_list)
    assert "DONE" in update_calls
```

Nota: `_make_sb` já mocka `leads.select(...).single()`. Como o branch usa `select("email")`, o teste sobrescreve o `.data` para incluir `email`.

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && pytest tests/test_scheduler.py::test_simulated_booking_calls_apply_and_skips_agent -v`
Expected: FAIL — o branch ainda não existe; cai em `run_agent`.

- [ ] **Step 3: Inserir o branch**

Em `backend/app/scheduler/jobs.py`, logo após a linha `lead_id = job["lead_id"]` (linha 36), antes do fetch do lead/condições, insira:

```python
    # Booking simulado (modo demo): transita via o MESMO caminho do webhook real do
    # Cal.com. Não passa pelo agente nem pelas condições — é resolução direta de stage.
    if job["job_type"] == "SIMULATED_BOOKING":
        lead_row = await _db(lambda: sb.table("leads").select("email").eq("id", lead_id).single().execute().data)
        email = (lead_row or {}).get("email")
        if email:
            from app.services.meeting import apply_booking_created
            await apply_booking_created(email)
        await _db(lambda: sb.table("scheduled_jobs").update({"status": "DONE"}).eq("id", job_id).execute())
        return
```

- [ ] **Step 4: Rodar os testes do scheduler**

Run: `cd backend && pytest tests/test_scheduler.py -v`
Expected: PASS (todos, incluindo o novo)

- [ ] **Step 5: Commit**

```bash
git add backend/app/scheduler/jobs.py backend/tests/test_scheduler.py
git commit -m "feat(scheduler): branch SIMULATED_BOOKING via apply_booking_created"
```

---

## Task 9: Sentinela `LOCK_BUSY` em `orchestrator.py`

**Files:**
- Modify: `backend/app/agent/orchestrator.py:13-16`
- Modify: `backend/tests/test_agent.py` (2 testes existentes mudam a asserção)

- [ ] **Step 1: Atualizar os testes existentes (que vão falhar com a mudança)**

Em `backend/tests/test_agent.py`, nos testes `test_run_agent_aborts_when_locked` e `test_run_agent_aborts_when_lock_not_acquired`, troque a asserção final:

De:
```python
    assert "abortando" in result
```
Para:
```python
    from app.agent.orchestrator import LOCK_BUSY
    assert result == LOCK_BUSY
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && pytest tests/test_agent.py::test_run_agent_aborts_when_locked -v`
Expected: FAIL — `LOCK_BUSY` ainda não existe / retorno atual é a string "abortando".

- [ ] **Step 3: Adicionar o sentinela e retorná-lo**

Em `backend/app/agent/orchestrator.py`, adicione antes de `run_agent` (após os imports, linha 11):

```python
# Sentinela inequívoco para "lock já segurado por outra execução".
# check_and_run_job trata isso como contenção (re-enfileira), não como falha.
LOCK_BUSY = "LOCK_BUSY"
```

E na função `run_agent`, troque (linhas 14-16):
```python
    acquired = await acquire_lock(lead_id)
    if not acquired:
        return f"Agent já em execução para lead {lead_id} — abortando"
```
Por:
```python
    acquired = await acquire_lock(lead_id)
    if not acquired:
        return LOCK_BUSY
```

- [ ] **Step 4: Rodar a suíte de agente**

Run: `cd backend && pytest tests/test_agent.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/orchestrator.py backend/tests/test_agent.py
git commit -m "refactor(agent): sentinela LOCK_BUSY para contenção de lock"
```

---

## Task 10: Re-enfileiramento por contenção de lock com teto

**Files:**
- Modify: `backend/app/scheduler/jobs.py:84-88` (bloco try em torno de `run_agent`)
- Test: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Escrever os testes que falham**

Adicione a `backend/tests/test_scheduler.py`:

```python
async def test_lock_busy_reenqueues_without_retry_increment():
    """run_agent retornando LOCK_BUSY re-enfileira (PENDING) sem incrementar retry_count."""
    from app.agent.orchestrator import LOCK_BUSY
    job = {**_JOB, "contention_count": 0}
    mock_sb = _make_sb(job=job, lead_stage="ENRICHED")

    with patch("app.scheduler.jobs.get_supabase", return_value=mock_sb), \
         patch("app.scheduler.jobs.run_agent", AsyncMock(return_value=LOCK_BUSY)), \
         patch("app.scheduler.runner.add_job_to_scheduler") as mock_add:
        from app.scheduler.jobs import check_and_run_job
        await check_and_run_job("job-001")

    update_calls = str(mock_sb.table("scheduled_jobs").update.call_args_list)
    assert "contention_count" in update_calls
    assert "PENDING" in update_calls
    assert "DONE" not in update_calls
    assert "retry_count" not in update_calls
    mock_add.assert_called_once()


async def test_lock_busy_fails_after_max_contention():
    """Atingido o teto de contenção, o job vai para FAILED (sem loop infinito)."""
    from app.agent.orchestrator import LOCK_BUSY
    job = {**_JOB, "contention_count": 5}  # já no teto
    mock_sb = _make_sb(job=job, lead_stage="ENRICHED")

    with patch("app.scheduler.jobs.get_supabase", return_value=mock_sb), \
         patch("app.scheduler.jobs.run_agent", AsyncMock(return_value=LOCK_BUSY)), \
         patch("app.scheduler.runner.add_job_to_scheduler") as mock_add:
        from app.scheduler.jobs import check_and_run_job
        await check_and_run_job("job-001")

    update_calls = str(mock_sb.table("scheduled_jobs").update.call_args_list)
    assert "FAILED" in update_calls
    mock_add.assert_not_called()
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && pytest tests/test_scheduler.py::test_lock_busy_reenqueues_without_retry_increment -v`
Expected: FAIL — hoje `run_agent` retornando LOCK_BUSY ainda marca DONE.

- [ ] **Step 3: Adicionar a constante e o tratamento**

Em `backend/app/scheduler/jobs.py`, no topo (após os imports), adicione:

```python
from app.agent.orchestrator import run_agent, LOCK_BUSY

# Teto de re-tentativas por contenção de lock — evita loop infinito se o lock
# ficar preso (ex.: heartbeat renovando uma execução lenta).
MAX_CONTENTION = 5
```

(Remova o `from app.agent.orchestrator import run_agent` antigo do topo, substituído pela linha acima.)

Substitua o bloco `try` (linhas 84-88, a parte do sucesso) por:

```python
    try:
        result = await run_agent(lead_id, job["job_type"])

        if result == LOCK_BUSY:
            # Contenção, não falha: re-enfileira com atraso curto, sem mexer em retry_count.
            contention = (job.get("contention_count") or 0) + 1
            if contention <= MAX_CONTENTION:
                next_run = datetime.now(timezone.utc) + timedelta(seconds=30)
                await _db(lambda: sb.table("scheduled_jobs").update({
                    "status": "PENDING",
                    "contention_count": contention,
                    "run_at": next_run.isoformat(),
                }).eq("id", job_id).execute())
                from app.scheduler.runner import add_job_to_scheduler
                add_job_to_scheduler(job_id, next_run)
            else:
                await _db(lambda: sb.table("scheduled_jobs").update({
                    "status": "FAILED",
                    "error": "lock preso: máximo de contenções atingido",
                }).eq("id", job_id).execute())
            return

        await _db(
            lambda: sb.table("scheduled_jobs").update({"status": "DONE"}).eq("id", job_id).execute()
        )
    except Exception as e:
```

(O `except Exception as e:` e o bloco de retry exponencial abaixo dele permanecem inalterados.)

- [ ] **Step 4: Rodar os testes do scheduler**

Run: `cd backend && pytest tests/test_scheduler.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add backend/app/scheduler/jobs.py backend/tests/test_scheduler.py
git commit -m "feat(scheduler): re-enfileira em contenção de lock com teto anti-loop"
```

---

## Task 11: Flag `demo_fast_forward` em `config.py`

**Files:**
- Modify: `backend/app/config.py:22`
- Test: `backend/tests/test_config_validator.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicione a `backend/tests/test_config_validator.py`:

```python
def test_demo_fast_forward_defaults_false():
    from app.config import settings
    assert settings.demo_fast_forward is False
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && pytest tests/test_config_validator.py::test_demo_fast_forward_defaults_false -v`
Expected: FAIL — `AttributeError: ... no attribute 'demo_fast_forward'`

- [ ] **Step 3: Adicionar a flag**

Em `backend/app/config.py`, após a linha `stale_job_threshold_hours: int = 2` (linha 22), adicione:

```python
    demo_fast_forward: bool = False  # comprime a régua (dias→minutos) para a demo
```

- [ ] **Step 4: Rodar o teste**

Run: `cd backend && pytest tests/test_config_validator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/tests/test_config_validator.py
git commit -m "feat(config): flag demo_fast_forward"
```

---

## Task 12: Fast-forward em `prompts._build_regua`

**Files:**
- Modify: `backend/app/agent/prompts.py:120-147`
- Test: `backend/tests/test_prompts_regua.py` (novo)

- [ ] **Step 1: Escrever o teste que falha**

```python
# backend/tests/test_prompts_regua.py
from datetime import datetime, timezone
from unittest.mock import patch
from app.agent.prompts import _build_regua


def test_fast_forward_uses_minutes_from_now():
    from app.config import settings
    with patch.object(settings, "demo_fast_forward", True):
        plan = _build_regua("NEW_LEAD_REGISTERED", None, "REGISTERED", False, False)
    today = datetime.now(timezone.utc).date().isoformat()
    assert today in plan          # âncoras são hoje + minutos
    assert "2026-08" not in plan  # NÃO usa as datas-calendário do evento


def test_normal_mode_uses_event_calendar_dates():
    from app.config import settings
    with patch.object(settings, "demo_fast_forward", False):
        plan = _build_regua("NEW_LEAD_REGISTERED", None, "REGISTERED", False, False)
    assert "2026-08" in plan      # t14/t10/... derivados do evento (15 Ago 2026)
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && pytest tests/test_prompts_regua.py -v`
Expected: FAIL no `test_fast_forward_uses_minutes_from_now` (hoje sempre usa datas-calendário).

- [ ] **Step 3: Aplicar o fast-forward**

Em `backend/app/agent/prompts.py`, dentro de `_build_regua`, substitua o bloco que calcula as âncoras (linhas 129-147, de `now = datetime.now(...)` até a definição de `d14`) por:

```python
    from app.config import settings

    now = datetime.now(timezone.utc)

    # Fallback da data do evento se não vier do DB (15 Ago 2026 09:00 BRT = 12:00 UTC)
    if not event_date:
        event_date = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)

    if settings.demo_fast_forward:
        # Demo: comprime dias→minutos. A LÓGICA não muda — só a escala de tempo.
        # Passo de 2 min dá folga sobre o lock de agente (spec §7).
        t14 = _iso(now + timedelta(minutes=2))
        t10 = _iso(now + timedelta(minutes=4))
        t7  = _iso(now + timedelta(minutes=6))
        t3  = _iso(now + timedelta(minutes=8))
        t1  = _iso(now + timedelta(minutes=10))
        t0  = _iso(now + timedelta(minutes=12))
        d3  = _iso(now + timedelta(minutes=2))
        d7  = _iso(now + timedelta(minutes=4))
        d14 = _iso(now + timedelta(minutes=6))
    else:
        # Pré-evento: âncoras relativas à data do evento
        t14 = _iso(event_date - timedelta(days=14))
        t10 = _iso(event_date - timedelta(days=10))
        t7  = _iso(event_date - timedelta(days=7))
        t3  = _iso(event_date - timedelta(days=3))
        t1  = _iso(event_date - timedelta(days=1))
        t0  = _iso(event_date.replace(hour=6, minute=0))  # 06:00 UTC = 03:00 BRT
        # Pós-evento: âncoras relativas a agora
        d3  = _iso(now + timedelta(days=3))
        d7  = _iso(now + timedelta(days=7))
        d14 = _iso(now + timedelta(days=14))
```

- [ ] **Step 4: Rodar o teste + suíte de prompts/agente**

Run: `cd backend && pytest tests/test_prompts_regua.py tests/test_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/prompts.py backend/tests/test_prompts_regua.py
git commit -m "feat(regua): DEMO_FAST_FORWARD comprime âncoras (lógica intacta)"
```

---

## Task 13: Endpoint `POST /{id}/simulate-engagement`

**Files:**
- Modify: `backend/app/api/leads.py` (novo endpoint após `mark_no_show`, ~linha 121)
- Test: `backend/tests/test_leads_api.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicione a `backend/tests/test_leads_api.py`:

```python
def test_simulate_engagement_sets_opened(client, mock_supabase):
    # última msg OUT/EMAIL existe
    (mock_supabase.return_value.table.return_value
        .select.return_value.eq.return_value.eq.return_value.eq.return_value
        .order.return_value.limit.return_value.execute.return_value.data) = [{"id": "msg-1"}]
    (mock_supabase.return_value.table.return_value
        .update.return_value.eq.return_value.is_.return_value.execute.return_value) = MagicMock()

    resp = client.post(
        "/api/leads/lead-1/simulate-engagement",
        json={"opened": True, "clicked": False},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_simulate_engagement_requires_api_key(client):
    resp = client.post("/api/leads/lead-1/simulate-engagement", json={"opened": True})
    assert resp.status_code in (401, 403)


def test_simulate_engagement_404_when_no_message(client, mock_supabase):
    (mock_supabase.return_value.table.return_value
        .select.return_value.eq.return_value.eq.return_value.eq.return_value
        .order.return_value.limit.return_value.execute.return_value.data) = []
    resp = client.post(
        "/api/leads/lead-1/simulate-engagement",
        json={"opened": True},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && pytest tests/test_leads_api.py -k simulate_engagement -v`
Expected: FAIL — rota inexistente (404 para todos, inclusive o "requires_api_key").

- [ ] **Step 3: Implementar o endpoint**

Em `backend/app/api/leads.py`, após a função `mark_no_show` (linha ~120), adicione:

```python
@router.post("/{lead_id}/simulate-engagement", dependencies=[Security(_require_api_key)])
async def simulate_engagement(lead_id: str, payload: dict):
    """Demo: marca a última mensagem OUT/EMAIL do lead como aberta/clicada, espelhando
    o webhook do Resend. Permite ao avaliador dirigir o branching da régua na janela
    comprimida. Idempotente: só seta o que ainda é nulo (igual ao webhook)."""
    opened = bool(payload.get("opened"))
    clicked = bool(payload.get("clicked"))
    sb = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    msgs = await asyncio.to_thread(lambda: (
        sb.table("messages")
        .select("id")
        .eq("lead_id", lead_id)
        .eq("direction", "OUT")
        .eq("channel", "EMAIL")
        .order("sent_at", desc=True)
        .limit(1)
        .execute()
        .data
    ))
    if not msgs:
        raise HTTPException(status_code=404, detail="Nenhum email enviado para este lead")

    msg_id = msgs[0]["id"]

    # Um clique implica uma abertura — seta opened_at se opened OU clicked.
    if opened or clicked:
        await asyncio.to_thread(lambda: sb.table("messages")
            .update({"opened_at": now}).eq("id", msg_id).is_("opened_at", "null").execute())
    if clicked:
        await asyncio.to_thread(lambda: sb.table("messages")
            .update({"clicked_at": now}).eq("id", msg_id).is_("clicked_at", "null").execute())

    return {"status": "ok", "message_id": msg_id, "opened": opened, "clicked": clicked}
```

- [ ] **Step 4: Rodar os testes**

Run: `cd backend && pytest tests/test_leads_api.py -k simulate_engagement -v`
Expected: PASS (3 testes)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/leads.py backend/tests/test_leads_api.py
git commit -m "feat(api): POST /leads/{id}/simulate-engagement (demo branching)"
```

---

## Task 14: Frontend — proxy + `api.ts` `simulateEngagement`

**Files:**
- Create: `frontend/app/api/leads/[id]/simulate-engagement/route.ts`
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Criar o proxy autenticado**

Crie `frontend/app/api/leads/[id]/simulate-engagement/route.ts` (espelha o proxy `/checkin`, mas repassa o corpo JSON):

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase-server'

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const supabase = await createSupabaseServerClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return NextResponse.json({ error: 'Não autorizado' }, { status: 401 })
  }

  const backendUrl = process.env.BACKEND_API_URL
  const backendKey = process.env.BACKEND_API_KEY
  if (!backendUrl || !backendKey) {
    return NextResponse.json({ error: 'Configuração ausente' }, { status: 500 })
  }

  let body = {}
  try { body = await request.json() } catch { /* corpo vazio é aceitável */ }

  const res = await fetch(`${backendUrl}/api/leads/${params.id}/simulate-engagement`, {
    method: 'POST',
    headers: { 'X-API-Key': backendKey, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
```

- [ ] **Step 2: Adicionar `simulateEngagement` ao `api.ts`**

Em `frontend/lib/api.ts`, ao final do arquivo, adicione:

```typescript
export async function simulateEngagement(
  lead_id: string,
  opts: { opened?: boolean; clicked?: boolean }
) {
  const res = await fetch(`/api/leads/${lead_id}/simulate-engagement`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(opts),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
```

- [ ] **Step 3: Verificar lint + build**

Run: `cd frontend && npm run lint`
Expected: sem erros nos arquivos novos.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/api/leads/[id]/simulate-engagement/route.ts frontend/lib/api.ts
git commit -m "feat(frontend): proxy + cliente simulateEngagement"
```

---

## Task 15: Frontend — botões no `LeadDrawer`

**Files:**
- Modify: `frontend/components/dashboard/LeadDrawer.tsx`

- [ ] **Step 1: Importar as funções de API**

No topo de `frontend/components/dashboard/LeadDrawer.tsx`, após o import de tipos (linha 3), adicione:

```typescript
import { checkinLead, markNoShow, simulateEngagement } from '@/lib/api'
```

- [ ] **Step 2: Adicionar handlers (padrão Realtime — dispara e aguarda o WebSocket)**

Dentro do componente, logo após `handleRunAgent` (linha ~72), adicione:

```typescript
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  async function runAction(fn: () => Promise<unknown>, ok: string) {
    setActionMsg(null)
    try {
      await fn()
      // Padrão do dashboard: o Realtime (FunnelBoard) propaga a mudança de stage/engajamento.
      setActionMsg(ok)
    } catch {
      setActionMsg('Falha na ação (verifique se está logado).')
    }
  }
```

- [ ] **Step 3: Adicionar os botões na UI**

No bloco "Ação do Agente" (após o `{agentResult && ...}` que fecha na linha ~139), adicione um novo bloco de controles de demo:

```tsx
          <div className="mt-3 grid grid-cols-2 gap-1.5">
            <button
              onClick={() => runAction(() => checkinLead(lead.id), 'Check-in registrado — aguarde o Realtime')}
              className="bg-brand-teal/10 text-brand-teal text-[11px] font-bold py-2 rounded-md hover:bg-brand-teal/20 transition-colors"
            >
              ✓ Check-in
            </button>
            <button
              onClick={() => runAction(() => markNoShow(lead.id), 'No-show registrado — aguarde o Realtime')}
              className="bg-red-50 text-red-500 text-[11px] font-bold py-2 rounded-md hover:bg-red-100 transition-colors"
            >
              ✗ No-show
            </button>
            <button
              onClick={() => runAction(() => simulateEngagement(lead.id, { opened: true }), 'Abertura simulada')}
              className="bg-brand-bg text-brand-muted text-[11px] font-bold py-2 rounded-md hover:bg-brand-border/40 transition-colors"
            >
              ✉ Simular abertura
            </button>
            <button
              onClick={() => runAction(() => simulateEngagement(lead.id, { clicked: true }), 'Clique simulado')}
              className="bg-brand-bg text-brand-muted text-[11px] font-bold py-2 rounded-md hover:bg-brand-border/40 transition-colors"
            >
              🔗 Simular clique
            </button>
          </div>
          {actionMsg && (
            <p className="text-[10px] mt-1.5 text-center font-semibold text-brand-muted">{actionMsg}</p>
          )}
```

- [ ] **Step 4: Verificar lint + build**

Run: `cd frontend && npm run lint && npm run build`
Expected: build conclui sem erros de tipo.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/dashboard/LeadDrawer.tsx
git commit -m "feat(frontend): controles de demo (check-in/no-show/simular engajamento)"
```

---

## Task 16: Frontend — badge SIMULATED / WhatsApp no histórico

**Files:**
- Modify: `frontend/lib/types.ts:33-39`
- Modify: `frontend/components/dashboard/FunnelBoard.tsx:128-149` (select de mensagens)
- Modify: `frontend/components/dashboard/LeadDrawer.tsx` (render do status)

- [ ] **Step 1: Estender o tipo `Message`**

Em `frontend/lib/types.ts`, substitua o tipo `Message` (linhas 33-39) por:

```typescript
export type Message = {
  lead_id: string
  sent_at: string
  opened_at: string | null
  clicked_at: string | null
  subject: string | null
  channel?: string | null
  status?: string | null
}
```

- [ ] **Step 2: Incluir channel/status no fetch de mensagens**

Em `frontend/components/dashboard/FunnelBoard.tsx`, no `fetchMessages`, atualize os dois `.select(...)` para incluir as colunas novas:

- O select principal (linha 132): `.select('lead_id, sent_at, opened_at, clicked_at, subject, channel, status')`
- O select de fallback (linha 145): `.select('lead_id, sent_at, opened_at, clicked_at, channel, status')`

E no `.map` do fallback (linha 149), mantenha o spread (já inclui channel/status):
```typescript
            return ((data ?? []) as Omit<Message, 'subject'>[]).map(m => ({ ...m, subject: null }))
```

- [ ] **Step 3: Renderizar o badge no drawer**

Em `frontend/components/dashboard/LeadDrawer.tsx`, atualize `msgStatus` (linhas 33-38) para reconhecer WhatsApp/SIMULATED:

```typescript
function msgStatus(msg: Message): string {
  if (msg.channel === 'WHATSAPP') {
    return msg.status === 'SIMULATED' ? '📱 WhatsApp (simulado)' : '📱 WhatsApp enviado'
  }
  const parts: string[] = []
  if (msg.opened_at) parts.push('✓ Aberto')
  if (msg.clicked_at) parts.push('✓ Link clicado')
  return parts.length > 0 ? parts.join(' · ') : 'Enviado (sem abertura registrada)'
}
```

- [ ] **Step 4: Verificar lint + build**

Run: `cd frontend && npm run lint && npm run build`
Expected: build sem erros.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/types.ts frontend/components/dashboard/FunnelBoard.tsx frontend/components/dashboard/LeadDrawer.tsx
git commit -m "feat(frontend): badge WhatsApp/SIMULATED no histórico de mensagens"
```

---

## Task 17: Documentação — `.env.example` + `CLAUDE.md`

**Files:**
- Modify: `backend/.env.example`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Documentar o modo demo no `.env.example`**

Em `backend/.env.example`, adicione um bloco (após as chaves opcionais existentes):

```
# ── MODO DEMO ───────────────────────────────────────────────────────────────
# Deixe APOLLO_API_KEY, EVOLUTION_API_KEY e CAL_API_KEY VAZIAS para ativar os
# mocks automaticamente (enriquecimento determinístico, WhatsApp simulado,
# booking simulado). Email (Resend) e LLM (Claude/OpenAI) seguem reais.
# DEMO_FAST_FORWARD comprime a régua (dias→minutos) para testar o funil em minutos.
DEMO_FAST_FORWARD=false
```

- [ ] **Step 2: Documentar no `CLAUDE.md`**

Em `CLAUDE.md`, na seção de invariantes (após o bloco de multi-provider LLM), adicione:

```markdown
**Modo demo (mocks por ausência de chave):** Apollo, Cal.com e WhatsApp/Evolution
degradam para mock quando a chave correspondente está vazia — mesmo padrão de
`detect_provider()`. As fronteiras vivem em `app/services/` (`enrichment.py`,
`whatsapp.py`, `meeting.py`); o `tool_executor` só orquestra (sem `httpx`). O
enriquecimento mock (`services/mocks.py`) é determinístico por email e "Apollo-shaped"
(o `sector` é uma chave de `_APOLLO_TO_SECTOR`). WhatsApp simulado grava `messages`
com `status="SIMULATED"`. O funil fecha via `apply_booking_created` — o MESMO núcleo
do webhook real do Cal.com — disparado por um job `SIMULATED_BOOKING`. Email e LLM
são sempre reais.

**Régua acelerada:** `DEMO_FAST_FORWARD=true` comprime as âncoras em `_build_regua`
(dias→minutos); a lógica/condições/ordem não mudam. Na janela comprimida, o webhook
de abertura/clique do Resend não chega a tempo — use `POST /leads/{id}/simulate-engagement`
(e os botões do dashboard) para dirigir o branching por engajamento.

**Resiliência de lock do scheduler:** `run_agent` retorna o sentinela `LOCK_BUSY`
quando o lock do lead está ocupado; `check_and_run_job` re-enfileira o job (não conta
como `retry_count`) com teto `MAX_CONTENTION` (→ `FAILED` se exceder), evitando loop
infinito e perda silenciosa de jobs.
```

- [ ] **Step 3: Rodar a suíte backend inteira (regressão final)**

Run: `cd backend && pytest -v`
Expected: PASS (toda a suíte, incluindo os testes novos das Tasks 2-13)

- [ ] **Step 4: Commit**

```bash
git add backend/.env.example CLAUDE.md
git commit -m "docs: modo demo, régua acelerada e resiliência de lock"
```

---

## Verificação final (após todas as tasks)

- [ ] Backend: `cd backend && pytest -v` → tudo verde
- [ ] Frontend: `cd frontend && npm run lint && npm run build` → sem erros
- [ ] Migração `003_demo_mode.sql` aplicada ao Supabase (Task 1, Step 2-3)
- [ ] Smoke manual: subir backend+frontend com as 3 chaves vazias e `DEMO_FAST_FORWARD=true`; cadastrar um lead; verificar no dashboard: REGISTERED→ENRICHED, email de boas-vindas, WhatsApp simulado; clicar Check-in; ver a régua pós-evento fechar em MEETING_SCHEDULED.
