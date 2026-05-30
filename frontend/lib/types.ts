export type LeadEnrichment = {
  lead_id: string
  sector: string | null
  company_size: string | null
  is_decision_maker: boolean | null
}

export type LastMessage = {
  lead_id: string
  sent_at: string
  opened_at: string | null
  clicked_at: string | null
}

export type RichLead = {
  id: string
  name: string | null
  role: string | null
  company: string | null
  stage: string
  enrichment: LeadEnrichment | null
  lastMessage: LastMessage | null
}
