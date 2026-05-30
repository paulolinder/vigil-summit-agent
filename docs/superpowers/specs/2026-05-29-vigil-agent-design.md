# Vigil Summit Agent — Design Spec

**Data:** 2026-05-29  
**Projeto:** Case AI Engineer — Pareto × Vigil.AI  
**Stack:** Claude Sonnet + FastAPI + Supabase + Apollo.io + Resend + APScheduler + Next.js  
**Estrutura:** `frontend/` + `backend/` separados  

---

## 1. Arquitetura Geral e Fluxo de Dados

### Diagrama

```
┌──────────────────────────────────────────────────────────────┐
│                  FRONTEND  (Next.js / Vercel)                 │
│                                                              │
│  ┌──────────────────────────┐  ┌────────────────────────┐   │
│  │  Landing Page            │  │  Dashboard (senha)      │   │
│  │  · Formulário inscrição  │  │  · Funil de leads       │   │
│  │  · Chatbot Claude embed  │  │  · Status em tempo real │   │
│  └──────────────────────────┘  └────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                          │  REST API
┌──────────────────────────────────────────────────────────────┐
│                  BACKEND  (FastAPI / Railway)                 │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │          Agente Orquestrador  (Claude Sonnet)          │  │
│  │                                                        │  │
│  │  enrich_lead()       → Apollo.io                      │  │
│  │  send_pre_event_msg() → Resend (email)                 │  │
│  │  check_engagement()  → Supabase (abriu? clicou?)      │  │
│  │  send_followup()     → Resend + WhatsApp              │  │
│  │  update_lead_stage() → Supabase                       │  │
│  │  schedule_meeting()  → Cal.com API                    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │ APScheduler  │  │  Webhooks   │  │ POST /api/leads  │   │
│  │ (régua jobs) │  │ (email open)│  │ (nova inscrição) │   │
│  └──────────────┘  └─────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                          │
┌──────────────────────────────────────────────────────────────┐
│               Supabase  (PostgreSQL)                          │
│  leads · messages · lead_enrichment · lead_memory            │
│  scheduled_jobs · events · agent_locks                       │
└──────────────────────────────────────────────────────────────┘
```

### Fluxo principal

1. Lead preenche formulário ou conversa com chatbot na landing page
2. Backend cria registro no Supabase via `POST /api/leads` e dispara `run_agent` como background task
3. `run_agent` aciona o Agente: Claude recebe perfil bruto e chama `enrich_lead()`
4. Com perfil enriquecido, agente define estágio no funil e agenda jobs no APScheduler (persistidos no Supabase)
5. APScheduler dispara o agente em cada gatilho de tempo/condição — Claude lê estado atual do lead e decide qual ferramenta usar
6. Pós-evento: agente lê sinais de engajamento (abertura/clique de emails, setor do lead como proxy de interesse) e inicia régua de follow-up personalizada
7. Dashboard reflete estado do banco em tempo real via Supabase Realtime

### Onde cada fase do funil se encaixa

| Fase | Componente responsável |
|---|---|
| Captação | Landing page (formulário + chatbot) → POST /api/leads |
| Enriquecimento | Agente + tool `enrich_lead()` → Apollo.io |
| Engajamento pré-evento | APScheduler → Agente → tools `send_pre_event_msg()`, `check_engagement()` |
| Follow-up pós-evento | Webhook checkin → Agente → tools `send_followup()`, `schedule_meeting()` |

---

## 2. Stack Tecnológico Justificado

| Tecnologia | Papel | Justificativa |
|---|---|---|
| **Claude Sonnet** (Anthropic SDK nativo) | LLM + agente orquestrador | Preferência explícita da Pareto; SDK nativo expõe tool use com raciocínio auditável via `tool_use` no banco |
| **FastAPI** (Python) | Backend REST + orquestração | Padrão de mercado para AI engineering; async nativo, integração direta com SDK Anthropic |
| **Supabase** (PostgreSQL) | Banco de dados + Realtime | Tier gratuito; painel web acessível para `ramon@pareto.io` validar sem instalar nada; RLS facilita LGPD |
| **Apollo.io API** | Enriquecimento de leads | Melhor cobertura B2B brasileira; retorna cargo real, setor, tamanho, technographics |
| **Resend** | E-mail transacional | API limpa, tier gratuito generoso, webhooks de abertura/clique nativos |
| **Evolution API** | WhatsApp (escalada) | Open source, sem custo Twilio, adequado para canal secundário |
| **Cal.com API** | Agendamento de reuniões | Open source, API REST, self-hostável |
| **APScheduler `AsyncIOScheduler` + Supabase** | Régua de mensagens | Jobs persistidos no banco — Railway restarts não perdem a régua; `AsyncIOScheduler` (não `BackgroundScheduler`) integra com o event loop do FastAPI sem causar `RuntimeError` |
| **Next.js** (Vercel) | Frontend + dashboard | Turbopack automático; deploy gratuito; SSE para chatbot streaming |
| **Railway** | Deploy do backend | CI/CD via GitHub push; domínio público automático |

