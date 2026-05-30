# Vigil Summit Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completar os arquivos faltantes do projeto Vigil Summit Agent — config de deploy do backend no Railway e todas as páginas/componentes do frontend Next.js — deixando o sistema pronto para deploy e demonstração ponta a ponta.

**Architecture:** Backend FastAPI já implementado e testado em `backend/`; frontend Next.js 14 em `frontend/` precisa de scaffolding, landing page com formulário + chatbot, dashboard protegido por senha com funil em tempo real via Supabase Realtime. Deploy: backend no Railway via Nixpacks, frontend no Vercel.

**Tech Stack:** Python 3.11 / FastAPI / Railway (backend) · Next.js 14 / TypeScript / Tailwind CSS / Supabase Realtime / Vercel (frontend)

---

## Mapa de Arquivos

### Backend (criar/modificar)

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `backend/requirements.txt` | Modificar | Adicionar `slowapi==0.1.9` (usado em main.py mas ausente) |
| `backend/app/__init__.py` | Criar | Marca `app` como package Python |
| `backend/app/agent/__init__.py` | Criar | Marks `agent` sub-package |
| `backend/app/api/__init__.py` | Criar | Marks `api` sub-package |
| `backend/app/db/__init__.py` | Criar | Marks `db` sub-package |
| `backend/app/scheduler/__init__.py` | Criar | Marks `scheduler` sub-package |
| `backend/app/services/__init__.py` | Criar | Marks `services` sub-package |
| `backend/.env.example` | Criar | Template de variáveis de ambiente |
| `backend/Procfile` | Criar | Comando de start para Railway |
| `backend/railway.json` | Criar | Configuração de build/deploy Railway |
| `backend/scripts/seed_personas.py` | Criar | Script para criar leads de teste |

### Frontend (criar)

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `frontend/package.json` | Criar | Dependências Node.js |
| `frontend/tsconfig.json` | Criar | Configuração TypeScript |
| `frontend/next.config.ts` | Criar | Configuração Next.js |
| `frontend/tailwind.config.ts` | Criar | Configuração Tailwind CSS |
| `frontend/postcss.config.js` | Criar | PostCSS (requerido pelo Tailwind) |
| `frontend/app/globals.css` | Criar | Tailwind directives |
| `frontend/app/layout.tsx` | Criar | Root layout com metadata |
| `frontend/app/page.tsx` | Criar | Landing page (hero + form + chatbot) |
| `frontend/app/login/page.tsx` | Criar | Tela de login do dashboard |
| `frontend/app/api/auth/route.ts` | Criar | Endpoint que seta cookie de autenticação |
| `frontend/app/dashboard/page.tsx` | Criar | Dashboard com funil de leads |
| `frontend/middleware.ts` | Criar | Proteção por senha de `/dashboard/*` |
| `frontend/components/landing/RegistrationForm.tsx` | Criar | Formulário de inscrição com LGPD |
| `frontend/components/dashboard/FunnelBoard.tsx` | Criar | Board Kanban com Supabase Realtime |
| `frontend/lib/supabase.ts` | Criar | Supabase client para frontend |

---

## Task 1: Corrigir requirements.txt — adicionar slowapi

**Files:**
- Modify: `backend/requirements.txt`

`slowapi` é usado em `app/main.py` e `app/api/leads.py` mas está ausente do `requirements.txt`. O deploy no Railway falharia no `import slowapi`.

- [ ] **Step 1: Adicionar slowapi**

Editar `backend/requirements.txt`, adicionar após `httpx==0.27.2`:

```
slowapi==0.1.9
```

Conteúdo final do arquivo:
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.2
pydantic-settings==2.5.2
anthropic==0.40.0
supabase==2.9.1
resend==2.5.0
apscheduler==3.10.4
httpx==0.27.2
slowapi==0.1.9
svix==1.24.0
python-dotenv==1.0.1
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Verificar instalação local**

```bash
cd backend
pip install slowapi==0.1.9
```

