# Confirmação de Presença por Clique no Email — Design

**Data:** 2026-06-01
**Status:** Aprovado para planejamento
**Contexto:** O botão "Confirmar presença" dos emails hoje aponta apenas para a landing
(`FRONTEND_URL`) e **não tem ação por trás** — o lead clica e o funil não muda. Não
existe endpoint que mova `ENRICHED → CONFIRMED` a partir do clique. A transição só
acontecia indiretamente, num passo posterior da régua (`WARMUP_T10`), dependente do
webhook de clique do Resend. Resultado observado: lead clica e nada acontece.

---

## 1. Objetivo

Dar ação real ao botão de confirmação dos emails: o lead clica → abre uma página
`/confirmar` → o sistema move o lead `ENRICHED → CONFIRMED` na hora e dispara um email
imediato de confirmação (com a agenda). Isso destrava a régua de CONFIRMED (agenda T-3,
logística T-1, lembrete T-0). Espelha o fluxo de confirmação LGPD (`/deletion-confirm`)
que já existe e funciona.

---

## 2. Decisões travadas (do brainstorming)

1. **Token:** HMAC-SHA256 **stateless** do `lead_id` (sem tabela, **sem expiração**).
2. **Fluxo:** página frontend `/confirmar?token=` que **auto-confirma ao abrir** (POST
   no backend), espelhando `/deletion-confirm`. POST evita confirmação acidental por
   prefetch de cliente de email.
3. **Efeito:** transição `ENRICHED → CONFIRMED` via RPC atômica **+ dispara o agente**
   (`run_agent(lead_id, "LEAD_CONFIRMED")`) para um email imediato.
4. **Régua do `LEAD_CONFIRMED`:** reusa o template `agenda` (não cria template novo).
5. **Botões:** só os 3 convites de confirmação (`welcome`, `confirmation_request`,
   `confirmation_followup`) apontam para `/confirmar?token=`; os demais seguem na landing.

---

## 3. Token assinado (módulo neutro `app/utils/tokens.py` — NOVO)

> **Por que módulo novo (evita import circular):** `resend_service.send_email` precisa
> gerar o `confirm_url` (logo, precisa de `_sign_confirm_token`). Se o token morasse em
> `api/leads.py`, teríamos o ciclo `leads → orchestrator → tool_executor → resend_service
> → leads`. Colocar em `app/utils/tokens.py` (sem dependências de app, só `hmac`/`settings`)
> quebra o ciclo. Tanto `resend_service` quanto `api/leads` importam de lá.

```python
# app/utils/tokens.py
import hmac, hashlib
from app.config import settings

def _confirm_secret() -> str:
    return settings.confirm_token_secret or settings.api_key

def sign_confirm_token(lead_id: str) -> str:
    """HMAC-SHA256 stateless do lead_id. Sem tabela, sem expiração."""
    sig = hmac.new(_confirm_secret().encode(), lead_id.encode(), hashlib.sha256).hexdigest()
    return f"{lead_id}.{sig}"

def verify_confirm_token(token: str) -> str | None:
    """Valida via hmac.compare_digest; retorna lead_id se ok, senão None."""
    if not token or "." not in token:
        return None
    lead_id, _, sig = token.rpartition(".")
    if not lead_id:
        return None
    expected = hmac.new(_confirm_secret().encode(), lead_id.encode(), hashlib.sha256).hexdigest()
    return lead_id if hmac.compare_digest(sig, expected) else None
```

- **Secret:** nova env var **opcional** `confirm_token_secret: str = ""` em `config.py`,
  com **fallback para `api_key`** (sempre presente) → zero config obrigatória nova.
- Formato: `"{lead_id}.{hmac_hexdigest}"`. Uso de `rpartition(".")` (não `split`) para
  robustez. `compare_digest` para comparação constante.
- Stateless: nada gravado; o link no email carrega o token.
- **Rotação de chave:** se `confirm_token_secret` (ou `api_key`, no fallback) mudar, **todos
  os tokens de confirmação em trânsito invalidam** — o lead veria "link inválido" e
  confirmaria pelo próximo email da régua. Aceitável; documentar no CLAUDE.md.

---

## 4. Endpoint de confirmação (backend)

`POST /api/leads/confirm` — **público** (o lead não tem `X-API-Key`; o token é a
credencial), **rate-limited `10/minute`** (padrão dos endpoints públicos). Corpo:
`{"token": "..."}`.

Fluxo:
1. `verify_confirm_token(token)` (de `app/utils/tokens.py`) → inválido/ausente → **404** "Link inválido".
2. `atomic_transition_lead_stage(lead_id, "CONFIRMED", ["ENRICHED"])` —
   RPC atômica (nunca UPDATE cru; invariante do projeto).
