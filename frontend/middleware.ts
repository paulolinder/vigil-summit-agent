import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

async function hashPassword(password: string): Promise<string> {
  const data = new TextEncoder().encode(password)
  const hash = await crypto.subtle.digest('SHA-256', data)
  return Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
}

export async function middleware(request: NextRequest) {
  const expected = process.env.DASHBOARD_PASSWORD
  if (!expected) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  const auth = request.cookies.get('dashboard_auth')
  const validToken = await hashPassword(expected)

  if (auth?.value !== validToken) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*'],
}
