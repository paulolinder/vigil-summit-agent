// Centralized event-date formatting.
//
// IMPORTANT: the event_date is stored as TIMESTAMPTZ (UTC) and the app may render on
// Vercel, whose Node runtime defaults to UTC. A naive `toLocaleDateString` would then
// risk showing the previous day for evening-in-Brazil timestamps. We pin the timezone to
// America/Sao_Paulo and extract the calendar parts explicitly, so the displayed day is
// always the Brazil-local day regardless of where the code runs.

const MONTHS_PT = [
  'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
  'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez',
]

/**
 * Formats an ISO timestamp as "15 Ago 2026" in the America/Sao_Paulo timezone.
 * Returns '' for missing/invalid input so callers can apply their own fallback.
 */
export function formatEventDate(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''

  // en-CA + 2-digit parts gives stable numeric values to assemble ourselves.
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Sao_Paulo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(d)

  const get = (type: string) => parts.find(p => p.type === type)?.value ?? ''
  const day = get('day')
  const month = MONTHS_PT[parseInt(get('month'), 10) - 1] ?? ''
  const year = get('year')
  if (!day || !month || !year) return ''

  return `${day} ${month} ${year}`
}
