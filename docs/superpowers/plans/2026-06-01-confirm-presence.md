# Confirmação de Presença por Clique — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) ou superpowers:executing-plans. Steps usam checkbox (`- [ ]`).

**Goal:** Dar ação ao botão "Confirmar presença" dos emails: clique → página `/confirmar?token=` → POST backend → move `ENRICHED → CONFIRMED` (RPC atômica) → dispara o agente (`LEAD_CONFIRMED`) para um email imediato de agenda.

**Architecture:** Token HMAC stateless (módulo neutro `app/utils/tokens.py`, evita import circular). Endpoint público `POST /api/leads/confirm` (token é a credencial). Novo template `confirmation_agenda` (o `agenda` tem âncoras temporais fixas erradas para disparo imediato). Frontend espelha o fluxo `/deletion-confirm` existente.

**Tech Stack:** FastAPI, Supabase RPC, pytest, Next.js 14 (App Router).

**Spec:** `docs/superpowers/specs/2026-06-01-confirm-presence-design.md`

**Como rodar testes:** de `backend/`, `./venv/Scripts/python.exe -m pytest tests/ -q` (o `python` global não tem pytest). Frontend: de `frontend/`, `npx tsc --noEmit` (não há ESLint; `npm run lint` trava).

**Fatos verificados no código:**
- `state_machine.py`: `ENRICHED → CONFIRMED` é válido; `REGISTERED → CONFIRMED` NÃO.
- `_resolve_cta(template_key, cta_url)` (email_templates.py:122) e `render_html(template_key, ctx, cta_url=None)` (linha 291) — assinaturas atuais.
- `CTA_MAP` tem `welcome`/`confirmation_request`/`confirmation_followup` com `dest:"landing"`.
- Padrão da página: `frontend/app/deletion-confirm/page.tsx` (useSearchParams + Suspense + POST no useEffect).
- Padrão do proxy público: `frontend/app/api/leads/deletion-request/confirm/route.ts` (NÃO checa sessão; só repassa). Middleware cobre só `/dashboard/*`.
- `config.py`: `api_key: str = ""` (linha 21), `frontend_url`. `atomic_transition_lead_stage` retorna `OK`/`ALREADY_SET`/`INVALID_TRANSITION`/`NOT_FOUND`.

---

## Task 1: Módulo de token `app/utils/tokens.py`

**Files:**
- Create: `backend/app/utils/__init__.py`, `backend/app/utils/tokens.py`
- Test: `backend/tests/test_confirm_presence.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# backend/tests/test_confirm_presence.py
from app.utils.tokens import sign_confirm_token, verify_confirm_token


def test_token_roundtrip():
    lid = "abc-123-uuid"
    assert verify_confirm_token(sign_confirm_token(lid)) == lid


def test_token_tampered_returns_none():
    tok = sign_confirm_token("abc-123-uuid")
    assert verify_confirm_token(tok + "x") is None


def test_token_malformed_returns_none():
    assert verify_confirm_token("no-dot") is None
    assert verify_confirm_token("") is None
    assert verify_confirm_token(None) is None
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_confirm_presence.py -q`
Expected: FAIL — `No module named 'app.utils'`.

- [ ] **Step 3: Criar `backend/app/utils/__init__.py` (vazio) e `backend/app/utils/tokens.py`**

```python
# backend/app/utils/tokens.py
"""Token HMAC stateless para confirmação de presença por clique no email.
Módulo neutro (só hmac + settings) para evitar import circular entre
resend_service (gera o link) e api/leads (valida)."""
import hashlib
import hmac

from app.config import settings


def _confirm_secret() -> str:
    return settings.confirm_token_secret or settings.api_key


def sign_confirm_token(lead_id: str) -> str:
    """HMAC-SHA256 stateless do lead_id. Sem tabela, sem expiração."""
    sig = hmac.new(_confirm_secret().encode(), lead_id.encode(), hashlib.sha256).hexdigest()
    return f"{lead_id}.{sig}"


def verify_confirm_token(token: str | None) -> str | None:
    """Valida via compare_digest; retorna lead_id se ok, senão None."""
    if not token or "." not in token:
        return None
    lead_id, _, sig = token.rpartition(".")
    if not lead_id:
        return None
    expected = hmac.new(_confirm_secret().encode(), lead_id.encode(), hashlib.sha256).hexdigest()
    return lead_id if hmac.compare_digest(sig, expected) else None
```

