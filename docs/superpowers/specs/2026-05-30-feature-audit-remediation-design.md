# Auditoria de Funcionalidades — Design da Remediação

**Data:** 2026-05-30
**Origem:** Auditoria de produção (paulolinder.com.br) solicitada após o bug "Configurações → Salvar não salva".
**Estado do deploy na auditoria:** `master` == `origin/master` em `b8d5631` (produção rodava exatamente este código).
**Revisão:** code-review do spec realizado (feature-dev:code-reviewer). Achados válidos incorporados; ver "Achados do review".
**Addendum:** ver "Implementation notes / addendum (2026-05-31)" no fim — registra onde o que foi de fato entregue divergiu deste design.

---

## Contexto

Auditoria conduzida ao vivo contra produção (paulolinder.com.br) via Playwright + análise
estática do código. Objetivo: verificar se todos os botões, funções, ferramentas e utilidades
estão funcionando.

### O que está OK (verificado ao vivo)
- Landing: hero, tracks, público-alvo, footer.
- Navbar "Agenda" e "Garantir vaga"; CTAs do hero.
- Formulário de inscrição: carrega o evento, habilita o botão ao marcar consentimento,
  e alcança o backend cross-origin (CORS + `NEXT_PUBLIC_API_URL` configurados).
- Login (`/login`) e proteção de `/dashboard` (middleware redireciona quando sem sessão).
- Rotas autenticadas retornam 401 sem sessão (comportamento correto).
- Página de exclusão LGPD (`/deletion-confirm`).

### Bugs confirmados
| # | Bug | Causa raiz | Severidade |
|---|---|---|---|
| 1 | Configurações → "Salvar" não salva | `ConfigPanel` carrega o evento via `GET /api/events`, rota que **não existe** no frontend (só há `/api/events/[id]` PUT). 404 → `.catch()` engole → `event` fica `null` → `handleSave()` faz `if (!event) return`. **(Ver addendum: havia uma 2ª camada — o backend usava a chave ANON e o PUT batia em RLS.)** | Crítica |
| 2 | Links "Speakers" e "Local" da navbar não fazem nada | Âncoras `#speakers` e `#local` não existem na página. | Média |
| 3 | Data "15 Ago 2026" e "120 vagas" hardcoded | Landing e dashboard têm valores fixos no código; o que se edita em Configurações nunca é exibido, e diverge da data real do banco usada pela régua. | Média |
| 4 | Chatbot quebrado | `/api/chat` retorna `ANTHROPIC_API_KEY não configurada` (env var ausente na Vercel). Código está correto. | Crítica |

---

## Decisões do usuário

- **Fix #1:** manter proxy **autenticado** (não apontar para endpoint público).
- **Fix #2:** seções com conteúdo **placeholder genérico** (sem nomes/endereço reais ainda).
- **Fix #3:** data correta do evento = **2026-08-15 (15 Ago 2026)**; capacidade = 120.
- **Fix #4:** usuário configura `ANTHROPIC_API_KEY` na Vercel.

---

## Design das correções

### Fix #1 — Rota `GET /api/events` (proxy autenticado)

**Arquivo novo:** `frontend/app/api/events/route.ts`

Proxy GET autenticado seguindo o padrão idêntico de `frontend/app/api/leads/route.ts`:
1. `createSupabaseServerClient()` → `getUser()`; 401 se sem sessão.
2. Lê `BACKEND_API_URL` / `BACKEND_API_KEY`; 500 se ausentes.
3. `fetch(\`${backendUrl}/api/events/\`, { headers: { 'X-API-Key': backendKey }, cache: 'no-store' })`.
4. Repassa `data` e `status`.

**Por quê proxy autenticado:** mantém o controle de acesso do dashboard consistente — o PUT
`[id]` já exige sessão; a leitura no painel admin passa a exigir também. O `ConfigPanel` já
chama `/api/events`, então nenhuma alteração no componente é necessária.

**Nota de segurança (do review):** o backend `GET /api/events/` (`backend/app/api/events.py`) é
**público por necessidade** — o `RegistrationForm` da landing (sem login) o consome cross-origin
via `NEXT_PUBLIC_API_URL`, **sem** chave. Portanto **NÃO** adicionar `Security(_require_api_key)`
a esse endpoint (quebraria a inscrição pública). O proxy autenticado é controle de acesso apenas
na camada do dashboard; o `X-API-Key` enviado ao backend é inofensivo (o endpoint o ignora).

### Fix #2 — Seções Speakers + Local na landing

**Arquivo:** `frontend/app/page.tsx`

Adicionar duas `<section>` com `id="speakers"` e `id="local"`, usando os tokens de marca já
presentes. Conteúdo placeholder honesto e intencional, não lorem ipsum:
- **Speakers:** título "Palestrantes" + "Line-up completo anunciado em breve." e 3 cards
  genéricos de perfil (CISO, Head de IA, Especialista em Compliance).
