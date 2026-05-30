import type { BaseLead } from '@/lib/types'

const FUNNEL_STAGES = [
  { key: 'REGISTERED',        label: 'Inscritos',      color: '#48C2C5' },
  { key: 'ENRICHED',          label: 'Enriquecidos',   color: '#48C2C5' },
  { key: 'CONFIRMED',         label: 'Confirmados',    color: '#59BD75' },
  { key: 'ATTENDED',          label: 'Presentes',      color: '#48C2C5' },
  { key: 'NO_SHOW',           label: 'No-show',        color: '#f87171' },
  { key: 'MEETING_SCHEDULED', label: 'Reunião agend.', color: '#DDEB4F' },
  { key: 'CONVERTED',         label: 'Convertidos',    color: '#59BD75' },
] as const

// Sequential flow for conversion rate: excludes NO_SHOW (branch)
const SEQ = ['REGISTERED', 'ENRICHED', 'CONFIRMED', 'ATTENDED', 'MEETING_SCHEDULED', 'CONVERTED']

function rateColor(rate: number): string {
  if (rate >= 70) return 'text-brand-green'
  if (rate >= 50) return 'text-[#6b7a00]'
  return 'text-red-400'
}

export default function FunnelChart({ leads }: { leads: BaseLead[] }) {
  const counts = FUNNEL_STAGES.map(s => ({
    ...s,
    count: leads.filter(l => l.stage === s.key).length,
  }))
  const max = Math.max(...counts.map(s => s.count), 1)

  const total = leads.length
  const attendedCount = leads.filter(l =>
    ['ATTENDED', 'MEETING_SCHEDULED', 'CONVERTED'].includes(l.stage)
  ).length
  const convertedCount = leads.filter(l => l.stage === 'CONVERTED').length
  const attendanceRate = total > 0 ? Math.round((attendedCount / total) * 100) : 0
  const conversionRate = total > 0 ? Math.round((convertedCount / total) * 100) : 0

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-400 mb-3">
        Funil de Conversão
      </p>
      <div className="flex flex-col gap-1.5">
        {counts.map(stage => {
          const seqIdx = SEQ.indexOf(stage.key)
          const prevKey = seqIdx > 0 ? SEQ[seqIdx - 1] : null
          const prevCount = prevKey ? leads.filter(l => l.stage === prevKey).length : null
          const rate = prevCount && prevCount > 0
            ? Math.round((stage.count / prevCount) * 100)
            : null
          const pct = Math.round((stage.count / max) * 100)

          return (
            <div key={stage.key} className="flex items-center gap-2">
              <span className="w-[72px] text-[10px] text-brand-muted text-right flex-shrink-0 truncate">
                {stage.label}
              </span>
              <div className="flex-1 bg-brand-bg rounded-sm h-3">
                <div
                  className="h-full rounded-sm transition-all duration-300"
                  style={{ width: `${pct}%`, backgroundColor: stage.color }}
                />
              </div>
              <span className="w-6 text-[10px] font-bold text-brand-muted">{stage.count}</span>
              <span className={`w-8 text-[9px] text-right ${rate !== null ? rateColor(rate) : 'text-brand-border'}`}>
                {rate !== null ? `${rate}%` : '—'}
              </span>
            </div>
          )
        })}
      </div>
      <div className="mt-3 pt-2.5 border-t border-brand-border flex gap-4 flex-wrap">
        <p className="text-[10px] text-brand-muted">
          Comparecimento:{' '}
          <strong className="text-brand-text">{attendanceRate}%</strong>
          {attendanceRate >= 70
            ? <span className="text-brand-green ml-1">✓ meta</span>
            : <span className="text-red-400 ml-1"> abaixo da meta</span>
          }
        </p>
        <p className="text-[10px] text-brand-muted">
          Conversão total: <strong className="text-brand-text">{conversionRate}%</strong>
        </p>
      </div>
    </div>
  )
}
