# Modo Demo & Mocks de Integrações Externas — Design

**Data:** 2026-05-31
**Status:** Aprovado para planejamento
**Contexto:** Case técnico Vigil.AI (vaga AI Engineer, Pareto). O time avaliador precisa
testar o funil ponta-a-ponta **sem chaves de APIs pagas**. Hoje, sem `APOLLO_API_KEY`
(e análogos), o funil trava num beco-sem-saída (`"Apollo.io não configurado"`).

---

## 1. Objetivo

Permitir que o funil inteiro — captação → enriquecimento → régua pré-evento →
follow-up pós-evento → reunião agendada — rode de forma demonstrável e repetível,
mantendo **email (Resend) e LLM (Claude) reais** e **simulando** as três integrações
externas que exigem conta/chave: **Apollo (enriquecimento)**, **Evolution
(WhatsApp)** e **Cal.com (agendamento)**.

Princípio condutor: **degradação graciosa por serviço**, espelhando o padrão
`detect_provider()` já existente em `llm/provider.py` — ausência da chave ativa o
mock; presença da chave usa a API real. **Mesmo código** roda em modo demo e em
produção, sem reescrita.

### Fluxo de demonstração (resultado esperado)

```
Formulário (nome, email, telefone, consentimentos)
  → POST /api/leads → REGISTERED → run_agent("NEW_LEAD_REGISTERED")
       PASSO 1: enrich_lead()              → MOCK determinístico → grava lead_enrichment, ENRICHED
       PASSO 2: send_pre_event_msg("welcome") → Resend REAL (boas-vindas personalizado)
       PASSO 3: agenda a régua (jobs)      → datas comprimidas se DEMO_FAST_FORWARD
  → triggers da régua disparam email REAL + send_whatsapp() MOCK (visível no dashboard)
  → pós-evento: schedule_meeting() MOCK → link fake + booking simulado → MEETING_SCHEDULED
```

---

## 2. Decisões travadas (do brainstorming)

1. **Escopo do mock:** Apollo, Cal.com **e** WhatsApp/Evolution. Email + LLM reais.
2. **Ativação:** ausência da chave do serviço → mock automático (por serviço, não global).
3. **Dados de enriquecimento:** determinístico por `email`/domínio + pools curados do ICP de ciberssegurança.
4. **WhatsApp:** dentro do escopo do funil; mockado e visível no dashboard (`status=SIMULATED`).
5. **Régua na demo:** flag `DEMO_FAST_FORWARD` comprime os intervalos (dias → minutos) sem mudar a lógica.
6. **Fechar o funil:** mock dispara um **webhook simulado** pelo mesmo caminho de transição da produção (preserva o invariante "stage de reunião só pelo webhook").

---

## 3. Arquitetura — camada `services/`

Hoje `agent/tool_executor.py` faz chamadas `httpx` inline (Apollo, Evolution,
Cal.com) misturadas com orquestração. Vamos extrair essas chamadas para uma fina
camada de serviços, espelhando a organização de `app/llm/`. Cada serviço expõe
**uma função de fronteira** que decide real-vs-mock internamente; o
`tool_executor` volta a ser **só orquestração** (sem `httpx`).

```
app/services/
  resend_service.py   (já existe — email real, inalterado)
  enrichment.py       (NOVO) enrich_lead_data(lead) -> dict
  whatsapp.py         (NOVO) send_whatsapp_message(lead, text) -> dict
  meeting.py          (NOVO) generate_meeting_link(lead) -> dict
                             apply_booking_created(email) -> None   (núcleo extraído do webhook)
  mocks.py            (NOVO) geradores determinísticos + flags de modo
```

### Detecção real-vs-mock

Cada função de serviço começa com a mesma decisão, no espírito de `detect_provider()`:

```python
def _use_real_apollo() -> bool:
    return bool(settings.apollo_api_key)
```

