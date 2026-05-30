'use client'
import { useState, useRef, useEffect } from 'react'

interface FilterBarProps {
  search: string
  onSearchChange: (v: string) => void
  sectorFilter: string | null
  onSectorChange: (v: string | null) => void
  decisionMakerOnly: boolean
  onDecisionMakerChange: (v: boolean) => void
  availableSectors: string[]
  totalVisible: number
  totalAll: number
}

export default function FilterBar({
  search, onSearchChange,
  sectorFilter, onSectorChange,
  decisionMakerOnly, onDecisionMakerChange,
  availableSectors, totalVisible, totalAll,
}: FilterBarProps) {
  const [sectorOpen, setSectorOpen] = useState(false)
  const sectorRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sectorOpen) return
    const handler = (e: MouseEvent) => {
      if (sectorRef.current && !sectorRef.current.contains(e.target as Node)) {
        setSectorOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [sectorOpen])

  const activeCount =
    (search ? 1 : 0) + (sectorFilter ? 1 : 0) + (decisionMakerOnly ? 1 : 0)

  return (
    <div className="px-8 pb-4 flex items-center gap-3 flex-wrap">
      <input
        type="text"
        value={search}
        onChange={e => onSearchChange(e.target.value)}
        placeholder="Buscar por nome ou empresa..."
        className="flex-1 max-w-[280px] border border-slate-200 rounded-md px-3 py-1.5 text-xs text-slate-600 placeholder:text-slate-300 focus:outline-none focus:border-navy-700"
      />

      <div className="relative" ref={sectorRef}>
        <button
          onClick={() => setSectorOpen(v => !v)}
          className={`border rounded-2xl px-3 py-1 text-xs font-semibold transition-colors ${
            sectorFilter
              ? 'bg-blue-50 border-navy-700 text-navy-700'
              : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'
          }`}
        >
          {sectorFilter ?? 'Setor'} ▾
        </button>
        {sectorOpen && (
          <div className="absolute top-full left-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-md z-10 min-w-[160px]">
            <button
              onClick={() => { onSectorChange(null); setSectorOpen(false) }}
              className="w-full text-left px-3 py-2 text-xs text-slate-500 hover:bg-slate-50"
            >
              Todos os setores
            </button>
            {availableSectors.map(s => (
              <button
                key={s}
                onClick={() => { onSectorChange(s); setSectorOpen(false) }}
                className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-50 ${
                  sectorFilter === s ? 'text-navy-700 font-semibold' : 'text-slate-600'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      <button
        onClick={() => onDecisionMakerChange(!decisionMakerOnly)}
        className={`border rounded-2xl px-3 py-1 text-xs font-semibold transition-colors ${
          decisionMakerOnly
            ? 'bg-blue-50 border-navy-700 text-navy-700'
            : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'
        }`}
      >
        {decisionMakerOnly ? 'Decisores ✓' : 'Decisores'}
      </button>

      <span className="ml-auto text-[10px] text-slate-400">
        {totalVisible !== totalAll
          ? `${totalVisible} de ${totalAll} leads`
          : `${totalAll} leads`}
        {activeCount > 0 &&
          ` · ${activeCount} filtro${activeCount > 1 ? 's' : ''} ativo${activeCount > 1 ? 's' : ''}`
        }
      </span>
    </div>
  )
}