Expected: `Successfully installed slowapi-0.1.9`

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "fix: add missing slowapi dependency"
```

---

## Task 2: `__init__.py` em todos os sub-pacotes

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/agent/__init__.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/scheduler/__init__.py`
- Create: `backend/app/services/__init__.py`

Sem esses arquivos, alguns ambientes de deploy (especialmente com Python < 3.12) podem não reconhecer os diretórios como packages e falhar nos imports.

- [ ] **Step 1: Criar os arquivos vazios**

Cada arquivo deve conter apenas uma linha vazia. Criar todos:

`backend/app/__init__.py` — arquivo vazio  
`backend/app/agent/__init__.py` — arquivo vazio  
`backend/app/api/__init__.py` — arquivo vazio  
`backend/app/db/__init__.py` — arquivo vazio  
`backend/app/scheduler/__init__.py` — arquivo vazio  
`backend/app/services/__init__.py` — arquivo vazio  

- [ ] **Step 2: Verificar imports**

```bash
cd backend
python -c "from app.main import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Rodar testes para garantir que nada quebrou**

```bash
cd backend
pytest tests/ -v --tb=short
```

Expected: todos os testes PASS (14 testes).

- [ ] **Step 4: Commit**

```bash
git add backend/app/__init__.py backend/app/agent/__init__.py backend/app/api/__init__.py backend/app/db/__init__.py backend/app/scheduler/__init__.py backend/app/services/__init__.py
git commit -m "chore: add __init__.py to all backend packages"
```

---

## Task 3: Backend deployment config

**Files:**
- Create: `backend/.env.example`
- Create: `backend/Procfile`
- Create: `backend/railway.json`

- [ ] **Step 1: Criar `backend/.env.example`**

```
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJ...  # service_role key (não anon)

# Resend
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=Vigil Summit <noreply@vigil.ai>
RESEND_WEBHOOK_SECRET=whsec_...  # do painel Resend → Webhooks

# Apollo.io (opcional — enriquecimento desativa graciosamente sem ela)
APOLLO_API_KEY=

# Evolution API (WhatsApp — opcional)
EVOLUTION_API_URL=
EVOLUTION_API_KEY=
EVOLUTION_INSTANCE_NAME=vigil

# Cal.com (agendamento — opcional)
CAL_API_KEY=
CAL_EVENT_TYPE_ID=

# Segurança
API_KEY=vigil-secret-key-2026  # header X-API-Key para endpoints operacionais
```

- [ ] **Step 2: Criar `backend/Procfile`**

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

- [ ] **Step 3: Criar `backend/railway.json`**

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add backend/.env.example backend/Procfile backend/railway.json
git commit -m "chore: add Railway deploy configuration and env template"
```

---

## Task 4: Frontend — scaffolding do projeto Next.js

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/app/globals.css`

- [ ] **Step 1: Criar `frontend/package.json`**

```json
{
  "name": "vigil-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.2.5",
    "react": "^18",
    "react-dom": "^18",
    "@anthropic-ai/sdk": "^0.27.0",
    "@supabase/supabase-js": "^2.45.0"
  },
  "devDependencies": {
    "typescript": "^5",
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "tailwindcss": "^3.4.1",
    "postcss": "^8",
    "autoprefixer": "^10.0.1"
  }
}
```

- [ ] **Step 2: Criar `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Criar `frontend/next.config.ts`**

```typescript
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {}

export default nextConfig
```

- [ ] **Step 4: Criar `frontend/tailwind.config.ts`**

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: { extend: {} },
  plugins: [],
}
export default config
```

- [ ] **Step 5: Criar `frontend/postcss.config.js`**

```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 6: Criar `frontend/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 7: Instalar dependências**

```bash
cd frontend
npm install
```

Expected: `node_modules/` criado, sem erros.

- [ ] **Step 8: Verificar que o projeto compila**

```bash
cd frontend
npm run build 2>&1 | head -20
```

Expected: Build completa (pode falhar por falta de páginas — OK neste ponto).

- [ ] **Step 9: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/next.config.ts frontend/tailwind.config.ts frontend/postcss.config.js frontend/app/globals.css frontend/package-lock.json
git commit -m "feat: next.js frontend project scaffolding with tailwind"
```

