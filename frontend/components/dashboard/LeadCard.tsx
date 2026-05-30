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

export default function LeadCard({ lead }: { lead: RichLead }) {
  const tags = getTags(lead)
  const signal = getSignal(lead)
  const parts = (lead.name ?? '').split(' ')
  const shortName = parts.length > 1 ? `${parts[0]} ${parts[parts.length - 1]}` : (lead.name ?? '—')

  const roleLabel = [lead.role, lead.company, lead.enrichment?.company_size]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-md p-2.5 mb-1.5 cursor-pointer hover:border-sky-700 hover:bg-white hover:shadow-sm transition-all last:mb-0">
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
