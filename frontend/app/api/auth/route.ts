import { NextRequest, NextResponse } from 'next/server'

async function hashPassword(password: string): Promise<string> {
  const data = new TextEncoder().encode(password)
  const hash = await crypto.subtle.digest('SHA-256', data)
  return Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
}

export async function POST(request: NextRequest) {
  const { password } = await request.json()
  const expected = process.env.DASHBOARD_PASSWORD

  if (!expected || password !== expected) {
    return NextResponse.json({ error: 'Senha incorreta' }, { status: 401 })
  }

  const token = await hashPassword(expected)
  const res = NextResponse.json({ ok: true })
  res.cookies.set('dashboard_auth', token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24,
    path: '/',
  })
  return res
}
