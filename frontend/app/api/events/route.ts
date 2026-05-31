import { NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase-server'

export async function GET() {
  const supabase = await createSupabaseServerClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 })

  const backendUrl = process.env.BACKEND_API_URL
  const backendKey = process.env.BACKEND_API_KEY
  if (!backendUrl || !backendKey) return NextResponse.json({ error: 'Configuração ausente' }, { status: 500 })

  // Backend GET /api/events/ is public (the landing form consumes it unauthenticated),
  // so the X-API-Key is harmless here. Access control for the dashboard is enforced above
  // via the Supabase session, consistent with the other /api proxies.
  const res = await fetch(`${backendUrl}/api/events/`, {
    headers: { 'X-API-Key': backendKey },
    cache: 'no-store',
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
