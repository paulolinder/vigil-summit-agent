# Auditoria de Funcionalidades — Design da Remediação

**Data:** 2026-05-30
**Origem:** Auditoria de produção (paulolinder.com.br) solicitada após o bug "Configurações → Salvar não salva".
**Estado do deploy na auditoria:** `master` == `origin/master` em `b8d5631` (produção roda exatamente este código).
**Revisão:** code-review do spec realizado (feature-dev:code-reviewer). Achados válidos incorporados; ver seção "Achados do review".

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
| 1 | Configurações → "Salvar" não salva | `ConfigPanel` carrega o evento via `GET /api/events`, rota que **não existe** no frontend (só há `/api/events/[id]` PUT). 404 → `.catch()` engole → `event` fica `null` → `handleSave()` faz `if (!event) return`. | Crítica |
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

**Por quê proxy autenticado** (e não apontar o ConfigPanel para o endpoint público
`NEXT_PUBLIC_API_URL/api/events/`): mantém o controle de acesso do dashboard consistente — o
PUT `[id]` já exige sessão; a leitura no painel admin passa a exigir também. Mudança mínima: o
`ConfigPanel` já chama `/api/events`, então nenhuma alteração no componente é necessária.

**Nota de segurança (do review):** o backend `GET /api/events/`
(`backend/app/api/events.py:9-13`) é **público por necessidade** — o `RegistrationForm` da
landing (sem login) o consome cross-origin via `NEXT_PUBLIC_API_URL`, **sem** chave. Portanto
**NÃO** adicionar `Security(_require_api_key)` a esse endpoint (quebraria a inscrição pública).
O proxy autenticado é controle de acesso apenas na camada do dashboard; o header `X-API-Key`
enviado ao backend é inofensivo (o endpoint o ignora). Esta limitação é intencional e
documentada.

### Fix #2 — Seções Speakers + Local na landing

**Arquivo:** `frontend/app/page.tsx`

Adicionar duas `<section>` com `id="speakers"` e `id="local"`, usando os tokens de marca já
presentes (cards `bg-white border border-brand-border border-t-[3px] border-t-brand-teal`,
títulos `text-brand-teal uppercase tracking`, etc.). Conteúdo placeholder honesto e
intencional, não lorem ipsum:
- **Speakers:** título "Palestrantes" + nota "Line-up completo anunciado em breve." e
  3 cards genéricos de perfil de palestrante (CISO, Head de IA, Especialista em Compliance).
- **Local:** título "Local" + "São Paulo · Endereço divulgado aos confirmados." + data do evento.

Posicionamento: após a seção de tracks (`#agenda`) e antes de "Para quem é", para que os
âncoras da navbar façam scroll a conteúdo real.

### Fix #3 — Data e capacidade vindas do evento (fonte única = banco)

Eliminar valores hardcoded de data/capacidade; usar o evento real.

**Landing (`frontend/app/page.tsx`)** — já é `force-dynamic` (server component):
- Buscar o evento no **server component** via `fetch` direto ao backend usando
  **`process.env.BACKEND_API_URL`** (não `getEvents()`/`NEXT_PUBLIC_API_URL`). Motivo (review):
  o padrão server-side do projeto usa `BACKEND_API_URL`; o endpoint é público, então não exige
  chave. As strings de data/capacidade permanecem renderizadas no **server component** (não
  empurrar para estado de client component) — evita hydration mismatch.
- O `RegistrationForm` (client) continua obtendo `eventId` como hoje; opcionalmente recebe
  `capacity` via prop do server component em vez de refetch.
- Derivar uma string de data legível (pt-BR) de `event.event_date` e usar em: badge do hero
  ("São Paulo · {data} · Presencial") e seção Local.
- Usar `event.capacity` em "vagas exclusivas" e "Inscrições limitadas a N participantes".
- Fallback: se o fetch falhar, usar os valores atuais como default (não quebrar a landing).

**Dashboard:**
- `FunnelBoard` (client): o KPI "Total inscritos" mostra "de {capacity} vagas" e o badge do
  kanban mostra a data do evento. Buscar o evento uma vez no `FunnelBoard` via a nova rota
  `GET /api/events` (Fix #1) e passar `capacity`/`eventDate` aos filhos que precisam (KPI
  strip, badge), mantendo o `ConfigPanel` como está.
- **Três** locais hardcoded a substituir em `FunnelBoard.tsx` (review): `'de 120 vagas'` (KPI),
  `'📅 Vigil Summit · 15 Ago 2026'` (badge do kanban) e `'Dia do evento · 15 Ago'` (empty
  state da coluna ATTENDED).
- Formato de data centralizado num helper novo `frontend/lib/format.ts` `formatEventDate(iso)`.
  **Timezone (review):** usar `Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', day:'2-digit', month:'short', year:'numeric' })` — não confiar no timezone do runtime (Vercel roda
  em UTC; `toLocaleDateString` ingênuo pode exibir o dia anterior). O ConfigPanel já grava a
  data com sufixo `-03:00` (`ConfigPanel.tsx:82`), o que mitiga, mas o helper deve ser robusto
  para datas vindas de outras origens.

