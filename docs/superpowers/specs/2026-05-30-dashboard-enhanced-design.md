# Dashboard Enhanced — Spec

**Data:** 2026-05-30
**Projeto:** Case AI Engineer — Pareto × Vigil.AI
**Escopo:** Evolução do dashboard de "básico" para "command center" — corrige gaps do spec original + adiciona 4 features novas

---

## 1. Contexto e Motivação

O dashboard atual (`/dashboard`) tem KPI strip + kanban funcional, mas apresenta:

- **Gaps do spec**: cores `sky-700` ao invés de `navy-700` (`#0369a1`), KPIs incompletos (falta "delta semana" em reuniões e "X com email aberto" em no-show)
- **Ausência de features de impacto**: nenhuma visualização do funil de conversão, nenhum log de atividade do agente, sem drill-down de lead, sem filtros

Este spec cobre as correções + 4 novas features, todas usando dados já disponíveis no banco — sem mudanças de schema ou backend.

---

## 2. Layout Final

```
┌─────────────────────────────────────────────────────┐
│  NAVBAR (sticky, 56px, navy corrigido)              │
├─────────────────────────────────────────────────────┤
│  KPI STRIP (4 cards, grid-cols-4)                   │
├──────────────────────────┬──────────────────────────┤
│  FUNIL DE CONVERSÃO      │  ATIVIDADE DO AGENTE     │
│  (FunnelChart, 60%)      │  (ActivityFeed, 40%)     │
├─────────────────────────────────────────────────────┤
│  FILTER BAR (busca + chips)                         │
├─────────────────────────────────────────────────────┤
│  KANBAN (scroll-x, 7 colunas)                       │
└─────────────────────────────────────────────────────┘

Drawer de lead: posição fixed right, 380px, z-index 200
Overlay escurecido atrás do drawer ao abrir
```

---

## 3. Correções do Spec Original

### 3.1 Cores — `sky-700` → `navy-700`

Estender `tailwind.config.ts` com token `navy`:

```ts
colors: {
  navy: {
    700: '#0369a1',
    950: '#0f172a',
  }
}
```

Substituir em todos os arquivos do dashboard:
- `border-sky-700` → `border-navy-700`
- `text-sky-700` → `text-navy-700`
- `hover:border-sky-700` → `hover:border-navy-700`

Afeta: `FunnelBoard.tsx`, `LeadCard.tsx`, `Navbar.tsx`.

### 3.2 KPI "Reuniões agendadas" — adicionar delta semana

Computar `meetingsDeltaWeek`: contar leads que entraram em `MEETING_SCHEDULED` ou `CONVERTED` na última semana. Como não há timestamp de mudança de estágio, usar a data da última mensagem com `clicked_at` como proxy (clique no Cal.com ≈ reunião agendada).

Exibir: `+N essa semana` em amber-600 abaixo do sub-label.

### 3.3 KPI "No-show" — adicionar "X com email aberto"

De `allMessages` (ver seção 4.1), filtrar mensagens de leads em stage `NO_SHOW` que têm `opened_at != null`. Contar leads únicos com email aberto.

Exibir: `N com email aberto` em green-600 abaixo do sub-label.

---

## 4. Arquitetura de Dados

### 4.1 Mudança na query de mensagens (`FunnelBoard.tsx`)

**Atual:** busca last-per-lead para `messageMap`.

**Novo:** manter `messageMap` (para sinal nos cards) + armazenar `allMessages: Message[]` completo para drawer e feed.

Estender a query para incluir `subject`:

```ts
supabase
  .from('messages')
  .select('lead_id, sent_at, opened_at, clicked_at, subject')
  .in('lead_id', ids)
  .eq('direction', 'OUT')
  .order('sent_at', { ascending: false })
```

**Risco:** PostgREST retorna HTTP 400 se a coluna `subject` não existir. A implementação deve verificar a existência da coluna antes de adicioná-la ao select, ou usar um bloco try/catch que re-tente sem `subject` em caso de erro. Alternativa mais segura: verificar o schema via `supabase.from('messages').select('*').limit(1)` na inicialização e ajustar a query dinamicamente. Para o MVP, usar try/catch é suficiente.