3. Roteia pelo retorno:
   - `OK` → dispara `run_agent(lead_id, "LEAD_CONFIRMED")` em background → `{"status": "confirmed"}`.
   - `ALREADY_SET` → `{"status": "already_confirmed"}` — **idempotente, NÃO redispara o agente**.
   - `INVALID_TRANSITION` (já em ATTENDED/NO_SHOW/etc.) → `{"status": "already_processed"}`.
   - `NOT_FOUND` → 404.

**Idempotência (anti-prefetch + duplo clique):** a página confirma via POST (prefetchers
fazem GET e não rodam JS → não disparam). E `ALREADY_SET` não redispara o agente → abrir
o link 2× não duplica emails.

`valid_from` é apenas `["ENRICHED"]`: a máquina de estados (`state_machine.py`) NÃO
permite `REGISTERED → CONFIRMED` (REGISTERED só vai para ENRICHED). Na prática o lead já
está ENRICHED quando o welcome chega (o enrichment roda em segundos, antes do email). Se
por acaso ainda estiver REGISTERED, a RPC retorna `INVALID_TRANSITION` → a página mostra
"não foi possível confirmar agora, tente pelo próximo email" (tratado como o ramo
`already_processed`).

---

## 5. Régua do trigger `LEAD_CONFIRMED` (`prompts._build_regua`)

Novo plano no dict `plans`:

```
"LEAD_CONFIRMED": '''
PASSO 1 — Verificar engajamento
  Chame check_engagement().

PASSO 2 — Agradecer a confirmação e enviar a agenda
  Envie send_pre_event_msg("confirmation_agenda") com custom_note que AGRADECE a
  confirmação de presença e destaca 2-3 sessões mais relevantes para o cargo/setor.
  Ângulo: "presença confirmada — aqui está sua agenda personalizada".
'''
```

