import { NextRequest, NextResponse } from 'next/server'

export async function POST(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  const backendUrl = process.env.BACKEND_API_URL
  const backendKey = process.env.BACKEND_API_KEY

  if (!backendUrl || !backendKey) {
    return NextResponse.json({ error: 'Configuração ausente' }, { status: 500 })
  }

  const res = await fetch(`${backendUrl}/api/leads/${params.id}/checkin`, {
    method: 'POST',
    headers: { 'X-API-Key': backendKey },
  })

  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