| Função | Real (com chave) | Mock (sem chave) |
|---|---|---|
| `enrichment.enrich_lead_data(lead)` | Apollo `POST /api/v1/people/match` | gerador determinístico |
| `whatsapp.send_whatsapp_message(lead, text)` | Evolution `sendText` | grava `messages` `status=SIMULATED` |
| `meeting.generate_meeting_link(lead)` | Cal.com `GET /event-types/{id}` | link fake + agenda `SIMULATED_BOOKING` |
| `meeting.apply_booking_created(email)` | núcleo de transição compartilhado | idem (chamado pelo job simulado) |

**Importante:** as funções de serviço retornam dados normalizados (dict) e **não**
escrevem stage nem fazem upsert — o `tool_executor` continua dono dessas escritas
(upsert em `lead_enrichment`, `atomic_transition_lead_stage`). Isso mantém o
contrato atual do `tool_executor` e a fronteira de segurança do `lead_id`
autoritativo intacta. A única exceção é `apply_booking_created`, que encapsula a
transição de stage porque é o núcleo compartilhado com o webhook real.

---

## 4. Mock de enriquecimento (`services/mocks.py`)

### Requisitos

- **Determinístico:** `seed = int(sha256(email.lower()).hexdigest(), 16)`. Mesmo
  email ⇒ mesmo perfil, sempre. (Demo repetível e documentável.)
- **Apollo-shaped:** o campo `sector` DEVE sair no vocabulário de indústria do
  Apollo (ex.: `"financial services"`, `"computer software"`, `"hospital & health care"`,
  `"manufacturing"`) para casar com o mapa `_APOLLO_TO_SECTOR` em `resend_service.py`.
  Se o setor não casar, a personalização por setor degrada para o texto default —
  então os valores do pool são escolhidos **dentre as chaves de `_APOLLO_TO_SECTOR`**.
- **ICP-calibrado:** pools de `title`, `seniority`, `company_size` e
  `security_signals` representando CISOs/CTOs/diretores de TI/gestores de risco.

### Saída (formato que o `tool_executor._enrich_lead` espera hoje)

```python
{
  "real_role": str,            # ex. "Chief Information Security Officer"
  "company": str,              # do lead, ou derivada do domínio do email
  "sector": str,               # Apollo-shaped (chave de _APOLLO_TO_SECTOR)
  "company_size": str,         # ex. "1200"
  "linkedin_url": str,         # fake plausível: linkedin.com/in/<slug>
  "is_decision_maker": bool,   # derivado da seniority
  "security_signals": str,     # ex. "Pesquisou Zero Trust; baixou whitepaper LGPD"
  "enrichment_summary": str,   # frase pronta para o system prompt
  "source": "mock",            # distingue de "apollo" nos dados
}
```

### Derivação determinística

1. `domain = email.split("@")[1]`; `company = lead.company or titlecase(domain sem TLD)`.
2. Domínios genéricos (`gmail.com`, `outlook.com`, `hotmail.com`, `yahoo.com`) →
   empresa sintética de um pool ("Acme Security", etc.) para não gerar
   "Gmail" como empresa.
3. `seniority`/`title`/`is_decision_maker`: se o lead informou `role`, infere a
   senioridade do texto (contém "ciso"/"cto"/"diretor"/"head" → decisor); senão,
   sorteia do pool com `seed`.
4. `sector`, `company_size`, `security_signals`: sorteados do pool com `seed`
   (determinístico).

---

## 5. WhatsApp mock (`services/whatsapp.py`)

- `send_whatsapp` continua como tool do agente (`tools.py`) e no system prompt
  (`prompts.py`) — **inalterado**. A trava de consentimento LGPD
  (`whatsapp_consent_at IS NOT NULL`) permanece no `tool_executor._send_whatsapp`
  antes de chamar o serviço.
- Sem `evolution_api_key`: o serviço grava em `messages`:
  `channel="WHATSAPP", direction="OUT", body=text, status="SIMULATED",
  sent_at=now`. Retorna `{"simulated": True}`.
