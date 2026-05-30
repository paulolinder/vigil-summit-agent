import { NextRequest, NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase-server'

export async function GET(request: NextRequest) {
  const supabase = await createSupabaseServerClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 })

  const backendUrl = process.env.BACKEND_API_URL
  const backendKey = process.env.BACKEND_API_KEY
  if (!backendUrl || !backendKey) return NextResponse.json({ error: 'Configuração ausente' }, { status: 500 })

  // In this project, all authenticated users are operators (no public self-signup).
  // The dashboard login is team-only. If multi-tenant auth is added, enforce role check here.
  const rawLimit = request.nextUrl.searchParams.get('limit')
  const limit = Math.min(Math.max(parseInt(rawLimit ?? '20', 10) || 20, 1), 100)
  const res = await fetch(`${backendUrl}/api/admin/jobs?limit=${limit}`, {
    headers: { 'X-API-Key': backendKey },
    cache: 'no-store',
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
