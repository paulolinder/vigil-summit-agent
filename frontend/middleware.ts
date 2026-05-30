import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const expected = process.env.DASHBOARD_PASSWORD
  const auth = request.cookies.get('dashboard_auth')

  if (!expected || auth?.value !== expected) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*'],
}