---

## 3. Banco de Dados — Schema Completo

```sql
-- IF NOT EXISTS em todos os CREATE TABLE: SQL idempotente, pode ser re-executado sem erro
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Multi-tenant desde o início
CREATE TABLE IF NOT EXISTS events (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  event_date  TIMESTAMPTZ NOT NULL,
  capacity    INT DEFAULT 120,
  sector      TEXT,  -- manufatura, saúde, financeiro, governo
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- States: REGISTERED → ENRICHED → CONFIRMED → ATTENDED
--         → MEETING_SCHEDULED → CONVERTED | NO_SHOW | OPTED_OUT
-- PostgreSQL não suporta CREATE TYPE IF NOT EXISTS — bloco DO $$ para idempotência
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
  -- LGPD
  consent_at           TIMESTAMPTZ NOT NULL,
  consent_ip           TEXT NOT NULL,
  whatsapp_consent_at  TIMESTAMPTZ,   -- NULL = não optou; agente só usa send_whatsapp() se preenchido
  deletion_req_at      TIMESTAMPTZ,
  created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- ON DELETE CASCADE em todas as tabelas dependentes:
-- deletar um lead limpa automaticamente todos os seus registros filhos
CREATE TABLE IF NOT EXISTS lead_enrichment (
  lead_id          UUID PRIMARY KEY REFERENCES leads(id) ON DELETE CASCADE,
  real_role        TEXT,
  company          TEXT,
  sector           TEXT,
  company_size     TEXT,
  linkedin_url     TEXT,
  security_signals TEXT,
  is_decision_maker BOOL DEFAULT false,
  enrichment_summary TEXT,  -- injetado no system prompt do agente
  source           TEXT DEFAULT 'apollo',
  enriched_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id      UUID REFERENCES leads(id) ON DELETE CASCADE,
  event_id     UUID REFERENCES events(id) ON DELETE SET NULL,  -- SET NULL preserva histórico de mensagens ao deletar evento
  channel      TEXT CHECK (channel IN ('EMAIL','WHATSAPP','CHAT')),
  direction    TEXT CHECK (direction IN ('IN','OUT')),
  subject      TEXT,
  body         TEXT,
  funnel_stage lead_stage,
  resend_id    TEXT,  -- ID retornado pela Resend API; usado pelo webhook de abertura/clique
  opened_at    TIMESTAMPTZ,
  clicked_at   TIMESTAMPTZ,
  sent_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Memória de contexto do agente por lead
CREATE TABLE IF NOT EXISTS lead_memory (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id     UUID REFERENCES leads(id) ON DELETE CASCADE,
  role        TEXT CHECK (role IN ('user','assistant')),
  content     TEXT,
  tool_use    JSONB,  -- auditoria de decisões do agente
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Jobs persistidos para APScheduler
-- condition schema: {"only_if_stage": "REGISTERED"} | {"skip_if_opened": true} | {"only_if_not_clicked": true}
-- Avaliação: AND entre todas as chaves presentes; primeira falha causa SKIPPED imediatamente (short-circuit).
-- Chaves não reconhecidas são ignoradas (safe default — nunca bloqueiam execução).
CREATE TABLE IF NOT EXISTS scheduled_jobs (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id      UUID REFERENCES leads(id) ON DELETE CASCADE,
  event_id     UUID REFERENCES events(id) ON DELETE SET NULL,
  job_type     TEXT NOT NULL,   -- logicamente obrigatório; job sem tipo é inválido
  run_at       TIMESTAMPTZ NOT NULL,  -- logicamente obrigatório; job sem data é inválido
  condition    JSONB DEFAULT '{}',
  status       TEXT DEFAULT 'PENDING'
             CHECK (status IN ('PENDING','DONE','SKIPPED','FAILED')),
  error        TEXT,            -- mensagem de erro quando status = FAILED
  retry_count  INT DEFAULT 0,   -- incrementado a cada tentativa com falha
  max_retries  INT DEFAULT 3,   -- após max_retries, status permanece FAILED sem novo agendamento
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Mutex de execução por lead: evita que background task D+0 e APScheduler processem o mesmo lead simultaneamente.
-- Implementação: no início de run_agent(), DELETE WHERE expires_at < NOW() para limpar locks mortos,
-- depois INSERT. Se o INSERT falhar por violação de PK (lock válido já existe), aborta silenciosamente.
-- O `finally` de run_agent() faz DELETE do lock ao terminar (sucesso ou exceção).
-- Cleanup periódico: _reload_pending_jobs() do scheduler (executa a cada 5 min) também executa
-- DELETE FROM agent_locks WHERE expires_at < NOW() para remover locks de processos que crasharam
-- sem passar pelo finally.
CREATE TABLE IF NOT EXISTS agent_locks (
  lead_id    UUID PRIMARY KEY REFERENCES leads(id) ON DELETE CASCADE,
  locked_at  TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL  -- 5 min; evita deadlock permanente em crash do processo
);

-- Índices — IF NOT EXISTS para idempotência (consistente com CREATE TABLE IF NOT EXISTS)
CREATE UNIQUE INDEX IF NOT EXISTS leads_email_event_unique ON leads(email, event_id);  -- previne duplo registro
CREATE INDEX IF NOT EXISTS idx_leads_event_id ON leads(event_id);
CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
CREATE INDEX IF NOT EXISTS idx_messages_lead_id ON messages(lead_id);
-- Índice composto para check_engagement: busca do último email enviado (lead_id + sent_at DESC) sem full scan
CREATE INDEX IF NOT EXISTS idx_messages_lead_sent ON messages(lead_id, sent_at DESC) WHERE direction = 'OUT';
CREATE INDEX IF NOT EXISTS idx_messages_resend_id ON messages(resend_id);  -- usado pelo webhook de abertura/clique
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_run_at ON scheduled_jobs(run_at) WHERE status = 'PENDING';  -- partial index: evita full scan a cada reload
CREATE INDEX IF NOT EXISTS idx_lead_memory_lead_id ON lead_memory(lead_id);
CREATE INDEX IF NOT EXISTS idx_agent_locks_expires ON agent_locks(expires_at);  -- para limpeza periódica de locks expirados
```

