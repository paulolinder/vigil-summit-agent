import Anthropic from '@anthropic-ai/sdk'
import OpenAI from 'openai'
import { NextRequest, NextResponse } from 'next/server'

type Provider = 'anthropic' | 'openai'

function detectProvider(): Provider | null {
  if (process.env.ANTHROPIC_API_KEY) return 'anthropic'
  if (process.env.OPENAI_API_KEY) return 'openai'
  return null
}

// Simple in-memory rate limiter: 20 requests per minute per IP.
const rateLimitMap = new Map<string, { count: number; resetAt: number }>()
const RATE_LIMIT = 20
const RATE_WINDOW_MS = 60_000

const MAX_MESSAGES = 20
const MAX_MESSAGE_LENGTH = 2000
const ALLOWED_ROLES = new Set(['user', 'assistant'])

function checkRateLimit(ip: string): boolean {
  const now = Date.now()
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

function systemPrompt(leadContext: string): string {
  return `Você é o assistente de inscrição do Vigil Summit — Segurança para a Era da IA.

Seu objetivo é ajudar executivos de segurança e TI a se inscreverem no evento e esclarecer dúvidas.

O evento:
- Data: em 30 dias
- Local: São Paulo, presencial
- Público: CISOs, CTOs, diretores de TI, gestores de risco
- Capacidade: 120 vagas
- Foco: cibersegurança, IA em segurança, conformidade (LGPD, ISO 27001, SOC 2)

Se o usuário quiser se inscrever, colete: nome, e-mail, empresa e cargo.
Seja conciso e profissional. Não invente informações sobre programação.

${leadContext ? `Contexto atual do lead: ${leadContext}` : ''}`
}

export async function POST(request: NextRequest) {
  const ip =
    request.headers.get('x-forwarded-for')?.split(',')[0].trim() ??
    request.headers.get('x-real-ip') ??
    'unknown'

  if (!checkRateLimit(ip)) {
    return NextResponse.json({ error: 'Muitas requisições. Tente novamente em breve.' }, { status: 429 })
  }

  const provider = detectProvider()
  if (!provider) {
    return NextResponse.json({ error: 'Nenhum provedor de LLM configurado' }, { status: 500 })
  }

  const { messages, leadContext: rawLeadContext } = await request.json()
  const leadContext = rawLeadContext ? String(rawLeadContext).slice(0, 300).replace(/[<>]/g, '') : ''

  if (!messages || !Array.isArray(messages) || messages.length === 0) {
    return NextResponse.json({ error: 'messages inválido' }, { status: 400 })
  }
  if (messages.length > MAX_MESSAGES) {
    return NextResponse.json({ error: `Máximo de ${MAX_MESSAGES} mensagens por requisição` }, { status: 400 })
  }
  for (const msg of messages) {
    if (!msg || typeof msg !== 'object') {
      return NextResponse.json({ error: 'Formato de mensagem inválido' }, { status: 400 })
    }
    if (!ALLOWED_ROLES.has(msg.role)) {
      return NextResponse.json({ error: `Role '${msg.role}' não permitido` }, { status: 400 })
    }
    if (typeof msg.content !== 'string') {
      return NextResponse.json({ error: 'Conteúdo de mensagem deve ser string' }, { status: 400 })
    }
    if (msg.content.length > MAX_MESSAGE_LENGTH) {
      return NextResponse.json({ error: `Mensagem excede ${MAX_MESSAGE_LENGTH} caracteres` }, { status: 400 })
    }
  }
  if (messages[0]?.role !== 'user') {
    return NextResponse.json({ error: 'A primeira mensagem deve ser do usuário' }, { status: 400 })
  }

  const encoder = new TextEncoder()
  const system = systemPrompt(leadContext)

  const stream = new ReadableStream({
    async start(controller) {
      const send = (text: string) =>
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ text })}\n\n`))
      try {
        if (provider === 'anthropic') {
          const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY! })
          const response = await client.messages.create({
            model: 'claude-haiku-4-5-20251001',
            max_tokens: 1024,
            stream: true,
            system,
            // messages is runtime-validated above (role ∈ {user,assistant}, content string)
            messages: messages as unknown as Anthropic.MessageParam[],
          })
          for await (const chunk of response) {
            if (chunk.type === 'content_block_delta' && chunk.delta.type === 'text_delta') {
              send(chunk.delta.text)
            }
          }
        } else {
          const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY! })
          const response = await client.chat.completions.create({
            model: process.env.OPENAI_CHAT_MODEL || 'gpt-4.1-mini',
            max_tokens: 1024,
            stream: true,
            messages: [
              { role: 'system', content: system },
              ...messages,
            ] as unknown as OpenAI.Chat.ChatCompletionMessageParam[],
          })
          for await (const chunk of response) {
            const delta = chunk.choices[0]?.delta?.content
            if (delta) send(delta)
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
