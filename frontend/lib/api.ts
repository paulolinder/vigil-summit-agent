const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''

const authHeaders = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY,
}

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

export async function getLeads(event_id?: string) {
  const url = event_id
    ? `${API_URL}/api/leads/?event_id=${encodeURIComponent(event_id)}`
    : `${API_URL}/api/leads/`
  const res = await fetch(url, { headers: authHeaders })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getEvents() {
  const res = await fetch(`${API_URL}/api/events/`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function checkinLead(lead_id: string) {
  const res = await fetch(`${API_URL}/api/leads/${lead_id}/checkin`, {
    method: 'POST',
    headers: authHeaders,
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
