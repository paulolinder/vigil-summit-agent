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

        // Try fetching with subject; fall back without it if the column doesn't exist (PGRST204)
        const fetchMessages = async (): Promise<Message[]> => {
          try {
            const { data, error: msgErr } = await supabase
              .from('messages')
              .select('lead_id, sent_at, opened_at, clicked_at, subject')
              .in('lead_id', ids)
              .eq('direction', 'OUT')
              .order('sent_at', { ascending: false })
            if (msgErr && msgErr.code !== 'PGRST204') throw msgErr
            if (!msgErr) return (data ?? []) as Message[]
            // PGRST204: column doesn't exist — fall back
            throw msgErr
          } catch (err: unknown) {
            const pgErr = err as { code?: string }
            if (pgErr?.code !== 'PGRST204') throw err
            const { data } = await supabase
              .from('messages')
              .select('lead_id, sent_at, opened_at, clicked_at')
              .in('lead_id', ids)
              .eq('direction', 'OUT')
              .order('sent_at', { ascending: false })
            return ((data ?? []) as Omit<Message, 'subject'>[]).map(m => ({ ...m, subject: null }))
          }
        }

        const [msgRows, { data: enrichRows }] = await Promise.all([
          fetchMessages(),
          supabase
            .from('lead_enrichment')
            .select('lead_id, sector, company_size, is_decision_maker')
            .in('lead_id', ids),
        ])

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
