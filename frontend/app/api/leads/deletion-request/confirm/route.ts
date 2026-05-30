import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  const backendUrl = process.env.BACKEND_API_URL

  if (!backendUrl) {
    return NextResponse.json({ error: 'Configuração ausente' }, { status: 500 })
  }

  const body = await request.json()

  const res = await fetch(`${backendUrl}/api/leads/deletion-request/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
