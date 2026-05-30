import type { RichLead } from '@/lib/types'

type TagColor = 'navy' | 'green' | 'amber' | 'red' | 'slate'
type Tag = { label: string; color: TagColor }
type SignalColor = 'green' | 'amber' | 'gray' | 'red'

const TAG_CLASSES: Record<TagColor, string> = {
  navy:  'bg-brand-teal/10 text-brand-teal',
  green: 'bg-brand-green/10 text-brand-green',
  amber: 'bg-brand-lime/20 text-[#6b7a00]',
  red:   'bg-red-50 text-red-500',
  slate: 'bg-brand-bg text-brand-muted',
}

const SIGNAL_DOT: Record<SignalColor, string> = {
  green: 'bg-brand-green',
  amber: 'bg-brand-lime',
  gray:  'bg-brand-border',
  red:   'bg-red-400',
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
        className="bg-white border border-brand-border rounded-[10px] p-2.5 mb-1.5 cursor-pointer hover:border-brand-teal hover:bg-white hover:shadow-sm transition-all last:mb-0"
      >
      <p className="text-brand-text text-xs font-bold mb-0.5 truncate">{shortName}</p>
      {roleLabel && (
        <p className="text-brand-muted text-[10px] mb-1.5 truncate">{roleLabel}</p>
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
      <div className="flex items-center gap-1.5 pt-1.5 border-t border-brand-bg">
        <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${SIGNAL_DOT[signal.color]}`} />
        <span className="text-[9px] text-brand-muted truncate">{signal.text}</span>
      </div>
    </div>
  )
}
