# Modo Demo & Mocks de Integrações Externas — Design

**Data:** 2026-05-31
**Status:** Aprovado para planejamento (revisado pós code-review)
**Contexto:** Case técnico Vigil.AI (vaga AI Engineer, Pareto). O time avaliador precisa
testar o funil ponta-a-ponta **sem chaves de APIs pagas**. Hoje, sem `APOLLO_API_KEY`
(e análogos), o funil trava num beco-sem-saída (`"Apollo.io não configurado"`).

> **Histórico:** este spec passou por **duas rodadas** de code-review contra o código
> real. Todos os achados estão incorporados — ver §13 (Achados do review e resoluções).

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

### Fluxo de demonstração — DUAS FASES

O funil tem uma fronteira realista: a fase pós-evento (follow-up + reunião) só faz
sentido **depois que o evento aconteceu**. No código, "o evento aconteceu" é
sinalizado pelos endpoints `/checkin` (→ ATTENDED) e `/no-show` (→ NO_SHOW). A demo
respeita isso em duas fases:

**FASE 1 — autônoma (cadastro → régua pré-evento):**
```
Formulário (nome, email, telefone, consentimentos)
  → POST /api/leads → REGISTERED → run_agent("NEW_LEAD_REGISTERED")
       PASSO 1: enrich_lead()              → MOCK determinístico → grava lead_enrichment, ENRICHED
       PASSO 2: send_pre_event_msg("welcome") → Resend REAL (boas-vindas personalizado)
       PASSO 3: agenda a régua pré-evento   → datas comprimidas se DEMO_FAST_FORWARD
  → triggers da régua disparam email REAL + send_whatsapp() MOCK (visível no dashboard)
     (lead sobe REGISTERED → ENRICHED → CONFIRMED conforme engajamento)
```

**FASE 2 — disparada pelo avaliador (simula o evento → fecha o funil):**
```
Avaliador clica "Check-in" (ATTENDED) ou "No-show" no dashboard
  → run_agent("LEAD_ATTENDED" | "LEAD_NO_SHOW")
       → agenda régua pós-evento (FOLLOWUP_D3/D7/D14 | NOSHOW_D3/D7), comprimida
  → FOLLOWUP_D3 / NOSHOW_D3 → schedule_meeting() MOCK
       → link fake + job SIMULATED_BOOKING
  → SIMULATED_BOOKING → apply_booking_created() → ATTENDED/NO_SHOW → MEETING_SCHEDULED
```

> **Nota de honestidade:** o check-in/no-show modela a mesa de credenciamento real do
> evento — não é um atalho de demo. É o mesmo sinal que existiria em produção.

---

## 2. Decisões travadas (do brainstorming + review)

1. **Escopo do mock:** Apollo, Cal.com **e** WhatsApp/Evolution. Email + LLM reais.
2. **Ativação:** ausência da chave do serviço → mock automático (por serviço, não global).
3. **Dados de enriquecimento:** determinístico por `email`/domínio + pools curados do ICP de ciberssegurança.
4. **WhatsApp:** dentro do escopo do funil; mockado e visível no dashboard (`status=SIMULATED`).
5. **Régua na demo:** flag `DEMO_FAST_FORWARD` comprime os intervalos (dias → minutos) sem mudar a lógica.
6. **Fechar o funil:** mock dispara um **webhook simulado** pelo mesmo caminho de transição da produção.
7. **Fronteira do evento:** a fase pós-evento é disparada pelo avaliador via check-in/no-show no dashboard (reuso dos endpoints existentes; UI a ser fiada).
8. **Resiliência de lock:** jobs que perdem o lock de agente são re-enfileirados com **teto de contenção** (corrige bug latente de produção e a colisão sob compressão).
9. **Branching por engajamento demonstrável:** controle no dashboard que simula abertura/clique de email (seta `opened_at`/`clicked_at`, o mesmo que o webhook do Resend faz), permitindo ao avaliador dirigir o caminho da régua dentro da janela comprimida.

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
  mocks.py            (NOVO) geradores determinísticos
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

- **Determinístico:** `seed = int(sha256(email.lower().encode()).hexdigest(), 16)`.
  Mesmo email ⇒ mesmo perfil, sempre. (Demo repetível e documentável; `sha256` é
  estável entre processos — sem dependência de `hash()` aleatorizado do Python.)
