# Frontend Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign completo do frontend Next.js para identidade visual Navy Slate profissional — sem roxo, com Playfair Display em headings, Inter no corpo, KPIs e cards ricos no dashboard.

**Architecture:** Visual-only rewrite — toda lógica de negócio, endpoints e estado existentes são preservados. Novo design system via Tailwind + next/font/google. FunnelBoard estendido com queries secundárias ao Supabase para dados de enriquecimento e sinais do agente.

**Tech Stack:** Next.js 14, Tailwind CSS, next/font/google (Playfair Display + Inter), @supabase/supabase-js

---

## Mapa de arquivos

| Arquivo | Ação |
|---|---|
| `frontend/tailwind.config.ts` | Modificar — adicionar `font-playfair` e `font-sans` via CSS vars |
| `frontend/app/layout.tsx` | Modificar — next/font/google, body classes |
| `frontend/app/globals.css` | Modificar — remover `bg-gray-950 text-white` do body (moved to layout) |
| `frontend/lib/types.ts` | Criar — tipos `RichLead`, `LeadEnrichment`, `LastMessage` compartilhados |
| `frontend/components/ui/Navbar.tsx` | Criar — navbar compartilhada landing e dashboard |
| `frontend/app/page.tsx` | Reescrever — nova estrutura Hero/Trilhas/Público/Footer |
| `frontend/components/landing/RegistrationForm.tsx` | Modificar — restyle CSS, lógica intacta |
| `frontend/components/landing/ChatbotWidget.tsx` | Modificar — restyle navy + SVG icon, lógica intacta |
| `frontend/app/login/page.tsx` | Reescrever — identidade navy slate |
| `frontend/app/deletion-confirm/page.tsx` | Modificar — identidade navy slate |
| `frontend/components/dashboard/LeadCard.tsx` | Reescrever — card rico com tags e sinal do agente |
| `frontend/components/dashboard/FunnelBoard.tsx` | Reescrever — KPI strip + queries de enriquecimento + kanban rico |
| `frontend/app/dashboard/page.tsx` | Modificar — usar Navbar, remover header manual |

---

## Task 1: Design system — fontes e Tailwind

**Files:**
- Modify: `frontend/tailwind.config.ts`
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/app/globals.css`

- [ ] **Step 1: Atualizar `tailwind.config.ts`**

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        playfair: ['var(--font-playfair)', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
}
export default config
```

- [ ] **Step 2: Atualizar `app/layout.tsx`**

```typescript
import type { Metadata } from 'next'
import { Inter, Playfair_Display } from 'next/font/google'
import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-playfair',
  weight: ['700', '800', '900'],
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Vigil Summit — Segurança para a Era da IA',
  description: 'Evento exclusivo de cibersegurança para CISOs, CTOs e líderes de TI.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className={`${inter.variable} ${playfair.variable} font-sans bg-slate-100 text-slate-900 antialiased`}>
        {children}
      </body>
    </html>
  )
}
```

- [ ] **Step 3: Atualizar `app/globals.css`** — remover o fundo escuro antigo (body estilizado agora no layout)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 4: Verificar compilação**

```bash
cd frontend && npm run build
```

Esperado: sem erros de TypeScript. Se houver erro de fonte não encontrada, verificar se `next/font/google` está disponível (`npm ls next` — deve ser ≥ 13).

- [ ] **Step 5: Commit**

```bash
git add frontend/tailwind.config.ts frontend/app/layout.tsx frontend/app/globals.css
git commit -m "feat(frontend): design system — Playfair Display + Inter via next/font"
```

---

## Task 2: Tipos compartilhados

**Files:**
- Create: `frontend/lib/types.ts`

- [ ] **Step 1: Criar `lib/types.ts`**

```typescript
export type LeadEnrichment = {
  lead_id: string
  sector: string | null
  company_size: string | null
  is_decision_maker: boolean | null
}

export type LastMessage = {
  lead_id: string
  sent_at: string
  opened_at: string | null
  clicked_at: string | null
}

export type RichLead = {
  id: string
  name: string | null
  role: string | null
  company: string | null
  stage: string
  enrichment: LeadEnrichment | null
  lastMessage: LastMessage | null
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/lib/types.ts
git commit -m "feat(frontend): shared RichLead types"
```

---

## Task 3: Navbar compartilhada

**Files:**
- Create: `frontend/components/ui/Navbar.tsx`

- [ ] **Step 1: Criar `components/ui/Navbar.tsx`**

