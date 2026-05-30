import type { ActivityEvent } from '@/lib/types'

const DOT_COLOR: Record<ActivityEvent['type'], string> = {
  clicked: 'bg-amber-500',
  opened:  'bg-green-500',
  sent:    'bg-navy-700',
}

const EVENT_LABEL: Record<ActivityEvent['type'], string> = {
  clicked: 'clicou no link Cal.com',
  opened:  'abriu o email',
  sent:    'recebeu email do agente',
}

function relativeTime(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime()
  const min = Math.floor(diff / 60_000)
  if (min < 1) return 'agora'
  if (min < 60) return `${min}min`
  const h = Math.floor(min / 60)
  if (h < 24) return `${h}h`
  return `${Math.floor(h / 24)}d`
}

export default function ActivityFeed({ events }: { events: ActivityEvent[] }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 flex flex-col">
      <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-400 mb-3">
        Atividade do Agente
      </p>
      {events.length === 0 ? (
        <p className="text-xs text-slate-300 text-center py-8">Nenhuma atividade registrada</p>
      ) : (
        <div className="flex flex-col overflow-y-auto">
          {events.map((ev, i) => (
            <div
              key={`${ev.leadId}-${ev.type}-${ev.timestamp}-${i}`}
              className="flex items-start gap-2 py-1.5 border-b border-slate-50 last:border-0"
            >
              <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1 ${DOT_COLOR[ev.type]}`} />
              <p className="text-[11px] text-slate-500 flex-1 leading-snug">
                <strong className="text-slate-800 font-semibold">{ev.leadName}</strong>{' '}
                {EVENT_LABEL[ev.type]}
              </p>
              <span className="text-[10px] text-slate-300 flex-shrink-0 mt-0.5">
                {relativeTime(ev.timestamp)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