- [ ] **Step 4: Adicionar `confirm_token_secret` ao `config.py`**

Em `backend/app/config.py`, após a linha `api_key: str = ""` (linha 21), adicione:
```python
    confirm_token_secret: str = ""  # secret do token de confirmação; fallback p/ api_key
```

- [ ] **Step 5: Rodar para confirmar que passa**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_confirm_presence.py -q`
Expected: PASS (3 testes).

- [ ] **Step 6: Commit**
```bash
git add backend/app/utils/ backend/app/config.py backend/tests/test_confirm_presence.py
git commit -m "feat(confirm): token HMAC stateless em app/utils/tokens.py"
```

---

## Task 2: Endpoint `POST /api/leads/confirm`

**Files:**
- Modify: `backend/app/api/leads.py`
- Test: `backend/tests/test_confirm_presence.py`

- [ ] **Step 1: Adicionar os testes que falham** (append a `test_confirm_presence.py`)

```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

TEST_API_KEY = "test-key-vigil"


@pytest.fixture(autouse=True)
def _patch_key(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "api_key", TEST_API_KEY)


@pytest.fixture
def client():
    with patch("app.scheduler.runner.start_scheduler"):
        from app.main import app
        return TestClient(app)


def test_confirm_valid_token_confirms_and_runs_agent(client):
    from app.utils.tokens import sign_confirm_token
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value.data = "OK"
    ran = []
    async def fake_run(lead_id, trigger):
        ran.append((lead_id, trigger))
    with patch("app.api.leads.get_supabase", return_value=sb), \
         patch("app.agent.orchestrator.run_agent", fake_run):
        tok = sign_confirm_token("lead-1")
        resp = client.post("/api/leads/confirm", json={"token": tok})
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"
    # RPC chamada com CONFIRMED e origem ENRICHED
    args = str(sb.rpc.call_args)
    assert "CONFIRMED" in args and "ENRICHED" in args


def test_confirm_invalid_token_404(client):
    resp = client.post("/api/leads/confirm", json={"token": "garbage"})
    assert resp.status_code == 404


def test_confirm_already_set_does_not_rerun_agent(client):
    from app.utils.tokens import sign_confirm_token
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value.data = "ALREADY_SET"
    ran = []
    async def fake_run(lead_id, trigger):
        ran.append((lead_id, trigger))
    with patch("app.api.leads.get_supabase", return_value=sb), \
         patch("app.agent.orchestrator.run_agent", fake_run):
        tok = sign_confirm_token("lead-1")
        resp = client.post("/api/leads/confirm", json={"token": tok})
    assert resp.status_code == 200
    assert resp.json()["status"] == "already_confirmed"
    assert ran == []  # agente NÃO redisparado
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_confirm_presence.py -k confirm_valid -q`
Expected: FAIL — rota inexistente (404 com detail de not found, não "confirmed").

- [ ] **Step 3: Adicionar o endpoint em `backend/app/api/leads.py`**

No topo, adicione o import (junto aos outros):
```python
from app.utils.tokens import verify_confirm_token
```

Adicione o endpoint ANTES do `@router.post("/{lead_id}/checkin"...)` (rotas literais antes das paramétricas por clareza; o FastAPI casa literais primeiro de qualquer forma):

```python
@router.post("/confirm")
@limiter.limit("10/minute")
async def confirm_presence(request: Request, payload: dict, background_tasks: BackgroundTasks):
    """Público: o lead confirma presença clicando no botão do email. O token HMAC
    (do email) é a credencial — não usa X-API-Key. Move ENRICHED→CONFIRMED e dispara
    o agente para o email imediato de agenda. Idempotente."""
    token = (payload or {}).get("token")
    lead_id = verify_confirm_token(token)
    if not lead_id:
        raise HTTPException(status_code=404, detail="Link inválido")

    sb = get_supabase()
    result = await asyncio.to_thread(lambda: sb.rpc("atomic_transition_lead_stage", {
        "p_lead_id": lead_id,
        "p_target_stage": "CONFIRMED",
        "p_valid_from_stages": ["ENRICHED"],
    }).execute())
    outcome = result.data

    if outcome == "OK":
        from app.agent.orchestrator import run_agent
        background_tasks.add_task(run_agent, lead_id, "LEAD_CONFIRMED")
        return {"status": "confirmed"}
    if outcome == "ALREADY_SET":
        return {"status": "already_confirmed"}
    if outcome == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    # INVALID_TRANSITION (já em ATTENDED/NO_SHOW/etc.)
    return {"status": "already_processed"}
