'use client'
import { useState, useEffect, useCallback } from 'react'
import type { EventConfig, ServiceStatus, JobRow } from '@/lib/types'

const STATUS_BADGE: Record<string, { cls: string; label: string }> = {
  ok:       { cls: 'bg-brand-green/10 text-brand-green', label: '✓ Ativo' },
  warn:     { cls: 'bg-brand-lime/20 text-[#6b7a00]',   label: '⚠ Não configurado' },
  error:    { cls: 'bg-red-50 text-red-500',             label: '✗ Erro' },
  checking: { cls: 'bg-brand-bg text-brand-muted',       label: '⏳ Verificando…' },
}

const JOB_STATUS_BADGE: Record<string, string> = {
  DONE:    'bg-brand-green/10 text-brand-green',
  PENDING: 'bg-brand-teal/10 text-brand-teal',
  RUNNING: 'bg-brand-lime/20 text-[#6b7a00]',
  FAILED:  'bg-red-50 text-red-500',
  SKIPPED: 'bg-brand-bg text-brand-muted',
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
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-brand-muted mb-3">
          Configuração do Evento
        </p>
        <div className="bg-white border border-brand-border border-t-[3px] border-t-brand-teal rounded-lg p-5">
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-[10px] font-semibold text-brand-muted mb-1.5">Nome</label>
              <input
                type="text"
                value={form.name ?? ''}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full border border-brand-border rounded-[10px] px-3 py-2 text-xs text-brand-text focus:outline-none focus:border-brand-teal"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-brand-muted mb-1.5">Data do evento</label>
              <input
                type="date"
                value={form.event_date ?? ''}
                onChange={e => setForm(f => ({ ...f, event_date: e.target.value }))}
                className="w-full border border-brand-border rounded-[10px] px-3 py-2 text-xs text-brand-text focus:outline-none focus:border-brand-teal"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-brand-muted mb-1.5">Capacidade máxima</label>
              <input
                type="number"
                value={form.capacity ?? 120}
                onChange={e => setForm(f => ({ ...f, capacity: Number(e.target.value) }))}
                className="w-full border border-brand-border rounded-[10px] px-3 py-2 text-xs text-brand-text focus:outline-none focus:border-brand-teal"
              />
            </div>
          </div>
          <div className="mb-4">
            <div className="flex justify-between text-[10px] text-brand-muted mb-1">
              <span>Vagas ocupadas: <strong>{totalLeads} de {capacity}</strong> ({pct}%)</span>
              <span>{capacity - totalLeads} vagas disponíveis</span>
            </div>
            <div className="bg-brand-bg rounded-full h-1.5">
              <div
                className="bg-brand-teal rounded-full h-full transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="bg-brand-navy text-white text-xs font-bold px-5 py-2 rounded-[10px] hover:bg-brand-teal disabled:opacity-50 transition-colors"
            >
              {saving ? 'Salvando…' : 'Salvar alterações'}
            </button>
            {saveMsg && (
              <span className={`text-xs font-semibold ${saveMsg.startsWith('✓') ? 'text-brand-green' : 'text-red-500'}`}>
                {saveMsg}
              </span>
            )}
            <span className="text-[10px] text-brand-muted ml-1">
              Atualiza a data usada pelo agente para calcular os timings da régua
            </span>
          </div>
        </div>
      </div>

      {/* ── Service Status ───────────────────────────────────────────────── */}
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-brand-muted mb-3">
          Status das Integrações
        </p>
        <div className="grid grid-cols-3 gap-3 mb-3">
          {services.map(svc => {
            const badge = STATUS_BADGE[svc.status] ?? STATUS_BADGE.warn
            return (
              <div key={svc.name} className="bg-white border border-brand-border rounded-[14px] p-3">
                <div className="flex justify-between items-start mb-1.5">
                  <span className="text-xs font-bold text-brand-text">{svc.name}</span>
                  <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${badge.cls}`}>
                    {badge.label}
                  </span>
                </div>
                <p className="text-[10px] text-brand-muted">{svc.role}</p>
                <p className="text-[10px] text-brand-muted mt-0.5">{svc.detail}</p>
              </div>
            )
          })}
        </div>
        <button
          onClick={handleCheckLive}
          disabled={checking}
          className="border border-brand-border bg-white text-xs font-semibold text-brand-muted px-4 py-2 rounded-[10px] hover:border-brand-teal hover:text-brand-teal disabled:opacity-50 transition-colors"
        >
          {checking ? '⏳ Verificando conexões…' : '🔄 Verificar conexões agora'}
        </button>
      </div>

      {/* ── Jobs Queue ───────────────────────────────────────────────────── */}
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-brand-muted mb-3">
          Fila do Agente — Jobs Recentes
        </p>
        <div className="bg-white border border-brand-border rounded-lg overflow-hidden">
          <div className="flex justify-between items-center px-4 py-3 border-b border-brand-bg">
            <span className="text-xs font-semibold text-brand-text">Últimos 20 jobs</span>
            <span className="text-[10px] text-brand-muted">Atualiza a cada 30s</span>
          </div>
          {jobs.length === 0 ? (
            <p className="text-xs text-brand-border text-center py-8">Nenhum job encontrado</p>
          ) : (
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-brand-bg border-b border-brand-bg">
                  <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-brand-muted">Lead</th>
                  <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-brand-muted">Job</th>
                  <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-brand-muted">Agendado para</th>
                  <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-brand-muted">Status</th>
                  <th className="text-left px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-brand-muted">Ação</th>
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
                    <tr key={job.id} className="border-b border-brand-bg last:border-0 hover:bg-brand-bg">
                      <td className="px-4 py-2.5">
                        <div className="font-semibold text-brand-text text-[11px]">{leadName}</div>
                        {leadCompany && <div className="text-[10px] text-brand-muted">{leadCompany}</div>}
                      </td>
                      <td className="px-4 py-2.5">
                        <code className="bg-brand-bg text-brand-muted px-1.5 py-0.5 rounded text-[10px]">
                          {job.job_type}
                        </code>
                      </td>
                      <td className="px-4 py-2.5 text-[10px] text-brand-muted">{runAt}</td>
                      <td className="px-4 py-2.5">
                        <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${JOB_STATUS_BADGE[job.status] ?? 'bg-brand-bg text-brand-muted'}`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        {canRun ? (
                          <button
                            onClick={() => handleRunJob(job.id)}
                            disabled={isRunning}
                            className="border border-brand-border text-[10px] font-semibold text-brand-teal px-2 py-1 rounded hover:border-brand-teal disabled:opacity-50 transition-colors"
                          >
                            {isRunning ? '⏳' : job.status === 'FAILED' ? '↻ Retry' : '▶ Rodar agora'}
                          </button>
                        ) : (
                          <span className="text-[10px] text-brand-border">—</span>
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