- **Apollo-shaped:** o campo `sector` DEVE sair no vocabulário de indústria do
  Apollo (ex.: `"financial services"`, `"computer software"`, `"hospital & health care"`,
  `"manufacturing"`) para casar com o mapa `_APOLLO_TO_SECTOR` em `resend_service.py`.
  O pool de setores do mock é um **subconjunto explícito das chaves de
  `_APOLLO_TO_SECTOR`** (teste garante isso — §10).
- **Paridade real/mock:** a saída do mock contém **exatamente os mesmos campos** que o
  upsert do Apollo real grava hoje (`tool_executor._enrich_lead`). O Apollo real
  **não grava `security_signals`**, então o mock **também não** — o sinal de
  interesse em segurança entra **dentro do `enrichment_summary`** (campo que é de
  fato consumido por `prompts.py`). Isso evita divergência de dados real-vs-mock.
- **ICP-calibrado:** pools de `title`, `seniority` e `company_size` representando
  CISOs/CTOs/diretores de TI/gestores de risco.

### Saída (formato idêntico ao upsert real em `tool_executor._enrich_lead`)

```python
{
  "real_role": str,            # ex. "Chief Information Security Officer"
  "company": str,              # do lead, ou derivada do domínio do email
  "sector": str,               # Apollo-shaped (subconjunto de _APOLLO_TO_SECTOR)
  "company_size": str,         # ex. "1200"
  "linkedin_url": str,         # fake plausível: linkedin.com/in/<slug>
  "is_decision_maker": bool,   # derivado da seniority
  "enrichment_summary": str,   # frase pronta p/ system prompt — INCLUI o sinal de segurança
  "source": "mock",            # distingue de "apollo"
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
4. `sector`, `company_size` e o sinal de segurança (texto embutido no
   `enrichment_summary`): sorteados do pool com `seed` (determinístico).

---

## 5. WhatsApp mock (`services/whatsapp.py`)

- `send_whatsapp` continua como tool do agente (`tools.py`) e no system prompt
  (`prompts.py`) — **inalterado**. A trava de consentimento LGPD
  (`whatsapp_consent_at IS NOT NULL`) permanece no `tool_executor._send_whatsapp`
  antes de chamar o serviço.
- Sem `evolution_api_key`: o serviço grava em `messages`:
  `channel="WHATSAPP", direction="OUT", body=text, status="SIMULATED",
  sent_at=now`. Retorna `{"simulated": True}`. (`messages.status` é `TEXT` sem
  CHECK — `"SIMULATED"` é aceito; ver §12 pré-requisitos de schema.)
- Com chave: comportamento atual (Evolution `sendText`), gravando `status` normal.
- Dashboard: badge `SIMULATED` distinto de `SENT` (ajuste de label/cor — ver §9).

---

## 6. Meeting mock + webhook simulado (`services/meeting.py`)

> `schedule_meeting()` só é chamado pelos planos **pós-evento** (`FOLLOWUP_D3/D7`,
> `NOSHOW_D3`). Logo, só executa após a FASE 2 (check-in/no-show), quando o lead já
> está em `ATTENDED`/`NO_SHOW` — origens válidas da transição.

### `generate_meeting_link(lead)`
- **Real:** comportamento atual (busca o event-type no Cal.com, monta o link).
- **Mock:** monta um link fake plausível
  (`https://cal.com/vigil/demo-vigil?name=...&email=...`) **e** insere um job
  `SIMULATED_BOOKING` em `scheduled_jobs` com `run_at` curto (segundos, respeitando
  `DEMO_FAST_FORWARD`) e `condition={}`. Retorna o link + nota `[SIMULADO]`.

### `apply_booking_created(email)` — núcleo extraído do webhook
- Move-se a lógica essencial de `api/webhooks.py::calcom_webhook` (o loop que
  transita cada lead do email para `MEETING_SCHEDULED` via
  `atomic_transition_lead_stage`, origens `["ATTENDED", "NO_SHOW"]`) para esta
  função compartilhada. **Assinatura única: recebe `email`.**
