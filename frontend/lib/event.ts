// Single source for reading the current event + its display fallbacks.
//
// Two entry points because the landing is a server component (reads the public backend
// directly) while the dashboard is a client component (reads the authenticated proxy).
// Both share the same fallback constants and the same shape, so the "15 Ago 2026"/120
// literals live in exactly one place.

import { formatEventDate } from './format'
import type { EventConfig } from './types'

export const DEFAULT_CAPACITY = 120
export const DEFAULT_EVENT_DATE_LABEL = '15 Ago 2026'

export type EventInfo = { capacity: number; dateLabel: string }

const FALLBACK: EventInfo = {
  capacity: DEFAULT_CAPACITY,
  dateLabel: DEFAULT_EVENT_DATE_LABEL,
}

function toEventInfo(ev: Pick<EventConfig, 'capacity' | 'event_date'> | null): EventInfo {
  if (!ev) return FALLBACK
  return {
    capacity: ev.capacity ?? DEFAULT_CAPACITY,
    dateLabel: formatEventDate(ev.event_date) || DEFAULT_EVENT_DATE_LABEL,
  }
}

function firstEvent(payload: unknown): Pick<EventConfig, 'capacity' | 'event_date'> | null {
  return Array.isArray(payload) && payload.length > 0 ? payload[0] : null
}

// Server-side (landing): reads the public backend endpoint, no key required.
export async function getEventServer(): Promise<EventInfo> {
  const base = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL
  if (!base) {
    console.warn('[event] BACKEND_API_URL/NEXT_PUBLIC_API_URL ausentes — usando fallback')
    return FALLBACK
  }
  try {
    const res = await fetch(`${base}/api/events/`, { cache: 'no-store' })
    if (!res.ok) {
      console.warn(`[event] backend GET /api/events/ retornou ${res.status} — usando fallback`)
      return FALLBACK
    }
    return toEventInfo(firstEvent(await res.json()))
  } catch (e) {
    console.warn('[event] falha ao buscar evento no backend — usando fallback', e)
    return FALLBACK
  }
}

// Client-side (dashboard): reads the authenticated /api/events proxy.
export async function getEventClient(): Promise<EventInfo> {
  try {
    const res = await fetch('/api/events', { cache: 'no-store' })
    if (!res.ok) {
      console.warn(`[event] /api/events retornou ${res.status} — usando fallback`)
      return FALLBACK
    }
    return toEventInfo(firstEvent(await res.json()))
  } catch (e) {
    console.warn('[event] falha ao buscar /api/events — usando fallback', e)
    return FALLBACK
  }
}
