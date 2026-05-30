// frontend/lib/session.ts

const REQUIRED_SECRET_LENGTH = 32

function getSecret(): string {
  const secret = process.env.SESSION_SECRET
  if (!secret || secret.length < REQUIRED_SECRET_LENGTH) {
    throw new Error(`SESSION_SECRET deve ter ao menos ${REQUIRED_SECRET_LENGTH} caracteres`)
  }
  return secret
}

async function hmacSign(data: string, secret: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  )
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(data))
  return Array.from(new Uint8Array(sig))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  const ab = new TextEncoder().encode(a)
  const bb = new TextEncoder().encode(b)
  let diff = 0
  for (let i = 0; i < ab.length; i++) diff |= ab[i] ^ bb[i]
  return diff === 0
}

// Token format: <nonce_hex>.<expires_ms>.<hmac_hex>
// Nonce prevents replay of intercepted tokens even with same expiry.
export async function createSessionToken(): Promise<string> {
  const nonce = Array.from(crypto.getRandomValues(new Uint8Array(16)))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
  const expiresAt = Date.now() + 24 * 60 * 60 * 1000
  const payload = `${nonce}.${expiresAt}`
  const sig = await hmacSign(payload, getSecret())
  return `${payload}.${sig}`
}

export async function validateSessionToken(token: string): Promise<boolean> {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return false
    const [nonce, expiresAtStr, sig] = parts
    const expiresAt = parseInt(expiresAtStr, 10)
    if (isNaN(expiresAt) || Date.now() > expiresAt) return false
    const payload = `${nonce}.${expiresAt}`
    const expectedSig = await hmacSign(payload, getSecret())
    return timingSafeEqual(sig, expectedSig)
  } catch {
    return false
  }
}