```

Nota: o `limiter` exige o parâmetro `request: Request` na assinatura (padrão slowapi, como em `create_lead`). `Request`, `HTTPException`, `BackgroundTasks`, `asyncio`, `get_supabase`, `limiter` já estão importados no arquivo.

- [ ] **Step 4: Rodar os testes**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_confirm_presence.py -q`
Expected: PASS (6 testes). Rode também a suíte de leads p/ garantir que a rota nova não quebrou nada: `./venv/Scripts/python.exe -m pytest tests/test_leads_api.py -q` → PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/api/leads.py backend/tests/test_confirm_presence.py
git commit -m "feat(confirm): endpoint POST /api/leads/confirm (público, idempotente)"
```

---

## Task 3: Template `confirmation_agenda` (texto + HTML)

**Files:**
- Modify: `backend/app/services/resend_service.py`, `backend/app/services/email_templates.py`, `backend/app/agent/tools.py`
- Test: `backend/tests/test_email_templates.py`

- [ ] **Step 1: Adicionar o teste que falha** (append a `test_email_templates.py`)

```python
def test_confirmation_agenda_exists_and_no_temporal_anchor():
    from app.services.resend_service import TEMPLATES
    from app.services.email_templates import TEMPLATE_BODIES_HTML, render_html
    assert "confirmation_agenda" in TEMPLATES
    assert "confirmation_agenda" in TEMPLATE_BODIES_HTML
    html = render_html("confirmation_agenda", _min_ctx())
    assert "Vigil" in html
    # copy de disparo imediato — NÃO pode dizer "3 dias" nem "sábado"
    body = TEMPLATES["confirmation_agenda"]["body"]
    assert "3 dias" not in body and "sábado" not in body
```

(`_min_ctx()` já existe no arquivo — inclui `name`, `sector_content`, `custom_note`.)

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_email_templates.py::test_confirmation_agenda_exists_and_no_temporal_anchor -q`
Expected: FAIL — chave não existe.

- [ ] **Step 3: Adicionar o template TEXTO em `resend_service.py`**

No dict `TEMPLATES`, após a entrada `"agenda"`, adicione:
```python
    "confirmation_agenda": {
        "subject": "Presença confirmada, {name} — sua agenda do Vigil Summit",
        "body": """Olá {name},

Sua presença no Vigil Summit está confirmada! Obrigada por reservar seu lugar.

Selecionei as sessões mais relevantes para o seu perfil:

{sector_content}

{custom_note}

Programação completa:
→ 8h30 — Credenciamento e café
→ 9h00 — Abertura: IA e o novo perímetro de segurança
→ 10h30 — Track 1: Zero Trust | Track 2: IA em Segurança | Track 3: Conformidade
→ 12h30 — Almoço executivo
→ 14h00 — Mesas redondas por setor
→ 16h30 — Encerramento e networking

Nos vemos lá,
Ana Beatriz Costa
Account Executive, Vigil.AI"""
    },
```

- [ ] **Step 4: Adicionar o miolo HTML em `email_templates.py`**

No dict `TEMPLATE_BODIES_HTML`, adicione (reusa as constantes `_P`, `_EYEBROW`, `_SECTOR_BOX` já definidas):
```python
    "confirmation_agenda": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}">Sua presença no Vigil Summit está <strong>confirmada</strong>! Obrigada por reservar seu lugar.</p>'
        f'<p style="{_EYEBROW}">Sessões selecionadas para você</p>'
        f'<div style="{_SECTOR_BOX}">{{sector_content}}</div>'
        f'<p style="{_P}">{{custom_note}}</p>'
        f'<p style="{_EYEBROW}">Programação</p>'
        f'<ul style="margin:0 0 16px;padding-left:20px;">'
        f'<li style="margin-bottom:6px;">8h30 — Credenciamento e café</li>'
        f'<li style="margin-bottom:6px;">9h00 — Abertura: IA e o novo perímetro de segurança</li>'
        f'<li style="margin-bottom:6px;">10h30 — Tracks: Zero Trust · IA em Segurança · Conformidade</li>'
        f'<li style="margin-bottom:6px;">12h30 — Almoço executivo</li>'
        f'<li style="margin-bottom:6px;">14h00 — Mesas redondas por setor</li>'
        f'<li style="margin-bottom:6px;">16h30 — Encerramento e networking</li>'
        f'</ul>'
    ),
```