### 4.2 Novos tipos em `lib/types.ts`

```ts
export type Message = {
  lead_id: string
  sent_at: string
  opened_at: string | null
  clicked_at: string | null
  subject: string | null
}

export type ActivityEvent = {
  type: 'sent' | 'opened' | 'clicked'
  timestamp: string
  leadId: string
  leadName: string
}
```

`LastMessage` permanece inalterado (usado para sinal nos cards).

### 4.3 Derivação do ActivityFeed (sem nova tabela)

```
Para cada Message em allMessages:
  1. type='sent'    → timestamp = sent_at
  2. type='opened'  → timestamp = opened_at  (se não null)
  3. type='clicked' → timestamp = clicked_at (se não null)

Enriquecer cada evento com o nome do lead via leadMap.
Ordenar todos por timestamp DESC.
Tomar os 20 mais recentes.
```

Labels por tipo:
| type | label |
|---|---|
| `sent` | "Email enviado para **{Lead}**" |
| `opened` | "**{Lead}** abriu o email" |
| `clicked` | "**{Lead}** clicou no link Cal.com" |

Cor do dot:
| type | cor |
|---|---|
| `clicked` | `bg-amber-500` |
| `opened` | `bg-green-500` |
| `sent` | `bg-navy-700` |

O Realtime existente em `FunnelBoard` observa apenas a tabela `leads`. Quando um lead muda de estágio, o `useEffect` re-fetcha mensagens e enriquecimentos, re-derivando o feed. Isso cobre a maioria dos eventos relevantes (enriquecimento completo, stage change). Para eventos de abertura de email (`opened_at`, `clicked_at`) em tempo real, seria necessário adicionar uma subscription Realtime na tabela `messages` — mas como esses eventos são gerados pelo backend assíncrono e o dashboard já tem polling implícito via stage changes, a atualização eventual é aceitável para o MVP.

### 4.4 Estado de seleção do lead (drawer)

```ts
const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null)
```

Passado como `onLeadClick` para cada `LeadCard`. Quando `selectedLeadId != null`, renderizar `<LeadDrawer>`.

---

## 5. Novos Componentes

### 5.1 `components/dashboard/FunnelChart.tsx`

**Props:** `leads: BaseLead[]`

**Lógica:** contar leads por stage, calcular % relativo ao total.

**Renderização:** lista de 7 linhas com barra CSS pura (sem biblioteca de charts):
- Label do stage (10px, slate-400, right-align, 72px fixo)
- Barra `<div>` com `width: X%` e cor do stage
- Contagem (10px bold)
- Taxa de conversão para o próximo stage (9px, verde se ≥ 70%, âmbar se 50-70%, vermelho se < 50%)

Rodapé com resumo: "Taxa de comparecimento: X% · Conversão total: Y%"

Sem dependências externas — CSS puro.

### 5.2 `components/dashboard/ActivityFeed.tsx`

**Props:** `events: ActivityEvent[]`

**Renderização:** lista de até 20 itens com dot colorido + texto + tempo relativo.

**Tempo relativo:** função local `relativeTime(ts: string): string` — "agora", "Xmin", "Xh", "Xd" sem biblioteca.

Link "Ver histórico completo" no rodapé — por ora scroll dentro do componente (sem nova página).

### 5.3 `components/dashboard/FilterBar.tsx`

**Props:**
```ts
{
  search: string
  onSearchChange: (v: string) => void
  sectorFilter: string | null
  onSectorChange: (v: string | null) => void
  decisionMakerOnly: boolean
  onDecisionMakerChange: (v: boolean) => void
  totalVisible: number
  totalAll: number
}
```

**Renderização:**
- Input de busca (filtra por `name` e `company`, case-insensitive, client-side)
- Chip "Setor ▾" com dropdown dos setores únicos presentes nos enrichments
- Chip "Decisores" toggle (filtra `is_decision_maker === true`)
- Contador "N leads · M filtros ativos"

