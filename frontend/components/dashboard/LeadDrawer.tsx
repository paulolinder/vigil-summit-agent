'use client'
import { useEffect, useState } from 'react'
import type { RichLead, Message } from '@/lib/types'

const STAGE_STYLE: Record<string, { label: string; color: string; bg: string; border: string }> = {
  REGISTERED:        { label: 'Inscrito',       color: 'text-brand-teal',  bg: 'bg-brand-teal/10',  border: 'border-brand-teal/30' },
  ENRICHED:          { label: 'Enriquecido',    color: 'text-brand-teal',  bg: 'bg-brand-teal/10',  border: 'border-brand-teal/30' },
  CONFIRMED:         { label: 'Confirmado',     color: 'text-brand-green', bg: 'bg-brand-green/10', border: 'border-brand-green/30' },
  ATTENDED:          { label: 'Presente',       color: 'text-brand-teal',  bg: 'bg-brand-teal/10',  border: 'border-brand-teal/30' },
  NO_SHOW:           { label: 'No-show',        color: 'text-red-500',     bg: 'bg-red-50',         border: 'border-red-200' },
  MEETING_SCHEDULED: { label: 'Reunião agend.', color: 'text-[#6b7a00]',  bg: 'bg-brand-lime/20',  border: 'border-brand-lime/50' },
  CONVERTED:         { label: 'Convertido',     color: 'text-brand-green', bg: 'bg-brand-green/10', border: 'border-brand-green/30' },
}

function getDrawerTags(lead: RichLead) {
  const tags: Array<{ label: string; cls: string }> = []
  const role = (lead.role ?? '').toLowerCase()
  if (/ciso|cto|ceo|coo|cfo|\bvp\b|diretor|director|chief/.test(role)) {
    tags.push({ label: 'C-level', cls: 'bg-brand-teal/10 text-brand-teal' })
  }
  if (lead.enrichment?.is_decision_maker) {
    tags.push({ label: 'decisor', cls: 'bg-brand-lime/20 text-[#6b7a00]' })
  }
  return tags
}

function msgBorderColor(msg: Message): string {
  if (msg.clicked_at) return 'border-brand-green'
  if (msg.opened_at) return 'border-brand-green/50'
  return 'border-brand-teal'
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

  const [agentRunning, setAgentRunning] = useState(false)
  const [agentResult, setAgentResult] = useState<{ ok: boolean; message: string } | null>(null)

  async function handleRunAgent() {
    setAgentRunning(true)
    setAgentResult(null)
    try {
      const res = await fetch(`/api/leads/${lead.id}/run-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trigger: 'MANUAL_TRIGGER' }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setAgentResult({ ok: true, message: 'Agente iniciado — aguarde o Realtime atualizar o lead' })
    } catch {
      setAgentResult({ ok: false, message: 'Falha ao iniciar o agente' })
    } finally {
      setAgentRunning(false)
    }
  }

  const stage = STAGE_STYLE[lead.stage] ?? {
    label: lead.stage, color: 'text-slate-700', bg: 'bg-slate-50', border: 'border-slate-200',
  }
  const tags = getDrawerTags(lead)
  const isSecurityRole = tags.some(t => t.label === 'C-level')
  const sortedMessages = [...messages].sort(
    (a, b) => new Date(b.sent_at).getTime() - new Date(a.sent_at).getTime()
  )

  return (
    <>
      <div
        className="fixed inset-0 z-[200]"
        style={{ backgroundColor: 'rgba(15, 23, 42, 0.1)' }}
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
          <p className="font-extrabold text-[15px] text-brand-text">{lead.name ?? '—'}</p>
          <p className="text-[11px] text-brand-muted mt-0.5">
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

        {/* Run Agent */}
        <div className="px-5 py-3 border-b border-brand-border bg-brand-bg">
          <p className="text-[10px] font-bold uppercase tracking-[0.06em] text-brand-muted mb-2">
            Ação do Agente
          </p>
          <button
            onClick={handleRunAgent}
            disabled={agentRunning}
            className="w-full bg-brand-navy text-white text-[11px] font-bold py-2 rounded-md
                       hover:bg-brand-teal disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {agentRunning ? '⏳ Executando…' : '▶ Rodar Agente Agora'}
          </button>
          {agentResult && (
            <p className={`text-[10px] mt-1.5 text-center font-semibold ${
              agentResult.ok ? 'text-brand-green' : 'text-red-500'
            }`}>
              {agentResult.message}
            </p>
          )}
        </div>

        {/* Enrichment grid */}
        <div className="px-5 py-4 border-b border-brand-border">
          <p className="text-[10px] font-bold uppercase tracking-[0.06em] text-brand-muted mb-3">
            Perfil enriquecido
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-[10px] text-brand-muted">Setor</p>
              <p className="text-[11px] font-semibold text-brand-text">{lead.enrichment?.sector ?? '—'}</p>
            </div>
            <div>
              <p className="text-[10px] text-brand-muted">Porte da empresa</p>
              <p className="text-[11px] font-semibold text-brand-text">{lead.enrichment?.company_size ?? '—'}</p>
            </div>
            <div>
              <p className="text-[10px] text-brand-muted">Decisor</p>
              <p className={`text-[11px] font-semibold ${lead.enrichment?.is_decision_maker ? 'text-brand-green' : 'text-brand-muted'}`}>
                {lead.enrichment?.is_decision_maker ? '✓ Confirmado' : 'Não identificado'}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-brand-muted">Sinal de segurança</p>
              <p className={`text-[11px] font-semibold ${isSecurityRole ? 'text-brand-green' : 'text-brand-muted'}`}>
                {isSecurityRole ? '✓ Cargo relevante' : 'Não detectado'}
              </p>
            </div>
          </div>
        </div>

        {/* Message history */}
        <div className="px-5 py-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.06em] text-brand-muted mb-3">
            Histórico de mensagens
          </p>
          {sortedMessages.length === 0 ? (
            <p className="text-xs text-brand-border py-4 text-center">Nenhuma mensagem enviada ainda</p>
          ) : (
            <div className="flex flex-col gap-3">
              {sortedMessages.map((msg, i) => (
                <div key={`${msg.sent_at}-${i}`} className={`border-l-2 pl-2.5 ${msgBorderColor(msg)}`}>
                  <p className="text-[11px] font-bold text-brand-text">
                    {msg.subject ?? 'Email enviado'}
                  </p>
                  <p className="text-[10px] text-brand-muted mt-0.5">
                    {new Date(msg.sent_at).toLocaleDateString('pt-BR', {
                      day: '2-digit', month: 'short', year: 'numeric',
                    })}
                  </p>
                  <p className="text-[10px] text-brand-muted mt-0.5">{msgStatus(msg)}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
