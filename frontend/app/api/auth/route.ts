// frontend/app/api/auth/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createSessionToken } from '@/lib/session'

// In-memory rate limiter: 5 attempts per 5 minutes per IP
const authAttempts = new Map<string, { count: number; resetAt: number }>()
const AUTH_MAX = 5
const AUTH_WINDOW_MS = 5 * 60_000

function checkAuthRateLimit(ip: string): boolean {
  const now = Date.now()
  const entry = authAttempts.get(ip)
  if (!entry || now > entry.resetAt) {
    authAttempts.set(ip, { count: 1, resetAt: now + AUTH_WINDOW_MS })
    return true
  }
  if (entry.count >= AUTH_MAX) return false
  entry.count++
  return true
}

export async function POST(request: NextRequest) {
  const ip =
    request.headers.get('x-forwarded-for')?.split(',')[0].trim() ??
    request.headers.get('x-real-ip') ??
    'unknown'

  if (!checkAuthRateLimit(ip)) {
    return NextResponse.json(
      { error: 'Muitas tentativas. Aguarde 5 minutos.' },
      { status: 429 }
    )
  }

  const { password } = await request.json()
  const expected = process.env.DASHBOARD_PASSWORD

  if (!expected || password !== expected) {
    return NextResponse.json({ error: 'Senha incorreta' }, { status: 401 })
  }

  const token = await createSessionToken()
  const res = NextResponse.json({ ok: true })
  res.cookies.set('dashboard_auth', token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 60 * 60 * 24,
    path: '/',
  })
  return res
}
