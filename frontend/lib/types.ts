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

export type BaseLead = {
  id: string
  name: string | null
  role: string | null
  company: string | null
  stage: string
}

export type Message = {
  lead_id: string
  sent_at: string
  opened_at: string | null
  clicked_at: string | null
  subject: string | null
}

export type ActivityEvent = {
  type: 'sent' | 'opened' | 'clicked'
  timestamp: string
  leadId: string
  leadName: string
}