```typescript
import Link from 'next/link'

interface NavbarProps {
  variant?: 'landing' | 'dashboard'
}

export default function Navbar({ variant = 'landing' }: NavbarProps) {
  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-screen-xl mx-auto px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/" className="font-black text-lg tracking-wide text-slate-900">
            VIGIL<span className="text-sky-700">.AI</span>
          </Link>
          {variant === 'dashboard' && (
            <>
              <div className="w-px h-5 bg-slate-200" />
              <span className="font-playfair font-bold text-slate-500 text-[15px]">
                Vigil Summit — Funil de Leads
              </span>
            </>
          )}
        </div>

        {variant === 'landing' && (
          <div className="flex items-center gap-7">
            <a href="#agenda" className="text-slate-500 hover:text-slate-900 text-sm font-medium transition-colors">
              Agenda
            </a>
            <a href="#speakers" className="text-slate-500 hover:text-slate-900 text-sm font-medium transition-colors">
              Speakers
            </a>
            <a href="#local" className="text-slate-500 hover:text-slate-900 text-sm font-medium transition-colors">
              Local
            </a>
            <a
              href="#inscricao"
              className="bg-slate-900 text-white text-sm font-bold px-5 py-2.5 rounded hover:bg-sky-700 transition-colors"
            >
              Garantir vaga →
            </a>
          </div>
        )}

        {variant === 'dashboard' && (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 bg-green-50 border border-green-200 text-green-700 text-xs font-bold px-3 py-1.5 rounded-full">
              <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse inline-block" />
              Ao vivo
            </div>
            <Link href="/" className="text-slate-400 hover:text-slate-600 text-xs transition-colors">
              ← Landing page
            </Link>
          </div>
        )}
      </div>
    </nav>
  )
}
```

- [ ] **Step 2: Verificar compilação**

```bash
cd frontend && npm run build
```