**Filtragem:** aplicada em `FunnelBoard` antes de passar `richLeads` para o kanban. Não afeta os KPIs nem o FunnelChart (que usam `leads` brutos).

### 5.4 `components/dashboard/LeadDrawer.tsx`

**Props:**
```ts
{
  lead: RichLead
  messages: Message[]  // allMessages.filter(m => m.lead_id === lead.id)
  onClose: () => void
}
```

**Seções:**

1. **Header** (padding 16px 20px, border-bottom)
   - Nome (Inter 800, 15px, navy-950)
   - Cargo · Empresa · Porte (Inter 400, 11px, slate-600)
   - Tags (mesmo componente de tags do LeadCard)
   - Botão ✕ (float right, color slate-400)

2. **Stage bar** (bg conforme stage, 8px padding)
   - Dot animado + stage label uppercase

3. **Perfil enriquecido** (grid 2×2)
   - Setor · Porte da empresa · Decisor · Sinal de interesse em segurança (`is_decision_maker` + sinais do cargo como CISO/CTO)

4. **Histórico de mensagens**
   - Lista ordenada por `sent_at DESC`
   - Cada item: borda esquerda colorida (green se opened/clicked, navy se só sent) + subject + data + status icons (✓ Aberto · ✓ Link clicado)
   - Fallback se sem mensagens: "Nenhuma mensagem enviada ainda"

**Comportamento:**
- `position: fixed; top: 0; right: 0; width: 380px; height: 100vh; z-index: 201`
- Overlay `z-index: 200` fecha ao clicar fora
- Transição: `transform: translateX(0)` com `transition: transform 200ms ease`
- Fecha com `Escape` (keydown listener)
- Não bloqueia scroll do kanban

---

## 6. Mudanças em Arquivos Existentes

| Arquivo | O que muda |
|---|---|
| `tailwind.config.ts` | Adicionar token `navy: { 700: '#0369a1', 950: '#0f172a' }` |
| `lib/types.ts` | Adicionar tipos `Message` e `ActivityEvent` |
| `components/dashboard/FunnelBoard.tsx` | + estado `allMessages`, `selectedLeadId`, `search`, `sectorFilter`, `decisionMakerOnly`; renderizar `FunnelChart`, `ActivityFeed`, `FilterBar`, `LeadDrawer`; passar `onLeadClick` para cards |
| `components/dashboard/LeadCard.tsx` | + prop `onClick: () => void`; substituir `border-sky-700` por `border-navy-700` |
| `components/ui/Navbar.tsx` | Corrigir altura para `h-14` (56px) no variant dashboard |

---

## 7. Novos Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `components/dashboard/FunnelChart.tsx` | Gráfico de funil CSS puro |
| `components/dashboard/ActivityFeed.tsx` | Feed de atividade derivado de messages |
| `components/dashboard/FilterBar.tsx` | Busca + chips de filtro client-side |
| `components/dashboard/LeadDrawer.tsx` | Drawer de detalhes do lead |

---

## 8. Restrições e Decisões

- **Zero mudanças de backend/schema**: toda a nova funcionalidade usa dados já existentes (`messages`, `lead_enrichment`, `leads`). Nenhuma migration necessária.
- **Sem biblioteca de charts**: `FunnelChart` usa divs CSS com `width: X%`. Evita dependência, carrega instantâneo, fácil de estilizar.
- **KPIs calculados sobre dados brutos**: filtros do `FilterBar` não afetam KPIs nem `FunnelChart` — mostram sempre o total real do funil.
- **Supabase Realtime existente** cobre todos os novos componentes: quando `leads` muda, `FunnelBoard` re-fetcha mensagens e enriquecimentos, re-derivando feed e chart automaticamente.
- **`subject` da mensagem**: se a coluna não existir, o drawer exibe fallback "Email enviado" — tratado no componente com `message.subject ?? 'Email enviado'`.

---

*Documento gerado em 2026-05-30 — aprovado em sessão de brainstorming com o usuário*
