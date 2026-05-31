'use client'
import { useState, useEffect, useMemo } from 'react'
import { REALTIME_SUBSCRIBE_STATES } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'
import LeadCard from './LeadCard'
import FunnelChart from './FunnelChart'
import ActivityFeed from './ActivityFeed'
import FilterBar from './FilterBar'
import LeadDrawer from './LeadDrawer'
import type { RichLead, LeadEnrichment, LastMessage, BaseLead, Message, ActivityEvent, EventConfig } from '@/lib/types'
import ConfigPanel from './ConfigPanel'
import { formatEventDate } from '@/lib/format'

const STAGES = [
  { key: 'REGISTERED',        label: 'Inscritos',        color: 'border-brand-teal',    titleColor: 'text-brand-teal'   },
  { key: 'ENRICHED',          label: 'Enriquecidos',     color: 'border-brand-teal',    titleColor: 'text-brand-teal'   },
  { key: 'CONFIRMED',         label: 'Confirmados',      color: 'border-brand-green',   titleColor: 'text-brand-green'  },
  { key: 'ATTENDED',          label: 'Presentes',        color: 'border-brand-teal',    titleColor: 'text-brand-teal'   },
  { key: 'NO_SHOW',           label: 'No-show',          color: 'border-red-400',       titleColor: 'text-red-400'      },
  { key: 'MEETING_SCHEDULED', label: 'Reunião agendada', color: 'border-brand-lime',    titleColor: 'text-[#6b7a00]'    },
  { key: 'CONVERTED',         label: 'Convertidos',      color: 'border-brand-green',   titleColor: 'text-brand-green'  },
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
  const [eventCapacity, setEventCapacity] = useState<number>(120)
  const [eventDateLabel, setEventDateLabel] = useState<string>('')

  // Load event config (capacity + date) so the KPI strip and badges reflect the DB
  // instead of hardcoded values. Falls back to defaults if the request fails.
  useEffect(() => {
    fetch('/api/events', { cache: 'no-store' })
      .then(r => (r.ok ? r.json() : []))
      .then((data: EventConfig[]) => {
        if (Array.isArray(data) && data.length > 0) {
          setEventCapacity(data[0].capacity ?? 120)
          setEventDateLabel(formatEventDate(data[0].event_date))
        }
      })
      .catch(() => {/* keep defaults */})
  }, [])

  // Filter state
  const [search, setSearch] = useState('')
  const [sectorFilter, setSectorFilter] = useState<string | null>(null)
  const [decisionMakerOnly, setDecisionMakerOnly] = useState(false)

  // Drawer state
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'funnel' | 'config'>('funnel')

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

        // Try fetching with subject; fall back without it if the column doesn't exist (42703)
        const fetchMessages = async (): Promise<Message[]> => {
          try {
            const { data, error: msgErr } = await supabase
              .from('messages')
              .select('lead_id, sent_at, opened_at, clicked_at, subject')
              .in('lead_id', ids)
              .eq('direction', 'OUT')
              .order('sent_at', { ascending: false })
            if (msgErr && msgErr.code !== '42703') throw msgErr
            if (!msgErr) return (data ?? []) as Message[]
            // 42703: column doesn't exist — fall back
            throw msgErr
          } catch (err: unknown) {
            const pgErr = err as { code?: string }
            if (pgErr?.code !== '42703') throw err
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
          const newLead = payload.new as BaseLead
          setLeads(prev => [...prev, newLead])
          // Fetch enrichment + messages for the new lead
          Promise.all([
            supabase
              .from('lead_enrichment')
              .select('lead_id, sector, company_size, is_decision_maker')
              .eq('lead_id', newLead.id)
              .maybeSingle(),
            supabase
              .from('messages')
              .select('lead_id, sent_at, opened_at, clicked_at, subject')
              .eq('lead_id', newLead.id)
              .eq('direction', 'OUT')
              .order('sent_at', { ascending: false }),
          ]).then(([{ data: enrich }, { data: msgs }]) => {
            if (enrich) {
              setEnrichmentMap(prev => new Map(prev).set(newLead.id, enrich as LeadEnrichment))
            }
            if (msgs && msgs.length > 0) {
              setMessageMap(prev => {
                const next = new Map(prev)
                next.set(newLead.id, msgs[0] as LastMessage)
                return next
              })
              setAllMessages(prev => [...(msgs as Message[]), ...prev])
            }
          }).catch(() => {/* non-fatal: lead shows with no enrichment until next reload */})
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
  const metaColor = metaDiff >= 0 ? 'text-brand-green' : 'text-red-400'

  return (
    <div>
      {/* KPI STRIP */}
      <div className="bg-brand-navy px-8 py-5 grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: 'Total inscritos',
            value: String(total),
            sub: `de ${eventCapacity} vagas`,
            meta: null as string | null,
            metaColor: '',
            valueColor: 'text-brand-teal',
          },
          {
            label: 'Taxa de confirmação',
            value: `${confirmRate}%`,
            sub: 'meta: acima de 70%',
            meta: metaText,
            metaColor,
            valueColor: confirmRate >= 70 ? 'text-brand-green' : 'text-red-400',
          },
          {
            label: 'Reuniões agendadas',
            value: String(meetings),
            sub: 'via Cal.com',
            meta: meetingsDeltaWeek > 0 ? `+${meetingsDeltaWeek} essa semana` : null,
            metaColor: 'text-brand-lime',
            valueColor: 'text-brand-lime',
          },
          {
            label: 'No-show',
            value: String(noShow),
            sub: 'reengajamento ativo',
            meta: noShowEmailOpened > 0 ? `${noShowEmailOpened} com email aberto` : null,
            metaColor: 'text-brand-green',
            valueColor: 'text-red-400',
          },
        ].map(kpi => (
          <div
            key={kpi.label}
            className="bg-white/[0.07] border border-white/[0.12] rounded-[12px] p-4"
          >
            <p className="text-[10px] font-semibold text-white/50 uppercase tracking-[0.08em] mb-2">
              {kpi.label}
            </p>
            <p className={`font-extrabold text-4xl leading-none tracking-tight ${kpi.valueColor}`}>
              {kpi.value}
            </p>
            <p className="text-white/40 text-[11px] mt-1.5">{kpi.sub}</p>
            {kpi.meta && (
              <p className={`text-[10px] font-semibold mt-0.5 ${kpi.metaColor}`}>{kpi.meta}</p>
            )}
          </div>
        ))}
      </div>

      {/* TAB BAR */}
      <div className="bg-white border-b border-brand-border px-8 flex gap-0">
        <button
          onClick={() => setActiveTab('funnel')}
          className={`py-3 px-5 text-xs font-bold border-b-2 transition-colors -mb-px ${
            activeTab === 'funnel'
              ? 'border-brand-teal text-brand-teal'
              : 'border-transparent text-brand-muted hover:text-brand-text hover:border-brand-border'
          }`}
        >
          📊 Funil de Leads
        </button>
        <button
          onClick={() => setActiveTab('config')}
          className={`py-3 px-5 text-xs font-bold border-b-2 transition-colors -mb-px ${
            activeTab === 'config'
              ? 'border-brand-teal text-brand-teal'
              : 'border-transparent text-brand-muted hover:text-brand-text hover:border-brand-border'
          }`}
        >
          ⚙ Configurações
        </button>
      </div>

      {activeTab === 'funnel' && (
        <>
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
                <h2 className="font-extrabold text-xl text-brand-text">Funil de Leads</h2>
                <p className="text-brand-muted text-xs mt-0.5">
                  Atualização em tempo real — {total} leads carregados
                </p>
              </div>
              <div className="bg-white border border-brand-border rounded-[10px] px-3 py-1.5 text-brand-muted text-xs font-semibold">
                📅 Vigil Summit · {eventDateLabel || '15 Ago 2026'}
              </div>
            </div>

            <div className="flex gap-3 overflow-x-auto pb-4">
              {STAGES.map(({ key, label, color, titleColor }) => {
                const stageLeads = filteredLeads.filter(l => l.stage === key)
                return (
                  <div key={key} className="flex-shrink-0 w-[220px] flex flex-col">
                    <div
                      className={`bg-white border border-b-0 border-brand-border [border-top-width:3px] ${color} rounded-t-[10px] px-3 py-2 flex items-center justify-between`}
                    >
                      <span className={`text-[10px] font-bold uppercase tracking-[0.08em] ${titleColor}`}>
                        {label}
                      </span>
                      <span className="bg-brand-bg text-brand-muted text-[10px] font-bold px-2 py-0.5 rounded-full min-w-[22px] text-center">
                        {stageLeads.length || '—'}
                      </span>
                    </div>
                    <div className="bg-white border border-brand-border rounded-b-[10px] p-2 flex-1 min-h-[100px]">
                      {stageLeads.length === 0 ? (
                        <p className="text-brand-border text-xs text-center pt-6">
                          {key === 'ATTENDED' ? `Dia do evento · ${eventDateLabel || '15 Ago 2026'}` : '—'}
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
        </>
      )}

      {activeTab === 'config' && (
        <ConfigPanel totalLeads={leads.length} />
      )}

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
