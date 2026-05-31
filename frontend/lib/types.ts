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
  channel?: string | null
  status?: string | null
}

export type ActivityEvent = {
  type: 'sent' | 'opened' | 'clicked'
  timestamp: string
  leadId: string
  leadName: string
}

export type ServiceStatus = {
  name: string
  role: string
  status: 'ok' | 'warn' | 'error' | 'checking'
  detail: string
}

export type JobRow = {
  id: string
  lead_id: string
  job_type: string
  run_at: string
  status: 'PENDING' | 'RUNNING' | 'DONE' | 'FAILED' | 'SKIPPED'
  error: string | null
  created_at: string
  leads: { name: string | null; company: string | null; role: string | null } | null
}

export type EventConfig = {
  id: string
  name: string
  event_date: string | null
  capacity: number | null
}