- [ ] **Step 5: Adicionar `confirmation_agenda` ao enum de `send_pre_event_msg` em `tools.py`**

Em `backend/app/agent/tools.py`, na tool `send_pre_event_msg`, no `enum` do campo `template`, adicione `"confirmation_agenda"` à lista (junto a "welcome", "agenda", etc.).

- [ ] **Step 6: Rodar os testes de template**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_email_templates.py -q`
Expected: PASS (incl. o novo + `test_all_17_templates_render` que itera o dict).

- [ ] **Step 7: Commit**
```bash
git add backend/app/services/resend_service.py backend/app/services/email_templates.py backend/app/agent/tools.py backend/tests/test_email_templates.py
git commit -m "feat(email): template confirmation_agenda (sem âncora temporal fixa)"
```

---

## Task 4: Régua `LEAD_CONFIRMED` em `_build_regua`

**Files:**
- Modify: `backend/app/agent/prompts.py`
- Test: `backend/tests/test_prompts_regua.py`

- [ ] **Step 1: Adicionar o teste que falha** (append a `test_prompts_regua.py`)

```python
def test_lead_confirmed_plan_uses_confirmation_agenda():
    plan = _build_regua("LEAD_CONFIRMED", None, "CONFIRMED", False, False)
    assert "send_pre_event_msg" in plan
    assert "confirmation_agenda" in plan
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_prompts_regua.py::test_lead_confirmed_plan_uses_confirmation_agenda -q`
Expected: FAIL — cai no fallback genérico (não contém "confirmation_agenda").

- [ ] **Step 3: Adicionar o plano no dict `plans`**

Em `backend/app/agent/prompts.py`, dentro do dict `plans` de `_build_regua`, adicione a entrada (perto dos outros planos pré-evento):
```python
        "LEAD_CONFIRMED": """
PASSO 1 — Verificar engajamento
  Chame check_engagement().

PASSO 2 — Agradecer a confirmação e enviar a agenda
  Envie send_pre_event_msg("confirmation_agenda") com custom_note que AGRADECE a
  confirmação de presença e destaca 2-3 sessões mais relevantes para o cargo/setor do lead.
  Ângulo: "presença confirmada — aqui está sua agenda personalizada". NÃO repita o tom de
  cobrança dos emails de confirmação; este é um email de boas-vindas pós-confirmação.
""",
```

- [ ] **Step 4: Rodar os testes**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_prompts_regua.py tests/test_agent.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/agent/prompts.py backend/tests/test_prompts_regua.py
git commit -m "feat(regua): plano LEAD_CONFIRMED (agradece + agenda imediata)"
```

---

## Task 5: Wire do `confirm_url` em `render_html` + `send_email`

**Files:**
- Modify: `backend/app/services/email_templates.py`, `backend/app/services/resend_service.py`
- Test: `backend/tests/test_email_templates.py`, `backend/tests/test_send_email_html.py`

- [ ] **Step 1: Adicionar os testes que falham**

Em `test_email_templates.py`:
```python
def test_render_confirm_url_used_for_confirmation_invites(monkeypatch):
    from app.services import email_templates
    from app.services.email_templates import render_html
    monkeypatch.setattr(email_templates.settings, "frontend_url", "https://x.ai")
    html = render_html("welcome", _min_ctx(), confirm_url="https://x.ai/confirmar?token=abc")
    assert "https://x.ai/confirmar?token=abc" in html


def test_render_confirm_url_ignored_without_it(monkeypatch):
    from app.services import email_templates
    from app.services.email_templates import render_html
    monkeypatch.setattr(email_templates.settings, "frontend_url", "https://x.ai")
    html = render_html("welcome", _min_ctx())  # sem confirm_url → CTA aponta landing
    assert "https://x.ai" in html
    assert "/confirmar?token=" not in html
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_email_templates.py -k confirm_url -q`
Expected: FAIL — `render_html` não aceita `confirm_url`.

- [ ] **Step 3: Modificar `_resolve_cta` e `render_html` em `email_templates.py`**