- O webhook real **mantém** a verificação HMAC e o **503 quando
  `cal_webhook_secret` está ausente** (§13/#8). Após verificar/parsear, chama
  `apply_booking_created(attendee_email)`.
- O job simulado chama a **mesma** função → invariante de transição preservado.

### Roteamento do job simulado (`scheduler/jobs.py`)
- O job `SIMULATED_BOOKING` guarda apenas `lead_id`; o branch resolve
  `lead_id → leads.email` e chama `apply_booking_created(email)`.
- `check_and_run_job` ganha um branch **antes** de qualquer avaliação de condição e
  **antes** do `run_agent` (caso contrário o trigger `"SIMULATED_BOOKING"` cairia no
  fallback genérico do `prompts.py` e rodaria o agente sem instrução):
  ```python
  if job["job_type"] == "SIMULATED_BOOKING":
      email = <buscar leads.email por lead_id>
      await apply_booking_created(email)   # mesma função do webhook real
      # marca DONE; NÃO chama run_agent
      return
  ```

---

## 7. Modo demo acelerado (`DEMO_FAST_FORWARD`)

- Nova flag em `config.py`: `demo_fast_forward: bool = False`.
- Aplicada **exclusivamente** em `prompts.py::_build_regua()`. A função é síncrona;
  o acesso ao flag é via **import interno** de `settings` dentro de `_build_regua`
  (**não** altera a assinatura nem os call sites). Quando ligada, as âncoras deixam
  de ser datas-calendário e passam a ser offsets curtos a partir de `now`.

### Espaçamento — folga sobre o lock de agente

O lock de agente (`agent_locks`) é segurado durante toda a execução de `run_agent`.
Uma execução com Claude + tool calls pode levar dezenas de segundos. Se dois jobs do
**mesmo lead** dispararem mais perto do que a duração de uma execução, o segundo
perde o lock. Por isso os offsets de demo usam passo de **~2 minutos** (folga
confortável), e a resiliência de lock (§8) cobre o caso residual.

  | Âncora | Produção (off) | Demo (on) |
  |---|---|---|
  | t14 | `event_date - 14d` | `now + 2min` |
  | t10 | `event_date - 10d` | `now + 4min` |
  | t7  | `event_date - 7d`  | `now + 6min` |
  | t3  | `event_date - 3d`  | `now + 8min` |
  | t1  | `event_date - 1d`  | `now + 10min` |
  | t0  | dia do evento      | `now + 12min` |
  | d3/d7/d14 (pós) | `now + Nd` | `now + 2/4/6 min` |

- **A lógica da régua não muda:** mesmos `job_type`, `condition`, ordem e templates.
  Só a escala de tempo das âncoras. Offsets exatos são configuráveis (constante
  `_DEMO_OFFSETS`); 2 min é o default seguro.

> **Branching por engajamento na janela comprimida:** os passos com
> `condition={"skip_if_opened": ...}` / `{"only_if_not_clicked": ...}` e a lógica
> `opened/clicked` em `WARMUP_T10`/`FOLLOWUP_D7` dependem de `messages.opened_at`/
> `clicked_at`. Em 2 min, o webhook real do Resend não chega a tempo — então o
> avaliador usa o controle de **simular abertura/clique** (§9A) para dirigir o
> caminho antes do passo dependente disparar. Sem isso, a régua sempre cai no ramo
> "não abriu/não clicou".

---

## 8. Resiliência de lock (`scheduler/jobs.py` + `orchestrator.py`)

Bug latente atual: `run_agent` retorna a string `"Agent já em execução... abortando"`
quando não adquire o lock; `check_and_run_job` marca o job como `DONE` mesmo sem ter
executado — **o job é perdido** (vale para produção também).

Correção: `check_and_run_job` detecta o retorno de "lock ocupado" e **re-enfileira**
o job com delay curto em vez de marcar `DONE`.

- Mecanismo: `run_agent` passa a sinalizar o caso de lock-ocupado de forma
  inequívoca (ex.: retorno sentinela/flag) para `check_and_run_job` não depender de
  matching de string frágil.
- Re-enfileira via o mesmo caminho já existente (atualiza `run_at`,
  `status=PENDING`, `add_job_to_scheduler`), **sem** incrementar `retry_count` (não
  é erro — é contenção).
- **Teto de contenção (anti-loop-infinito):** um contador separado
  `contention_count` (novo campo em `scheduled_jobs`, ou reuso de `error`/metadata)
  limita as re-tentativas por contenção (ex.: **máx. 5**). Atingido o teto, o job
  vai para `FAILED` com motivo "lock preso". Isso evita o loop infinito caso o lock
  fique preso por uma execução travada cujo heartbeat continua renovando.
- **Delay de re-enfileiramento:** curto o suficiente para a demo (ex.: 30s), mas o
  teto garante terminação mesmo se o delay for menor que o TTL do lock (5 min).

---

## 9. Controles de demo no frontend (`LeadDrawer.tsx`)

### Padrão de atualização: Realtime, NÃO refetch

O dashboard é **Realtime-driven**: `FunnelBoard.tsx` (linha ~181) assina
`postgres_changes` na tabela `leads` via Supabase Realtime e re-renderiza ao receber
updates. O botão existente `handleRunAgent` (`LeadDrawer.tsx` linha 56–72)
**dispara a ação e exibe "aguarde o Realtime atualizar o lead" — sem refetch**.

Portanto, todos os controles novos **seguem esse padrão**: disparam a ação e
deixam o Realtime propagar a mudança de stage / engajamento para o board (e, via
props, para o drawer). **Não** fazem `getLeads()` manual. (Correção do achado do
review — a versão anterior do spec dizia "refetch", o que contradiz o padrão real.)

### Autenticação

Todos os proxies operacionais (`/api/leads/[id]/checkin`, `/no-show`, e o novo de
engajamento) fazem `supabase.auth.getUser()` e retornam **401 sem sessão**. Os
botões vivem em `app/dashboard`, que já exige login — então funcionam no contexto
logado. Documentar isso na UI (mensagem de erro clara em 401).

### Botões — Fase 2 (fechar o funil)

`lib/api.ts` já tem `checkinLead(lead_id)` e `markNoShow(lead_id)` e os proxies
`/checkin` e `/no-show` existem, mas **não são chamados em lugar nenhum**. Adicionar
no `LeadDrawer.tsx` dois botões — **"Check-in"** e **"No-show"** — visíveis quando o
stage permite a transição (REGISTERED/ENRICHED/CONFIRMED).

### Botões — simular engajamento (§9A — branching da régua)

Adicionar **"Simular abertura"** e **"Simular clique"**, chamando um novo proxy/endpoint
(ver §9A) que seta `opened_at`/`clicked_at` na última mensagem OUT/EMAIL do lead —
o mesmo efeito do webhook do Resend. Permite ao avaliador dirigir o branch da régua
antes do passo dependente disparar.

---

## 9A. Simular engajamento — endpoint + escrita de dados

Novo endpoint operacional, no padrão de `/checkin` e `/no-show`:

- **Backend** (`api/leads.py`): `POST /api/leads/{id}/simulate-engagement`
  (`X-API-Key`), corpo `{"opened": bool, "clicked": bool}`. Atualiza a **última**
  mensagem `direction="OUT", channel="EMAIL"` do lead, setando `opened_at`/
  `clicked_at = now` conforme o corpo (idempotente; só seta o que ainda é nulo,
  igual ao webhook do Resend). Não muda stage.
- **Frontend:** `lib/api.ts` ganha `simulateEngagement(lead_id, {opened, clicked})`;
  proxy `app/api/leads/[id]/simulate-engagement/route.ts` (auth de sessão, repassa
  `X-API-Key`), no mesmo molde do proxy `/checkin`.
- **Semântica:** escreve exatamente os mesmos campos que o webhook real do Resend
  (`resend_webhook` seta `opened_at`/`clicked_at`). Logo, `check_engagement()` e as
  `condition` de job (`skip_if_opened`, `only_if_not_clicked`) reagem de forma
  idêntica ao caminho real — é simulação fiel, não um atalho de lógica.
- **Rotulagem:** opcional marcar a mensagem como engajamento simulado (ex.: campo/
  flag) para honestidade na auditoria; mínimo viável é apenas setar os timestamps.

---

## 10. Estratégia de testes

- **Determinismo:** `enrich_lead_data` com o mesmo email duas vezes ⇒ dict idêntico.
- **Apollo-shaped (anti-drift):** `assert` que todo `sector` do pool do mock pertence
  a `set(_APOLLO_TO_SECTOR.keys())`, e que `_resolve_sector_content(sector)` retorna
  conteúdo específico (não o default) para cada valor do pool.
- **Paridade de campos:** o dict do mock tem o mesmo conjunto de chaves que o upsert
  do Apollo real (sem `security_signals`).
- **Detecção:** com chave (monkeypatch em `settings`) usa o caminho real (mockando
  `httpx`); sem chave usa o gerador.
- **WhatsApp simulado:** sem `evolution_api_key`, `send_whatsapp` grava `messages`
  com `status="SIMULATED"` e respeita a trava de consentimento (não grava se
  `whatsapp_consent_at` é nulo).
- **Booking simulado:** `generate_meeting_link` mock insere job `SIMULATED_BOOKING`
  (`condition={}`); `check_and_run_job` desse job, com lead em `ATTENDED`, leva o
  lead a `MEETING_SCHEDULED` via `apply_booking_created` (sem chamar o agente). E
  com lead em `ENRICHED` (origem inválida), não transita (retorno `INVALID_TRANSITION`).
- **Webhook real intacto:** `apply_booking_created` extraída produz o mesmo resultado
  que o handler fazia antes; o handler preserva HMAC e 503 sem secret (regressão).
- **Resiliência de lock:** job cujo `run_agent` retorna "lock ocupado" é re-enfileirado
  (`status=PENDING`, `run_at` adiado), não marcado `DONE`, e sem incrementar
  `retry_count`. **Teto:** após N contenções (ex.: 5), o job vai para `FAILED` (sem
  loop infinito).
- **Simular engajamento:** `POST /simulate-engagement {opened:true}` seta `opened_at`
  na última msg OUT/EMAIL; em seguida um job com `condition={"skip_if_opened":true}`
  é corretamente pulado, e `WARMUP_T10` toma o ramo "abriu". Idempotência: chamar
  duas vezes não sobrescreve o timestamp já setado.
- **Fast-forward:** com `demo_fast_forward=True`, `_build_regua("NEW_LEAD_REGISTERED")`
  emite `run_at` em minutos a partir de `now` (passo ~2 min); com `False`, em
  datas-calendário.

Cobertura preservada: os testes existentes de agente/estado/adapters continuam
passando (o `tool_executor` mantém o mesmo contrato externo).

---

## 11. Mudanças de config (`config.py`)

- `apollo_api_key`, `evolution_api_key`, `cal_api_key`: **já** opcionais (`""`).
  Nenhuma mudança no schema; apenas o comportamento muda (mock no lugar do erro).
- Adiciona: `demo_fast_forward: bool = False`.
- `.env.example` ganha bloco comentado documentando o modo demo.

---

## 12. Pré-requisitos de schema (verificar antes de implementar)

O `001_initial.sql` está **desatualizado** em relação às migrações posteriores. O
banco-alvo (incl. ambiente limpo) precisa ter aplicado:

- **`messages.status`** (`TEXT DEFAULT 'SENT'`) — adicionado em
  `scripts/migrations/001_audit_remediation.sql`. O mock de WhatsApp grava
  `status="SIMULATED"`; sem essa coluna o INSERT falha. (Não há CHECK constraint em
  `messages.status`, então `'SIMULATED'` é aceito.)
- **`scheduled_jobs.status` aceitando `'RUNNING'`** — `001_initial.sql` define
  `CHECK (status IN ('PENDING','DONE','SKIPPED','FAILED'))` **sem** `'RUNNING'`, mas
  `claim_scheduled_job` faz `SET status='RUNNING'`. O job `SIMULATED_BOOKING` usa o
  mesmo claim. Confirmar que o schema aplicado relaxou/corrigiu esse CHECK (a régua
  atual já depende disso). Se não, incluir o patch do CHECK como pré-requisito.

Esses pontos **não são introduzidos por este feature** (o app já grava `status` e já
usa `RUNNING`), mas são pré-condições para o caminho demo funcionar.

**Nova coluna introduzida por este feature:** o teto de contenção de lock (§8) precisa
de um contador persistente. Opções: (a) nova coluna `scheduled_jobs.contention_count
INTEGER DEFAULT 0` (migração nova); ou (b) reuso do campo `error`/metadata existente
para serializar o contador. Decisão fica para o plano de implementação; (a) é mais
limpo e testável.

---

## 13. Achados do code-review e resoluções

| # | Achado | Resolução |
|---|---|---|
| 3 | Funil só fecha pós-evento; ATTENDED/NO_SHOW exigem ação manual | Demo em 2 fases (§1); fiação de check-in/no-show no dashboard (§9) |
| 1 | `messages.status` vem de migração separada | Pré-requisito de schema documentado (§12) |
| 2 | CHECK de `scheduled_jobs.status` sem `'RUNNING'` | Pré-requisito de schema documentado (§12) |
| 4 | `security_signals` não é gravado pelo Apollo real | Mock não grava o campo; sinal entra no `enrichment_summary` (§4) |
| 7 | Lock de agente colide com jobs comprimidos | Espaçamento ~2 min (§7) + re-enfileirar em contenção (§8) |
| 5 | Pool de setor pode driftar das chaves do mapa | Teste anti-drift `sector ∈ keys` (§10) |
| 6/9 | Branch `SIMULATED_BOOKING` precisa posição/condição corretas | Branch antes de condições e de `run_agent`; `condition={}` (§6) |
| 8 | 503 do webhook calcom sem secret | Preservado explicitamente na extração (§6) |
| 11 | `_build_regua` é síncrona e não recebe `settings` | Import interno de `settings`, sem mudar assinatura (§7) |

### Segunda rodada de review (achados novos)

| # | Achado | Resolução |
|---|---|---|
| N1 | Re-enfileiramento de lock sem teto → loop infinito | Teto de contenção (máx. ~5) → `FAILED` (§8) |
| N2 | Padrão real é Realtime, não "refetch" | §9 reescrito: dispara + Realtime atualiza, sem refetch manual |
| N3 | Botões exigem sessão Supabase Auth | §9 documenta o requisito de login + 401 |
| N5 | Branching por engajamento não dispara em 2 min | Controle "simular abertura/clique" (§9A) + nota em §7 |
| N4 | `SIMULATED_BOOKING` em segundos colide com lock do `run_agent` criador? | **Sem problema** — `apply_booking_created` não adquire lock de agente |

---

## 14. Arquivos afetados

**Criar**
- `backend/app/services/enrichment.py`
- `backend/app/services/whatsapp.py`
- `backend/app/services/meeting.py`
- `backend/app/services/mocks.py`

**Modificar**
- `backend/app/agent/tool_executor.py` — remove `httpx`; chama as funções de serviço.
- `backend/app/api/webhooks.py` — extrai `apply_booking_created`; handler real chama-a (mantém HMAC + 503).
- `backend/app/api/leads.py` — novo endpoint `POST /{id}/simulate-engagement` (§9A).
- `backend/app/scheduler/jobs.py` — branch `SIMULATED_BOOKING`; re-enfileirar em contenção de lock com teto.
- `backend/app/agent/orchestrator.py` — sinalizar lock-ocupado de forma inequívoca.
- `backend/app/agent/prompts.py` — fast-forward em `_build_regua()` (import interno de `settings`).
- `backend/app/config.py` — flag `demo_fast_forward`.
- `backend/.env.example` — documenta modo demo.
- `frontend/lib/api.ts` — `simulateEngagement(...)` (checkin/markNoShow já existem).
- `frontend/app/api/leads/[id]/simulate-engagement/route.ts` (NOVO proxy autenticado).
- `frontend/components/dashboard/LeadDrawer.tsx` — botões Check-in / No-show / Simular abertura / Simular clique (padrão Realtime, sem refetch).
- `frontend/components/dashboard/LeadCard.tsx` (ou onde o badge vive) — label/cor para `SIMULATED`.
- `CLAUDE.md` — documenta a camada `services/`, o modo demo, o mock por ausência de
  chave, o webhook simulado, a resiliência de lock com teto e os controles de demo.

**Não muda**
- `services/resend_service.py` (email real), `tools.py` (definições de tool),
  `ChatbotWidget.tsx`, contrato SSE, RPCs do Postgres.

---

## 15. Pergunta bônus — escalar para 10 eventos regionais simultâneos

Não construído neste escopo, mas a arquitetura sustenta o argumento na documentação:

- **Multi-tenant por `event_id`:** `leads`, `messages`, `scheduled_jobs` já carregam
  `event_id`; a régua é por-lead/por-evento. Rodar N eventos não exige nova estrutura.
- **Conteúdo por evento:** pools de setor e templates parametrizáveis por evento
  (config/`events`) sem tocar a lógica do agente.
- **Subida incremental de integrações:** cada serviço sobe de mock → real trocando
  uma chave, por ambiente — sem reescrever o orquestrador. Mesma propriedade que já
  vale para o provider de LLM.

---

## 16. Riscos & mitigações

- **Mock "Apollo-shaped" desalinhar do mapa real:** teste anti-drift (§10).
- **Job simulado órfão se servidor reiniciar na janela:** baixo impacto (job
  persistido; `_reload_pending_jobs()` re-registra pendentes).
- **Pré-requisitos de schema (§12):** verificar antes de rodar a demo em banco limpo.
- **Honestidade na demo:** toda saída simulada é rotulada (`source="mock"`,
  `status="SIMULATED"`, nota `[SIMULADO]`) — o avaliador sempre distingue real de
  simulado. Documentado no CLAUDE.md.
