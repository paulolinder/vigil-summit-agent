// frontend/middleware.ts
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { validateSessionToken } from '@/lib/session'

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('dashboard_auth')?.value
  if (!token || !(await validateSessionToken(token))) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*'],
}