Esperado: sem erros.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ui/Navbar.tsx
git commit -m "feat(frontend): shared Navbar component — landing + dashboard variants"
```

---

## Task 4: Login page

**Files:**
- Modify: `frontend/app/login/page.tsx`

- [ ] **Step 1: Reescrever `app/login/page.tsx`**

```typescript
'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      if (!res.ok) {
        setError('Senha incorreta. Tente novamente.')
        setLoading(false)
      } else {
        router.push('/dashboard')
      }
    } catch {
      setError('Erro de conexão.')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center px-4">
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 w-full max-w-sm">
        <p className="font-black text-lg tracking-wide text-slate-900 text-center mb-1">
          VIGIL<span className="text-sky-700">.AI</span>
        </p>
        <h1 className="font-playfair font-bold text-2xl text-slate-900 text-center mb-1">
          Acesso ao Dashboard
        </h1>
        <p className="text-slate-500 text-sm text-center mb-7">Restrito à equipe Vigil.AI</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Senha"
            required
            className="w-full bg-slate-50 border border-slate-200 rounded px-4 py-3 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-700 transition-colors text-sm"
          />
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-slate-900 hover:bg-sky-700 disabled:opacity-50 text-white font-bold py-3 rounded transition-colors text-sm"
          >
            {loading ? 'Entrando…' : 'Entrar →'}
          </button>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/login/page.tsx
git commit -m "feat(frontend): login page — navy slate identity"
```

---

## Task 5: Deletion confirm page

**Files:**
- Modify: `frontend/app/deletion-confirm/page.tsx`

- [ ] **Step 1: Atualizar apenas as classes CSS — lógica intacta**

Substituir todas as ocorrências de classes escuras pelas equivalentes navy slate. As únicas mudanças são nos `className`:

```typescript
'use client'
import { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'

type Status = 'loading' | 'success' | 'error'

function DeletionConfirmContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [status, setStatus] = useState<Status>('loading')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setErrorMsg('Link inválido ou expirado.')
      return
    }
    fetch('/api/leads/deletion-request/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
      .then(async r => {
        if (r.status === 200) {
          setStatus('success')
        } else {
          const data = await r.json().catch(() => ({}))
          setStatus('error')
          setErrorMsg(
            r.status === 404
              ? 'Link expirado ou já utilizado.'
              : (data.detail || 'Erro ao processar solicitação.')
          )
        }
      })
      .catch(() => {
        setStatus('error')
        setErrorMsg('Erro de conexão. Tente novamente em instantes.')
      })
  }, [token])

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center px-4">
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 w-full max-w-md text-center">
        <p className="font-black text-base tracking-wide text-slate-900 mb-1">
          VIGIL<span className="text-sky-700">.AI</span>
        </p>
        <h1 className="font-playfair font-bold text-xl text-slate-900 mb-5">
          Exclusão de Dados
        </h1>

        {status === 'loading' && (
          <p className="text-slate-500 text-sm">Processando sua solicitação…</p>
        )}

        {status === 'success' && (
          <div>
            <p className="text-green-700 font-semibold mb-2">Dados excluídos com sucesso.</p>
            <p className="text-slate-500 text-sm">
              Seus dados pessoais foram removidos do Vigil Summit. Você não receberá mais
              comunicações nossas.
            </p>
          </div>
        )}

        {status === 'error' && (
          <div>
            <p className="text-red-600 font-semibold mb-2">Não foi possível processar.</p>
            <p className="text-slate-500 text-sm">{errorMsg}</p>
            <p className="text-slate-400 text-xs mt-4">
              Precisa de ajuda?{' '}
              <a href="mailto:privacidade@vigil.ai" className="underline text-sky-700">
                privacidade@vigil.ai
              </a>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function DeletionConfirmPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-slate-100 flex items-center justify-center">
        <p className="text-slate-500 text-sm">Carregando…</p>
      </div>
    }>
      <DeletionConfirmContent />
    </Suspense>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/deletion-confirm/page.tsx
git commit -m "feat(frontend): deletion-confirm page — navy slate identity"
```

---

## Task 6: RegistrationForm restyle

**Files:**
- Modify: `frontend/components/landing/RegistrationForm.tsx`

Apenas as classes CSS mudam — nenhuma lógica de estado, submit ou validação é alterada.

- [ ] **Step 1: Atualizar classes na constante `inputClass` e nos elementos**

```typescript
'use client'
import { useState, useEffect } from 'react'
import { createLead, getEvents } from '@/lib/api'

interface FormState {
  name: string
  email: string
  company: string
  role: string
  phone: string
  has_companion: boolean
  companion_name: string
  consent: boolean
  whatsapp_consent: boolean
}

export default function RegistrationForm() {
  const [eventId, setEventId] = useState<string>('')
  const [eventError, setEventError] = useState(false)
  const [form, setForm] = useState<FormState>({
    name: '', email: '', company: '', role: '', phone: '',
    has_companion: false, companion_name: '',
    consent: false, whatsapp_consent: false,
  })
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error' | 'duplicate'>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    getEvents()
      .then((events: { id: string }[]) => {
        if (events.length > 0) setEventId(events[0].id)
        else setEventError(true)
      })
      .catch(() => setEventError(true))
  }, [])

  const set = (field: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(prev => ({ ...prev, [field]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.consent || !eventId) return
    setStatus('loading')
    try {
      await createLead({
        event_id: eventId,
        name: form.name,
        email: form.email,
        company: form.company,
        role: form.role,
        phone: form.phone || undefined,
        has_companion: form.has_companion,
        companion_name: form.companion_name || undefined,
        consent: form.consent,
        whatsapp_consent: form.whatsapp_consent,
      })
      setStatus('success')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : ''
      if (msg.includes('409') || msg.includes('cadastrado')) {
        setStatus('duplicate')
      } else {
        setErrorMsg('Erro ao realizar inscrição. Tente novamente.')
        setStatus('error')
      }
    }
  }

  if (status === 'success') {
    return (
      <div className="text-center py-8 space-y-2">
        <p className="text-green-700 text-lg font-semibold">Inscrição confirmada ✓</p>
        <p className="text-slate-500 text-sm">Você receberá um e-mail de confirmação em breve.</p>
      </div>
    )
  }

  if (status === 'duplicate') {
    return (
      <div className="text-center py-8 space-y-2">
        <p className="text-sky-700 text-lg font-semibold">Você já está inscrito ✓</p>
        <p className="text-slate-500 text-sm">Este e-mail já está cadastrado para o evento.</p>
      </div>
    )
  }

  const inputClass = 'w-full bg-slate-50 border border-slate-200 rounded px-4 py-3 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-700 transition-colors text-sm'

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <input required value={form.name} onChange={set('name')}
        placeholder="Nome completo *" className={inputClass} />

      <input required type="email" value={form.email} onChange={set('email')}
        placeholder="E-mail corporativo *" className={inputClass} />

      <input required value={form.company} onChange={set('company')}
        placeholder="Empresa *" className={inputClass} />

      <input required value={form.role} onChange={set('role')}
        placeholder="Cargo *" className={inputClass} />

      <input value={form.phone} onChange={set('phone')}
        placeholder="Telefone (opcional)" className={inputClass} />

      <label className="flex items-center gap-3 cursor-pointer">
        <input type="checkbox" checked={form.has_companion} onChange={set('has_companion')}
          className="w-4 h-4 accent-sky-700 flex-shrink-0" />
        <span className="text-slate-600 text-sm">Vou com acompanhante</span>
      </label>

      {form.has_companion && (
        <input value={form.companion_name} onChange={set('companion_name')}
          placeholder="Nome do acompanhante" className={inputClass} />
      )}

      <label className="flex items-start gap-3 cursor-pointer">
        <input required type="checkbox" checked={form.consent} onChange={set('consent')}
          className="w-4 h-4 mt-0.5 accent-sky-700 flex-shrink-0" />
        <span className="text-slate-400 text-xs leading-relaxed">
          Concordo com o tratamento dos meus dados pessoais pela Vigil.AI para fins de inscrição no
          Vigil Summit, conforme a LGPD. *
        </span>
      </label>

      <label className="flex items-start gap-3 cursor-pointer">
        <input type="checkbox" checked={form.whatsapp_consent} onChange={set('whatsapp_consent')}
          className="w-4 h-4 mt-0.5 accent-sky-700 flex-shrink-0" />
        <span className="text-slate-400 text-xs leading-relaxed">
          Aceito receber comunicações sobre o evento via WhatsApp.
        </span>
      </label>

      {status === 'error' && <p className="text-red-600 text-sm">{errorMsg}</p>}

      {eventError && (
        <p className="text-amber-600 text-sm">
          Não foi possível carregar o evento. Verifique sua conexão e recarregue a página.
        </p>
      )}

      <button
        type="submit"
        disabled={status === 'loading' || !form.consent || !eventId}
        className="w-full bg-slate-900 hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3 rounded transition-colors text-sm"
      >
        {status === 'loading' ? 'Inscrevendo…' : 'Confirmar inscrição →'}
      </button>
    </form>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/landing/RegistrationForm.tsx
git commit -m "feat(frontend): RegistrationForm — navy slate restyle"
```

---

## Task 7: ChatbotWidget restyle

**Files:**
- Modify: `frontend/components/landing/ChatbotWidget.tsx`

Apenas classes CSS e ícone mudam — toda a lógica de streaming SSE é preservada.

- [ ] **Step 1: Reescrever `components/landing/ChatbotWidget.tsx`**

```typescript
'use client'
import { useState, useRef, useEffect } from 'react'

interface Message { role: 'user' | 'assistant'; content: string }

const WELCOME_MESSAGE: Message = {
  role: 'assistant',
  content: 'Olá! Posso ajudar com dúvidas sobre o Vigil Summit ou sua inscrição. O que você precisa saber?',
}

function ChatIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
    </svg>
  )
}

