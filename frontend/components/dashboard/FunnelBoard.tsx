'use client'
import { useState, useEffect } from 'react'
import { REALTIME_SUBSCRIBE_STATES } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'
import LeadCard from './LeadCard'
import type { RichLead, LeadEnrichment, LastMessage } from '@/lib/types'

const STAGES = [
  { key: 'REGISTERED',        label: 'Inscritos',        color: 'border-sky-700',     titleColor: 'text-slate-500' },
  { key: 'ENRICHED',          label: 'Enriquecidos',     color: 'border-sky-700',     titleColor: 'text-slate-500' },
  { key: 'CONFIRMED',         label: 'Confirmados',      color: 'border-green-500',   titleColor: 'text-green-600' },
  { key: 'ATTENDED',          label: 'Presentes',        color: 'border-sky-700',     titleColor: 'text-slate-500' },
  { key: 'NO_SHOW',           label: 'No-show',          color: 'border-red-500',     titleColor: 'text-red-600'   },
  { key: 'MEETING_SCHEDULED', label: 'Reunião agendada', color: 'border-amber-500',   titleColor: 'text-amber-600' },
  { key: 'CONVERTED',         label: 'Convertidos',      color: 'border-emerald-500', titleColor: 'text-emerald-600' },
] as const

type BaseLead = { id: string; name: string | null; role: string | null; company: string | null; stage: string }

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

function computeKpis(leads: BaseLead[]) {
  const total = leads.length
  const confirmedStages = new Set(['CONFIRMED', 'ATTENDED', 'MEETING_SCHEDULED', 'CONVERTED'])
  const confirmed = leads.filter(l => confirmedStages.has(l.stage)).length
  const confirmRate = total > 0 ? Math.round((confirmed / total) * 100) : 0
  const meetings = leads.filter(l => l.stage === 'MEETING_SCHEDULED' || l.stage === 'CONVERTED').length
  const noShow = leads.filter(l => l.stage === 'NO_SHOW').length
  return { total, confirmRate, meetings, noShow }
}

export default function FunnelBoard() {
  const [leads, setLeads] = useState<BaseLead[]>([])
  const [enrichmentMap, setEnrichmentMap] = useState<Map<string, LeadEnrichment>>(new Map())
  const [messageMap, setMessageMap] = useState<Map<string, LastMessage>>(new Map())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/leads', { cache: 'no-store' })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(async (response: { data: BaseLead[] } | BaseLead[]) => {
        const fetchedLeads = Array.isArray(response) ? response : (response as { data: BaseLead[] }).data ?? []
        setLeads(fetchedLeads)

        const ids = fetchedLeads.map(l => l.id)
        if (ids.length === 0) { setLoading(false); return }

        const [{ data: enrichRows }, { data: msgRows }] = await Promise.all([
          supabase
            .from('lead_enrichment')
            .select('lead_id, sector, company_size, is_decision_maker')
            .in('lead_id', ids),
          supabase
            .from('messages')
            .select('lead_id, sent_at, opened_at, clicked_at')
            .in('lead_id', ids)
            .eq('direction', 'OUT')
            .order('sent_at', { ascending: false }),
        ])

        const newEnrichMap = new Map<string, LeadEnrichment>()
        for (const row of (enrichRows ?? [])) {
          newEnrichMap.set(row.lead_id, row as LeadEnrichment)
        }
        setEnrichmentMap(newEnrichMap)

        const newMsgMap = new Map<string, LastMessage>()
        for (const row of (msgRows ?? [])) {
          if (!newMsgMap.has(row.lead_id)) newMsgMap.set(row.lead_id, row as LastMessage)
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

  const { total, confirmRate, meetings, noShow } = computeKpis(leads)
  const richLeads = buildRichLeads(leads, enrichmentMap, messageMap)
  const metaDiff = confirmRate - 70
  const metaText = metaDiff >= 0
    ? `${metaDiff}% acima da meta`
    : `${Math.abs(metaDiff)}% abaixo da meta`
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
            accent: 'border-sky-700',
            valueColor: 'text-slate-900',
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
            meta: null as string | null,
            metaColor: '',
            accent: 'border-amber-500',
            valueColor: 'text-amber-600',
          },
          {
            label: 'No-show',
            value: String(noShow),
            sub: 'reengajamento ativo',
            meta: null as string | null,
            metaColor: '',
            accent: 'border-red-500',
            valueColor: 'text-red-600',
          },
        ].map(kpi => (
          <div
            key={kpi.label}
            className={`bg-white border border-slate-200 [border-top-width:3px] ${kpi.accent} rounded-lg p-4`}
          >
            <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-[0.08em] mb-2">{kpi.label}</p>
            <p className={`font-playfair font-black text-4xl leading-none ${kpi.valueColor}`}>{kpi.value}</p>
            <p className="text-slate-400 text-[11px] mt-1.5">{kpi.sub}</p>
            {kpi.meta && (
              <p className={`text-[10px] font-semibold mt-0.5 ${kpi.metaColor}`}>{kpi.meta}</p>
            )}
          </div>
        ))}
      </div>

      {/* KANBAN */}
      <div className="p-8">
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
            const stageLeads = richLeads.filter(l => l.stage === key)
            return (
              <div key={key} className="flex-shrink-0 w-[220px] flex flex-col">
                <div
                  className={`bg-white border border-b-0 border-slate-200 [border-top-width:3px] ${color} rounded-t-lg px-3 py-2 flex items-center justify-between`}
                >
                  <span className={`text-[10px] font-bold uppercase tracking-[0.08em] ${titleColor}`}>{label}</span>
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
                    stageLeads.map(lead => <LeadCard key={lead.id} lead={lead} />)
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