- Com chave: comportamento atual (Evolution `sendText`), gravando `status` normal.
- Dashboard: a coluna/badge de status já existe; `SIMULATED` aparece distinto de
  `SENT` (ajuste mínimo de label/cor no frontend se necessário — ver §9).

---

## 6. Meeting mock + webhook simulado (`services/meeting.py`)

### `generate_meeting_link(lead)`
- **Real:** comportamento atual (busca o event-type no Cal.com, monta o link).
- **Mock:** monta um link fake plausível
  (`https://cal.com/vigil/demo-vigil?name=...&email=...`) **e** insere um job
  `SIMULATED_BOOKING` em `scheduled_jobs` com `run_at` curto (segundos/minutos,
  respeitando `DEMO_FAST_FORWARD`). Retorna o link + nota `[SIMULADO]`.

### `apply_booking_created(email)` — núcleo extraído do webhook
- Move-se a lógica essencial de `api/webhooks.py::calcom_webhook` (o loop que
  transita cada lead do email para `MEETING_SCHEDULED` via
  `atomic_transition_lead_stage`, origens `["ATTENDED", "NO_SHOW"]`) para esta
  função compartilhada.
- O webhook real passa a: verificar HMAC → parsear → chamar
  `apply_booking_created(attendee_email)`.
- O job simulado chama a **mesma** função → invariante de transição preservado.

### Roteamento do job simulado (`scheduler/jobs.py`)
- Assinatura única: `apply_booking_created(email)`. É a função compartilhada com o
  webhook real (que já tem o email do attendee). O job simulado guarda apenas
  `lead_id`, então o branch resolve `lead_id → email` e chama a mesma função.
- `check_and_run_job` ganha um branch **antes** do `run_agent`:
  ```python
  if job["job_type"] == "SIMULATED_BOOKING":
      email = <buscar leads.email por lead_id>
      await apply_booking_created(email)   # mesma função do webhook real
      # marca DONE; NÃO chama run_agent
      return
  ```
- As condições existentes (`only_if_stage` etc.) não se aplicam a este tipo; o
  branch é cedo, antes da avaliação de condições.
- Persistência: como é um job real em `scheduled_jobs`, sobrevive a restart e fica
  visível para auditoria.

---

## 7. Modo demo acelerado (`DEMO_FAST_FORWARD`)

- Nova flag em `config.py`: `demo_fast_forward: bool = False`.
- Aplicada **exclusivamente** em `prompts.py::_build_regua()`. Quando ligada, as
  âncoras deixam de ser datas-calendário (`event_date - 14d`) e passam a ser
  offsets curtos a partir de `now`:

  | Âncora | Produção (off) | Demo (on) |
  |---|---|---|
  | t14 | `event_date - 14d` | `now + 1min` |
  | t10 | `event_date - 10d` | `now + 2min` |
  | t7  | `event_date - 7d`  | `now + 3min` |
  | t3  | `event_date - 3d`  | `now + 4min` |
  | t1  | `event_date - 1d`  | `now + 5min` |
  | t0  | dia do evento      | `now + 6min` |
  | d3/d7/d14 (pós) | `now + Nd` | `now + N*1min` (escala comprimida) |

- **A lógica da régua não muda:** mesmos `job_type`, mesmas `condition`, mesma
  ordem e mesmos templates. Só a escala de tempo das âncoras. O agente recebe os
  timestamps já comprimidos no prompt e os usa nos `schedule_job`.
- Valores exatos de offset definidos no plano de implementação (config simples,
  ex.: `_DEMO_OFFSETS`).

---

## 8. Mudanças de config (`config.py`)

- `apollo_api_key`, `evolution_api_key`, `cal_api_key`: **já** opcionais (`""`).
  Nenhuma mudança no schema; apenas o comportamento muda (mock no lugar do erro).
- Adiciona: `demo_fast_forward: bool = False`.
- `.env.example` ganha bloco comentado documentando o modo demo.