---

## 4. Design do Agente — Tools e System Prompt

### Tools registradas

| Tool | Input | Output | Efeito |
|---|---|---|---|
| `enrich_lead` | `lead_id` | enrichment data | Cria `lead_enrichment`, stage → ENRICHED |
| `send_pre_event_msg` | `lead_id`, `template`, `custom_note` | message_id | Envia email via Resend, persiste em `messages` |
| `check_engagement` | `lead_id` | `{opened, clicked, last_message_at}` | Lê `messages` no Supabase |
| `send_whatsapp` | `lead_id`, `text` | message_id | Envia via Evolution API |
| `send_followup` | `lead_id`, `template`, `custom_note` | message_id | Envia email pós-evento via Resend |
| `update_lead_stage` | `lead_id`, `stage` | ok | Atualiza `leads.stage` |
| `schedule_job` | `lead_id`, `job_type`, `run_at`, `condition` | job_id | Persiste em `scheduled_jobs` |
| `schedule_meeting` | `lead_id`, `context_note` | calendar_link | Gera link Cal.com, atualiza stage → MEETING_SCHEDULED |

> **Nota:** `save_memory` **não é uma tool Claude** — é chamada internamente pelo orchestrator após cada resposta do agente. Expô-la como tool criaria entradas duplicadas em `lead_memory`. O orchestrator salva automaticamente `role=assistant` + texto + tool_use após cada iteração do loop.

### System prompt (estrutura)

