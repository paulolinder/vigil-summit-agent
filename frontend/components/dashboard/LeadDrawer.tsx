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
