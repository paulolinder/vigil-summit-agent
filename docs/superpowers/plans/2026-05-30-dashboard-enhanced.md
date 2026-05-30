# Dashboard Enhanced — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evoluir o dashboard de um kanban básico para um command center com gráfico de funil, feed de atividade do agente, filtros e drawer de detalhes do lead.

**Architecture:** Todos os dados já existem no banco (`leads`, `messages`, `lead_enrichment`). As novas features derivam eventos do agente da tabela `messages` existente e filtram client-side sem nenhuma mudança de schema. O `FunnelBoard.tsx` orquestra tudo; 4 novos componentes focados recebem props simples.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript, Tailwind CSS, Supabase JS client (já configurado em `lib/supabase.ts`)

**Spec:** `docs/superpowers/specs/2026-05-30-dashboard-enhanced-design.md`

---

## File Map

| Ação | Arquivo | Responsabilidade |
|---|---|---|
| Modificar | `frontend/tailwind.config.ts` | Adicionar tokens `navy-700` e `navy-950` |
| Modificar | `frontend/lib/types.ts` | Adicionar `BaseLead`, `Message`, `ActivityEvent` |
| Modificar | `frontend/components/ui/Navbar.tsx` | Corrigir altura dashboard (56px) |
| Modificar | `frontend/components/dashboard/LeadCard.tsx` | Cor navy + prop `onClick` |
| Criar | `frontend/components/dashboard/FunnelChart.tsx` | Gráfico de funil CSS puro |
| Criar | `frontend/components/dashboard/ActivityFeed.tsx` | Feed de atividade derivado de messages |
| Criar | `frontend/components/dashboard/FilterBar.tsx` | Busca + chips client-side |
| Criar | `frontend/components/dashboard/LeadDrawer.tsx` | Drawer de detalhes do lead |
| Modificar | `frontend/components/dashboard/FunnelBoard.tsx` | Orquestrar tudo + KPIs completos |

---

## Task 1: Tokens de cor + tipos base

**Files:**
- Modify: `frontend/tailwind.config.ts`
- Modify: `frontend/lib/types.ts`

- [ ] **1.1 — Adicionar token `navy` ao Tailwind**

  Abrir `frontend/tailwind.config.ts`. Substituir o bloco `theme.extend` por:

  ```ts
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        playfair: ['var(--font-playfair)', 'Georgia', 'serif'],
      },
      colors: {
        navy: {
          700: '#0369a1',
          950: '#0f172a',
        },
      },
    },
  },
  ```

