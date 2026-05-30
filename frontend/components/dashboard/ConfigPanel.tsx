'use client'
import { useState, useEffect, useCallback } from 'react'
import type { EventConfig, ServiceStatus, JobRow } from '@/lib/types'

const STATUS_BADGE: Record<string, { cls: string; label: string }> = {
  ok:       { cls: 'bg-green-50 text-green-700',  label: '✓ Ativo' },
  warn:     { cls: 'bg-amber-50 text-amber-700',  label: '⚠ Não configurado' },
  error:    { cls: 'bg-red-50 text-red-600',      label: '✗ Erro' },
  checking: { cls: 'bg-slate-100 text-slate-500', label: '⏳ Verificando…' },
}

const JOB_STATUS_BADGE: Record<string, string> = {
  DONE:    'bg-green-50 text-green-700',
  PENDING: 'bg-blue-50 text-blue-700',
  RUNNING: 'bg-amber-50 text-amber-700',
  FAILED:  'bg-red-50 text-red-600',
  SKIPPED: 'bg-slate-100 text-slate-500',
}

export default function ConfigPanel({ totalLeads }: { totalLeads: number }) {
  const [event, setEvent]           = useState<EventConfig | null>(null)
  const [form, setForm]             = useState<Partial<EventConfig>>({})
  const [saving, setSaving]         = useState(false)
  const [saveMsg, setSaveMsg]       = useState<string | null>(null)

  const [services, setServices]     = useState<ServiceStatus[]>([])
  const [checking, setChecking]     = useState(false)

  const [jobs, setJobs]             = useState<JobRow[]>([])
  const [runningJobs, setRunningJobs] = useState<Set<string>>(new Set())

  // ── Load event ───────────────────────────────────────────────────────────
  useEffect(() => {
    fetch('/api/events', { cache: 'no-store' })
      .then(r => r.json())
      .then((data: EventConfig[]) => {
        if (data.length > 0) {
          setEvent(data[0])
          setForm({
            name: data[0].name,
            event_date: data[0].event_date?.slice(0, 10) ?? '',
            capacity: data[0].capacity ?? 120,
          })
        }
      })
      .catch(() => {/* non-fatal */})
  }, [])

  // ── Load services (env-var check) ────────────────────────────────────────
  useEffect(() => {
    fetch('/api/admin/health', { cache: 'no-store' })
      .then(r => r.json())
      .then(data => setServices(data.services ?? []))
      .catch(() => {/* non-fatal */})
  }, [])

  // ── Load + poll jobs ─────────────────────────────────────────────────────
  const loadJobs = useCallback(() => {
    fetch('/api/admin/jobs?limit=20', { cache: 'no-store' })
      .then(r => r.json())
      .then(data => setJobs(data.data ?? []))
      .catch(() => {/* non-fatal */})
  }, [])

  useEffect(() => {
    loadJobs()
    const id = setInterval(loadJobs, 30_000)
    return () => clearInterval(id)
  }, [loadJobs])

  // ── Save event ───────────────────────────────────────────────────────────
  async function handleSave() {
    if (!event) return
    setSaving(true)
    setSaveMsg(null)
    try {
      const res = await fetch(`/api/events/${event.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name,
          event_date: form.event_date ? `${form.event_date}T09:00:00-03:00` : undefined,
          capacity: form.capacity,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const updated: EventConfig = await res.json()
      setEvent(updated)
      setSaveMsg('✓ Salvo com sucesso')
    } catch {
      setSaveMsg('✗ Falha ao salvar')
    } finally {
      setSaving(false)
      setTimeout(() => setSaveMsg(null), 3000)
    }
  }

  // ── Live health check ────────────────────────────────────────────────────
  async function handleCheckLive() {
    setChecking(true)
    setServices(prev => prev.map(s => ({ ...s, status: 'checking' as const })))
    try {
      const res = await fetch('/api/admin/health?live=true', { cache: 'no-store' })
      const data = await res.json()
      setServices(data.services ?? [])
    } catch {
      setServices(prev => prev.map(s => ({ ...s, status: 'error' as const })))
    } finally {
      setChecking(false)
    }
  }

  // ── Run job ──────────────────────────────────────────────────────────────
  async function handleRunJob(jobId: string) {
    setRunningJobs(prev => new Set(prev).add(jobId))
    setJobs(prev => prev.map(j => j.id === jobId ? { ...j, status: 'RUNNING' as const } : j))
    try {
      await fetch(`/api/admin/jobs/${jobId}/run`, { method: 'POST' })
    } catch {/* will refresh on next poll */}
    setTimeout(() => {
      setRunningJobs(prev => { const s = new Set(prev); s.delete(jobId); return s })
      loadJobs()
    }, 3000)
  }

  const capacity = form.capacity ?? 120
  const pct = capacity > 0 ? Math.min(Math.round((totalLeads / capacity) * 100), 100) : 0

  return (
    <div className="px-8 py-6 space-y-6">

      {/* ── Event Config ─────────────────────────────────────────────────── */}
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-400 mb-3">
          Configuração do Evento
        </p>
        <div className="bg-white border border-slate-200 border-t-[3px] border-t-navy-700 rounded-lg p-5">
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 mb-1.5">Nome</label>
              <input
                type="text"
                value={form.name ?? ''}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full border border-slate-200 rounded-md px-3 py-2 text-xs focus:outline-none focus:border-navy-700"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 mb-1.5">Data do evento</label>
              <input
                type="date"
                value={form.event_date ?? ''}
                onChange={e => setForm(f => ({ ...f, event_date: e.target.value }))}
                className="w-full border border-slate-200 rounded-md px-3 py-2 text-xs focus:outline-none focus:border-navy-700"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 mb-1.5">Capacidade máxima</label>
              <input
                type="number"
                value={form.capacity ?? 120}
                onChange={e => setForm(f => ({ ...f, capacity: Number(e.target.value) }))}
                className="w-full border border-slate-200 rounded-md px-3 py-2 text-xs focus:outline-none focus:border-navy-700"
              />
            </div>
          </div>
          <div className="mb-4">
            <div className="flex justify-between text-[10px] text-slate-500 mb-1">
              <span>Vagas ocupadas: <strong>{totalLeads} de {capacity}</strong> ({pct}%)</span>
              <span>{capacity - totalLeads} vagas disponíveis</span>
            </div>
            <div className="bg-slate-100 rounded-full h-1.5">
              <div
                className="bg-navy-700 rounded-full h-full transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="bg-navy-950 text-white text-xs font-bold px-5 py-2 rounded-md hover:bg-navy-700 disabled:opacity-50 transition-colors"
            >
              {saving ? 'Salvando…' : 'Salvar alterações'}
            </button>
            {saveMsg && (
              <span className={`text-xs font-semibold ${saveMsg.startsWith('✓') ? 'text-green-600' : 'text-red-500'}`}>
                {saveMsg}
              </span>
            )}
            <span className="text-[10px] text-slate-400 ml-1">
              Atualiza a data usada pelo agente para calcular os timings da régua
            </span>
          </div>
        </div>
      </div>

      {/* ── Service Status ───────────────────────────────────────────────── */}
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-400 mb-3">
          Status das Integrações
        </p>
        <div className="grid grid-cols-3 gap-3 mb-3">
          {services.map(svc => {
            const badge = STATUS_BADGE[svc.status] ?? STATUS_BADGE.warn
            return (
              <div key={svc.name} className="bg-white border border-slate-200 rounded-lg p-3">
                <div className="flex justify-between items-start mb-1.5">
                  <span className="text-xs font-bold text-navy-950">{svc.name}</span>
                  <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${badge.cls}`}>
                    {badge.label}
                  </span>
                </div>
                <p className="text-[10px] text-slate-500">{svc.role}</p>
                <p className="text-[10px] text-slate-400 mt-0.5">{svc.detail}</p>
              </div>
            )
          })}
        </div>
        <button
          onClick={handleCheckLive}
          disabled={checking}
          className="border border-slate-200 bg-white text-xs font-semibold text-slate-500 px-4 py-2 rounded-md hover:border-navy-700 hover:text-navy-700 disabled:opacity-50 transition-colors"
        >
          {checking ? '⏳ Verificando conexões…' : '🔄 Verificar conexões agora'}
        </button>
      </div>

      {/* ── Jobs Queue ───────────────────────────────────────────────────── */}
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-400 mb-3">
          Fila do Agente — Jobs Recentes
        </p>
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="flex justify-between items-center px-4 py-3 border-b border-slate-100">
            <span className="text-xs font-semibold text-navy-950">Últimos 20 jobs</span>
            <span className="text-[10px] text-slate-400">Atualiza a cada 30s</span>
          </div>
          {jobs.length === 0 ? (
            <p className="text-xs text-slate-300 text-center py-8">Nenhum job encontrado</p>
          ) : (
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Lead</th>
                  <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Job</th>
                  <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Agendado para</th>
                  <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Status</th>
                  <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Ação</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map(job => {
                  const canRun = job.status === 'PENDING' || job.status === 'FAILED'
                  const isRunning = runningJobs.has(job.id)
                  const leadName = job.leads?.name ?? job.lead_id.slice(0, 8) + '…'
                  const leadCompany = job.leads?.company ?? ''
                  const runAt = new Date(job.run_at).toLocaleString('pt-BR', {
                    day: '2-digit', month: 'short', year: 'numeric',
                    hour: '2-digit', minute: '2-digit',
                  })
                  return (
                    <tr key={job.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                      <td className="px-4 py-2.5">
                        <div className="font-semibold text-navy-950 text-[11px]">{leadName}</div>
                        {leadCompany && <div className="text-[10px] text-slate-400">{leadCompany}</div>}
                      </td>
                      <td className="px-4 py-2.5">
                        <code className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-[10px]">
                          {job.job_type}
                        </code>
                      </td>
                      <td className="px-4 py-2.5 text-[10px] text-slate-500">{runAt}</td>
                      <td className="px-4 py-2.5">
                        <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${JOB_STATUS_BADGE[job.status] ?? 'bg-slate-100 text-slate-500'}`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        {canRun ? (
                          <button
                            onClick={() => handleRunJob(job.id)}
                            disabled={isRunning}
                            className="border border-slate-200 text-[10px] font-semibold text-navy-700 px-2 py-1 rounded hover:border-navy-700 disabled:opacity-50 transition-colors"
                          >
                            {isRunning ? '⏳' : job.status === 'FAILED' ? '↻ Retry' : '▶ Rodar agora'}
                          </button>
                        ) : (
                          <span className="text-[10px] text-slate-300">—</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

    </div>
  )
}