export default function ChatbotWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => () => { abortRef.current?.abort() }, [])

  const sendMessage = async () => {
    if (!input.trim() || loading) return
    const userMsg: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    const allMessages = [...messages, userMsg]
      .filter(m => m !== WELCOME_MESSAGE)
      .map(m => ({ role: m.role, content: m.content }))

    setMessages(prev => [...prev, { role: 'assistant', content: '' }])
    abortRef.current = new AbortController()

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: allMessages }),
        signal: abortRef.current.signal,
      })

      if (!res.ok || !res.body) {
        setMessages(prev => [
          ...prev.slice(0, -1),
          { role: 'assistant', content: 'Erro ao conectar. Tente novamente.' },
        ])
        setLoading(false)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value)
        const lines = text.split('\n').filter(l => l.startsWith('data: '))
        for (const line of lines) {
          const data = line.replace('data: ', '')
          if (data === '[DONE]') break
          try {
            const parsed = JSON.parse(data)
            if (parsed.error) {
              setMessages(prev => [
                ...prev.slice(0, -1),
                { role: 'assistant', content: 'Desculpe, ocorreu um erro. Tente novamente.' },
              ])
              break
            }
            if (parsed.text) {
              setMessages(prev => {
                const updated = [...prev]
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: updated[updated.length - 1].content + parsed.text,
                }
                return updated
              })
            }
          } catch {}
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        setMessages(prev => [
          ...prev.slice(0, -1),
          { role: 'assistant', content: 'Erro de conexão. Verifique sua internet e tente novamente.' },
        ])
      }
    }

    setLoading(false)
  }

  return (
    <>
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-slate-900 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-sky-700 transition-colors z-50"
        aria-label={open ? 'Fechar chat' : 'Abrir chat'}
      >
        {open
          ? <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          : <ChatIcon />
        }
      </button>

      {open && (
        <div
          className="fixed bottom-24 right-6 w-80 bg-white rounded-2xl shadow-2xl border border-slate-200 z-50 flex flex-col"
          style={{ height: '420px' }}
        >
          <div className="px-4 py-3 border-b border-slate-200 bg-slate-900 rounded-t-2xl">
            <p className="text-white font-semibold text-sm">Assistente Vigil Summit</p>
            <p className="text-slate-400 text-xs">Resposta imediata</p>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-xs px-3 py-2 rounded-xl text-sm ${
                  msg.role === 'user'
                    ? 'bg-sky-700 text-white'
                    : 'bg-slate-100 text-slate-700'
                }`}>
                  {msg.content || <span className="animate-pulse text-slate-400">…</span>}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
          <div className="p-3 border-t border-slate-200 flex gap-2">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage()}
              placeholder="Digite sua dúvida…"
              className="flex-1 bg-slate-50 text-slate-900 text-sm p-2 rounded border border-slate-200 placeholder-slate-400 focus:outline-none focus:border-sky-700"
            />
            <button
              onClick={sendMessage}
              disabled={loading}
              className="bg-slate-900 text-white px-3 py-2 rounded text-sm hover:bg-sky-700 disabled:opacity-50 transition-colors"
            >
              →
            </button>
          </div>
        </div>
      )}
    </>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/landing/ChatbotWidget.tsx
git commit -m "feat(frontend): ChatbotWidget — navy restyle + SVG icon"
```

---

## Task 8: Landing page

**Files:**
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Reescrever `app/page.tsx`**

```typescript
export const dynamic = 'force-dynamic'

import Navbar from '@/components/ui/Navbar'
import RegistrationForm from '@/components/landing/RegistrationForm'
import ChatbotWidget from '@/components/landing/ChatbotWidget'

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-100">
      <Navbar variant="landing" />

      {/* HERO */}
      <section className="bg-white border-b border-slate-200">
        <div className="max-w-screen-xl mx-auto px-8 py-20 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <div className="flex items-center gap-2 mb-6">
              <div className="w-2 h-2 bg-sky-700 rounded-full" />
              <span className="text-sky-700 text-xs font-bold tracking-[0.15em] uppercase">
                São Paulo · 15 Ago 2026 · Presencial
              </span>
            </div>
            <h1 className="font-playfair font-black text-5xl text-slate-900 leading-[1.1] tracking-tight mb-5">
              Vigil Summit<br />
              <span className="text-sky-700">Segurança para<br />a Era da IA</span>
            </h1>
            <p className="text-slate-500 text-lg leading-relaxed mb-8 max-w-xl">
              O encontro definitivo de CISOs, CTOs e líderes de segurança corporativa para discutir
              IA, Zero Trust e conformidade em 2026.
            </p>
            <div className="flex gap-3 mb-10">
              <a
                href="#inscricao"
                className="bg-slate-900 text-white font-bold text-sm px-7 py-3.5 rounded hover:bg-sky-700 transition-colors"
              >
                Garantir minha vaga →
              </a>
              <a
                href="#agenda"
                className="border-2 border-slate-200 text-slate-500 font-semibold text-sm px-5 py-3.5 rounded hover:border-slate-400 transition-colors"
              >
                Ver programação
              </a>
            </div>
            <div className="flex gap-8 border-t border-slate-100 pt-8">
              {[
                { num: '120', label: 'vagas exclusivas' },
                { num: '8h', label: 'de conteúdo' },
                { num: 'C-level', label: 'público-alvo' },
              ].map(({ num, label }) => (
                <div key={label}>
                  <div className="font-playfair font-black text-3xl text-slate-900 leading-none">{num}</div>
                  <div className="text-slate-400 text-xs font-medium mt-1">{label}</div>
                </div>
              ))}
            </div>
          </div>

          <div id="inscricao" className="bg-white rounded-xl border border-slate-200 p-8 shadow-md">
            <h2 className="text-slate-900 text-lg font-extrabold mb-1">Garanta sua vaga</h2>
            <p className="text-slate-500 text-sm mb-5">Inscrições limitadas a 120 participantes.</p>
            <RegistrationForm />
          </div>
        </div>
      </section>

      {/* TRILHAS */}
      <section className="bg-slate-50 border-y border-slate-200 py-14" id="agenda">
        <div className="max-w-screen-xl mx-auto px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                track: 'Track 01',
                title: 'Zero Trust',
                desc: 'Arquitetura moderna para ambientes híbridos e multicloud em empresas brasileiras.',
              },
              {
                track: 'Track 02',
                title: 'IA em Segurança',
                desc: 'Detecção e resposta com modelos de linguagem. O que realmente funciona em 2026.',
              },
              {
                track: 'Track 03',
                title: 'Conformidade',
                desc: 'LGPD, ISO 27001, SOC 2 na prática. Gestão de riscos para médias e grandes empresas.',
              },
            ].map(({ track, title, desc }) => (
              <div
                key={track}
                className="bg-white rounded-lg border border-slate-200 [border-top-width:3px] border-t-sky-700 p-6"
              >
                <p className="text-sky-700 text-xs font-bold tracking-[0.1em] uppercase mb-2">{track}</p>
                <p className="text-slate-900 font-extrabold text-base mb-2">{title}</p>
                <p className="text-slate-500 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* PÚBLICO-ALVO */}
      <section className="bg-white py-16">
        <div className="max-w-screen-xl mx-auto px-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-5 h-0.5 bg-sky-700" />
            <span className="text-sky-700 text-xs font-bold tracking-[0.15em] uppercase">Para quem é</span>
          </div>
          <h2 className="font-playfair font-black text-3xl text-slate-900 mb-3 tracking-tight">
            Feito para quem decide em segurança
          </h2>
          <p className="text-slate-500 text-base leading-relaxed mb-8 max-w-xl">
            Evento exclusivo para executivos e gestores de empresas com mais de 200 funcionários.
          </p>
          <div className="flex flex-wrap gap-3">
            {[
              { label: 'CISOs', highlight: true },
              { label: 'CTOs', highlight: true },
              { label: 'Diretores de TI', highlight: false },
              { label: 'Gestores de Risco', highlight: false },
              { label: 'VPs de Segurança', highlight: false },
              { label: 'Heads de Compliance', highlight: false },
            ].map(({ label, highlight }) => (
              <span
                key={label}
                className={`px-4 py-2 rounded-full text-sm font-semibold border-2 ${
                  highlight
                    ? 'border-sky-700 text-sky-700 bg-sky-50'
                    : 'border-slate-200 text-slate-600 bg-white'
                }`}
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-slate-900 py-5 px-8">
        <div className="max-w-screen-xl mx-auto flex items-center justify-between">
          <p className="text-slate-400 text-xs">
            <span className="text-white font-semibold">Vigil Summit 2026</span> · São Paulo · Evento corporativo exclusivo
          </p>
          <a href="#" className="text-sky-300 hover:text-sky-200 text-xs transition-colors">
            Política de privacidade
          </a>
        </div>
      </footer>

      <ChatbotWidget />
    </main>
  )
}
```

- [ ] **Step 2: Rodar o servidor de desenvolvimento e verificar visualmente**

```bash
cd frontend && npm run dev
```

Verificar em `http://localhost:3000`:
- Navbar branca sticky com logo, links e CTA
- Hero: h1 em Playfair Display, formulário à direita em card com sombra
- 3 cards de trilha com borda superior sky-700 3px
- Chips de público com highlight nos C-level
- Footer slate-900

- [ ] **Step 3: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat(frontend): landing page redesign — Navy Slate + Playfair Display"
```

---

## Task 9: Rich LeadCard

**Files:**
- Rewrite: `frontend/components/dashboard/LeadCard.tsx`

- [ ] **Step 1: Reescrever `components/dashboard/LeadCard.tsx`**

```typescript
import type { RichLead } from '@/lib/types'

type TagColor = 'navy' | 'green' | 'amber' | 'red' | 'slate'
type Tag = { label: string; color: TagColor }
type SignalColor = 'green' | 'amber' | 'gray' | 'red'

const TAG_CLASSES: Record<TagColor, string> = {
  navy:  'bg-blue-50 text-blue-700',
  green: 'bg-green-50 text-green-700',
  amber: 'bg-amber-50 text-amber-700',
  red:   'bg-red-50 text-red-600',
  slate: 'bg-slate-100 text-slate-500',
}

const SIGNAL_DOT: Record<SignalColor, string> = {
  green: 'bg-green-500',
  amber: 'bg-amber-500',
  gray:  'bg-slate-300',
  red:   'bg-red-500',
}

function getTags(lead: RichLead): Tag[] {
  const tags: Tag[] = []
  const role = (lead.role ?? '').toLowerCase()
  if (/ciso|cto|ceo|coo|cfo|\bvp\b|diretor|director|chief/.test(role)) {
    tags.push({ label: 'C-level', color: 'navy' })
  }
  if (lead.enrichment?.is_decision_maker) {
    tags.push({ label: 'decisor', color: 'amber' })
  }
  const stageTag: Partial<Record<string, Tag>> = {
    CONFIRMED:         { label: 'confirmado',   color: 'green' },
    NO_SHOW:           { label: 'no-show',       color: 'red' },
    MEETING_SCHEDULED: { label: 'demo agendada', color: 'amber' },
    CONVERTED:         { label: 'convertido',    color: 'green' },
  }
  if (stageTag[lead.stage]) tags.push(stageTag[lead.stage]!)
  if (lead.enrichment?.sector) tags.push({ label: lead.enrichment.sector, color: 'slate' })
  return tags.slice(0, 3)
}

function getSignal(lead: RichLead): { color: SignalColor; text: string } {
  if (!lead.enrichment) return { color: 'amber', text: 'Aguardando enriquecimento' }
  if (!lead.lastMessage) return { color: 'gray', text: 'Nenhuma mensagem enviada' }
  const date = new Date(lead.lastMessage.sent_at).toLocaleDateString('pt-BR', {
    day: '2-digit', month: 'short',
  })
  if (lead.lastMessage.clicked_at) return { color: 'green', text: `Link clicado · ${date}` }
  if (lead.lastMessage.opened_at) return { color: 'green', text: `Email aberto · ${date}` }
  return { color: 'amber', text: `Email enviado · ${date}` }
}

export default function LeadCard({ lead }: { lead: RichLead }) {
  const tags = getTags(lead)
  const signal = getSignal(lead)
  const parts = (lead.name ?? '').split(' ')
  const shortName = parts.length > 1 ? `${parts[0]} ${parts[parts.length - 1]}` : (lead.name ?? '—')

  const roleLabel = [lead.role, lead.company, lead.enrichment?.company_size]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-md p-2.5 mb-1.5 cursor-pointer hover:border-sky-700 hover:bg-white hover:shadow-sm transition-all last:mb-0">
      <p className="text-slate-900 text-xs font-bold mb-0.5 truncate">{shortName}</p>
      {roleLabel && (
        <p className="text-slate-500 text-[10px] mb-1.5 truncate">{roleLabel}</p>
      )}
      {tags.length > 0 && (
        <div className="flex gap-1 flex-wrap mb-1.5">
          {tags.map(tag => (
            <span
              key={tag.label}
              className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${TAG_CLASSES[tag.color]}`}
            >
              {tag.label}
            </span>
          ))}
        </div>
      )}
      <div className="flex items-center gap-1.5 pt-1.5 border-t border-slate-100">
        <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${SIGNAL_DOT[signal.color]}`} />
        <span className="text-[9px] text-slate-400 truncate">{signal.text}</span>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/dashboard/LeadCard.tsx
git commit -m "feat(frontend): LeadCard rich — tags, signal, enrichment data"
```

---

## Task 10: FunnelBoard com KPI strip

**Files:**
- Rewrite: `frontend/components/dashboard/FunnelBoard.tsx`

- [ ] **Step 1: Reescrever `components/dashboard/FunnelBoard.tsx`**

```typescript
'use client'
import { useState, useEffect } from 'react'
import { REALTIME_SUBSCRIBE_STATES } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'
import LeadCard from './LeadCard'
import type { RichLead, LeadEnrichment, LastMessage } from '@/lib/types'

const STAGES = [
  { key: 'REGISTERED',        label: 'Inscritos',        color: 'border-sky-700',    titleColor: 'text-slate-500' },
  { key: 'ENRICHED',          label: 'Enriquecidos',     color: 'border-sky-700',    titleColor: 'text-slate-500' },
  { key: 'CONFIRMED',         label: 'Confirmados',      color: 'border-green-500',  titleColor: 'text-green-600' },
  { key: 'ATTENDED',          label: 'Presentes',        color: 'border-sky-700',    titleColor: 'text-slate-500' },
  { key: 'NO_SHOW',           label: 'No-show',          color: 'border-red-500',    titleColor: 'text-red-600'   },
  { key: 'MEETING_SCHEDULED', label: 'Reunião agendada', color: 'border-amber-500',  titleColor: 'text-amber-600' },
  { key: 'CONVERTED',         label: 'Convertidos',      color: 'border-emerald-500',titleColor: 'text-emerald-600' },
] as const

type BaseLead = { id: string; name: string | null; role: string | null; company: string | null; stage: string }

function buildRichLeads(
  leads: BaseLead[],
  enrichmentMap: Map<string, LeadEnrichment>,
  messageMap: Map<string, LastMessage>,
): RichLead[] {
  return leads.map(l => ({
    ...l,
    enrichment: enrichmentMap.get(l.id) ?? null,
    lastMessage: messageMap.get(l.id) ?? null,
  }))
}

function computeKpis(leads: BaseLead[]) {
  const total = leads.length
  const confirmedStages = new Set(['CONFIRMED', 'ATTENDED', 'MEETING_SCHEDULED', 'CONVERTED'])
  const confirmed = leads.filter(l => confirmedStages.has(l.stage)).length
  const confirmRate = total > 0 ? Math.round((confirmed / total) * 100) : 0
  const meetings = leads.filter(l => l.stage === 'MEETING_SCHEDULED' || l.stage === 'CONVERTED').length
  const noShow = leads.filter(l => l.stage === 'NO_SHOW').length
  return { total, confirmRate, meetings, noShow }
}

export default function FunnelBoard() {
  const [leads, setLeads] = useState<BaseLead[]>([])
  const [enrichmentMap, setEnrichmentMap] = useState<Map<string, LeadEnrichment>>(new Map())
  const [messageMap, setMessageMap] = useState<Map<string, LastMessage>>(new Map())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Initial load: leads from authenticated proxy
    fetch('/api/leads', { cache: 'no-store' })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(async (response: { data: BaseLead[] } | BaseLead[]) => {
        const fetchedLeads = Array.isArray(response) ? response : (response as { data: BaseLead[] }).data ?? []
        setLeads(fetchedLeads)

        const ids = fetchedLeads.map(l => l.id)
        if (ids.length === 0) { setLoading(false); return }

        // Enrichment + last message: best-effort (graceful degradation if RLS blocks)
        const [{ data: enrichRows }, { data: msgRows }] = await Promise.all([
          supabase
            .from('lead_enrichment')
            .select('lead_id, sector, company_size, is_decision_maker')
            .in('lead_id', ids),
          supabase
            .from('messages')
            .select('lead_id, sent_at, opened_at, clicked_at')
            .in('lead_id', ids)
            .eq('direction', 'OUT')
            .order('sent_at', { ascending: false }),
        ])

        const newEnrichMap = new Map<string, LeadEnrichment>()
        for (const row of (enrichRows ?? [])) {
          newEnrichMap.set(row.lead_id, row as LeadEnrichment)
        }
        setEnrichmentMap(newEnrichMap)

        // One entry per lead: keep only the most recent message (rows already ordered desc)
        const newMsgMap = new Map<string, LastMessage>()
        for (const row of (msgRows ?? [])) {
          if (!newMsgMap.has(row.lead_id)) newMsgMap.set(row.lead_id, row as LastMessage)
        }
        setMessageMap(newMsgMap)
        setLoading(false)
      })
      .catch(() => {
        setError('Falha ao carregar leads. Verifique o backend.')
        setLoading(false)
      })

    // Realtime: update stage changes
    const channel = supabase
      .channel('leads-board')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'leads' }, payload => {
        if (payload.eventType === 'INSERT') {
          setLeads(prev => [...prev, payload.new as BaseLead])
        } else if (payload.eventType === 'UPDATE') {
          setLeads(prev =>
            prev.map(l => l.id === (payload.new as BaseLead).id ? (payload.new as BaseLead) : l)
          )
        } else if (payload.eventType === 'DELETE') {
          setLeads(prev => prev.filter(l => l.id !== (payload.old as { id: string }).id))
        }
      })
      .subscribe(status => {
        if (
          status === REALTIME_SUBSCRIBE_STATES.CHANNEL_ERROR ||
          status === REALTIME_SUBSCRIBE_STATES.TIMED_OUT
        ) {
          setError('Conexão em tempo real perdida. Atualize a página para reconectar.')
        }
      })

    return () => { supabase.removeChannel(channel) }
  }, [])

  if (loading) {
    return (
      <div className="p-8">
        <p className="text-slate-400 text-sm">Carregando leads…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      </div>
    )
  }

  const { total, confirmRate, meetings, noShow } = computeKpis(leads)
  const richLeads = buildRichLeads(leads, enrichmentMap, messageMap)
  const metaDiff = confirmRate - 70
  const metaText = metaDiff >= 0
    ? `${metaDiff}% acima da meta`
    : `${Math.abs(metaDiff)}% abaixo da meta`
  const metaColor = metaDiff >= 0 ? 'text-green-600' : 'text-red-600'

  return (
    <div>
      {/* KPI STRIP */}
      <div className="bg-white border-b border-slate-200 px-8 py-5 grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: 'Total inscritos',
            value: String(total),
            sub: `de 120 vagas`,
            meta: null,
            accent: 'border-sky-700',
            valueColor: 'text-slate-900',
          },
          {
            label: 'Taxa de confirmação',
            value: `${confirmRate}%`,
            sub: 'meta: acima de 70%',
            meta: metaText,
            metaColor,
            accent: 'border-green-500',
            valueColor: confirmRate >= 70 ? 'text-green-600' : 'text-red-600',
          },
          {
            label: 'Reuniões agendadas',
            value: String(meetings),
            sub: 'via Cal.com',
            meta: null,
            accent: 'border-amber-500',
            valueColor: 'text-amber-600',
          },
          {
            label: 'No-show',
            value: String(noShow),
            sub: 'reengajamento ativo',
            meta: null,
            accent: 'border-red-500',
            valueColor: 'text-red-600',
          },
        ].map(kpi => (
          <div
            key={kpi.label}
            className={`bg-white border border-slate-200 [border-top-width:3px] ${kpi.accent} rounded-lg p-4`}
          >
            <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-[0.08em] mb-2">{kpi.label}</p>
            <p className={`font-playfair font-black text-4xl leading-none ${kpi.valueColor}`}>{kpi.value}</p>
            <p className="text-slate-400 text-[11px] mt-1.5">{kpi.sub}</p>
            {kpi.meta && (
              <p className={`text-[10px] font-semibold mt-0.5 ${kpi.metaColor}`}>{kpi.meta}</p>
            )}
          </div>
        ))}
      </div>

      {/* KANBAN */}
      <div className="p-8">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="font-playfair font-extrabold text-xl text-slate-900">Funil de Leads</h2>
            <p className="text-slate-400 text-xs mt-0.5">
              Atualização em tempo real — {total} leads carregados
            </p>
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-slate-500 text-xs font-semibold">
            📅 Vigil Summit · 15 Ago 2026
          </div>
        </div>

        <div className="flex gap-3 overflow-x-auto pb-4">
          {STAGES.map(({ key, label, color, titleColor }) => {
            const stageLeads = richLeads.filter(l => l.stage === key)
            return (
              <div key={key} className="flex-shrink-0 w-[220px] flex flex-col">
                <div
                  className={`bg-white border border-b-0 border-slate-200 [border-top-width:3px] ${color} rounded-t-lg px-3 py-2 flex items-center justify-between`}
                >
                  <span className={`text-[10px] font-bold uppercase tracking-[0.08em] ${titleColor}`}>{label}</span>
                  <span className="bg-slate-100 text-slate-500 text-[10px] font-bold px-2 py-0.5 rounded-full min-w-[22px] text-center">
                    {stageLeads.length || '—'}
                  </span>
                </div>
                <div className="bg-white border border-slate-200 rounded-b-lg p-2 flex-1 min-h-[100px]">
                  {stageLeads.length === 0 ? (
                    <p className="text-slate-200 text-xs text-center pt-6">
                      {key === 'ATTENDED' ? 'Dia do evento · 15 Ago' : '—'}
                    </p>
                  ) : (
                    stageLeads.map(lead => <LeadCard key={lead.id} lead={lead} />)
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verificar TypeScript**

```bash
cd frontend && npm run build
```

Esperado: sem erros. Se houver erro de tipo em `STAGES` (const assertion e `titleColor`), verificar se os campos `color` e `titleColor` estão sendo usados como `string` sem problema.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/dashboard/FunnelBoard.tsx
git commit -m "feat(frontend): FunnelBoard — KPI strip + rich cards + enrichment queries"
```

---

## Task 11: Dashboard page

**Files:**
- Modify: `frontend/app/dashboard/page.tsx`

- [ ] **Step 1: Atualizar `app/dashboard/page.tsx`**

```typescript
export const dynamic = 'force-dynamic'

import Navbar from '@/components/ui/Navbar'
import FunnelBoard from '@/components/dashboard/FunnelBoard'

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-100">
      <Navbar variant="dashboard" />
      <FunnelBoard />
    </div>
  )
}
```

- [ ] **Step 2: Rodar dev server e verificar dashboard**

```bash
cd frontend && npm run dev
```

Verificar em `http://localhost:3000/dashboard` (após login):
- Navbar com logo + título Playfair + badge "● Ao vivo"
- 4 KPI cards com borda top colorida e número em Playfair Display
- Kanban com 7 colunas, cards ricos com tags e sinal do agente
- Badge "Ao vivo" sem mencionar "Supabase" ou outras tecnologias internas

- [ ] **Step 3: Build final**

```bash
cd frontend && npm run build
```

Esperado: build completo sem erros de TypeScript nem warnings de lint.

- [ ] **Step 4: Commit final**

```bash
git add frontend/app/dashboard/page.tsx
git commit -m "feat(frontend): dashboard page — Navbar + FunnelBoard integrados"
```

---

## Notas de degradação

- **Queries de enriquecimento no Supabase:** se o RLS bloquear a query anon em `lead_enrichment` ou `messages`, `enrichmentMap` e `messageMap` ficam vazios e os cards mostram "Aguardando enriquecimento" — comportamento correto. Não quebra o dashboard.
- **Dados da coluna "Presentes":** ficará sempre vazia até o dia do evento (15 Ago 2026). O placeholder "Dia do evento · 15 Ago" é intencional.
- **`[border-top-width:3px]`:** classe Tailwind com valor arbitrário (Tailwind v3+). Se o projeto usar Tailwind v2, substituir por `border-t-4` (4px).

---

*Plano gerado em 2026-05-30*