Substitua `_resolve_cta` (linhas 122-130) por uma versão que conhece os convites de confirmação:
```python
# Templates cujo CTA é um convite de confirmação de presença.
_CONFIRM_INVITES = {"welcome", "confirmation_request", "confirmation_followup"}


def _resolve_cta(template_key: str, cta_url: str | None, confirm_url: str | None) -> dict | None:
    spec = CTA_MAP.get(template_key)
    if not spec:
        return None
    if template_key in _CONFIRM_INVITES and confirm_url and confirm_url.startswith(("http://", "https://")):
        url = confirm_url
    elif spec["dest"] == "calcom" and cta_url and cta_url.startswith(("http://", "https://")):
        url = cta_url
    else:
        url = settings.frontend_url
    return {"label": spec["label"], "url": url, "variant": spec["variant"]}
```

Atualize `render_html` (linha 291) para aceitar e repassar `confirm_url`:
```python
def render_html(template_key: str, ctx: dict, cta_url: str | None = None, confirm_url: str | None = None) -> str:
    """Monta o email HTML completo: escape do ctx → miolo → shell com CTA + chip."""
    escaped = {k: _esc(v) for k, v in ctx.items()}
    if "event_highlights" in escaped:
        lines = [ln.strip().lstrip("→").strip() for ln in escaped["event_highlights"].split("\n") if ln.strip()]
        escaped["event_highlights"] = "".join(
            f'<li style="margin-bottom:6px;">{ln}</li>' for ln in lines
        )
    inner_tpl = TEMPLATE_BODIES_HTML.get(template_key, "<p>{custom_note}</p>")
    inner = inner_tpl.format(**escaped)
    cta = _resolve_cta(template_key, cta_url, confirm_url)
    chip = _perso_chip(ctx.get("role"), ctx.get("sector"))
    return _shell(inner, cta, chip)
```

- [ ] **Step 4: Modificar `send_email` em `resend_service.py` para gerar e passar o `confirm_url`**

No topo, adicione o import:
```python
from app.utils.tokens import sign_confirm_token
```

Onde hoje há `html_body = render_html(template_key, ctx, cta_url)` (dentro do try best-effort), troque por:
```python
        confirm_url = f"{settings.frontend_url}/confirmar?token={sign_confirm_token(lead['id'])}"
        html_body = render_html(template_key, ctx, cta_url, confirm_url)
```
(O `lead["id"]` está disponível em `send_email` — confirme; é usado no insert de `messages`. O bloco já é try/except: se algo falhar, cai para texto-only, como hoje.)

