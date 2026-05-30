# Auditoria de Funcionalidades — Design da Remediação

**Data:** 2026-05-30
**Origem:** Auditoria de produção (paulolinder.com.br) solicitada após o bug "Configurações → Salvar não salva".
**Estado do deploy na auditoria:** `master` == `origin/master` em `b8d5631` (produção roda exatamente este código).

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

## Escopo aprovado

Corrigir os 4 itens. Fix #4 é majoritariamente configuração (env var na Vercel, feita pelo
usuário); o código recebe apenas uma melhoria de mensagem de erro.

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
`NEXT_PUBLIC_API_URL/api/events/`): mantém o modelo de segurança do dashboard consistente —
o PUT `[id]` já exige sessão; a leitura no painel admin deve exigir também. Mudança mínima:
o `ConfigPanel` já chama `/api/events`, então nenhuma alteração no componente é necessária.

**Resultado:** `event` deixa de ser `null`; "Salvar" passa a enviar o PUT e persistir.

### Fix #2 — Seções Speakers + Local na landing

**Arquivo:** `frontend/app/page.tsx`

Adicionar duas `<section>` com `id="speakers"` e `id="local"`, usando os tokens de marca já
presentes (cards `bg-white border border-brand-border border-t-[3px] border-t-brand-teal`,
títulos `text-brand-teal uppercase tracking`, etc.). Conteúdo placeholder honesto e
intencional, não lorem ipsum:
- **Speakers:** título "Palestrantes" + nota "Line-up completo anunciado em breve." e
  3 cards genéricos de trilha/perfil de palestrante (CISO, Head de IA, Especialista em Compliance).
- **Local:** título "Local" + "São Paulo · Endereço divulgado aos confirmados." + data do evento.

Posicionamento: após a seção de tracks (`#agenda`) e antes de "Para quem é", para que os
âncoras da navbar façam scroll a conteúdo real.

### Fix #3 — Data e capacidade vindas do evento (fonte única = banco)

Eliminar valores hardcoded de data/capacidade; usar o evento real.

**Landing (`frontend/app/page.tsx`)** — já é `force-dynamic`:
- Buscar o evento no server component via `getEvents()` (ou fetch direto ao backend público).
- Derivar uma string de data legível (pt-BR) de `event.event_date` e usar em: badge do hero
  ("São Paulo · {data} · Presencial") e seção Local.
- Usar `event.capacity` em "vagas exclusivas" e "Inscrições limitadas a N participantes".
- Fallback: se o fetch falhar, usar os valores atuais como default (não quebrar a landing).

**Dashboard:**
- `FunnelBoard`: o KPI "Total inscritos" mostra "de {capacity} vagas" e o badge do kanban
  mostra a data do evento. `FunnelBoard` já é cliente; pode buscar o evento via a nova rota
  `GET /api/events` (Fix #1) no mesmo `useEffect`, ou receber via prop. Decisão de
  implementação: buscar uma vez no `FunnelBoard` e passar `capacity`/`eventDate` para os
  filhos que precisam (KPI strip, badge), mantendo o `ConfigPanel` como está.
- Formato de data centralizado num helper (`lib/format.ts` `formatEventDate(iso)`), evitando
  duplicação de `toLocaleDateString` espalhada.

**Consistência:** após o Fix #1, editar a data/capacidade em Configurações e salvar passa a
refletir no dashboard (próximo load) e na landing (próximo request), pois todos leem a mesma
linha de `events`.

### Fix #4 — Chatbot (configuração + melhoria de mensagem)

**Configuração (usuário):** definir `ANTHROPIC_API_KEY` na Vercel (Project → Settings →
Environment Variables, **sem** prefixo `NEXT_PUBLIC_`, escopo Production), e redeploy. Passo-a-passo
entregue ao usuário fora do código.

**Código (`frontend/components/landing/ChatbotWidget.tsx`):** quando o stream retornar o erro
de chave ausente, exibir mensagem clara ("Assistente temporariamente indisponível.") em vez de
genérica. Mudança pequena, não bloqueante.

---

## Arquivos afetados

| Arquivo | Ação |
|---|---|
| `frontend/app/api/events/route.ts` | **Criar** (proxy GET autenticado) |
| `frontend/app/page.tsx` | Editar (seções Speakers/Local + data/capacidade do evento) |
| `frontend/components/dashboard/FunnelBoard.tsx` | Editar (data/capacidade do evento) |
| `frontend/lib/format.ts` | **Criar** (helper `formatEventDate`) |
| `frontend/components/landing/ChatbotWidget.tsx` | Editar (mensagem de erro mais clara) |

Nenhuma mudança de backend é necessária (o backend já expõe `GET /api/events/` e PUT funcionais).

---

## Verificação

1. **Fix #1:** logar no dashboard, ir em Configurações, alterar nome/data/capacidade, Salvar →
   "✓ Salvo com sucesso", e recarregar mostra os valores persistidos. (Validação ao vivo com
   login de teste fornecido pelo usuário.)
2. **Fix #2:** clicar "Speakers" e "Local" na navbar → scroll para as seções correspondentes.
3. **Fix #3:** badge do hero e "vagas" refletem o evento do banco; alterar capacidade em
   Configurações e salvar reflete no KPI do dashboard.
4. **Fix #4:** após setar a env var na Vercel e redeploy, enviar mensagem no chat → resposta
   em streaming, sem erro de chave.

---

## Fora de escopo

- Refatoração não relacionada (estrutura de pastas, testes do backend, etc.).
- Tornar a navbar/landing totalmente CMS-driven (apenas a data/capacidade do evento saem do
  hardcode; demais textos permanecem estáticos).
- Painel de edição de Speakers/Local no dashboard (conteúdo placeholder estático por ora).