```
Você é o agente comercial do Vigil Summit, evento de cibersegurança da Vigil.AI.

Seu objetivo é guiar cada lead do momento da inscrição até uma reunião comercial 
agendada. Você toma decisões autônomas com base no estado atual do lead.

PERFIL DO LEAD:
{enrichment_summary}

ESTADO ATUAL:
- Stage: {stage}
- Trigger: {trigger}
- Dias até o evento: {days_until_event}
- Último e-mail enviado: {last_message_at}
- Abriu último e-mail: {last_opened}
- Clicou no último e-mail: {last_clicked}
- Tem acompanhante: {has_companion}  ← aciona fluxo paralelo de confirmação do acompanhante
- Optou por WhatsApp: {whatsapp_opted_in}  ← se False, não use a tool send_whatsapp()

HISTÓRICO RECENTE:
{last_5_memory_entries}

Antes de qualquer ação, avalie o estado e decida a ação mais adequada.
Registre seu raciocínio antes de chamar qualquer tool.
```

### Como `{last_message_at}`, `{last_opened}`, `{last_clicked}` são populados

```python
# Em build_system_prompt() — busca o último email OUT enviado ao lead
msgs = (
    sb.table("messages")
    .select("sent_at, opened_at, clicked_at")
    .eq("lead_id", lead_id)
    .eq("direction", "OUT")
    .eq("channel", "EMAIL")
    .order("sent_at", desc=True)
    .limit(1)
    .execute()
    .data
)
msg = msgs[0] if msgs else {}
last_message_at = (msg.get("sent_at") or "N/A")[:16]   # ex: "2026-05-29T14:30"
last_opened     = str(bool(msg.get("opened_at")))        # "True" ou "False"
last_clicked    = str(bool(msg.get("clicked_at")))       # "True" ou "False"
```

- Usa `idx_messages_lead_sent` (índice composto `lead_id, sent_at DESC WHERE direction='OUT'`) — sem full scan
- Se nenhum email foi enviado ainda, todos retornam `"N/A"` / `"False"` — agente não toma decisão de follow-up prematura

### Como `{last_5_memory_entries}` é construído

```python
# Em build_system_prompt(), antes de retornar o prompt:
rows = (
    sb.table("lead_memory")
    .select("role, content, created_at")
    .eq("lead_id", lead_id)
    .order("created_at", desc=True)
    .limit(5)
    .execute()
    .data
)
# Inverte para ordem cronológica (mais antigo primeiro)
rows.reverse()
last_5_memory_entries = "\n".join(
    f"[{r['created_at'][:16]}] {r['role'].upper()}: {r['content'][:300]}"
    for r in rows
) or "Sem histórico anterior."
```

- Limite de 300 chars por entrada evita overflow do contexto em leads com histórico longo
- `tool_use` não é incluído no prompt (apenas no banco, para auditoria) — o texto do assistente já descreve o raciocínio

---

## 5. Réguas de Comunicação

### Régua Pré-Evento

```
[D+0]  enrich_lead() → welcome email com cargo enriquecido (sequência: enriquecimento primeiro, depois boas-vindas personalizadas com cargo real do Apollo.io)
[D+1]  Se C-level detectado no enriquecimento de D+0 → VIP Briefing por setor
[T-21] Aquecimento de conteúdo por setor
[T-14] Pedido de confirmação de presença
  ├── Confirmou → [T-7] Agenda personalizada por trilha
  ├── Abriu, não confirmou → [T-10] Segunda tentativa
  └── Não abriu → [T-10] Reenvio com assunto diferente
        └── 2ª sem abertura → [T-7] Escalada WhatsApp ← somente se whatsapp_consent_at IS NOT NULL
[T-3]  Logística (endereço, credencial, parking)
[T-1]  Lembrete final + demo recomendada por cargo
[D 07h] Check-in + instruções de acesso
```

**Regras especiais:**
- `has_companion = true` → fluxo paralelo endereçado ao acompanhante
- C-level → timeline comprimida, atendimento VIP desde D+1
- Cancelamento → oferta de rescheduling, stage = OPTED_OUT temporário

### Régua Pós-Evento

> **Nota sobre personalização:** "sessão assistida" e "demo interagida" são inferidas pelo **setor do lead** (ex: manufatura → OT/ICS, financeiro → Zero Trust/LGPD), não por tracking explícito de presença em sessão. O schema não possui tabela de sessões — a personalização usa `lead_enrichment.sector` como proxy. Essa é uma decisão de escopo deliberada: adicionar check-in por sessão exigiria infraestrutura de evento (QR code, app mobile) fora do escopo do case.

