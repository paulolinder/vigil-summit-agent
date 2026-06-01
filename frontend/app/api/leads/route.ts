import { NextRequest, NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase-server'

export async function GET(request: NextRequest) {
  const supabase = await createSupabaseServerClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return NextResponse.json({ error: 'Não autorizado' }, { status: 401 })
  }

  const backendUrl = process.env.BACKEND_API_URL
  const backendKey = process.env.BACKEND_API_KEY

  if (!backendUrl || !backendKey) {
    return NextResponse.json({ error: 'Configuração ausente' }, { status: 500 })
  }

  const { searchParams } = new URL(request.url)
  const eventId = searchParams.get('event_id')
  // Sanitiza limit/offset antes de repassar (o backend revalida, mas o proxy não
  // deve encaminhar lixo): limit em [1,500], offset >= 0.
  const limit = Math.min(Math.max(parseInt(searchParams.get('limit') ?? '100', 10) || 100, 1), 500)
  const offset = Math.max(parseInt(searchParams.get('offset') ?? '0', 10) || 0, 0)

  const url = new URL(`${backendUrl}/api/leads/`)
  if (eventId) url.searchParams.set('event_id', eventId)
  url.searchParams.set('limit', String(limit))
  url.searchParams.set('offset', String(offset))

  const res = await fetch(url.toString(), {
    headers: { 'X-API-Key': backendKey },
    cache: 'no-store',
  })

  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