- [ ] **Step 5: Rodar os testes (templates + send_email + regressão)**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_email_templates.py tests/test_send_email_html.py -q`
Expected: PASS. Depois a suíte inteira: `./venv/Scripts/python.exe -m pytest tests/ -q` → tudo verde.

- [ ] **Step 6: Commit**
```bash
git add backend/app/services/email_templates.py backend/app/services/resend_service.py backend/tests/
git commit -m "feat(email): CTA de convites de confirmação aponta p/ /confirmar?token="
```

---

## Task 6: Frontend — proxy público + página `/confirmar`

**Files:**
- Create: `frontend/app/api/leads/confirm/route.ts`, `frontend/app/confirmar/page.tsx`

- [ ] **Step 1: Criar o proxy público** `frontend/app/api/leads/confirm/route.ts`

Espelha `deletion-request/confirm/route.ts` (público, sem sessão, só repassa):
```typescript
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  const backendUrl = process.env.BACKEND_API_URL
  if (!backendUrl) {
    return NextResponse.json({ error: 'Configuração ausente' }, { status: 500 })
  }
  const body = await request.json()
  const res = await fetch(`${backendUrl}/api/leads/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
```

- [ ] **Step 2: Criar a página** `frontend/app/confirmar/page.tsx`

Espelha `deletion-confirm/page.tsx` (useSearchParams + Suspense + POST no useEffect):
```tsx
'use client'
import { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'

type Status = 'loading' | 'success' | 'already' | 'error'

function ConfirmContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [status, setStatus] = useState<Status>('loading')

  useEffect(() => {
    if (!token) { setStatus('error'); return }
    fetch('/api/leads/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
      .then(async r => {
        if (r.status !== 200) { setStatus('error'); return }
        const data = await r.json().catch(() => ({}))
        setStatus(data.status === 'confirmed' ? 'success' : 'already')
      })
      .catch(() => setStatus('error'))
  }, [token])

  return (
    <div className="min-h-screen bg-brand-bg flex items-center justify-center px-4">
      <div className="bg-white rounded-[20px] border border-slate-200 shadow-[0_16px_40px_rgba(15,42,52,0.08)] p-8 w-full max-w-md text-center">
        <p className="font-black text-base tracking-wide text-brand-navy mb-1">
          VIGIL<span className="text-brand-teal">.AI</span>
        </p>
        <h1 className="font-bold text-xl text-brand-text mb-5">Confirmação de Presença</h1>
        {status === 'loading' && <p className="text-slate-500 text-sm">Confirmando sua presença…</p>}
        {status === 'success' && (
          <div>
            <p className="text-brand-green font-semibold mb-2">Presença confirmada! ✓</p>
            <p className="text-slate-500 text-sm">Sua vaga no Vigil Summit está garantida. Em breve você recebe a agenda personalizada por email.</p>
          </div>
        )}
        {status === 'already' && (
          <div>
            <p className="text-brand-teal font-semibold mb-2">Presença já confirmada ✓</p>
            <p className="text-slate-500 text-sm">Você já está confirmado no Vigil Summit. Nos vemos lá!</p>
          </div>
        )}
        {status === 'error' && (
          <div>
            <p className="text-red-600 font-semibold mb-2">Não foi possível confirmar.</p>
            <p className="text-slate-500 text-sm">O link pode estar inválido. Use o botão do email mais recente, ou fale com a gente.</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function ConfirmPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-brand-bg flex items-center justify-center">
        <p className="text-slate-500 text-sm">Carregando…</p>
      </div>
    }>
      <ConfirmContent />
    </Suspense>
  )
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: TSC_EXIT=0 (sem erros).

- [ ] **Step 4: Commit**
```bash
git add frontend/app/api/leads/confirm/route.ts frontend/app/confirmar/page.tsx
git commit -m "feat(frontend): página /confirmar + proxy público de confirmação"
```

---

## Task 7: Docs — `.env.example` + `CLAUDE.md`

**Files:**
- Modify: `backend/.env.example`, `CLAUDE.md`

- [ ] **Step 1: `.env.example`** — adicionar (perto de `API_KEY`):
```
# Secret do token de confirmação de presença (opcional; fallback para API_KEY).
# ATENÇÃO: trocar este valor invalida os links de confirmação já enviados.
CONFIRM_TOKEN_SECRET=
```

- [ ] **Step 2: `CLAUDE.md`** — adicionar nota (após a seção de emails HTML):
```markdown
**Confirmação de presença por clique:** o botão "Confirmar presença" dos emails de
convite (`welcome`, `confirmation_request`, `confirmation_followup`) aponta para
`{FRONTEND_URL}/confirmar?token=<hmac>`. A página faz POST em `/api/leads/confirm`
(público, token HMAC stateless de `app/utils/tokens.py` é a credencial), que move
`ENRICHED→CONFIRMED` via `atomic_transition_lead_stage` e dispara `run_agent(LEAD_CONFIRMED)`
→ email `confirmation_agenda` imediato. Idempotente (ALREADY_SET não redispara o agente).
O token usa `CONFIRM_TOKEN_SECRET` (fallback `API_KEY`) — trocar a secret invalida links
em trânsito. NÃO reusar o template `agenda` para esse disparo (ele tem âncoras "3 dias/
sábado" fixas); usar `confirmation_agenda`.
```

- [ ] **Step 3: Regressão final + commit**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/ -q` → tudo verde.
Run: `cd frontend && npx tsc --noEmit` → limpo.
```bash
git add backend/.env.example CLAUDE.md
git commit -m "docs: fluxo de confirmação de presença por clique"
```

---

## Verificação final (após todas as tasks)

- [ ] `cd backend && ./venv/Scripts/python.exe -m pytest tests/ -q` → tudo verde
- [ ] `cd frontend && npx tsc --noEmit` → sem erros
- [ ] Smoke (após redeploy do Railway): cadastrar lead → abrir o email de boas-vindas → clicar "Confirmar presença" → página mostra "Presença confirmada ✓" → no dashboard o lead vai para CONFIRMED e chega o email `confirmation_agenda`.