```
ATTENDED:
[D+1]  Agradecimento + referência à sessão do setor do lead
[D+3]  Follow-up com conteúdo de demo relevante ao setor + case study
  ├── Clicou → agendar reunião (Cal.com)
  ├── Abriu, não clicou → [D+5] WhatsApp com dor específica do cargo ← somente se whatsapp_consent_at IS NOT NULL
  └── Não abriu → [D+5] Reenvio, [D+7] Pergunta direta, [D+14] Break-up email

NO_SHOW:
[D+1]  "Sentimos sua falta" + highlights do evento
[D+5]  Oferta de demo privada
[D+10] Última tentativa + link de conteúdo
```

### Exemplo de mensagem personalizada — Pré-evento (T-14)

> Lead: Maria Santos, CISO, Banco Itararé, setor financeiro, 800 funcionários

```
Assunto: Maria, sua vaga no Vigil Summit está reservada — confirme presença

Oi Maria,

Faltam 14 dias para o Vigil Summit e sua vaga ainda está reservada.

Como CISO do Banco Itararé, você vai encontrar no Summit exatamente o que
move a agenda de segurança do setor financeiro agora: conformidade LGPD na
prática, Zero Trust para ambientes de open banking e como priorizar
vulnerabilidades quando tudo parece urgente ao mesmo tempo.

[Confirmar minha presença →]

Se quiser trazer alguém da sua equipe, responda com nome e e-mail — 
cuidamos do credenciamento.

Nos vemos daqui a 14 dias.
Equipe Vigil.AI
```

### Exemplo de mensagem personalizada — Pós-evento (D+1)

> Lead: Carlos Mendes, CTO, TechManufatura SA, 450 funcionários, setor manufatura
> Personalização: inferida via `lead_enrichment.sector = 'manufatura'` → tema OT/ICS

```
Assunto: Carlos, o tema que mais move CTOs de manufatura agora

Carlos,

Obrigado por estar no Vigil Summit ontem.

Com o chão de fábrica cada vez mais conectado, CTOs de manufatura 
que conversamos têm o mesmo desafio: firewalls tradicionais protegem 
o perímetro de TI, mas não falam a língua dos sistemas OT/ICS.

Na TechManufatura, com 450 colaboradores e linhas de produção conectadas, 
esse gap é real — e provavelmente já está na sua lista de prioridades.

Consigo te mostrar em 30 minutos como a Vigil.AI endereça isso no 
ambiente de manufatura?

[Escolher um horário →]

Ana Beatriz Costa
Account Executive, Vigil.AI
```

> **Nota de implementação:** o copy não afirma presença em sessão específica — a personalização parte do setor do lead, não de tracking explícito. Referência à sessão assistida exigiria infraestrutura de check-in por sessão (QR code, app mobile) fora do escopo deste case.

---

## 6. Estratégia de Dados e LGPD

### Coleta
- Formulário com campos mínimos: nome, e-mail corporativo, empresa, cargo, telefone (opcional)
- Checkbox LGPD obrigatório (não pré-marcado) com texto de consentimento explícito
- `consent_at` + `consent_ip` registrados no momento do submit

### Enriquecimento
- Apollo.io People Enrichment API: cargo real, setor, tamanho, technographics
- Agente deriva `enrichment_summary` (texto livre injetado no system prompt)
- Re-enriquecimento possível sem tocar no registro principal (tabela 1:1)

### LGPD — Direito de exclusão
- Endpoint `POST /api/leads/deletion-request`
- **Busca todos os registros do titular**: o mesmo email pode estar em múltiplos eventos (`event_id` universal). A query retorna todos os `lead_id` associados ao email; o loop itera e anonimiza cada um. Um `result.data[0]` silencioso violaria a LGPD ao deixar registros não tratados.
- Anonimiza PII em `leads` **para cada `lead_id` encontrado**:
  - `name → "ANONIMIZADO"`
  - `email → gen_random_uuid()::TEXT` (UUID aleatório sem relação com o original — SHA-256 seria reversível por dicionário dado o espaço finito de emails corporativos)
  - `phone → NULL`
  - `company → NULL`
  - `role → NULL` (cargo + timestamp pode identificar em organizações pequenas)
  - `companion_name → NULL` (PII de terceiro que não fez opt-in direto)
  - `consent_ip → NULL` (IP é PII explícita sob LGPD/GDPR — omitir viola o direito de exclusão)
  - `whatsapp_consent_at → NULL`
