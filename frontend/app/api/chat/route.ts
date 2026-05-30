import Anthropic from '@anthropic-ai/sdk'
import { NextRequest, NextResponse } from 'next/server'

// Client initialized lazily inside the handler — ANTHROPIC_API_KEY is a
// runtime env var and must not be read at module load time (build phase).
function getClient(): Anthropic {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error('ANTHROPIC_API_KEY não configurada')
  }
  return new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
}

// Simple in-memory rate limiter: 20 requests per minute per IP.
// For multi-instance deployments, replace with a Redis-backed store.
const rateLimitMap = new Map<string, { count: number; resetAt: number }>()
const RATE_LIMIT = 20
const RATE_WINDOW_MS = 60_000

const MAX_MESSAGES = 20
const MAX_MESSAGE_LENGTH = 2000
const ALLOWED_ROLES = new Set(['user', 'assistant'])

function checkRateLimit(ip: string): boolean {
  const now = Date.now()

  // Prune expired entries to prevent unbounded memory growth on long-running instances
  if (rateLimitMap.size > 1000) {
    for (const [key, val] of rateLimitMap) {
      if (now > val.resetAt) rateLimitMap.delete(key)
    }
  }

  const entry = rateLimitMap.get(ip)

  if (!entry || now > entry.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_WINDOW_MS })
    return true
  }

  if (entry.count >= RATE_LIMIT) return false

  entry.count++
  return true
}

export async function POST(request: NextRequest) {
  const ip =
    request.headers.get('x-forwarded-for')?.split(',')[0].trim() ??
    request.headers.get('x-real-ip') ??
    'unknown'

  if (!checkRateLimit(ip)) {
    return NextResponse.json({ error: 'Muitas requisições. Tente novamente em breve.' }, { status: 429 })
  }

  const { messages, leadContext: rawLeadContext } = await request.json()

  // Truncate and strip angle brackets to limit prompt injection surface
  const leadContext = rawLeadContext
    ? String(rawLeadContext).slice(0, 300).replace(/[<>]/g, '')
    : ''

  if (!messages || !Array.isArray(messages) || messages.length === 0) {
    return NextResponse.json({ error: 'messages inválido' }, { status: 400 })
  }

  if (messages.length > MAX_MESSAGES) {
    return NextResponse.json(
      { error: `Máximo de ${MAX_MESSAGES} mensagens por requisição` },
      { status: 400 }
    )
  }

  for (const msg of messages) {
    if (!msg || typeof msg !== 'object') {
      return NextResponse.json({ error: 'Formato de mensagem inválido' }, { status: 400 })
    }
    if (!ALLOWED_ROLES.has(msg.role)) {
      return NextResponse.json(
        { error: `Role '${msg.role}' não permitido` },
        { status: 400 }
      )
    }
    if (typeof msg.content !== 'string') {
      return NextResponse.json({ error: 'Conteúdo de mensagem deve ser string' }, { status: 400 })
    }
    if (msg.content.length > MAX_MESSAGE_LENGTH) {
      return NextResponse.json(
        { error: `Mensagem excede ${MAX_MESSAGE_LENGTH} caracteres` },
        { status: 400 }
      )
    }
  }

  if (messages[0]?.role !== 'user') {
    return NextResponse.json({ error: 'A primeira mensagem deve ser do usuário' }, { status: 400 })
  }

  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    async start(controller) {
      try {
        const response = await getClient().messages.create({
          model: 'claude-haiku-4-5-20251001',
          max_tokens: 1024,
          stream: true,
          system: `Você é o assistente de inscrição do Vigil Summit — Segurança para a Era da IA.

Seu objetivo é ajudar executivos de segurança e TI a se inscreverem no evento e esclarecer dúvidas.

O evento:
- Data: em 30 dias
- Local: São Paulo, presencial
- Público: CISOs, CTOs, diretores de TI, gestores de risco
- Capacidade: 120 vagas
- Foco: cibersegurança, IA em segurança, conformidade (LGPD, ISO 27001, SOC 2)

Se o usuário quiser se inscrever, colete: nome, e-mail, empresa e cargo.
Seja conciso e profissional. Não invente informações sobre programação.

${leadContext ? `Contexto atual do lead: ${leadContext}` : ''}`,
          messages,
        })

        for await (const chunk of response) {
          if (chunk.type === 'content_block_delta' && chunk.delta.type === 'text_delta') {
            const data = `data: ${JSON.stringify({ text: chunk.delta.text })}\n\n`
            controller.enqueue(encoder.encode(data))
          }
        }

        controller.enqueue(encoder.encode('data: [DONE]\n\n'))
        controller.close()
      } catch (error) {
        const errMsg = error instanceof Error ? error.message : 'Erro interno'
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ error: errMsg })}\n\n`))
        controller.enqueue(encoder.encode('data: [DONE]\n\n'))
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  })
}