- **NOVO template `confirmation_agenda`** (não reusa `agenda`). Motivo: o corpo do
  `agenda` diz literalmente "O Vigil Summit acontece em **3 dias**" e "Até **sábado**" —
  factualmente errado num disparo **imediato** pós-confirmação (o evento pode estar a
  14 dias). O `confirmation_agenda` tem copy adequada ("Sua presença está confirmada!
  Reservei a agenda que faz mais sentido para você"), sem âncora temporal fixa, mesmos
  placeholders (`name`, `sector_content`, `custom_note`) + a programação. Entra em
  `resend_service.TEMPLATES` (texto) **e** `email_templates.TEMPLATE_BODIES_HTML` (HTML),
  preservando a paridade validada por teste. Adicionar `"confirmation_agenda"` ao enum de
  `send_pre_event_msg` em `tools.py`.
- **Não duplica com `AGENDA_T3`:** o AGENDA_T3 (condição `only_if_stage=CONFIRMED`,
  T-3) é a véspera; este é o envio imediato na confirmação. Em produção são momentos bem
  distintos. **No `DEMO_FAST_FORWARD`** a janela é comprimida (AGENDA_T3 em ~now+8min), então
  o `confirmation_agenda` imediato e o `agenda` do T-3 podem chegar com poucos minutos de
  diferença — esperado na demo (a régua inteira roda em ~12min); o copy distinto evita que
  pareçam idênticos.
- **Destrava a régua existente:** ao virar CONFIRMED, os jobs já agendados
  `AGENDA_T3`/`LOGISTICS_T1`/`DAY_T0` (bloqueados por `only_if_stage=CONFIRMED`) passam a
  disparar nas suas datas. A confirmação só destrava — não recria nem mexe nesses jobs.
- **Interação com `WARMUP_T10`:** esse passo já tentava mover o lead para CONFIRMED ao
  detectar clique. Com a confirmação direta, o lead provavelmente já estará CONFIRMED quando
  o WARMUP_T10 rodar; a RPC é idempotente (`ALREADY_SET`), então **mantém-se** o WARMUP_T10
  como está — é um fallback inofensivo para quem clicou mas não chegou pela página.

---

## 6. Frontend

### Página `frontend/app/confirmar/page.tsx`
Espelha `frontend/app/deletion-confirm/page.tsx`:
- Lê `?token=` via `useSearchParams` dentro de `<Suspense>` (evita o crash de static render).
- No `useEffect`: **POST** para o proxy `/api/leads/confirm` com `{token}`. Estados:
  `confirmando…` → `✓ Presença confirmada!` / `Presença já confirmada` / `Link inválido`.
- Identidade visual Vigil (card navy/teal, igual ao login/deletion-confirm).

### Proxy `frontend/app/api/leads/confirm/route.ts`
- **Público** (NÃO checa sessão Supabase — o token HMAC é a credencial; é o mesmo modelo
  do proxy `deletion-request/confirm`, o único outro proxy de leads público).
- Repassa o body JSON ao backend `POST {BACKEND_API_URL}/api/leads/confirm`. **Não** envia
  `X-API-Key` (endpoint é público no backend). Retorna o status do backend.

---

## 7. Wire dos botões nos emails (`email_templates.py` + `resend_service.py`)

- `render_html(template_key, ctx, cta_url=None, confirm_url=None)` ganha o parâmetro
  `confirm_url`. Em `_resolve_cta`: se o template é um **convite de confirmação**
  (`welcome`, `confirmation_request`, `confirmation_followup`) e `confirm_url` está
  presente, o href do CTA é o `confirm_url`; senão, mantém o comportamento atual (landing).
- `send_email`: gera `confirm_url = f"{settings.frontend_url}/confirmar?token={sign_confirm_token(lead_id)}"`
  (import de `app.utils.tokens`) e passa a `render_html`. A geração é best-effort
  (try/except → cai no comportamento atual se falhar; nunca bloqueia o envio).
- Os demais templates landing (`warmup`, `vip_briefing`, `agenda`) seguem apontando para a
  landing — inalterados.

---

## 8. Config

- `config.py`: adiciona `confirm_token_secret: str = ""` (opcional; fallback para `api_key`).
- `.env.example`: documenta a var como opcional.

---

## 9. Estratégia de testes (TDD)

Backend (`./venv/Scripts/python.exe -m pytest tests/ -q`):
- **Token:** `verify_confirm_token(sign_confirm_token(id)) == id`; token adulterado → `None`;
  token malformado (sem `.`) → `None`; string vazia → `None`.
- **Endpoint:** token válido + lead ENRICHED → 200 `confirmed`, transição chamada, agente
  disparado (mock de `run_agent`); token inválido → 404; segunda chamada (lead já CONFIRMED,
  RPC retorna ALREADY_SET) → `already_confirmed` e `run_agent` NÃO chamado de novo.
- **Régua:** `_build_regua("LEAD_CONFIRMED", ...)` contém `send_pre_event_msg` e
  `confirmation_agenda`.
- **Template novo:** `confirmation_agenda` existe em `resend_service.TEMPLATES` E em
  `email_templates.TEMPLATE_BODIES_HTML` (paridade); renderiza com o ctx mínimo sem KeyError;
  o copy NÃO contém "3 dias" nem "sábado".
- **Email/CTA:** `render_html("welcome", ctx, confirm_url="https://x/confirmar?token=abc")` →
  o href do CTA é essa URL; sem `confirm_url` → mantém landing.
- **Regressão:** suíte existente verde (contrato de `send_email`/`render_html` preservado
  via defaults).

Frontend: `npx tsc --noEmit` limpo; a página segue o padrão do `deletion-confirm`.

---

## 10. Arquivos afetados

**Criar:**
- `backend/app/utils/tokens.py` — `sign_confirm_token`/`verify_confirm_token` (módulo neutro).
- `backend/app/utils/__init__.py` (se ainda não existir o pacote).
- `frontend/app/confirmar/page.tsx`
- `frontend/app/api/leads/confirm/route.ts`
- `backend/tests/test_confirm_presence.py`

**Modificar:**
- `backend/app/api/leads.py` — endpoint `POST /confirm` (importa de `app.utils.tokens`).
- `backend/app/agent/prompts.py` — plano `LEAD_CONFIRMED` no `_build_regua`.
- `backend/app/agent/tools.py` — adiciona `"confirmation_agenda"` ao enum de `send_pre_event_msg`.
- `backend/app/services/resend_service.py` — novo template `confirmation_agenda` em `TEMPLATES`;
  `send_email` gera e passa o `confirm_url` (import de `app.utils.tokens`).
- `backend/app/services/email_templates.py` — `render_html`/`_resolve_cta` aceitam `confirm_url`;
  novo miolo `confirmation_agenda` em `TEMPLATE_BODIES_HTML`.
- `backend/app/config.py` — `confirm_token_secret`.
- `backend/.env.example` — documenta a var.
- `CLAUDE.md` — nota sobre o fluxo de confirmação por clique + rotação de chave invalida tokens.

**Não muda:** RPC de transição, dashboard, demais templates, a régua existente
(só é destravada). O `WARMUP_T10` permanece (fallback idempotente).

---

## 11. Riscos & mitigações

- **Prefetch de email confirmando sem intenção:** mitigado — confirmação via POST (JS),
  não GET; prefetchers não executam.
- **Duplo clique / reenvio:** idempotente — `ALREADY_SET` não redispara o agente.
- **Geração de token falha:** try/except → email sai com CTA landing (comportamento atual).
- **Duplicação de email (LEAD_CONFIRMED vs AGENDA_T3):** momentos distintos (imediato vs
  T-3); `custom_note` diferencia o ângulo.
- **Segredo do token:** usa `api_key` por fallback (já secreto). Se `confirm_token_secret`
  for definido depois, tokens antigos invalidam — aceitável (lead reenvia/reclica).