- **Nula `lead_enrichment`**: tabela com PII mais densa do sistema (`real_role`, `company`, `sector`, `linkedin_url`, `enrichment_summary`). UPDATE em vez de DELETE para preservar a linha (integridade referencial). `ON DELETE CASCADE` não dispara porque o lead é anonimizado, não deletado.
- **Nula `messages.body` e `messages.subject`**: emails renderizados contêm PII direta (nome, cargo, empresa do lead). Mantém metadados (channel, direction, funnel_stage, sent_at, opened_at, clicked_at) para métricas.
- **Deleta `lead_memory`**: registros de conversa deletados imediatamente (contêm PII indireta — nome, cargo e empresa nas mensagens do agente)
- Mantém linha em `leads` e metadados de `messages` para integridade referencial e métricas do evento
- Stage = OPTED_OUT, todos os jobs pendentes → SKIPPED
- Retenção natural (sem solicitação explícita): PII por 24 meses, `lead_memory` por 12 meses

---

## 6.5 Segurança de Integrações

### Autenticação — Endpoints operacionais e de leitura
- Header `X-API-Key` obrigatório em: `GET /api/leads/`, `POST /{lead_id}/checkin`, `POST /{lead_id}/no-show`
- `POST /api/leads/` e `POST /deletion-request` permanecem públicos (inscrição e direito LGPD não requerem autenticação)
- Env var `API_KEY` no Railway; frontend Dashboard inclui o header em todas as chamadas autenticadas
- Implementação em `api/leads.py`: `APIKeyHeader(name="X-API-Key")` via FastAPI `Security` dependency

### Rate limiting — `POST /api/leads`
- `slowapi` com limite de **10 req/min por IP** no endpoint de inscrição
- Evita abuso de custo: cada lead dispara chamada Apollo.io (paga) + email Resend
- Em produção, adicionar Cloudflare proxy na frente do Railway para WAF básico

**`app/limiter.py`** — instância única compartilhada (evita dois `Limiter` independentes que quebram o rate limiting):
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
```

**Wire-up em `main.py`:**
```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.limiter import limiter  # mesma instância

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**Decorator em `api/leads.py`:**
```python
from app.limiter import limiter  # importa, não recria

@router.post("/", status_code=201)
@limiter.limit("10/minute")
async def create_lead(lead_data: LeadCreate, request: Request, ...):
    ...
```

### Verificação HMAC — Webhooks Resend
- Resend assina cada webhook com `svix-signature` no header
- O endpoint `/api/webhooks/resend` deve verificar a assinatura antes de processar:
  ```python
  from svix.webhooks import Webhook
  wh = Webhook(RESEND_WEBHOOK_SECRET)
  wh.verify(payload_bytes, headers)  # levanta WebhookVerificationError se inválido
  ```
- Sem verificação, atores externos podem injetar aberturas/cliques falsos e corromper a régua

### WhatsApp — Opt-in por canal
- WhatsApp Business API exige opt-in explícito separado do consentimento geral LGPD
- O formulário de inscrição deve incluir checkbox não obrigatório e não pré-marcado:
  `[ ] Aceito receber comunicações via WhatsApp sobre o Vigil Summit`
- Campo `whatsapp_consent_at TIMESTAMPTZ` adicionado à tabela `leads` (NULL = não optou)
- O agente só executa `send_whatsapp()` se `whatsapp_consent_at IS NOT NULL`

### Cal.com — Autenticação e configuração
- `schedule_meeting` requer:
  - `CAL_API_KEY`: API key gerada em `app.cal.com/settings/developer/api-keys`
  - `CAL_EVENT_TYPE_ID`: ID do tipo de evento "Demo Vigil.AI 30min" criado previamente no Cal.com
- **Como o link é gerado:** a tool **não** faz `POST /booking` (isso criaria uma reserva real sem o lead escolher o horário). O fluxo correto:
  1. `GET https://api.cal.com/v1/event-types/{CAL_EVENT_TYPE_ID}` → extrai `slug` e `team.slug`
  2. Constrói URL: `https://cal.com/{team_slug}/{event_slug}?name={lead_name}&email={lead_email}`
  3. Esse link abre o calendário Cal.com com nome e email do lead pré-preenchidos — o lead escolhe o horário
