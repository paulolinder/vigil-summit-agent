// frontend/app/api/auth/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createSessionToken } from '@/lib/session'

// Per-IP limiter: 5 attempts per 5 minutes
const authAttempts = new Map<string, { count: number; resetAt: number }>()
// Global failed-attempt counter: backstop against IP spoofing via X-Forwarded-For rotation.
// An attacker cycling fake IPs still hits this ceiling.
const globalFailures = { count: 0; resetAt: 0 }
const AUTH_MAX_PER_IP = 5
const AUTH_MAX_GLOBAL = 20
const AUTH_WINDOW_MS = 5 * 60_000
const MAP_PRUNE_THRESHOLD = 500

function pruneExpiredEntries(now: number): void {
  if (authAttempts.size > MAP_PRUNE_THRESHOLD) {
    for (const [key, val] of authAttempts) {
      if (now > val.resetAt) authAttempts.delete(key)
    }
  }
}

function checkAuthRateLimit(ip: string): boolean {
  const now = Date.now()
  pruneExpiredEntries(now)

  // Global check first — prevents IP-spoofing bypass
  if (now > globalFailures.resetAt) {
    globalFailures.count = 0
    globalFailures.resetAt = now + AUTH_WINDOW_MS
  }
  if (globalFailures.count >= AUTH_MAX_GLOBAL) return false

  // Per-IP check
  const entry = authAttempts.get(ip)
  if (!entry || now > entry.resetAt) {
    authAttempts.set(ip, { count: 1, resetAt: now + AUTH_WINDOW_MS })
    return true
  }
  if (entry.count >= AUTH_MAX_PER_IP) return false
  entry.count++
  return true
}

function recordFailedAttempt(): void {
  const now = Date.now()
  if (now > globalFailures.resetAt) {
    globalFailures.count = 0
    globalFailures.resetAt = now + AUTH_WINDOW_MS
  }
  globalFailures.count++
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
    recordFailedAttempt()
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