---

## 9. Arquivos afetados

**Criar**
- `backend/app/services/enrichment.py`
- `backend/app/services/whatsapp.py`
- `backend/app/services/meeting.py`
- `backend/app/services/mocks.py`

**Modificar**
- `backend/app/agent/tool_executor.py` — remove `httpx`; chama as funções de serviço.
- `backend/app/api/webhooks.py` — extrai `apply_booking_created`; handler real passa a chamá-la.
- `backend/app/scheduler/jobs.py` — branch `SIMULATED_BOOKING`.
- `backend/app/agent/prompts.py` — fast-forward em `_build_regua()`.
- `backend/app/config.py` — flag `demo_fast_forward`.
- `backend/.env.example` — documenta modo demo.
- `CLAUDE.md` — documenta a camada `services/`, o modo demo, o mock por ausência
  de chave e o invariante do webhook simulado.

**Não muda**
- `services/resend_service.py` (email real), `tools.py` (definições de tool),
  `ChatbotWidget.tsx`, contrato SSE, RPCs do Postgres.

---

## 10. Estratégia de testes

- **Determinismo:** `enrich_lead_data` com o mesmo email duas vezes ⇒ dict idêntico.
- **Apollo-shaped:** todo `sector` gerado pertence às chaves de `_APOLLO_TO_SECTOR`,
  e `_resolve_sector_content(sector)` retorna conteúdo específico (não o default).
- **Detecção:** com chave setada (monkeypatch em `settings`) usa o caminho real
  (mockando `httpx`); sem chave usa o gerador.
- **WhatsApp simulado:** sem `evolution_api_key`, `send_whatsapp` grava `messages`
  com `status="SIMULATED"` e respeita a trava de consentimento (não grava se
  `whatsapp_consent_at` é nulo).
- **Booking simulado:** `generate_meeting_link` mock insere job `SIMULATED_BOOKING`;
  `check_and_run_job` desse job leva o lead `ATTENDED → MEETING_SCHEDULED` via a
  função compartilhada (sem chamar o agente).
- **Webhook real intacto:** `apply_booking_created` extraída produz o mesmo
  resultado que o handler fazia antes (teste de regressão).
- **Fast-forward:** com `demo_fast_forward=True`, `_build_regua("NEW_LEAD_REGISTERED")`
  emite `run_at` em minutos a partir de `now`; com `False`, em datas-calendário.

Cobertura preservada: os testes existentes de agente/estado/adapters continuam
passando (o `tool_executor` mantém o mesmo contrato externo).

---

## 11. Pergunta bônus — escalar para 10 eventos regionais simultâneos

Não construído neste escopo, mas a arquitetura sustenta o argumento na documentação:

- **Multi-tenant por `event_id`:** `leads`, `messages`, `scheduled_jobs` já carregam
  `event_id`; a régua é por-lead/por-evento. Rodar N eventos não exige nova
  estrutura.
- **Conteúdo por evento:** os pools de setor e os templates podem ser
  parametrizados por evento (config/`events`) sem tocar a lógica do agente.
- **Subida incremental de integrações:** cada serviço sobe de mock → real trocando
  uma chave, por ambiente — sem reescrever o orquestrador. Mesma propriedade que
  já vale para o provider de LLM.

---

## 12. Riscos & mitigações

- **Mock "Apollo-shaped" desalinhar do mapa real:** mitigado por teste que cruza os
  valores gerados com as chaves de `_APOLLO_TO_SECTOR`.
- **Job simulado órfão se servidor reiniciar na janela:** baixo impacto (job
  persistido em `scheduled_jobs`; `_reload_pending_jobs()` re-registra pendentes).
- **Honestidade na demo:** toda saída simulada é rotulada (`source="mock"`,
  `status="SIMULATED"`, nota `[SIMULADO]`) — o avaliador sempre distingue real de
  simulado. Documentado no CLAUDE.md.