- O link é incluído no corpo do email de follow-up; stage → `MEETING_SCHEDULED` ao gerar o link
- **Limitação de escopo:** `MEETING_SCHEDULED` é definido no momento de geração do link, não na confirmação real da reunião. Isso significa que um lead que recebe o link mas nunca agenda aparece como `MEETING_SCHEDULED` no funil. A alternativa — aguardar webhook Cal.com de booking confirmado — exigiria configuração adicional de webhook e está fora do escopo do case. Para o avaliador: o stage reflete "link enviado", não "reunião confirmada".
- Configuração inicial (Dia 1): criar o event type no Cal.com, copiar o ID numérico e salvar como `CAL_EVENT_TYPE_ID`

---

## 7. Decisões Estratégicas

### Decisão 1 — Agente que raciocina vs. automação sequencial
SDK nativo Anthropic com tool use. Alternativas descartadas: n8n (não toma decisões condicionais complexas), LangChain (abstração esconde raciocínio auditável). Referência: Anthropic *"Building Effective Agents"*.

### Decisão 2 — Email primário, WhatsApp como escalada
WhatsApp é invasivo para C-level em primeiro contato. Email é canal preferido por 67% dos executivos sênior B2B (Salesforce B2B Engagement 2024). WhatsApp acionado apenas após 2 e-mails sem abertura. Referência: Outreach.io, Salesloft sequence benchmarks.

### Decisão 3 — Apollo.io vs. pesquisa web pelo agente
Web search é lento (5–15s/lead), inconsistente e viola ToS do LinkedIn. Apollo.io retorna dados estruturados para +275M contatos B2B com cobertura brasileira superior ao Clearbit. Referência: padrão de mercado em stacks Gong/Outreach/HubSpot.

### Decisão 4 — `AsyncIOScheduler` vs. `BackgroundScheduler`
O APScheduler oferece dois schedulers principais: `BackgroundScheduler` (roda em threads separadas) e `AsyncIOScheduler` (roda no event loop asyncio). A escolha foi `AsyncIOScheduler` porque o backend usa FastAPI com uvicorn, que já opera um event loop asyncio. Usar `BackgroundScheduler` exigiria `asyncio.run()` dentro dos jobs para executar `run_agent` (que é `async`), o que causa `RuntimeError: This event loop is already running` quando chamado de dentro de um contexto assíncrono ativo. `AsyncIOScheduler` executa jobs `async` nativamente via `await`, eliminando o problema. Alternativa descartada: Celery + Redis — infraestrutura excessiva para o escopo do case. Referência: documentação oficial APScheduler — *Integrating APScheduler with asyncio*; FastAPI docs sobre async lifecycle e integração com schedulers.

**Bootstrap após restart (Railway redeploy):** O `AsyncIOScheduler` usa jobstore in-memory por padrão — todos os jobs são perdidos em cada redeploy. A estratégia adotada é bootstrap via `lifespan` do FastAPI ao startup:

1. **Jobs futuros** (`run_at > NOW()`): re-registrados com `DateTrigger(run_date=run_at)` — executam no horário original
2. **Jobs atrasados** (`run_at ≤ NOW()`): re-registrados com `DateTrigger(run_date=datetime.now())` — executam imediatamente. **Não** são marcados como `FAILED` antes de tentar; `retry_count` só é incrementado se a execução lançar exceção. Um restart não conta como falha do job.
3. **Cleanup de locks expirados**: `_reload_pending_jobs()` executa `DELETE FROM agent_locks WHERE expires_at < NOW()` para liberar locks de processos que crasharam sem passar pelo `finally`.

---

## 8. Cenário de Escala — 10 eventos simultâneos

A coluna `event_id` em todas as tabelas já habilita multi-tenant. Para escalar:

