import { NextRequest, NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase-server'

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const supabase = await createSupabaseServerClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 })

  const backendUrl = process.env.BACKEND_API_URL
  const backendKey = process.env.BACKEND_API_KEY
  if (!backendUrl || !backendKey) return NextResponse.json({ error: 'Configuração ausente' }, { status: 500 })

  if (!UUID_RE.test(params.id)) return NextResponse.json({ error: 'ID inválido' }, { status: 400 })

  let body = {}
  try { body = await request.json() } catch { /* empty body is fine */ }

  const res = await fetch(`${backendUrl}/api/leads/${params.id}/run-agent`, {
    method: 'POST',
    headers: { 'X-API-Key': backendKey, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