- [ ] **1.2 — Adicionar `BaseLead`, `Message` e `ActivityEvent` a `lib/types.ts`**

  Abrir `frontend/lib/types.ts` e adicionar ao final do arquivo:

  ```ts
  export type BaseLead = {
    id: string
    name: string | null
    role: string | null
    company: string | null
    stage: string
  }

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

- [ ] **1.3 — Commit**

  ```bash
  git add frontend/tailwind.config.ts frontend/lib/types.ts
  git commit -m "feat(dashboard): add navy color tokens and extended types"
  ```

---

## Task 2: Corrigir componentes existentes (cores + onClick)

**Files:**
- Modify: `frontend/components/ui/Navbar.tsx`
- Modify: `frontend/components/dashboard/LeadCard.tsx`

- [ ] **2.1 — Corrigir altura do Navbar variant dashboard**

  Em `frontend/components/ui/Navbar.tsx`, a `<nav>` tem `h-16` (64px). A classe `h-16` não muda para a landing — apenas o variant dashboard deve usar `h-14` (56px). Substituir:

  ```tsx
  <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
    <div className="max-w-screen-xl mx-auto px-8 h-16 flex items-center justify-between">
  ```

  por:

  ```tsx
  <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
    <div className={`max-w-screen-xl mx-auto px-8 flex items-center justify-between ${variant === 'dashboard' ? 'h-14' : 'h-16'}`}>
  ```

- [ ] **2.2 — Corrigir LeadCard: cor navy + prop onClick**

  Substituir o conteúdo completo de `frontend/components/dashboard/LeadCard.tsx` por:

  ```tsx
  import type { RichLead } from '@/lib/types'

  type TagColor = 'navy' | 'green' | 'amber' | 'red' | 'slate'
  type Tag = { label: string; color: TagColor }
  type SignalColor = 'green' | 'amber' | 'gray' | 'red'

  const TAG_CLASSES: Record<TagColor, string> = {
    navy:  'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    amber: 'bg-amber-50 text-amber-700',
    red:   'bg-red-50 text-red-600',
    slate: 'bg-slate-100 text-slate-500',
  }

  const SIGNAL_DOT: Record<SignalColor, string> = {
    green: 'bg-green-500',
    amber: 'bg-amber-500',
    gray:  'bg-slate-300',
    red:   'bg-red-500',
  }

  function getTags(lead: RichLead): Tag[] {
    const tags: Tag[] = []
    const role = (lead.role ?? '').toLowerCase()
    if (/ciso|cto|ceo|coo|cfo|\bvp\b|diretor|director|chief/.test(role)) {
      tags.push({ label: 'C-level', color: 'navy' })
    }
    if (lead.enrichment?.is_decision_maker) {
      tags.push({ label: 'decisor', color: 'amber' })
    }
    const stageTag: Partial<Record<string, Tag>> = {
      CONFIRMED:         { label: 'confirmado',   color: 'green' },
      NO_SHOW:           { label: 'no-show',       color: 'red' },
      MEETING_SCHEDULED: { label: 'demo agendada', color: 'amber' },
      CONVERTED:         { label: 'convertido',    color: 'green' },
    }
    if (stageTag[lead.stage]) tags.push(stageTag[lead.stage]!)
    if (lead.enrichment?.sector) tags.push({ label: lead.enrichment.sector, color: 'slate' })
    return tags.slice(0, 3)
  }

  function getSignal(lead: RichLead): { color: SignalColor; text: string } {
    if (!lead.enrichment) return { color: 'amber', text: 'Aguardando enriquecimento' }
    if (!lead.lastMessage) return { color: 'gray', text: 'Nenhuma mensagem enviada' }
    const date = new Date(lead.lastMessage.sent_at).toLocaleDateString('pt-BR', {
      day: '2-digit', month: 'short',
    })
    if (lead.lastMessage.clicked_at) return { color: 'green', text: `Link clicado · ${date}` }
    if (lead.lastMessage.opened_at) return { color: 'green', text: `Email aberto · ${date}` }
    return { color: 'amber', text: `Email enviado · ${date}` }
  }

  export default function LeadCard({ lead, onClick }: { lead: RichLead; onClick?: () => void }) {
    const tags = getTags(lead)
    const signal = getSignal(lead)
    const parts = (lead.name ?? '').split(' ')
    const shortName = parts.length > 1 ? `${parts[0]} ${parts[parts.length - 1]}` : (lead.name ?? '—')
    const roleLabel = [lead.role, lead.company, lead.enrichment?.company_size]
      .filter(Boolean)
      .join(' · ')

    return (
      <div
        onClick={onClick}
        className="bg-slate-50 border border-slate-200 rounded-md p-2.5 mb-1.5 cursor-pointer hover:border-navy-700 hover:bg-white hover:shadow-sm transition-all last:mb-0"
      >
        <p className="text-slate-900 text-xs font-bold mb-0.5 truncate">{shortName}</p>
        {roleLabel && (
          <p className="text-slate-500 text-[10px] mb-1.5 truncate">{roleLabel}</p>
        )}
        {tags.length > 0 && (
          <div className="flex gap-1 flex-wrap mb-1.5">
            {tags.map(tag => (
              <span
                key={tag.label}
                className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${TAG_CLASSES[tag.color]}`}
              >
                {tag.label}
              </span>
            ))}
          </div>
        )}
        <div className="flex items-center gap-1.5 pt-1.5 border-t border-slate-100">
          <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${SIGNAL_DOT[signal.color]}`} />
          <span className="text-[9px] text-slate-400 truncate">{signal.text}</span>
        </div>
      </div>
    )
  }
  ```

- [ ] **2.3 — Commit**

  ```bash
  git add frontend/components/ui/Navbar.tsx frontend/components/dashboard/LeadCard.tsx
  git commit -m "feat(dashboard): fix navy colors and add onClick to LeadCard"
  ```

---

## Task 3: FunnelChart component

**Files:**
- Create: `frontend/components/dashboard/FunnelChart.tsx`

- [ ] **3.1 — Criar `FunnelChart.tsx`**

  Criar `frontend/components/dashboard/FunnelChart.tsx` com o conteúdo:

  ```tsx
  import type { BaseLead } from '@/lib/types'

  const FUNNEL_STAGES = [
    { key: 'REGISTERED',        label: 'Inscritos',      color: '#0369a1' },
    { key: 'ENRICHED',          label: 'Enriquecidos',   color: '#0369a1' },
    { key: 'CONFIRMED',         label: 'Confirmados',    color: '#16a34a' },
    { key: 'ATTENDED',          label: 'Presentes',      color: '#0369a1' },
    { key: 'NO_SHOW',           label: 'No-show',        color: '#dc2626' },
    { key: 'MEETING_SCHEDULED', label: 'Reunião agend.', color: '#d97706' },
    { key: 'CONVERTED',         label: 'Convertidos',    color: '#059669' },
  ] as const

  // Sequential flow for conversion rate: excludes NO_SHOW (branch)
  const SEQ = ['REGISTERED', 'ENRICHED', 'CONFIRMED', 'ATTENDED', 'MEETING_SCHEDULED', 'CONVERTED']

  function rateColor(rate: number): string {
    if (rate >= 70) return 'text-green-600'
    if (rate >= 50) return 'text-amber-600'
    return 'text-red-500'
  }

  export default function FunnelChart({ leads }: { leads: BaseLead[] }) {
    const counts = FUNNEL_STAGES.map(s => ({
      ...s,
      count: leads.filter(l => l.stage === s.key).length,
    }))
    const max = Math.max(...counts.map(s => s.count), 1)

    const total = leads.length
    const attendedCount = leads.filter(l =>
      ['ATTENDED', 'MEETING_SCHEDULED', 'CONVERTED'].includes(l.stage)
    ).length
    const convertedCount = leads.filter(l => l.stage === 'CONVERTED').length
    const attendanceRate = total > 0 ? Math.round((attendedCount / total) * 100) : 0
    const conversionRate = total > 0 ? Math.round((convertedCount / total) * 100) : 0

    return (
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-400 mb-3">
          Funil de Conversão
        </p>
        <div className="flex flex-col gap-1.5">
          {counts.map(stage => {
            const seqIdx = SEQ.indexOf(stage.key)
            const prevKey = seqIdx > 0 ? SEQ[seqIdx - 1] : null
            const prevCount = prevKey ? leads.filter(l => l.stage === prevKey).length : null
            const rate = prevCount && prevCount > 0
              ? Math.round((stage.count / prevCount) * 100)
              : null
            const pct = Math.round((stage.count / max) * 100)

            return (
              <div key={stage.key} className="flex items-center gap-2">
                <span className="w-[72px] text-[10px] text-slate-400 text-right flex-shrink-0 truncate">
                  {stage.label}
                </span>
                <div className="flex-1 bg-slate-100 rounded-sm h-3">
                  <div
                    className="h-full rounded-sm transition-all duration-300"
                    style={{ width: `${pct}%`, backgroundColor: stage.color }}
                  />
                </div>
                <span className="w-6 text-[10px] font-bold text-slate-500">{stage.count}</span>
                <span className={`w-8 text-[9px] text-right ${rate !== null ? rateColor(rate) : 'text-slate-300'}`}>
                  {rate !== null ? `${rate}%` : '—'}
                </span>
              </div>
            )
          })}
        </div>
        <div className="mt-3 pt-2.5 border-t border-slate-100 flex gap-4 flex-wrap">
          <p className="text-[10px] text-slate-400">
            Comparecimento:{' '}
            <strong className="text-slate-700">{attendanceRate}%</strong>
            {attendanceRate >= 70
              ? <span className="text-green-600 ml-1">✓ meta</span>
              : <span className="text-red-500 ml-1"> abaixo da meta</span>
            }
          </p>
          <p className="text-[10px] text-slate-400">
            Conversão total: <strong className="text-slate-700">{conversionRate}%</strong>
          </p>
        </div>
      </div>
    )
  }
  ```

- [ ] **3.2 — Commit**

  ```bash
  git add frontend/components/dashboard/FunnelChart.tsx
  git commit -m "feat(dashboard): add FunnelChart component — CSS pure bars"
  ```

---

## Task 4: ActivityFeed component

**Files:**
- Create: `frontend/components/dashboard/ActivityFeed.tsx`

- [ ] **4.1 — Criar `ActivityFeed.tsx`**

  Criar `frontend/components/dashboard/ActivityFeed.tsx` com o conteúdo:

  ```tsx
  import type { ActivityEvent } from '@/lib/types'

  const DOT_COLOR: Record<ActivityEvent['type'], string> = {
    clicked: 'bg-amber-500',
    opened:  'bg-green-500',
    sent:    'bg-navy-700',
  }

  const EVENT_LABEL: Record<ActivityEvent['type'], string> = {
    clicked: 'clicou no link Cal.com',
    opened:  'abriu o email',
    sent:    'recebeu email do agente',
  }

  function relativeTime(ts: string): string {
    const diff = Date.now() - new Date(ts).getTime()
    const min = Math.floor(diff / 60_000)
    if (min < 1) return 'agora'
    if (min < 60) return `${min}min`
    const h = Math.floor(min / 60)
    if (h < 24) return `${h}h`
    return `${Math.floor(h / 24)}d`
  }

  export default function ActivityFeed({ events }: { events: ActivityEvent[] }) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-4 flex flex-col">
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-400 mb-3">
          Atividade do Agente
        </p>
        {events.length === 0 ? (
          <p className="text-xs text-slate-300 text-center py-8">Nenhuma atividade registrada</p>
        ) : (
          <div className="flex flex-col overflow-y-auto">
            {events.map((ev, i) => (
              <div
                key={`${ev.leadId}-${ev.type}-${ev.timestamp}-${i}`}
                className="flex items-start gap-2 py-1.5 border-b border-slate-50 last:border-0"
              >
                <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1 ${DOT_COLOR[ev.type]}`} />
                <p className="text-[11px] text-slate-500 flex-1 leading-snug">
                  <strong className="text-slate-800 font-semibold">{ev.leadName}</strong>{' '}
                  {EVENT_LABEL[ev.type]}
                </p>
                <span className="text-[10px] text-slate-300 flex-shrink-0 mt-0.5">
                  {relativeTime(ev.timestamp)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }
  ```

- [ ] **4.2 — Commit**

  ```bash
  git add frontend/components/dashboard/ActivityFeed.tsx
  git commit -m "feat(dashboard): add ActivityFeed component — derived from messages table"
  ```

---

## Task 5: FilterBar component

**Files:**
- Create: `frontend/components/dashboard/FilterBar.tsx`

- [ ] **5.1 — Criar `FilterBar.tsx`**

  Criar `frontend/components/dashboard/FilterBar.tsx` com o conteúdo:

  ```tsx
  'use client'
  import { useState } from 'react'

  interface FilterBarProps {
    search: string
    onSearchChange: (v: string) => void
    sectorFilter: string | null
    onSectorChange: (v: string | null) => void
    decisionMakerOnly: boolean
    onDecisionMakerChange: (v: boolean) => void
    availableSectors: string[]
    totalVisible: number
    totalAll: number
  }

  export default function FilterBar({
    search, onSearchChange,
    sectorFilter, onSectorChange,
    decisionMakerOnly, onDecisionMakerChange,
    availableSectors, totalVisible, totalAll,
  }: FilterBarProps) {
    const [sectorOpen, setSectorOpen] = useState(false)
    const activeCount =
      (search ? 1 : 0) + (sectorFilter ? 1 : 0) + (decisionMakerOnly ? 1 : 0)

    return (
      <div className="px-8 pb-4 flex items-center gap-3 flex-wrap">
        <input
          type="text"
          value={search}
          onChange={e => onSearchChange(e.target.value)}
          placeholder="Buscar por nome ou empresa..."
          className="flex-1 max-w-[280px] border border-slate-200 rounded-md px-3 py-1.5 text-xs text-slate-600 placeholder:text-slate-300 focus:outline-none focus:border-navy-700"
        />

        <div className="relative">
          <button
            onClick={() => setSectorOpen(v => !v)}
            className={`border rounded-2xl px-3 py-1 text-xs font-semibold transition-colors ${
              sectorFilter
                ? 'bg-blue-50 border-navy-700 text-navy-700'
                : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'
            }`}
          >
            {sectorFilter ?? 'Setor'} ▾
          </button>
          {sectorOpen && (
            <div className="absolute top-full left-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-md z-10 min-w-[160px]">
              <button
                onClick={() => { onSectorChange(null); setSectorOpen(false) }}
                className="w-full text-left px-3 py-2 text-xs text-slate-500 hover:bg-slate-50"
              >
                Todos os setores
              </button>
              {availableSectors.map(s => (
                <button
                  key={s}
                  onClick={() => { onSectorChange(s); setSectorOpen(false) }}
                  className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-50 ${
                    sectorFilter === s ? 'text-navy-700 font-semibold' : 'text-slate-600'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>

        <button
          onClick={() => onDecisionMakerChange(!decisionMakerOnly)}
          className={`border rounded-2xl px-3 py-1 text-xs font-semibold transition-colors ${
            decisionMakerOnly
              ? 'bg-blue-50 border-navy-700 text-navy-700'
              : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'
          }`}
        >
          {decisionMakerOnly ? 'Decisores ✓' : 'Decisores'}
        </button>

        <span className="ml-auto text-[10px] text-slate-400">
          {totalVisible !== totalAll
            ? `${totalVisible} de ${totalAll} leads`
            : `${totalAll} leads`}
          {activeCount > 0 &&
            ` · ${activeCount} filtro${activeCount > 1 ? 's' : ''} ativo${activeCount > 1 ? 's' : ''}`
          }
        </span>
      </div>
    )
  }
  ```

- [ ] **5.2 — Commit**

  ```bash
  git add frontend/components/dashboard/FilterBar.tsx
  git commit -m "feat(dashboard): add FilterBar component — search + sector + decision maker"
  ```

---

## Task 6: LeadDrawer component

**Files:**
- Create: `frontend/components/dashboard/LeadDrawer.tsx`

- [ ] **6.1 — Criar `LeadDrawer.tsx`**

  Criar `frontend/components/dashboard/LeadDrawer.tsx` com o conteúdo:

  ```tsx
  'use client'
  import { useEffect } from 'react'
  import type { RichLead, Message } from '@/lib/types'

  const STAGE_STYLE: Record<string, { label: string; color: string; bg: string; border: string }> = {
    REGISTERED:        { label: 'Inscrito',        color: 'text-navy-700',   bg: 'bg-blue-50',    border: 'border-blue-200' },
    ENRICHED:          { label: 'Enriquecido',     color: 'text-navy-700',   bg: 'bg-blue-50',    border: 'border-blue-200' },
    CONFIRMED:         { label: 'Confirmado',      color: 'text-green-700',  bg: 'bg-green-50',   border: 'border-green-200' },
    ATTENDED:          { label: 'Presente',        color: 'text-navy-700',   bg: 'bg-blue-50',    border: 'border-blue-200' },
    NO_SHOW:           { label: 'No-show',         color: 'text-red-700',    bg: 'bg-red-50',     border: 'border-red-200' },
    MEETING_SCHEDULED: { label: 'Reunião agend.',  color: 'text-amber-700',  bg: 'bg-amber-50',   border: 'border-amber-200' },
    CONVERTED:         { label: 'Convertido',      color: 'text-emerald-700',bg: 'bg-emerald-50', border: 'border-emerald-200' },
  }

  function getDrawerTags(lead: RichLead) {
    const tags: Array<{ label: string; cls: string }> = []
    const role = (lead.role ?? '').toLowerCase()
    if (/ciso|cto|ceo|coo|cfo|\bvp\b|diretor|director|chief/.test(role)) {
      tags.push({ label: 'C-level', cls: 'bg-blue-50 text-blue-700' })
    }
    if (lead.enrichment?.is_decision_maker) {
      tags.push({ label: 'decisor', cls: 'bg-amber-50 text-amber-700' })
    }
    return tags
  }

  function msgBorderColor(msg: Message): string {
    if (msg.clicked_at) return 'border-green-500'
    if (msg.opened_at) return 'border-green-300'
    return 'border-navy-700'
  }

  function msgStatus(msg: Message): string {
    const parts: string[] = []
    if (msg.opened_at) parts.push('✓ Aberto')
    if (msg.clicked_at) parts.push('✓ Link clicado')
    return parts.length > 0 ? parts.join(' · ') : 'Enviado (sem abertura registrada)'
  }

  interface LeadDrawerProps {
    lead: RichLead
    messages: Message[]
    onClose: () => void
  }

  export default function LeadDrawer({ lead, messages, onClose }: LeadDrawerProps) {
    useEffect(() => {
      const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
      document.addEventListener('keydown', handler)
      return () => document.removeEventListener('keydown', handler)
    }, [onClose])

    const stage = STAGE_STYLE[lead.stage] ?? {
      label: lead.stage, color: 'text-slate-700', bg: 'bg-slate-50', border: 'border-slate-200',
    }
    const tags = getDrawerTags(lead)
    const isSecurityRole = /ciso|cto|ceo|\bvp\b|diretor|chief/.test((lead.role ?? '').toLowerCase())
    const sortedMessages = [...messages].sort(
      (a, b) => new Date(b.sent_at).getTime() - new Date(a.sent_at).getTime()
    )

    return (
      <>
        <div
          className="fixed inset-0 bg-navy-950/10 z-[200]"
          onClick={onClose}
        />
        <div className="fixed top-0 right-0 w-[380px] h-screen bg-white border-l border-slate-200 z-[201] flex flex-col shadow-xl overflow-y-auto">

          {/* Header */}
          <div className="px-5 pt-5 pb-4 border-b border-slate-200">
            <button
              onClick={onClose}
              className="float-right text-slate-300 hover:text-slate-500 text-xl leading-none ml-2"
            >
              ✕
            </button>
            <p className="font-extrabold text-[15px] text-navy-950">{lead.name ?? '—'}</p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              {[lead.role, lead.company, lead.enrichment?.company_size].filter(Boolean).join(' · ')}
            </p>
            {tags.length > 0 && (
              <div className="flex gap-1.5 mt-2">
                {tags.map(t => (
                  <span key={t.label} className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${t.cls}`}>
                    {t.label}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Stage bar */}
          <div className={`px-5 py-2 ${stage.bg} border-b ${stage.border} text-[10px] font-bold uppercase tracking-wide ${stage.color}`}>
            ● {stage.label}
          </div>

          {/* Enrichment grid */}
          <div className="px-5 py-4 border-b border-slate-100">
            <p className="text-[10px] font-bold uppercase tracking-[0.06em] text-slate-400 mb-3">
              Perfil enriquecido
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-[10px] text-slate-400">Setor</p>
                <p className="text-[11px] font-semibold text-navy-950">{lead.enrichment?.sector ?? '—'}</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-400">Porte da empresa</p>
                <p className="text-[11px] font-semibold text-navy-950">{lead.enrichment?.company_size ?? '—'}</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-400">Decisor</p>
                <p className={`text-[11px] font-semibold ${lead.enrichment?.is_decision_maker ? 'text-green-600' : 'text-slate-400'}`}>
                  {lead.enrichment?.is_decision_maker ? '✓ Confirmado' : 'Não identificado'}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-slate-400">Sinal de segurança</p>
                <p className={`text-[11px] font-semibold ${isSecurityRole ? 'text-green-600' : 'text-slate-400'}`}>
                  {isSecurityRole ? '✓ Cargo relevante' : 'Não detectado'}
                </p>
              </div>
            </div>
          </div>

          {/* Message history */}
          <div className="px-5 py-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.06em] text-slate-400 mb-3">
              Histórico de mensagens
            </p>
            {sortedMessages.length === 0 ? (
              <p className="text-xs text-slate-300 py-4 text-center">Nenhuma mensagem enviada ainda</p>
            ) : (
              <div className="flex flex-col gap-3">
                {sortedMessages.map((msg, i) => (
                  <div key={`${msg.sent_at}-${i}`} className={`border-l-2 pl-2.5 ${msgBorderColor(msg)}`}>
                    <p className="text-[11px] font-bold text-navy-950">
                      {msg.subject ?? 'Email enviado'}
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5">
                      {new Date(msg.sent_at).toLocaleDateString('pt-BR', {
                        day: '2-digit', month: 'short', year: 'numeric',
                      })}
                    </p>
                    <p className="text-[10px] text-slate-500 mt-0.5">{msgStatus(msg)}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </>
    )
  }
  ```

- [ ] **6.2 — Commit**

  ```bash
  git add frontend/components/dashboard/LeadDrawer.tsx
  git commit -m "feat(dashboard): add LeadDrawer — enrichment profile + message history"
  ```

---

## Task 7: Orquestrar tudo no FunnelBoard

**Files:**
- Modify: `frontend/components/dashboard/FunnelBoard.tsx`

Esta é a maior mudança. O `FunnelBoard.tsx` existente será substituído na íntegra. A lógica de negócio existente (Realtime, buildRichLeads, computeKpis) é preservada e expandida.

- [ ] **7.1 — Substituir `FunnelBoard.tsx` completo**

  Substituir o conteúdo completo de `frontend/components/dashboard/FunnelBoard.tsx` por:

  ```tsx
  'use client'
  import { useState, useEffect, useMemo } from 'react'
  import { REALTIME_SUBSCRIBE_STATES } from '@supabase/supabase-js'
  import { supabase } from '@/lib/supabase'
  import LeadCard from './LeadCard'
  import FunnelChart from './FunnelChart'
  import ActivityFeed from './ActivityFeed'
  import FilterBar from './FilterBar'
  import LeadDrawer from './LeadDrawer'
  import type { RichLead, LeadEnrichment, LastMessage, BaseLead, Message, ActivityEvent } from '@/lib/types'

  const STAGES = [
    { key: 'REGISTERED',        label: 'Inscritos',        color: 'border-navy-700',    titleColor: 'text-navy-700'   },
    { key: 'ENRICHED',          label: 'Enriquecidos',     color: 'border-navy-700',    titleColor: 'text-navy-700'   },
    { key: 'CONFIRMED',         label: 'Confirmados',      color: 'border-green-500',   titleColor: 'text-green-600'  },
    { key: 'ATTENDED',          label: 'Presentes',        color: 'border-navy-700',    titleColor: 'text-navy-700'   },
    { key: 'NO_SHOW',           label: 'No-show',          color: 'border-red-500',     titleColor: 'text-red-600'    },
    { key: 'MEETING_SCHEDULED', label: 'Reunião agendada', color: 'border-amber-500',   titleColor: 'text-amber-600'  },
    { key: 'CONVERTED',         label: 'Convertidos',      color: 'border-emerald-500', titleColor: 'text-emerald-600'},
  ] as const

  function buildRichLeads(
    leads: BaseLead[],
    enrichmentMap: Map<string, LeadEnrichment>,
    messageMap: Map<string, LastMessage>,
  ): RichLead[] {
    return leads.map(l => ({
      ...l,
      enrichment: enrichmentMap.get(l.id) ?? null,
      lastMessage: messageMap.get(l.id) ?? null,
    }))
  }

  function computeKpis(leads: BaseLead[], allMessages: Message[]) {
    const total = leads.length
    const confirmedStages = new Set(['CONFIRMED', 'ATTENDED', 'MEETING_SCHEDULED', 'CONVERTED'])
    const confirmed = leads.filter(l => confirmedStages.has(l.stage)).length
    const confirmRate = total > 0 ? Math.round((confirmed / total) * 100) : 0
    const meetings = leads.filter(l =>
      l.stage === 'MEETING_SCHEDULED' || l.stage === 'CONVERTED'
    ).length
    const noShow = leads.filter(l => l.stage === 'NO_SHOW').length

    const oneWeekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
    const meetingLeadIds = new Set(
      leads.filter(l => l.stage === 'MEETING_SCHEDULED' || l.stage === 'CONVERTED').map(l => l.id)
    )
    const meetingsDeltaWeek = new Set(
      allMessages.filter(m =>
        meetingLeadIds.has(m.lead_id) && m.clicked_at && m.clicked_at >= oneWeekAgo
      ).map(m => m.lead_id)
    ).size

    const noShowLeadIds = new Set(leads.filter(l => l.stage === 'NO_SHOW').map(l => l.id))
    const noShowEmailOpened = new Set(
      allMessages.filter(m => noShowLeadIds.has(m.lead_id) && m.opened_at).map(m => m.lead_id)
    ).size

    return { total, confirmRate, meetings, noShow, meetingsDeltaWeek, noShowEmailOpened }
  }

  function deriveActivityEvents(
    allMessages: Message[],
    leadMap: Map<string, string>,
  ): ActivityEvent[] {
    const events: ActivityEvent[] = []
    for (const msg of allMessages) {
      const leadName = leadMap.get(msg.lead_id) ?? 'Lead'
      if (msg.clicked_at) {
        events.push({ type: 'clicked', timestamp: msg.clicked_at, leadId: msg.lead_id, leadName })
      }
      if (msg.opened_at) {
        events.push({ type: 'opened', timestamp: msg.opened_at, leadId: msg.lead_id, leadName })
      }
      events.push({ type: 'sent', timestamp: msg.sent_at, leadId: msg.lead_id, leadName })
    }
    return events
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 20)
  }

  export default function FunnelBoard() {
    const [leads, setLeads] = useState<BaseLead[]>([])
    const [enrichmentMap, setEnrichmentMap] = useState<Map<string, LeadEnrichment>>(new Map())
    const [messageMap, setMessageMap] = useState<Map<string, LastMessage>>(new Map())
    const [allMessages, setAllMessages] = useState<Message[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Filter state
    const [search, setSearch] = useState('')
    const [sectorFilter, setSectorFilter] = useState<string | null>(null)
    const [decisionMakerOnly, setDecisionMakerOnly] = useState(false)

    // Drawer state
    const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null)

    useEffect(() => {
      fetch('/api/leads', { cache: 'no-store' })
        .then(r => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`)
          return r.json()
        })
        .then(async (response: { data: BaseLead[] } | BaseLead[]) => {
          const fetchedLeads = Array.isArray(response)
            ? response
            : (response as { data: BaseLead[] }).data ?? []
          setLeads(fetchedLeads)

          const ids = fetchedLeads.map(l => l.id)
          if (ids.length === 0) { setLoading(false); return }

          // Try fetching with subject; fall back without it if the column doesn't exist
          let msgRows: Message[] | null = null
          try {
            const { data, error: msgErr } = await supabase
              .from('messages')
              .select('lead_id, sent_at, opened_at, clicked_at, subject')
              .in('lead_id', ids)
              .eq('direction', 'OUT')
              .order('sent_at', { ascending: false })
            if (msgErr) throw msgErr
            msgRows = (data ?? []) as Message[]
          } catch {
            const { data } = await supabase
              .from('messages')
              .select('lead_id, sent_at, opened_at, clicked_at')
              .in('lead_id', ids)
              .eq('direction', 'OUT')
              .order('sent_at', { ascending: false })
            msgRows = ((data ?? []) as Omit<Message, 'subject'>[]).map(m => ({ ...m, subject: null }))
          }

          const { data: enrichRows } = await supabase
            .from('lead_enrichment')
            .select('lead_id, sector, company_size, is_decision_maker')
            .in('lead_id', ids)

          const newEnrichMap = new Map<string, LeadEnrichment>()
          for (const row of (enrichRows ?? [])) {
            newEnrichMap.set(row.lead_id, row as LeadEnrichment)
          }
          setEnrichmentMap(newEnrichMap)

          setAllMessages(msgRows)

          const newMsgMap = new Map<string, LastMessage>()
          for (const row of msgRows) {
            if (!newMsgMap.has(row.lead_id)) newMsgMap.set(row.lead_id, row)
          }
          setMessageMap(newMsgMap)
          setLoading(false)
        })
        .catch(() => {
          setError('Falha ao carregar leads. Verifique o backend.')
          setLoading(false)
        })

      const channel = supabase
        .channel('leads-board')
        .on('postgres_changes', { event: '*', schema: 'public', table: 'leads' }, payload => {
          if (payload.eventType === 'INSERT') {
            setLeads(prev => [...prev, payload.new as BaseLead])
          } else if (payload.eventType === 'UPDATE') {
            setLeads(prev =>
              prev.map(l => l.id === (payload.new as BaseLead).id ? (payload.new as BaseLead) : l)
            )
          } else if (payload.eventType === 'DELETE') {
            setLeads(prev => prev.filter(l => l.id !== (payload.old as { id: string }).id))
          }
        })
        .subscribe(status => {
          if (
            status === REALTIME_SUBSCRIBE_STATES.CHANNEL_ERROR ||
            status === REALTIME_SUBSCRIBE_STATES.TIMED_OUT
          ) {
            setError('Conexão em tempo real perdida. Atualize a página para reconectar.')
          }
        })

      return () => { supabase.removeChannel(channel) }
    }, [])

    const richLeads = useMemo(
      () => buildRichLeads(leads, enrichmentMap, messageMap),
      [leads, enrichmentMap, messageMap]
    )

    const availableSectors = useMemo(() => {
      const sectors = new Set<string>()
      for (const lead of richLeads) {
        if (lead.enrichment?.sector) sectors.add(lead.enrichment.sector)
      }
      return Array.from(sectors).sort()
    }, [richLeads])

    const filteredLeads = useMemo(() => {
      return richLeads.filter(lead => {
        if (search) {
          const q = search.toLowerCase()
          const nameMatch = (lead.name ?? '').toLowerCase().includes(q)
          const companyMatch = (lead.company ?? '').toLowerCase().includes(q)
          if (!nameMatch && !companyMatch) return false
        }
        if (sectorFilter && lead.enrichment?.sector !== sectorFilter) return false
        if (decisionMakerOnly && !lead.enrichment?.is_decision_maker) return false
        return true
      })
    }, [richLeads, search, sectorFilter, decisionMakerOnly])

    const leadMap = useMemo(() => {
      const m = new Map<string, string>()
      for (const l of leads) m.set(l.id, l.name ?? 'Lead')
      return m
    }, [leads])

    const activityEvents = useMemo(
      () => deriveActivityEvents(allMessages, leadMap),
      [allMessages, leadMap]
    )

    const selectedLead = selectedLeadId
      ? richLeads.find(l => l.id === selectedLeadId) ?? null
      : null

    const selectedLeadMessages = useMemo(() =>
      selectedLeadId
        ? allMessages.filter(m => m.lead_id === selectedLeadId)
        : [],
      [selectedLeadId, allMessages]
    )

    if (loading) {
      return (
        <div className="p-8">
          <p className="text-slate-400 text-sm">Carregando leads…</p>
        </div>
      )
    }

    if (error) {
      return (
        <div className="p-8">
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        </div>
      )
    }

    const { total, confirmRate, meetings, noShow, meetingsDeltaWeek, noShowEmailOpened } =
      computeKpis(leads, allMessages)
    const metaDiff = confirmRate - 70
    const metaText = metaDiff >= 0 ? `${metaDiff}% acima da meta` : `${Math.abs(metaDiff)}% abaixo da meta`
    const metaColor = metaDiff >= 0 ? 'text-green-600' : 'text-red-600'

    return (
      <div>
        {/* KPI STRIP */}
        <div className="bg-white border-b border-slate-200 px-8 py-5 grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            {
              label: 'Total inscritos',
              value: String(total),
              sub: 'de 120 vagas',
              meta: null as string | null,
              metaColor: '',
              accent: 'border-navy-700',
              valueColor: 'text-navy-700',
            },
            {
              label: 'Taxa de confirmação',
              value: `${confirmRate}%`,
              sub: 'meta: acima de 70%',
              meta: metaText,
              metaColor,
              accent: 'border-green-500',
              valueColor: confirmRate >= 70 ? 'text-green-600' : 'text-red-600',
            },
            {
              label: 'Reuniões agendadas',
              value: String(meetings),
              sub: 'via Cal.com',
              meta: meetingsDeltaWeek > 0 ? `+${meetingsDeltaWeek} essa semana` : null,
              metaColor: 'text-amber-600',
              accent: 'border-amber-500',
              valueColor: 'text-amber-600',
            },
            {
              label: 'No-show',
              value: String(noShow),
              sub: 'reengajamento ativo',
              meta: noShowEmailOpened > 0 ? `${noShowEmailOpened} com email aberto` : null,
              metaColor: 'text-green-600',
              accent: 'border-red-500',
              valueColor: 'text-red-600',
            },
          ].map(kpi => (
            <div
              key={kpi.label}
              className={`bg-white border border-slate-200 [border-top-width:3px] ${kpi.accent} rounded-lg p-4`}
            >
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-[0.08em] mb-2">
                {kpi.label}
              </p>
              <p className={`font-playfair font-black text-4xl leading-none ${kpi.valueColor}`}>
                {kpi.value}
              </p>
              <p className="text-slate-400 text-[11px] mt-1.5">{kpi.sub}</p>
              {kpi.meta && (
                <p className={`text-[10px] font-semibold mt-0.5 ${kpi.metaColor}`}>{kpi.meta}</p>
              )}
            </div>
          ))}
        </div>

        {/* MIDDLE ROW: Funnel Chart + Activity Feed */}
        <div className="px-8 py-5 grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-4">
          <FunnelChart leads={leads} />
          <ActivityFeed events={activityEvents} />
        </div>

        {/* FILTER BAR */}
        <FilterBar
          search={search}
          onSearchChange={setSearch}
          sectorFilter={sectorFilter}
          onSectorChange={setSectorFilter}
          decisionMakerOnly={decisionMakerOnly}
          onDecisionMakerChange={setDecisionMakerOnly}
          availableSectors={availableSectors}
          totalVisible={filteredLeads.length}
          totalAll={richLeads.length}
        />

        {/* KANBAN */}
        <div className="px-8 pb-8">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="font-playfair font-extrabold text-xl text-slate-900">Funil de Leads</h2>
              <p className="text-slate-400 text-xs mt-0.5">
                Atualização em tempo real — {total} leads carregados
              </p>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-slate-500 text-xs font-semibold">
              📅 Vigil Summit · 15 Ago 2026
            </div>
          </div>

          <div className="flex gap-3 overflow-x-auto pb-4">
            {STAGES.map(({ key, label, color, titleColor }) => {
              const stageLeads = filteredLeads.filter(l => l.stage === key)
              return (
                <div key={key} className="flex-shrink-0 w-[220px] flex flex-col">
                  <div
                    className={`bg-white border border-b-0 border-slate-200 [border-top-width:3px] ${color} rounded-t-lg px-3 py-2 flex items-center justify-between`}
                  >
                    <span className={`text-[10px] font-bold uppercase tracking-[0.08em] ${titleColor}`}>
                      {label}
                    </span>
                    <span className="bg-slate-100 text-slate-500 text-[10px] font-bold px-2 py-0.5 rounded-full min-w-[22px] text-center">
                      {stageLeads.length || '—'}
                    </span>
                  </div>
                  <div className="bg-white border border-slate-200 rounded-b-lg p-2 flex-1 min-h-[100px]">
                    {stageLeads.length === 0 ? (
                      <p className="text-slate-200 text-xs text-center pt-6">
                        {key === 'ATTENDED' ? 'Dia do evento · 15 Ago' : '—'}
                      </p>
                    ) : (
                      stageLeads.map(lead => (
                        <LeadCard
                          key={lead.id}
                          lead={lead}
                          onClick={() => setSelectedLeadId(lead.id)}
                        />
                      ))
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* LEAD DRAWER */}
        {selectedLead && (
          <LeadDrawer
            lead={selectedLead}
            messages={selectedLeadMessages}
            onClose={() => setSelectedLeadId(null)}
          />
        )}
      </div>
    )
  }
  ```

- [ ] **7.2 — Verificar build sem erros de TypeScript**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

  Esperado: sem erros. Se houver erro de tipo, corrigir antes de continuar.

- [ ] **7.3 — Rodar o servidor de desenvolvimento e verificar visualmente**

  ```bash
  cd frontend && npm run dev
  ```

  Abrir `http://localhost:3000/dashboard` e verificar:
  - [ ] KPI strip com 4 cards em `navy-700` / green / amber / red
  - [ ] Gráfico de funil com barras horizontais abaixo dos KPIs
  - [ ] Feed de atividade ao lado do gráfico (ou abaixo em mobile)
  - [ ] Barra de filtros com input de busca e chips
  - [ ] Kanban com 7 colunas usando `border-navy-700` (não mais `border-sky-700`)
  - [ ] Clicar num card abre o drawer pela direita com perfil e histórico
  - [ ] Clicar fora ou pressionar Escape fecha o drawer
  - [ ] Filtrar por nome funciona — cards somem/aparecem no kanban
  - [ ] Chip "Decisores" filtra leads com `is_decision_maker = true`

- [ ] **7.4 — Commit final**

  ```bash
  git add frontend/components/dashboard/FunnelBoard.tsx
  git commit -m "feat(dashboard): wire FunnelChart, ActivityFeed, FilterBar, LeadDrawer into FunnelBoard"
  ```

---

## Self-Review

**Spec coverage:**
- ✅ Cores `sky-700` → `navy-700` — Task 1 (tailwind) + Task 2 (LeadCard, Navbar)
- ✅ KPI "delta semana" reuniões — `meetingsDeltaWeek` em `computeKpis` (Task 7)
- ✅ KPI "X com email aberto" no-show — `noShowEmailOpened` em `computeKpis` (Task 7)
- ✅ `FunnelChart` com barras CSS + taxa de conversão — Task 3
- ✅ `ActivityFeed` derivado de messages — Task 4
- ✅ `FilterBar` busca + sector + decisor — Task 5
- ✅ `LeadDrawer` perfil + histórico de mensagens — Task 6
- ✅ `BaseLead` movido para `lib/types.ts` — Task 1
- ✅ try/catch na query de messages com subject — Task 7
- ✅ Realtime existente preservado — Task 7

**Tipos consistentes em todos os tasks:** `BaseLead`, `Message`, `ActivityEvent`, `RichLead`, `LeadEnrichment`, `LastMessage` definidos em Task 1 e usados identicamente em Tasks 3–7. ✅