- **Local:** título "Local" + "São Paulo · Endereço divulgado aos confirmados." + data do evento.

Posicionamento: após a seção de tracks (`#agenda`) e antes de "Para quem é".

### Fix #3 — Data e capacidade vindas do evento (fonte única = banco)

**Landing (`frontend/app/page.tsx`)** — server component `force-dynamic`:
- Buscar o evento no server component via `fetch` direto ao backend usando `BACKEND_API_URL`
  (não `getEvents()`/`NEXT_PUBLIC_API_URL`). Strings ficam renderizadas no server (sem hydration
  mismatch). **(Ver addendum: a implementação extraiu isso para `lib/event.ts`.)**
- Derivar data legível (pt-BR) de `event.event_date` para badge do hero e seção Local.
- Usar `event.capacity` em "vagas exclusivas" e "Inscrições limitadas a N participantes".
- Fallback: se o fetch falhar, usar os valores atuais como default.

**Dashboard (`FunnelBoard`, client):** KPI "de {capacity} vagas" e badge com a data; buscar via
a rota `/api/events`. **Três** locais hardcoded a substituir: `'de 120 vagas'` (KPI),
`'📅 Vigil Summit · 15 Ago 2026'` (badge) e `'Dia do evento · 15 Ago'` (empty state ATTENDED).

**Helper de data:** `frontend/lib/format.ts` `formatEventDate(iso)` com
`Intl.DateTimeFormat(..., { timeZone: 'America/Sao_Paulo' })` — não confiar no timezone do
runtime (Vercel = UTC; `toLocaleDateString` ingênuo pode exibir o dia anterior).

