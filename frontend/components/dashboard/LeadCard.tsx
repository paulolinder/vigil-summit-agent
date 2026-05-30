type Lead = {
  id: string
  name: string | null
  company: string | null
  role: string | null
  stage: string
}

export default function LeadCard({ lead }: { lead: Lead }) {
  const parts = (lead.name || '').split(' ')
  const shortName = parts.length > 1
    ? `${parts[0]} ${parts[parts.length - 1]}`
    : (lead.name || '—')

  return (
    <div className="bg-gray-800 rounded p-2 hover:bg-gray-750 transition-colors">
      <p className="text-white text-sm font-medium truncate">{shortName}</p>
      <p className="text-gray-400 text-xs truncate">{lead.role}</p>
      <p className="text-gray-500 text-xs truncate">{lead.company}</p>
    </div>
  )
}