---

## Task 5: Root layout

**Files:**
- Create: `frontend/app/layout.tsx`

- [ ] **Step 1: Criar `frontend/app/layout.tsx`**

```typescript
import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Vigil Summit — Segurança para a Era da IA',
  description: 'Evento exclusivo de cibersegurança para CISOs, CTOs e líderes de TI.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="bg-gray-950 text-white antialiased">{children}</body>
    </html>
  )
}
```

- [ ] **Step 2: Verificar TypeScript**

```bash
cd frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: sem erros de tipo.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/layout.tsx
git commit -m "feat: root layout with tailwind and metadata"
```

---

## Task 6: Landing page — RegistrationForm + página principal

**Files:**
- Create: `frontend/components/landing/RegistrationForm.tsx`
- Create: `frontend/app/page.tsx`

- [ ] **Step 1: Criar `frontend/components/landing/RegistrationForm.tsx`**

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
  const [form, setForm] = useState<FormState>({
    name: '', email: '', company: '', role: '', phone: '',
    has_companion: false, companion_name: '',
    consent: false, whatsapp_consent: false,
  })
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error' | 'duplicate'>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    getEvents()
      .then((events: { id: string }[]) => { if (events.length > 0) setEventId(events[0].id) })
      .catch(() => {})
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
        <p className="text-green-400 text-lg font-semibold">Inscrição confirmada ✓</p>
        <p className="text-gray-400 text-sm">Você receberá um e-mail de confirmação em breve.</p>
      </div>
    )
  }

  if (status === 'duplicate') {
    return (
      <div className="text-center py-8 space-y-2">
        <p className="text-yellow-400 text-lg font-semibold">Você já está inscrito ✓</p>
        <p className="text-gray-400 text-sm">Este e-mail já está cadastrado para o evento.</p>
      </div>
    )
  }

  const inputClass = 'w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors'

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
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
          className="w-4 h-4 accent-purple-600 flex-shrink-0" />
        <span className="text-gray-300 text-sm">Vou com acompanhante</span>
      </label>

      {form.has_companion && (
        <input value={form.companion_name} onChange={set('companion_name')}
          placeholder="Nome do acompanhante" className={inputClass} />
      )}

      <label className="flex items-start gap-3 cursor-pointer">
        <input required type="checkbox" checked={form.consent} onChange={set('consent')}
          className="w-4 h-4 mt-0.5 accent-purple-600 flex-shrink-0" />
        <span className="text-gray-500 text-xs leading-relaxed">
          Concordo com o tratamento dos meus dados pessoais pela Vigil.AI para fins de inscrição no Vigil Summit, conforme a LGPD. *
        </span>
      </label>

      <label className="flex items-start gap-3 cursor-pointer">
        <input type="checkbox" checked={form.whatsapp_consent} onChange={set('whatsapp_consent')}
          className="w-4 h-4 mt-0.5 accent-purple-600 flex-shrink-0" />
        <span className="text-gray-500 text-xs leading-relaxed">
          Aceito receber comunicações sobre o evento via WhatsApp.
        </span>
      </label>

      {status === 'error' && <p className="text-red-400 text-sm">{errorMsg}</p>}

      <button type="submit"
        disabled={status === 'loading' || !form.consent || !eventId}
        className="w-full bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-lg transition-colors">
        {status === 'loading' ? 'Inscrevendo...' : 'Garantir minha vaga →'}
      </button>
    </form>
  )
}
```

- [ ] **Step 2: Criar `frontend/app/page.tsx`**

```typescript
import RegistrationForm from '@/components/landing/RegistrationForm'
import ChatbotWidget from '@/components/landing/ChatbotWidget'

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-950">
      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 pt-20 pb-12 text-center">
        <p className="text-purple-400 text-sm font-semibold tracking-widest uppercase mb-4">
          São Paulo · Presencial · 120 vagas
        </p>
        <h1 className="text-5xl font-bold text-white mb-6 leading-tight">
          Vigil Summit<br />
          <span className="text-purple-400">Segurança para a Era da IA</span>
        </h1>
        <p className="text-gray-400 text-lg max-w-xl mx-auto leading-relaxed">
          O encontro definitivo de CISOs, CTOs e líderes de segurança para discutir IA, conformidade e Zero Trust em 2026.
        </p>
      </section>

      {/* Tópicos */}
      <section className="max-w-3xl mx-auto px-6 pb-12">
        <div className="grid grid-cols-3 gap-4">
          {[
            { icon: '🛡️', title: 'Zero Trust', desc: 'Arquitetura moderna para ambientes híbridos' },
            { icon: '🤖', title: 'IA em Segurança', desc: 'Detecção e resposta com modelos de linguagem' },
            { icon: '📋', title: 'Conformidade', desc: 'LGPD, ISO 27001, SOC 2 na prática' },
          ].map(({ icon, title, desc }) => (
            <div key={title} className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
              <span className="text-2xl">{icon}</span>
              <p className="text-white font-medium mt-2 text-sm">{title}</p>
              <p className="text-gray-500 text-xs mt-1">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Form */}
      <section className="max-w-lg mx-auto px-6 pb-24" id="inscricao">
        <div className="bg-gray-900 rounded-2xl p-8 border border-gray-800">
          <h2 className="text-white text-xl font-semibold mb-6 text-center">Garanta sua vaga</h2>
          <RegistrationForm />
        </div>
      </section>

      <ChatbotWidget />
    </main>
  )
}
```

- [ ] **Step 3: Verificar TypeScript**

```bash
cd frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: sem erros de tipo.