**Data correta = 2026-08-15.** O banco tinha `event_date` ≈ 2026-06-29 (seed `NOW()+30d`,
`backend/migrations/001_initial.sql`). Como o Fix #3 exibe a data **do banco**, é obrigatório
corrigir o registro para 2026-08-15. **(Ver addendum: a correção foi feita via UPDATE direto no
banco, não pela UI, pois o Salvar ainda estava quebrado pela 2ª camada do Fix #1.)**

### Fix #4 — Chatbot (configuração + melhoria de mensagem)

**Configuração (usuário):** definir `ANTHROPIC_API_KEY` na Vercel (sem prefixo `NEXT_PUBLIC_`,
escopo Production) + redeploy.

**Código (`frontend/components/landing/ChatbotWidget.tsx`):** o erro chega como
`data: {"error": ...}` no corpo SSE com HTTP 200; quem trata é `if (parsed.error)`. Trocar a
string genérica por `'Assistente temporariamente indisponível.'`.

---

## Arquivos afetados (design original)

| Arquivo | Ação |
|---|---|
| `frontend/app/api/events/route.ts` | **Criar** (proxy GET autenticado) |
| `frontend/lib/format.ts` | **Criar** (helper `formatEventDate` com timezone SP) |
| `frontend/lib/event.ts` | **Criar** (helper compartilhado `getEventServer`/`getEventClient` — ver addendum §3) |
| `frontend/app/page.tsx` | Editar (seções Speakers/Local + data/capacidade, via `lib/event.ts`) |
| `frontend/components/dashboard/FunnelBoard.tsx` | Editar (3 locais de data/capacidade, via `lib/event.ts`) |
| `frontend/components/landing/ChatbotWidget.tsx` | Editar (mensagem de erro mais clara) |
| _Banco_ | Corrigir `events.event_date` para 2026-08-15 |

> ⚠️ O design original afirmava "nenhuma mudança de código de backend é necessária". **Isso se
> provou incorreto** — ver addendum. A lista completa de arquivos realmente afetados está lá.

---

## Achados do review (do spec, incorporados antes da implementação)

| Severidade | Achado | Resolução |
|---|---|---|
| Crítico | Server component usaria `getEvents()`/`NEXT_PUBLIC_API_URL` | Trocado para `BACKEND_API_URL`; strings no server render. |
| Crítico (parcial) | Backend `GET /api/events/` público; rationale ambíguo | Documentado: público **por necessidade**. Não securizar. |
| Alto | `formatEventDate` sem timezone | `Intl.DateTimeFormat` com `America/Sao_Paulo`. |
| Médio | 3ª data hardcoded em `FunnelBoard` ausente do escopo | Adicionada (3 locais). |
| Médio | String exata do ChatbotWidget | Confirmada. |

---

## Verificação

1. **Fix #1:** Configurações → alterar data/capacidade → Salvar → "✓ Salvo" e persiste no reload.
2. **Fix #2:** clicar "Speakers"/"Local" → scroll para as seções.
3. **Fix #3:** data e vagas refletem o banco; dia exibido é 15 (não 14) — teste de timezone.
4. **Fix #4:** após a env var na Vercel + redeploy, chat responde em streaming sem erro de chave.

---

## Fora de escopo

- Refatoração não relacionada (estrutura de pastas, testes do backend, etc.).
- Tornar a navbar/landing totalmente CMS-driven (apenas data/capacidade saem do hardcode).
- Painel de edição de Speakers/Local no dashboard (placeholder estático por ora).
- Securizar o backend `GET /api/events/` (intencionalmente público).

---

## Implementation notes / addendum (2026-05-31)

> Registro do que **realmente** foi entregue, onde divergiu deste design. O design acima fica como
> registro do que foi *planejado*; este addendum é a fonte de verdade do que *shipou*.

### 1. Fix #1 tinha DUAS camadas (o design só viu a primeira)

O design tratou "Salvar não salva" como causa única (rota frontend ausente). A causa real:
- **Camada A (frontend):** faltava `GET /api/events` → `event` nulo → `handleSave` retornava cedo.
  Resolvida pelo proxy (commit `2175836`).
- **Camada B (backend/RLS):** o backend rodava com a chave **anon** do Supabase. Com RLS ativo, o
  `PUT /api/events/{id}` (`update_event`) fazia um UPDATE que afetava **0 linhas** → `result.data`
  vazio → 404 "Evento não encontrado". O Salvar só funcionou de fato após trocar `SUPABASE_KEY`
  pela chave **service_role** no Railway. Verificado ao vivo (capacity 120→150→120 persistiu).

A afirmação do design "nenhuma mudança de backend é necessária" estava **errada**.

### 2. Workstream de backend (ausente do design, surgiu do code review do backend)

| Arquivo | Mudança | Commit |
|---|---|---|
| `backend/app/db/models.py` | Novo modelo `EventUpdate` (Pydantic): valida `name`, `event_date` ISO-8601, `capacity` (>0, ≤100000) | `4c4e2c2` |
| `backend/app/api/events.py` | `update_event` recebe `EventUpdate` (era `dict` cru), `model_dump(exclude_none=True)` | `4c4e2c2` |
| `backend/app/api/webhooks.py` | Webhook Cal.com `BOOKING_CREATED` passa a usar o RPC `atomic_transition_lead_stage` (era UPDATE cru de stage) | `4c4e2c2` |
| `backend/app/agent/tool_executor.py` | `update_lead_stage` e enriquecimento (`_enrich_lead`) usam o RPC atômico (eram UPDATE cru) | `4c4e2c2`, `dfdc6d2` |
| `backend/migrations/002_security_definer_rpcs.sql` | Os 4 guard RPCs recriados como `SECURITY DEFINER` + `search_path` fixo | `74a0d1e`, `dfdc6d2` |

Validado ao vivo (Railway redeployado): `PUT` com `capacity:0` ou `event_date` inválido → **422**
com mensagem por campo (antes era 500 opaco); `capacity` válido → 200 e persiste.

**Incidente registrado:** a 1ª versão da migration 002 reconstruiu os corpos das RPCs de memória e
referenciou colunas inexistentes (`leads.updated_at`, `scheduled_jobs.updated_at`); aplicada no
banco vivo, quebrou transições de stage por ~2 min até reverter com os corpos exatos
(`pg_get_functiondef`). Lição: para `CREATE OR REPLACE` de função existente, sempre partir da
definição real do banco. Colunas reais: `scheduled_jobs.started_at`, `agent_locks.locked_at`;
`leads` NÃO tem `updated_at`.

### 3. `frontend/lib/event.ts` (ausente da tabela "Arquivos afetados")

O refactor `6ec0606` extraiu um helper compartilhado `frontend/lib/event.ts` com
`getEventServer()` (landing/server, lê `BACKEND_API_URL`, com fallback para `NEXT_PUBLIC_API_URL`),
`getEventClient()` (dashboard/client, lê `/api/events`), constantes
`DEFAULT_CAPACITY`/`DEFAULT_EVENT_DATE_LABEL` e tipo `EventInfo`.
Substituiu o `getEvent()` inline que o design esboçava e eliminou os literais de fallback
duplicados. `page.tsx` e `FunnelBoard.tsx` consomem esse helper. Também: `EventConfig.event_date`
tipado como `string | null` (batia com o schema) e `console.warn` nos caminhos de fallback.

### 4. Correção da data foi via banco, não pela UI

O design dizia "corrigir em Configurações". Como o Salvar estava quebrado pela camada B, a data foi
corrigida por `UPDATE` direto (Supabase MCP) → `2026-08-15T12:00:00+00:00`. Confirmado ao vivo.

### 5. Confirmado ainda válido

- `GET /api/events/` do backend permanece **público** (sem `Security`), como o "Fora de escopo" diz.
- O padrão 404-on-empty em `update_event` continua, mas com service_role só dispara para evento
  realmente inexistente. Era exatamente o mecanismo que mascarava o bug da chave anon (camada B).

### Estado final (2026-05-31)
Frontend no ar (Vercel) e backend no ar (Railway redeployado). Tudo validado ao vivo, exceto o
chatbot e o agente, que aguardam `ANTHROPIC_API_KEY` na Vercel e no Railway respectivamente.
