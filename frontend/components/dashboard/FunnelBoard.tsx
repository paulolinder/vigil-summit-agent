'use client'
import { useState, useEffect } from 'react'
import { REALTIME_SUBSCRIBE_STATES } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'
import LeadCard from './LeadCard'

const STAGES = [
  { key: 'REGISTERED',        label: 'Inscritos',     color: 'border-gray-500' },
  { key: 'ENRICHED',          label: 'Enriquecidos',  color: 'border-blue-500' },
  { key: 'CONFIRMED',         label: 'Confirmados',   color: 'border-green-500' },
  { key: 'ATTENDED',          label: 'Presentes',     color: 'border-purple-500' },
  { key: 'NO_SHOW',           label: 'No-show',       color: 'border-red-500' },
  { key: 'MEETING_SCHEDULED', label: 'Reunião',       color: 'border-yellow-500' },
  { key: 'CONVERTED',         label: 'Convertidos',   color: 'border-emerald-500' },
] as const

type Lead = {
  id: string
  name: string | null
  role: string | null
  company: string | null
  stage: string
}

export default function FunnelBoard() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Calls the Next.js server-side proxy at /api/leads — never exposes BACKEND_API_KEY to the browser
    fetch('/api/leads', { cache: 'no-store' })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((response: { data: Lead[] } | Lead[]) => {
        const leads = Array.isArray(response) ? response : (response as { data: Lead[] }).data ?? []
        setLeads(leads)
        setLoading(false)
      })
      .catch(() => {
        setError('Falha ao carregar leads. Verifique o backend.')
        setLoading(false)
      })

    const channel = supabase
      .channel('leads-board')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'leads' },
        payload => {
          if (payload.eventType === 'INSERT') {
            setLeads(prev => [...prev, payload.new as Lead])
          } else if (payload.eventType === 'UPDATE') {
            setLeads(prev =>
              prev.map(l => l.id === (payload.new as Lead).id ? (payload.new as Lead) : l)
            )
          } else if (payload.eventType === 'DELETE') {
            setLeads(prev => prev.filter(l => l.id !== (payload.old as { id: string }).id))
          }
        }
      )
      .subscribe((status) => {
        if (
          status === REALTIME_SUBSCRIBE_STATES.CHANNEL_ERROR ||
          status === REALTIME_SUBSCRIBE_STATES.TIMED_OUT
        ) {
          setError('Conexão Realtime perdida. Atualize a página para reconectar.')
        }
      })

    return () => { supabase.removeChannel(channel) }
  }, [])

  const byStage = (stageKey: string) =>
    leads.filter(l => l.stage === stageKey)

  if (loading) {
    return <p className="text-gray-500 text-sm">Carregando leads...</p>
  }

  if (error) {
    return (
      <div className="bg-red-950 border border-red-800 rounded-xl p-4">
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    )
  }

  return (
    <div className="flex gap-4 overflow-x-auto pb-4 min-h-64">
      {STAGES.map(({ key, label, color }) => (
        <div key={key} className={`flex-shrink-0 w-48 rounded-xl border-t-2 ${color} bg-gray-900 p-3`}>
          <div className="flex items-center justify-between mb-3">
            <p className="text-gray-300 text-xs font-semibold uppercase tracking-wide">{label}</p>
            <span className="bg-gray-800 text-gray-400 text-xs rounded-full px-2 py-0.5 min-w-[1.5rem] text-center">
              {byStage(key).length}
            </span>
          </div>
          <div className="space-y-2">
            {byStage(key).length === 0
              ? <p className="text-gray-700 text-xs text-center py-6">—</p>
              : byStage(key).map(lead => <LeadCard key={lead.id} lead={lead} />)
            }
          </div>
        </div>
      ))}
    </div>
  )
}