**Consistência:** após o Fix #1, editar a data/capacidade em Configurações e salvar passa a
refletir no dashboard (próximo load) e na landing (próximo request), pois todos leem a mesma
linha de `events`.

**Data correta = 2026-08-15.** O banco hoje contém `event_date` ≈ 2026-06-29, herdado do seed
`NOW() + INTERVAL '30 days'` (`backend/migrations/001_initial.sql:113-119`). Como o Fix #3 passa
a exibir a data **do banco**, é obrigatório corrigir o registro para 2026-08-15 — senão a
landing mostrará 29/06. Resolução: após o Fix #1 destravar o Salvar, definir a data como
15/08/2026 em Configurações e confirmar a persistência. Sem migration (UPDATE de uma linha via
UI). Capacidade permanece 120.

### Fix #4 — Chatbot (configuração + melhoria de mensagem)

**Configuração (usuário):** definir `ANTHROPIC_API_KEY` na Vercel (Project → Settings →
Environment Variables, **sem** prefixo `NEXT_PUBLIC_`, escopo Production), e redeploy. Passo-a-passo
entregue ao usuário fora do código.

**Código (`frontend/components/landing/ChatbotWidget.tsx`):** o erro chega como
`data: {"error": ...}` no corpo SSE com HTTP 200 (confirmado no review: `route.ts:134` captura e
serializa o erro; o guard `if (!res.ok)` em `ChatbotWidget.tsx:53` não pega esse caso — quem
trata é `if (parsed.error)` em `:75-80`). Trocar a string genérica de `:78`
(`'Desculpe, ocorreu um erro. Tente novamente.'`) por `'Assistente temporariamente indisponível.'`.
Mudança pequena, não bloqueante. Nenhuma outra alteração de código é necessária para o Fix #4.

---

## Arquivos afetados

| Arquivo | Ação |
|---|---|
| `frontend/app/api/events/route.ts` | **Criar** (proxy GET autenticado) |
| `frontend/lib/format.ts` | **Criar** (helper `formatEventDate` com timezone SP) |
| `frontend/app/page.tsx` | Editar (seções Speakers/Local + data/capacidade via `BACKEND_API_URL`) |
| `frontend/components/dashboard/FunnelBoard.tsx` | Editar (3 locais de data/capacidade) |
| `frontend/components/landing/ChatbotWidget.tsx` | Editar (mensagem de erro mais clara) |
| _Banco (via UI)_ | Corrigir `events.event_date` para 2026-08-15 após Fix #1 |

Nenhuma mudança de **código** de backend é necessária (o backend já expõe `GET /api/events/`
público e `PUT` autenticado funcionais).

---

## Achados do review (incorporados)

| Severidade | Achado | Resolução |
|---|---|---|
| Crítico | Server component usaria `getEvents()`/`NEXT_PUBLIC_API_URL` | Trocado para `fetch` direto com `BACKEND_API_URL`; strings ficam no server render (sem hydration mismatch). |
| Crítico (parcial) | Backend `GET /api/events/` é público; rationale do spec era ambíguo | Documentado: público **por necessidade** (inscrição pública depende disso). **Não** securizar o backend GET. |
| Alto | `formatEventDate` sem tratamento de timezone | Especificado `Intl.DateTimeFormat` com `timeZone: 'America/Sao_Paulo'`. |
| Médio | Terceira data hardcoded em `FunnelBoard.tsx:427` ausente do escopo | Adicionada à lista (3 locais). |
| Médio | String exata do ChatbotWidget | Confirmada: trocar `:78`. |

Todas as alegações factuais do spec sobre o código foram **confirmadas** pelo review.

---

## Verificação

1. **Fix #1:** logar no dashboard, ir em Configurações, alterar nome/data/capacidade, Salvar →
   "✓ Salvo com sucesso", e recarregar mostra os valores persistidos. (Validação ao vivo com
   login de teste fornecido pelo usuário.)
2. **Fix #2:** clicar "Speakers" e "Local" na navbar → scroll para as seções correspondentes.
3. **Fix #3:** após corrigir a data para 2026-08-15 em Configurações, o badge do hero e a
   seção Local exibem "15 Ago 2026" e "vagas" reflete `capacity` (120) do banco; alterar a
   capacidade em Configurações e salvar reflete no KPI do dashboard no próximo load. Confirmar
   que o dia exibido é 15 (não 14) — teste do timezone.
4. **Fix #4:** após setar a env var na Vercel e redeploy, enviar mensagem no chat → resposta
   em streaming, sem erro de chave.

---

## Fora de escopo

- Refatoração não relacionada (estrutura de pastas, testes do backend, etc.).
- Tornar a navbar/landing totalmente CMS-driven (apenas a data/capacidade do evento saem do
  hardcode; demais textos permanecem estáticos).
- Painel de edição de Speakers/Local no dashboard (conteúdo placeholder estático por ora).
- Securizar o backend `GET /api/events/` (intencionalmente público).