- [ ] **Step 4: Testar no browser**

```bash
cd frontend
npm run dev
```

Abrir `http://localhost:3000`. Verificar:
- Landing page renderiza
- Formulário aparece com todos os campos
- Chatbot aparece no canto inferior direito

- [ ] **Step 5: Commit**

```bash
git add frontend/components/landing/RegistrationForm.tsx frontend/app/page.tsx
git commit -m "feat: landing page with LGPD-compliant registration form"
```

---

## Task 7: Dashboard auth — login page + API route + middleware

**Files:**
- Create: `frontend/app/api/auth/route.ts`
- Create: `frontend/app/login/page.tsx`
- Create: `frontend/middleware.ts`

- [ ] **Step 1: Criar `frontend/app/api/auth/route.ts`**

```typescript
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  const { password } = await request.json()
  const expected = process.env.DASHBOARD_PASSWORD

  if (!expected || password !== expected) {
    return NextResponse.json({ error: 'Senha incorreta' }, { status: 401 })
  }

  const res = NextResponse.json({ ok: true })
  res.cookies.set('dashboard_auth', expected, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24,
    path: '/',
  })
  return res
}
```

- [ ] **Step 2: Criar `frontend/app/login/page.tsx`**

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
      } else {
        router.push('/dashboard')
      }
    } catch {
      setError('Erro de conexão.')
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="bg-gray-900 rounded-2xl p-8 border border-gray-800 w-full max-w-sm">
        <h1 className="text-white text-xl font-semibold mb-2 text-center">Dashboard Vigil</h1>
        <p className="text-gray-500 text-sm text-center mb-6">Acesso restrito à equipe Vigil.AI</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Senha"
            required
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors"
          />
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white font-semibold py-3 rounded-lg transition-colors"
          >
            {loading ? 'Entrando...' : 'Entrar →'}
          </button>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Criar `frontend/middleware.ts`**

```typescript
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const auth = request.cookies.get('dashboard_auth')
  const expected = process.env.DASHBOARD_PASSWORD

  if (!expected || auth?.value !== expected) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*'],
}
```

- [ ] **Step 4: Testar proteção do dashboard**

```bash
cd frontend
npm run dev
```

Abrir `http://localhost:3000/dashboard` — deve redirecionar para `/login`.  
Logar com `DASHBOARD_PASSWORD` do `.env.local` — deve entrar no dashboard (404 por enquanto, a página ainda não existe).

- [ ] **Step 5: Commit**

```bash
git add frontend/app/api/auth/route.ts frontend/app/login/page.tsx frontend/middleware.ts
git commit -m "feat: dashboard password protection with httpOnly cookie"
```

---

## Task 8: Dashboard — Supabase client + FunnelBoard + página

**Files:**
- Create: `frontend/lib/supabase.ts`
- Create: `frontend/components/dashboard/FunnelBoard.tsx`
- Create: `frontend/app/dashboard/page.tsx`

- [ ] **Step 1: Criar `frontend/lib/supabase.ts`**

```typescript
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)
```

- [ ] **Step 2: Criar `frontend/components/dashboard/FunnelBoard.tsx`**

```typescript
'use client'
import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import LeadCard from './LeadCard'

const STAGES = [
  { key: 'REGISTERED',        label: 'Inscritos',     color: 'border-gray-500' },
  { key: 'ENRICHED',          label: 'Enriquecidos',  color: 'border-blue-500' },
  { key: 'CONFIRMED',         label: 'Confirmados',   color: 'border-green-500' },
  { key: 'ATTENDED',          label: 'Presentes',     color: 'border-purple-500' },
  { key: 'NO_SHOW',           label: 'No-show',       color: 'border-red-500' },
  { key: 'MEETING_SCHEDULED', label: 'Reunião',       color: 'border-yellow-500' },
  { key: 'CONVERTED',         label: 'Convertidos',   color: 'border-emerald-500' },
] as const

type Lead = {
  id: string
  name: string | null
  role: string | null
  company: string | null
  stage: string
}

export default function FunnelBoard({ apiKey }: { apiKey: string }) {
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    // Fetch inicial via API autenticada
    fetch(`${apiUrl}/api/leads/`, {
      headers: { 'X-API-Key': apiKey, 'Content-Type': 'application/json' },
    })
      .then(r => r.json())
      .then((data: Lead[]) => { setLeads(data); setLoading(false) })
      .catch(() => setLoading(false))

    // Realtime via Supabase
    const channel = supabase
      .channel('leads-board')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'leads' },
        payload => {
          if (payload.eventType === 'INSERT') {
            setLeads(prev => [...prev, payload.new as Lead])
          } else if (payload.eventType === 'UPDATE') {
            setLeads(prev =>
              prev.map(l => l.id === (payload.new as Lead).id ? (payload.new as Lead) : l)
            )
          } else if (payload.eventType === 'DELETE') {
            setLeads(prev => prev.filter(l => l.id !== (payload.old as { id: string }).id))
          }
        }
      )
      .subscribe()

    return () => { supabase.removeChannel(channel) }
  }, [apiKey, apiUrl])

  const byStage = (stageKey: string) =>
    leads.filter(l => l.stage === stageKey)

  if (loading) {
    return <p className="text-gray-500 text-sm">Carregando leads...</p>
  }

  return (
    <div className="flex gap-4 overflow-x-auto pb-4 min-h-64">
      {STAGES.map(({ key, label, color }) => (
        <div key={key} className={`flex-shrink-0 w-48 rounded-xl border-t-2 ${color} bg-gray-900 p-3`}>
          <div className="flex items-center justify-between mb-3">
            <p className="text-gray-300 text-xs font-semibold uppercase tracking-wide">{label}</p>
            <span className="bg-gray-800 text-gray-400 text-xs rounded-full px-2 py-0.5 min-w-[1.5rem] text-center">
              {byStage(key).length}
            </span>
          </div>
          <div className="space-y-2">
            {byStage(key).length === 0
              ? <p className="text-gray-700 text-xs text-center py-6">—</p>
              : byStage(key).map(lead => <LeadCard key={lead.id} lead={lead} />)
            }
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: Criar `frontend/app/dashboard/page.tsx`**

```typescript
import FunnelBoard from '@/components/dashboard/FunnelBoard'

export default function DashboardPage() {
  const apiKey = process.env.NEXT_PUBLIC_API_KEY || ''

  return (
    <div className="min-h-screen bg-gray-950 p-6">
      <div className="max-w-screen-xl mx-auto">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="text-white text-2xl font-bold">Vigil Summit — Funil de Leads</h1>
            <p className="text-gray-500 text-sm mt-1">
              Atualização em tempo real via Supabase Realtime
            </p>
          </div>
          <a href="/" className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
            ← Landing page
          </a>
        </div>
        <FunnelBoard apiKey={apiKey} />
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Testar dashboard localmente**

Adicionar ao `frontend/.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=vigil-secret-key-2026
DASHBOARD_PASSWORD=vigil2026
ANTHROPIC_API_KEY=sk-ant-...
```

```bash
cd frontend
npm run dev
```

Verificar em `http://localhost:3000/dashboard`:
- Redireciona para `/login` sem cookie
- Após login, mostra o board de estágios
- Leads existentes no Supabase aparecem nos cards

- [ ] **Step 5: Testar Realtime**

Com o backend rodando (`cd backend && uvicorn app.main:app --reload --port 8000`) e o frontend em dev:
1. Abrir o dashboard
2. Fazer `POST /api/leads/` via curl ou Postman com dados de lead
3. O novo card deve aparecer em `REGISTERED` sem refresh

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/supabase.ts frontend/components/dashboard/FunnelBoard.tsx frontend/app/dashboard/page.tsx
git commit -m "feat: dashboard with Supabase Realtime funnel board"
```

---

## Task 9: Script de seed — personas de teste

**Files:**
- Create: `backend/scripts/seed_personas.py`

- [ ] **Step 1: Criar `backend/scripts/__init__.py`** (arquivo vazio)

- [ ] **Step 2: Criar `backend/scripts/seed_personas.py`**

```python
"""
Cria 3 personas sintéticas para demonstração do funil completo.
Uso: cd backend && python scripts/seed_personas.py
Pré-requisito: backend rodando em localhost:8000
"""
import asyncio
import httpx
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"

PERSONAS = [
    {
        "name": "Maria Santos",
        "email": "maria.santos.demo@vigil-test.com",
        "company": "Banco Itararé",
        "role": "CISO",
        "phone": "+5511999990001",
        "scenario": "ATTENDED",         # → check-in no evento
    },
    {
        "name": "Carlos Mendes",
        "email": "carlos.mendes.demo@vigil-test.com",
        "company": "TechManufatura SA",
        "role": "CTO",
        "phone": "+5511999990002",
        "scenario": "NO_SHOW",          # → marcado como no-show
    },
    {
        "name": "Pedro Alves",
        "email": "pedro.alves.demo@vigil-test.com",
        "company": "Clínica São Paulo",
        "role": "Diretor de TI",
        "phone": None,
        "scenario": "REGISTERED",       # → só inscrito, sem ação adicional
    },
]


async def seed():
    async with httpx.AsyncClient(timeout=30) as client:
        # Busca o event_id do único evento existente
        resp = await client.get(f"{BASE_URL}/api/events/")
        events = resp.json()
        if not events:
            print("ERRO: nenhum evento encontrado. Execute o SQL da migration primeiro.")
            return
        event_id = events[0]["id"]
        print(f"Usando evento: {events[0]['name']} ({event_id})")

        for persona in PERSONAS:
            print(f"\nCriando {persona['name']} ({persona['scenario']})...")

            resp = await client.post(f"{BASE_URL}/api/leads/", json={
                "event_id": event_id,
                "name": persona["name"],
                "email": persona["email"],
                "company": persona["company"],
                "role": persona["role"],
                "phone": persona["phone"],
                "consent": True,
                "whatsapp_consent": bool(persona["phone"]),
            })

            if resp.status_code == 409:
                print(f"  ↳ Já existe, pulando.")
                continue
            if resp.status_code != 201:
                print(f"  ↳ ERRO {resp.status_code}: {resp.text}")
                continue

            lead_id = resp.json()["id"]
            print(f"  ↳ Criado: lead_id={lead_id}")

            # Aguarda o agente processar o registro
            await asyncio.sleep(3)

            # Aplica o cenário
            if persona["scenario"] == "ATTENDED":
                resp2 = await client.post(
                    f"{BASE_URL}/api/leads/{lead_id}/checkin",
                    headers={"X-API-Key": "vigil-secret-key-2026"},
                )
                print(f"  ↳ Check-in: {resp2.status_code}")

            elif persona["scenario"] == "NO_SHOW":
                resp2 = await client.post(
                    f"{BASE_URL}/api/leads/{lead_id}/no-show",
                    headers={"X-API-Key": "vigil-secret-key-2026"},
                )
                print(f"  ↳ No-show: {resp2.status_code}")

    print("\n✓ Seed concluído. Verificar no dashboard ou Supabase.")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 3: Rodar o seed**

Com backend rodando:
```bash
cd backend
python scripts/seed_personas.py
```

Expected:
```
Usando evento: Vigil Summit — Segurança para a Era da IA (uuid...)
Criando Maria Santos (ATTENDED)...
  ↳ Criado: lead_id=uuid...
  ↳ Check-in: 200
Criando Carlos Mendes (NO_SHOW)...
  ↳ Criado: lead_id=uuid...
  ↳ No-show: 200
Criando Pedro Alves (REGISTERED)...
  ↳ Criado: lead_id=uuid...
✓ Seed concluído.
```

- [ ] **Step 4: Verificar no Supabase**

No Supabase Table Editor:
- `leads`: 3 linhas com stages ATTENDED, NO_SHOW, ENRICHED/REGISTERED
- `lead_enrichment`: linhas criadas pelo agente
- `lead_memory`: entradas de raciocínio do agente

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/__init__.py backend/scripts/seed_personas.py
git commit -m "feat: seed script for demo personas covering all funnel branches"
```

---

## Task 10: Deploy — Railway (backend)

- [ ] **Step 1: Criar projeto no Railway**

Acessar `https://railway.app` → **New Project** → **Deploy from GitHub repo** → selecionar o repositório → definir **Root Directory** como `backend`.

- [ ] **Step 2: Configurar variáveis de ambiente**

No painel Railway → **Variables**, adicionar todas as variáveis do `.env.example` com valores reais:

```
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJ...
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=Vigil Summit <noreply@vigil.ai>
RESEND_WEBHOOK_SECRET=whsec_...
APOLLO_API_KEY=...
API_KEY=vigil-secret-key-2026
EVOLUTION_INSTANCE_NAME=vigil
```

- [ ] **Step 3: Aguardar deploy**

O Railway detecta o `Procfile` automaticamente e executa `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

- [ ] **Step 4: Verificar health check**

```bash
curl https://<projeto>.up.railway.app/health
```

Expected: `{"status": "ok"}`

- [ ] **Step 5: Executar migration no Supabase**

Abrir `https://supabase.com/dashboard` → seu projeto → **SQL Editor** → colar o conteúdo de `backend/migrations/001_initial.sql` → **Run**.

Expected: todas as tabelas criadas sem erro. Verificar no **Table Editor** que existem: `events`, `leads`, `lead_enrichment`, `messages`, `lead_memory`, `scheduled_jobs`, `agent_locks`.

- [ ] **Step 6: Configurar Realtime no Supabase**

No Supabase → **Database** → **Replication** → habilitar Realtime para a tabela `leads`.

- [ ] **Step 7: Configurar webhook Resend**

No painel Resend → **Webhooks** → adicionar endpoint: `https://<projeto>.up.railway.app/api/webhooks/resend`  
Eventos: `email.opened`, `email.clicked`  
Copiar o `Signing Secret` → adicionar como `RESEND_WEBHOOK_SECRET` no Railway.

- [ ] **Step 8: Commit das URLs**

Atualizar `docs/superpowers/specs/2026-05-29-vigil-agent-design.md` seção 10 com as URLs reais:
```markdown
- **API Backend:** `https://<projeto>.up.railway.app`
```

---

## Task 11: Deploy — Vercel (frontend)

- [ ] **Step 1: Criar projeto no Vercel**

Acessar `https://vercel.com` → **Add New Project** → importar do GitHub → selecionar repositório → definir **Root Directory** como `frontend`.

- [ ] **Step 2: Configurar variáveis de ambiente**

No painel Vercel → **Settings** → **Environment Variables**, adicionar:

```
NEXT_PUBLIC_API_URL=https://<projeto>.up.railway.app
NEXT_PUBLIC_API_KEY=vigil-secret-key-2026
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...  # chave anon (pública)
DASHBOARD_PASSWORD=vigil2026
ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 3: Aguardar deploy**

O Vercel detecta Next.js automaticamente e executa `next build`.

- [ ] **Step 4: Verificar landing page**

Abrir `https://<projeto>.vercel.app`:
- Landing page renderiza
- Formulário de inscrição funciona (preencher e submeter uma persona teste)
- Chatbot responde perguntas sobre o evento

- [ ] **Step 5: Verificar dashboard**

Abrir `https://<projeto>.vercel.app/dashboard`:
- Redireciona para `/login`
- Login com `DASHBOARD_PASSWORD` funciona
- Board mostra leads do Supabase
- Abrir outra aba e criar um lead — card aparece em REGISTERED sem refresh

- [ ] **Step 6: Atualizar CORS no backend**

Atualizar `backend/app/main.py` com a URL real do Vercel:

```python
allow_origins=[
    "https://<projeto>.vercel.app",
    "http://localhost:3000",
],
```

Fazer push → Railway redeploy automático.

- [ ] **Step 7: Atualizar URLs na spec**

Atualizar `docs/superpowers/specs/2026-05-29-vigil-agent-design.md` seção 10:
```markdown
- **Dashboard:** `https://<projeto>.vercel.app` (senha: vigil2026)
- **API Backend:** `https://<projeto>.up.railway.app`
```

- [ ] **Step 8: Rodar seed de personas no ambiente de produção**

Editar `backend/scripts/seed_personas.py` linha `BASE_URL`:
```python
BASE_URL = "https://<projeto>.up.railway.app"
```

```bash
cd backend
python scripts/seed_personas.py
```

Expected: 3 personas criadas no Supabase de produção, agente processando cada uma.

- [ ] **Step 9: Commit final**

```bash
git add backend/app/main.py docs/superpowers/specs/2026-05-29-vigil-agent-design.md
git commit -m "chore: update production URLs and CORS for Vercel domain"
```

---

## Self-Review: Cobertura da Spec

### Seção 1 — Arquitetura e Fluxo de Dados
- ✅ Landing page + formulário (Task 6)
- ✅ Dashboard em tempo real (Task 8)
- ✅ Backend FastAPI já implementado
- ✅ Supabase Realtime (Task 8 — FunnelBoard)

### Seção 3 — Requisitos Técnicos
- ✅ Agente funcional (backend já implementado)
- ✅ Banco de dados schema (Task 10 — migration)
- ✅ Documentação (spec + plano)
- ✅ Acesso de teste (Task 10/11 — URLs de produção + ramon@pareto.io)
- ✅ Conversas demonstráveis (Task 9 — seed)
- ✅ LLM stack: Claude Sonnet (orchestrator) + Haiku (chatbot)

### Seção 6.5 — Segurança
- ✅ `X-API-Key` em endpoints operacionais (já no backend)
- ✅ Rate limiting leads + chat (já implementado)
- ✅ Svix webhook verification (já implementado)
- ✅ Dashboard password + httpOnly cookie (Task 7)

### Gaps identificados
- ⚠️ `slowapi` ausente do requirements.txt → corrigido na Task 1
- ⚠️ `__init__.py` ausentes → corrigido na Task 2
- Tudo mais coberto.
