// frontend/lib/api.ts
// IMPORTANT: No NEXT_PUBLIC_API_KEY here.
// Authenticated calls go through server-side proxies at /api/leads/*

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function createLead(data: {
  event_id: string
  name: string
  email: string
  company: string
  role: string
  phone?: string
  has_companion?: boolean
  companion_name?: string
  consent: boolean
  whatsapp_consent?: boolean
}) {
  const res = await fetch(`${API_URL}/api/leads/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// Goes to Next.js server proxy at /api/leads — never exposes backend key to browser
export async function getLeads(event_id?: string, limit = 100, offset = 0) {
  const url = new URL('/api/leads', window.location.origin)
  if (event_id) url.searchParams.set('event_id', event_id)
  url.searchParams.set('limit', String(limit))
  url.searchParams.set('offset', String(offset))

  const res = await fetch(url.toString(), { cache: 'no-store' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getEvents() {
  const res = await fetch(`${API_URL}/api/events/`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function checkinLead(lead_id: string) {
  const res = await fetch(`/api/leads/${lead_id}/checkin`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function markNoShow(lead_id: string) {
  const res = await fetch(`/api/leads/${lead_id}/no-show`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function simulateEngagement(
  lead_id: string,
  opts: { opened?: boolean; clicked?: boolean }
) {
  const res = await fetch(`/api/leads/${lead_id}/simulate-engagement`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(opts),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
