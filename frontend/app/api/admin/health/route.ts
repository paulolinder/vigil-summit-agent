import { NextRequest, NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase-server'

export async function GET(request: NextRequest) {
  const supabase = await createSupabaseServerClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 })

  // In this project, all authenticated users are operators (no public self-signup).
  // The dashboard login is team-only. If multi-tenant auth is added, enforce role check here.
  const backendUrl = process.env.BACKEND_API_URL
  const backendKey = process.env.BACKEND_API_KEY
  if (!backendUrl || !backendKey) return NextResponse.json({ error: 'Configuração ausente' }, { status: 500 })

  const live = request.nextUrl.searchParams.get('live') === 'true'
  const url = `${backendUrl}/api/admin/health${live ? '?live=true' : ''}`
  const res = await fetch(url, { headers: { 'X-API-Key': backendKey }, cache: 'no-store' })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