- **Nível de dados:** cada evento é uma linha em `events` com `sector` específico
- **Nível do agente:** `system_prompt` parametrizado por evento — o mesmo agente recebe contexto diferente por `event_id`
- **Nível de scheduler:** o `AsyncIOScheduler` processa **uma fila global única** — `event_id` é um filtro de condição em `check_and_run_job`, não uma fila separada. Para 10 eventos simultâneos com alto volume, a solução de escala seria adicionar workers paralelos (Celery + Redis) ou particionar o scheduler por `event_id`. Na arquitetura atual, o volume esperado (120 leads × 10 eventos = 1.200 leads) é gerenciável por uma única instância.
- **Nível de deploy:** um backend Railway serve todos os eventos. **Limitação de escala horizontal:** com múltiplas instâncias, cada processo inicializa seu próprio `AsyncIOScheduler` e executa `_reload_pending_jobs()` — todas as instâncias registram e disparam os mesmos jobs em paralelo. O mutex `agent_locks` evita processamento duplo do agente, mas há overhead de tentativas concorrentes. Para escala horizontal real: extrair o scheduler para um processo dedicado (worker Railway separado) ou adotar Celery + Redis com lock distribuído.
- **Zero reescrita de dados:** a arquitetura já suporta multi-tenant pelo design de `event_id` universal

---

## 9. Plano de Execução — 5 dias

| Dia | Foco | Critério de saída |
|---|---|---|
| **1** | Infraestrutura: Supabase schema, FastAPI skeleton, Railway deploy | Lead criado via API, banco respondendo; schema inclui `agent_locks`, `whatsapp_consent_at`, `retry_count`/`max_retries`; Cal.com event type configurado |
| **2** | Agente core: tool use, enriquecimento Apollo.io, lead_memory | Lead enriquecido com contexto persistido; chamadas simultâneas a `run_agent` para o mesmo lead resultam em uma execução e um abort silencioso (mutex via `agent_locks`) |
| **3** | Régua pré-evento completa: Resend, APScheduler persistente, branches | 5 dias de régua simulados com personas sintéticas; critério verificável: todos os branches (confirmou / abriu sem confirmar / não abriu / escalada WhatsApp) executados ao menos uma vez |
| **4** | Régua pós-evento + dashboard Next.js | Follow-up disparando, funil visível no dashboard |
| **5** | Landing page + chatbot + documentação + acesso ramon@pareto.io | Fluxo ponta a ponta demonstrável, README completo |

### Estratégia de simulação — Dia 3

Para testar a régua pré-evento sem esperar semanas, inserir personas sintéticas com `run_at` no passado direto no banco:

```sql
-- Simula job T-14 disparando agora para persona de teste
INSERT INTO scheduled_jobs (lead_id, job_type, run_at, condition, status)
VALUES (
  '<uuid-maria-santos>',
  'CONFIRMATION_T14',
  NOW() - INTERVAL '1 minute',   -- run_at no passado → APScheduler executa imediatamente no bootstrap
  '{}',
  'PENDING'
);
```

Alternativamente, invocar `check_and_run_job(job_id)` diretamente via script de teste para cada branch:
- Branch "confirmou": setar `stage = 'CONFIRMED'` antes de disparar o job T-7
- Branch "abriu sem confirmar": inserir `opened_at` em messages, manter stage `ENRICHED`
- Branch "não abriu": não inserir `opened_at`, disparar job de reenvio
- Branch "escalada WhatsApp": após 2ª sem abertura, verificar que `send_whatsapp` é chamado apenas para leads com `whatsapp_consent_at IS NOT NULL`

---

## 10. Acesso para Avaliação

> ⚠️ URLs abaixo são **placeholders** — serão substituídas após o deploy no Dia 1 e enviadas para ramon@pareto.io.

- **Dashboard:** `[PREENCHER APÓS DEPLOY — ex: https://vigil-summit.vercel.app]` (senha fornecida via e-mail)
- **API Backend:** `[PREENCHER APÓS DEPLOY — ex: https://vigil-summit.up.railway.app]`
- **Supabase:** convite de acesso de leitura para ramon@pareto.io
- **Personas de teste:** 3 leads sintéticos pré-cadastrados cobrindo todos os branches do funil:
  - Maria Santos (CISO, banco, setor financeiro) — fluxo CONFIRMED → ATTENDED
  - Carlos Mendes (CTO, manufatura) — fluxo ATTENDED → MEETING_SCHEDULED
  - Pedro Alves (Diretor de TI, saúde) — fluxo NO_SHOW → reengajamento

---

*Documento gerado em 2026-05-29*
