# Visual Redesign — SaaS B2B Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrar a identidade visual do projeto de Navy Slate para paleta SaaS B2B moderna (teal/navy/lime/green), eliminar Playfair Display e modernizar border-radius e sombras em todos os componentes.

**Architecture:** Puramente visual — zero mudança de lógica de negócio. A Task 1 é a fundação (design system tokens no Tailwind); todas as outras dependem dela. Cada task subsequente é independente entre si. As mudanças são substituições mecânicas de classes Tailwind seguindo a tabela de mapeamento da spec.

**Tech Stack:** Next.js 14 App Router, Tailwind CSS v3, TypeScript, Inter (Google Fonts via next/font)

**Spec:** `docs/superpowers/specs/2026-05-30-visual-redesign-design.md`

---

## Mapeamento de Tokens — Referência Rápida

| Token antigo | Token novo | Hex |
|---|---|---|
| `navy-950` / `slate-900` | `brand-navy` | `#0F2A34` |
| `navy-700` / `sky-700` | `brand-teal` | `#48C2C5` |
| `green-600` / `green-500` | `brand-green` | `#59BD75` |
| `amber-600` / `amber-500` | `brand-lime` | `#DDEB4F` |
| `slate-100` / fundo página | `brand-bg` | `#F7F9FB` |
| `slate-200` / bordas | `brand-border` | `#E5EAF0` |
| `slate-500` / texto sec. | `brand-muted` | `#64748B` |
| `slate-900` / texto prin. | `brand-text` | `#102A34` |

## File Map

| Tarefa | Arquivo |
|---|---|
| Task 1 | `frontend/tailwind.config.ts`, `frontend/app/layout.tsx` |
| Task 2 | `frontend/components/ui/Navbar.tsx` |
| Task 3 | `frontend/app/page.tsx` |
| Task 4 | `frontend/components/landing/RegistrationForm.tsx`, `frontend/components/landing/ChatbotWidget.tsx` |
| Task 5 | `frontend/app/login/page.tsx`, `frontend/app/deletion-confirm/page.tsx` |
| Task 6 | `frontend/components/dashboard/FunnelChart.tsx`, `frontend/components/dashboard/ActivityFeed.tsx`, `frontend/components/dashboard/FilterBar.tsx`, `frontend/components/dashboard/LeadCard.tsx` |
| Task 7 | `frontend/components/dashboard/LeadDrawer.tsx`, `frontend/components/dashboard/ConfigPanel.tsx` |
| Task 8 | `frontend/components/dashboard/FunnelBoard.tsx` |

---

## Task 1: Design system — Tailwind tokens + layout

**Files:**
- Modify: `frontend/tailwind.config.ts`
- Modify: `frontend/app/layout.tsx`

- [ ] **1.1 — Substituir tailwind.config.ts completo**

  ```ts
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
        },
        colors: {
          brand: {
            navy:   '#0F2A34',
            teal:   '#48C2C5',
            green:  '#59BD75',
            lime:   '#DDEB4F',
            bg:     '#F7F9FB',
            border: '#E5EAF0',
            muted:  '#64748B',
            text:   '#102A34',
          },
        },
      },
    },
    plugins: [],
  }
  export default config
  ```

  **Mudanças chave:**
  - Remove `playfair` de `fontFamily`
  - Remove `navy: { 700, 950 }` — substituído por `brand.navy` e `brand.teal`
  - Adiciona paleta `brand` completa

- [ ] **1.2 — Atualizar `frontend/app/layout.tsx`**

  Substituir o arquivo completo por:

  ```tsx
  import type { Metadata } from 'next'
  import { Inter } from 'next/font/google'
  import './globals.css'

  const inter = Inter({
    subsets: ['latin'],
    variable: '--font-inter',
    display: 'swap',
  })

  export const metadata: Metadata = {
    title: 'Vigil Summit — Segurança para a Era da IA',
    description: 'Evento exclusivo de cibersegurança para CISOs, CTOs e líderes de TI.',
  }

  export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
      <html lang="pt-BR">
        <body className={`${inter.variable} bg-brand-bg text-brand-text antialiased`}>
          {children}
        </body>
      </html>
    )
  }
  ```

  **Mudanças:** Remove `Playfair_Display` import e instanciação; remove `${playfair.variable}` do body; muda `bg-slate-100 text-slate-900` → `bg-brand-bg text-brand-text`.

- [ ] **1.3 — Verificar TypeScript**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

  Esperado: zero erros.

- [ ] **1.4 — Commit**

  ```bash
  git add frontend/tailwind.config.ts frontend/app/layout.tsx
  git commit -m "feat(design): new brand token system — teal/navy/lime/green, remove Playfair"
  ```

---

## Task 2: Navbar

**Files:**
- Modify: `frontend/components/ui/Navbar.tsx`

- [ ] **2.1 — Substituir `Navbar.tsx` completo**

  ```tsx
  import Link from 'next/link'

  interface NavbarProps {
    variant?: 'landing' | 'dashboard'
  }

  export default function Navbar({ variant = 'landing' }: NavbarProps) {
    return (
      <nav className="bg-brand-navy sticky top-0 z-50">
        <div className={`max-w-screen-xl mx-auto px-8 flex items-center justify-between ${variant === 'dashboard' ? 'h-14' : 'h-16'}`}>
          <div className="flex items-center gap-3">
            <Link href="/" className="font-black text-lg tracking-wide text-white">
              VIGIL<span className="text-brand-teal">.AI</span>
            </Link>
            {variant === 'dashboard' && (
              <>
                <div className="w-px h-5 bg-white/20" />
                <span className="font-bold text-white/70 text-[15px]">
                  Vigil Summit — Funil de Leads
                </span>
              </>
            )}
          </div>

          {variant === 'landing' && (
            <div className="flex items-center gap-7">
              <a href="#agenda" className="text-white/60 hover:text-white text-sm font-medium transition-colors">
                Agenda
              </a>
              <a href="#speakers" className="text-white/60 hover:text-white text-sm font-medium transition-colors">
                Speakers
              </a>
              <a href="#local" className="text-white/60 hover:text-white text-sm font-medium transition-colors">
                Local
              </a>
              <a
                href="#inscricao"
                className="bg-brand-lime text-brand-navy text-sm font-bold px-5 py-2.5 rounded-[10px] hover:bg-brand-lime/90 transition-colors"
              >
                Garantir vaga →
              </a>
            </div>
          )}

          {variant === 'dashboard' && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5 bg-brand-teal/20 border border-brand-teal/40 text-brand-teal text-xs font-bold px-3 py-1.5 rounded-full">
                <span className="w-1.5 h-1.5 bg-brand-teal rounded-full animate-pulse inline-block" />
                Ao vivo
              </div>
              <Link href="/" className="text-white/50 hover:text-white/80 text-xs transition-colors">
                ← Landing page
              </Link>
            </div>
          )}
        </div>
      </nav>
    )
  }
  ```

- [ ] **2.2 — Verificar TypeScript**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

- [ ] **2.3 — Commit**

  ```bash
  git add frontend/components/ui/Navbar.tsx
  git commit -m "feat(design): Navbar — dark navy background, teal accent, lime CTA"
  ```

---

## Task 3: Landing page

**Files:**
- Modify: `frontend/app/page.tsx`

- [ ] **3.1 — Substituir `app/page.tsx` completo**

  ```tsx
  export const dynamic = 'force-dynamic'

  import Navbar from '@/components/ui/Navbar'
  import RegistrationForm from '@/components/landing/RegistrationForm'
  import ChatbotWidget from '@/components/landing/ChatbotWidget'

  export default function Home() {
    return (
      <main className="min-h-screen bg-brand-bg">
        <Navbar variant="landing" />

        {/* HERO */}
        <section className="bg-white border-b border-brand-border">
          <div className="max-w-screen-xl mx-auto px-8 py-20 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div>
              <div className="flex items-center gap-2 mb-6">
                <div className="w-2 h-2 bg-brand-teal rounded-full" />
                <span className="text-brand-teal text-xs font-bold tracking-[0.15em] uppercase">
                  São Paulo · 15 Ago 2026 · Presencial
                </span>
              </div>
              <h1 className="font-extrabold text-5xl text-brand-text leading-[1.1] tracking-tight mb-5">
                Vigil Summit<br />
                <span className="text-brand-teal">Segurança para<br />a Era da IA</span>
              </h1>
              <p className="text-brand-muted text-lg leading-relaxed mb-8 max-w-xl">
                O encontro definitivo de CISOs, CTOs e líderes de segurança corporativa para discutir
                IA, Zero Trust e conformidade em 2026.
              </p>
              <div className="flex gap-3 mb-10">
                <a
                  href="#inscricao"
                  className="bg-brand-navy text-white font-bold text-sm px-7 py-3.5 rounded-[10px] hover:bg-brand-navy/90 transition-colors"
                >
                  Garantir minha vaga →
                </a>
                <a
                  href="#agenda"
                  className="bg-brand-lime text-brand-navy font-bold text-sm px-5 py-3.5 rounded-[10px] hover:bg-brand-lime/90 transition-colors"
                >
                  Ver programação
                </a>
              </div>
              <div className="flex gap-8 border-t border-brand-border pt-8">
                {[
                  { num: '120', label: 'vagas exclusivas' },
                  { num: '8h', label: 'de conteúdo' },
                  { num: 'C-level', label: 'público-alvo' },
                ].map(({ num, label }) => (
                  <div key={label}>
                    <div className="font-extrabold text-3xl text-brand-text tracking-tight leading-none">{num}</div>
                    <div className="text-brand-muted text-xs font-medium mt-1">{label}</div>
                  </div>
                ))}
              </div>
            </div>

            <div id="inscricao" className="bg-white rounded-[20px] border border-brand-border p-8 shadow-[0_16px_40px_rgba(15,42,52,0.08)]">
              <h2 className="text-brand-text text-lg font-extrabold mb-1">Garante sua vaga</h2>
              <p className="text-brand-muted text-sm mb-5">Inscrições limitadas a 120 participantes.</p>
              <RegistrationForm />
            </div>
          </div>
        </section>

        {/* TRILHAS */}
        <section className="bg-brand-bg border-y border-brand-border py-14" id="agenda">
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
                  className="bg-white rounded-[16px] border border-brand-border border-t-[3px] border-t-brand-teal p-6"
                >
                  <p className="text-brand-teal text-xs font-bold tracking-[0.1em] uppercase mb-2">{track}</p>
                  <p className="text-brand-text font-extrabold text-base mb-2">{title}</p>
                  <p className="text-brand-muted text-sm leading-relaxed">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* PÚBLICO-ALVO */}
        <section className="bg-white py-16">
          <div className="max-w-screen-xl mx-auto px-8">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-5 h-0.5 bg-brand-teal" />
              <span className="text-brand-teal text-xs font-bold tracking-[0.15em] uppercase">Para quem é</span>
            </div>
            <h2 className="font-extrabold text-3xl text-brand-text mb-3 tracking-tight">
              Feito para quem decide em segurança
            </h2>
            <p className="text-brand-muted text-base leading-relaxed mb-8 max-w-xl">
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
                      ? 'border-brand-teal text-brand-teal bg-brand-teal/10'
                      : 'border-brand-border text-brand-muted bg-white'
                  }`}
                >
                  {label}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="bg-brand-navy py-5 px-8">
          <div className="max-w-screen-xl mx-auto flex items-center justify-between">
            <p className="text-white/40 text-sm">
              © 2026 Vigil.AI · Todos os direitos reservados
            </p>
            <a href="/deletion-confirm" className="text-brand-teal text-sm hover:text-brand-teal/80 transition-colors">
              Política de privacidade
            </a>
          </div>
        </footer>

        <ChatbotWidget />
      </main>
    )
  }
  ```

- [ ] **3.2 — Verificar TypeScript**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

- [ ] **3.3 — Commit**

  ```bash
  git add frontend/app/page.tsx
  git commit -m "feat(design): landing page — new SaaS B2B visual identity"
  ```

---

## Task 4: Componentes landing (RegistrationForm + ChatbotWidget)

**Files:**
- Modify: `frontend/components/landing/RegistrationForm.tsx`
- Modify: `frontend/components/landing/ChatbotWidget.tsx`

- [ ] **4.1 — Atualizar classes visuais em `RegistrationForm.tsx`**

  Apenas três mudanças de classes, preservando toda a lógica:

  **Linha com `inputClass`** (por volta da linha 87), substituir:
  ```tsx
  const inputClass = 'w-full bg-slate-50 border border-slate-200 rounded px-4 py-3 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-700 transition-colors text-sm'
  ```
  por:
  ```tsx
  const inputClass = 'w-full bg-brand-bg border border-brand-border rounded-[10px] px-4 py-3 text-brand-text placeholder-brand-muted focus:outline-none focus:border-brand-teal transition-colors text-sm'
  ```

  **Checkboxes `accent-sky-700`** (2 ocorrências): substituir ambas por `accent-brand-teal`.

  **Botão submit** (última linha com `className` do button), substituir:
  ```tsx
  className="w-full bg-slate-900 hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3 rounded transition-colors text-sm"
  ```
  por:
  ```tsx
  className="w-full bg-brand-navy hover:bg-brand-teal disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3 rounded-[10px] transition-colors text-sm"
  ```

  **Status "duplicate"** (texto de e-mail já inscrito), substituir `text-sky-700` por `text-brand-teal`.

  **Status "success"**, substituir `text-green-700` por `text-brand-green`.

  **eventError** (`text-amber-600`) → `text-brand-lime` e adicionar `text-brand-navy` para legibilidade:
  substituir `text-amber-600` por `text-[#6b7a00]`.

- [ ] **4.2 — Atualizar classes visuais em `ChatbotWidget.tsx`**

  Apenas as classes de estilo, preservando toda a lógica de streaming:

  **Botão bolha** (linha ~111), substituir:
  ```tsx
  className="fixed bottom-6 right-6 w-14 h-14 bg-slate-900 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-sky-700 transition-colors z-50"
  ```
  por:
  ```tsx
  className="fixed bottom-6 right-6 w-14 h-14 bg-brand-navy text-white rounded-full shadow-lg flex items-center justify-center hover:bg-brand-teal transition-colors z-50"
  ```

  **Header do chat** (linha ~125), substituir `bg-slate-900`:
  ```tsx
  className="px-4 py-3 border-b border-brand-border bg-brand-navy rounded-t-2xl"
  ```

  **Sub-header** (`text-slate-400`) → `text-white/50`.

  **Mensagem do usuário** (`bg-sky-700 text-white`) → `bg-brand-teal text-white`.

  **Input de texto** (linha ~149), substituir:
  ```tsx
  className="flex-1 bg-slate-50 text-slate-900 text-sm p-2 rounded border border-slate-200 placeholder-slate-400 focus:outline-none focus:border-sky-700"
  ```
  por:
  ```tsx
  className="flex-1 bg-brand-bg text-brand-text text-sm p-2 rounded-[8px] border border-brand-border placeholder-brand-muted focus:outline-none focus:border-brand-teal"
  ```

  **Botão enviar** (linha ~153):
  ```tsx
  className="bg-brand-navy text-white px-3 py-2 rounded-[8px] text-sm hover:bg-brand-teal disabled:opacity-50 transition-colors"
  ```

  **Container chat popup** (linha ~122), substituir `border-slate-200`:
  ```tsx
  className="fixed bottom-24 right-6 w-80 bg-white rounded-2xl shadow-2xl border border-brand-border z-50 flex flex-col"
  ```

  **Divisor de input** (`border-t border-slate-200`) → `border-t border-brand-border`.

- [ ] **4.3 — Verificar TypeScript**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

- [ ] **4.4 — Commit**

  ```bash
  git add frontend/components/landing/RegistrationForm.tsx frontend/components/landing/ChatbotWidget.tsx
  git commit -m "feat(design): landing components — RegistrationForm and ChatbotWidget rebrand"
  ```

---

## Task 5: Login + Deletion Confirm

**Files:**
- Modify: `frontend/app/login/page.tsx`
- Modify: `frontend/app/deletion-confirm/page.tsx`

- [ ] **5.1 — Substituir `app/login/page.tsx` completo**

  ```tsx
  'use client'
  import { useState } from 'react'
  import { useRouter } from 'next/navigation'
  import { createBrowserClient } from '@supabase/ssr'

  export default function LoginPage() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const router = useRouter()

    const handleSubmit = async (e: React.FormEvent) => {
      e.preventDefault()
      setLoading(true)
      setError('')
      const supabase = createBrowserClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
      )
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) {
        setError('Credenciais inválidas. Verifique e-mail e senha.')
        setLoading(false)
      } else {
        router.push('/dashboard')
        router.refresh()
      }
    }

    return (
      <div className="min-h-screen bg-brand-bg flex items-center justify-center px-4">
        <div className="bg-white rounded-[20px] border border-brand-border shadow-[0_16px_40px_rgba(15,42,52,0.08)] p-8 w-full max-w-sm">
          <p className="font-black text-lg tracking-wide text-brand-navy text-center mb-1">
            VIGIL<span className="text-brand-teal">.AI</span>
          </p>
          <h1 className="font-bold text-2xl text-brand-text text-center mb-1">
            Acesso ao Dashboard
          </h1>
          <p className="text-brand-muted text-sm text-center mb-7">Restrito à equipe Vigil.AI</p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="E-mail"
              required
              className="w-full bg-brand-bg border border-brand-border rounded-[10px] px-4 py-3 text-brand-text placeholder-brand-muted focus:outline-none focus:border-brand-teal transition-colors text-sm"
            />
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Senha"
              required
              className="w-full bg-brand-bg border border-brand-border rounded-[10px] px-4 py-3 text-brand-text placeholder-brand-muted focus:outline-none focus:border-brand-teal transition-colors text-sm"
            />
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-brand-navy hover:bg-brand-teal disabled:opacity-50 text-white font-bold py-3 rounded-[10px] transition-colors text-sm"
            >
              {loading ? 'Entrando…' : 'Entrar →'}
            </button>
          </form>
        </div>
      </div>
    )
  }
  ```

- [ ] **5.2 — Atualizar classes em `app/deletion-confirm/page.tsx`**

  Preservar toda a lógica. Apenas substituir as classes:

  - `bg-slate-100` (2 ocorrências) → `bg-brand-bg`
  - `rounded-xl` → `rounded-[20px]`
  - `shadow-sm` → `shadow-[0_16px_40px_rgba(15,42,52,0.08)]`
  - Logo: `text-slate-900` → `text-brand-navy`, `text-sky-700` → `text-brand-teal`
  - H1: `font-playfair font-bold text-xl text-slate-900` → `font-bold text-xl text-brand-text`
  - `text-green-700` → `text-brand-green`
  - `text-sky-700` (link email) → `text-brand-teal`

- [ ] **5.3 — Verificar TypeScript**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

- [ ] **5.4 — Commit**

  ```bash
  git add frontend/app/login/page.tsx frontend/app/deletion-confirm/page.tsx
  git commit -m "feat(design): login and deletion-confirm — new brand identity"
  ```

---

## Task 6: Dashboard leaf components (FunnelChart, ActivityFeed, FilterBar, LeadCard)

**Files:**
- Modify: `frontend/components/dashboard/FunnelChart.tsx`
- Modify: `frontend/components/dashboard/ActivityFeed.tsx`
- Modify: `frontend/components/dashboard/FilterBar.tsx`
- Modify: `frontend/components/dashboard/LeadCard.tsx`

- [ ] **6.1 — Atualizar `FunnelChart.tsx`**

  Substituir o objeto `FUNNEL_STAGES` (cores inline):
  ```tsx
  const FUNNEL_STAGES = [
    { key: 'REGISTERED',        label: 'Inscritos',      color: '#48C2C5' },
    { key: 'ENRICHED',          label: 'Enriquecidos',   color: '#48C2C5' },
    { key: 'CONFIRMED',         label: 'Confirmados',    color: '#59BD75' },
    { key: 'ATTENDED',          label: 'Presentes',      color: '#48C2C5' },
    { key: 'NO_SHOW',           label: 'No-show',        color: '#f87171' },
    { key: 'MEETING_SCHEDULED', label: 'Reunião agend.', color: '#DDEB4F' },
    { key: 'CONVERTED',         label: 'Convertidos',    color: '#59BD75' },
  ] as const
  ```

  Substituir `rateColor`:
  ```tsx
  function rateColor(rate: number): string {
    if (rate >= 70) return 'text-brand-green'
    if (rate >= 50) return 'text-[#6b7a00]'
    return 'text-red-400'
  }
  ```

  Nas classes do JSX:
  - `bg-slate-100` (barra de fundo) → `bg-brand-bg`
  - `text-slate-400` (labels e texto secundário) → `text-brand-muted`
  - `text-slate-700` (valores em negrito no rodapé) → `text-brand-text`
  - `text-green-600` (✓ meta) → `text-brand-green`
  - `text-red-500` (abaixo da meta) → `text-red-400`
  - `border-slate-100` (divisor) → `border-brand-border`

- [ ] **6.2 — Atualizar `ActivityFeed.tsx`**

  Substituir `DOT_COLOR`:
  ```tsx
  const DOT_COLOR: Record<ActivityEvent['type'], string> = {
    clicked: 'bg-brand-lime',
    opened:  'bg-brand-green',
    sent:    'bg-brand-teal',
  }
  ```

  Nas classes do JSX:
  - `text-slate-800 font-semibold` (lead name) → `text-brand-text font-semibold`
  - `text-slate-500` (texto evento) → `text-brand-muted`
  - `text-slate-300` (tempo relativo) → `text-brand-border`
  - `border-slate-50` (divisores de linha) → `border-brand-bg`
  - `text-xs text-slate-300` (empty state) → `text-xs text-brand-border`

- [ ] **6.3 — Atualizar `FilterBar.tsx`**

  Substituir classes no input e chips:

  **Input search:**
  ```tsx
  className="flex-1 max-w-[280px] border border-brand-border rounded-md px-3 py-1.5 text-xs text-brand-muted placeholder:text-brand-border focus:outline-none focus:border-brand-teal"
  ```

  **Botão setor ativo** (quando `sectorFilter` ativo):
  ```tsx
  'bg-brand-teal/10 border-brand-teal text-brand-teal'
  ```
  **Botão setor inativo:**
  ```tsx
  'bg-white border-brand-border text-brand-muted hover:border-brand-teal'
  ```

  **Botão decisores ativo:**
  ```tsx
  'bg-brand-teal/10 border-brand-teal text-brand-teal'
  ```
  **Botão decisores inativo:**
  ```tsx
  'bg-white border-brand-border text-brand-muted hover:border-brand-teal'
  ```

  **Texto do item selecionado no dropdown:**
  ```tsx
  sectorFilter === s ? 'text-brand-teal font-semibold' : 'text-brand-muted'
  ```

  **Contador de filtros** (`text-[10px] text-slate-400`) → `text-[10px] text-brand-muted`.

- [ ] **6.4 — Atualizar `LeadCard.tsx`**

  Substituir `TAG_CLASSES`:
  ```tsx
  const TAG_CLASSES: Record<TagColor, string> = {
    navy:  'bg-brand-teal/10 text-brand-teal',
    green: 'bg-brand-green/10 text-brand-green',
    amber: 'bg-brand-lime/20 text-[#6b7a00]',
    red:   'bg-red-50 text-red-500',
    slate: 'bg-brand-bg text-brand-muted',
  }
  ```

  Substituir `SIGNAL_DOT`:
  ```tsx
  const SIGNAL_DOT: Record<SignalColor, string> = {
    green: 'bg-brand-green',
    amber: 'bg-brand-lime',
    gray:  'bg-brand-border',
    red:   'bg-red-400',
  }
  ```

  No JSX do card:
  ```tsx
  <div
    onClick={onClick}
    className="bg-white border border-brand-border rounded-[10px] p-2.5 mb-1.5 cursor-pointer hover:border-brand-teal hover:shadow-sm transition-all last:mb-0"
  >
    <p className="text-brand-text text-xs font-bold mb-0.5 truncate">{shortName}</p>
    {roleLabel && (
      <p className="text-brand-muted text-[10px] mb-1.5 truncate">{roleLabel}</p>
    )}
    ...
    <div className="flex items-center gap-1.5 pt-1.5 border-t border-brand-bg">
  ```

- [ ] **6.5 — Verificar TypeScript**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

- [ ] **6.6 — Commit**

  ```bash
  git add frontend/components/dashboard/FunnelChart.tsx \
    frontend/components/dashboard/ActivityFeed.tsx \
    frontend/components/dashboard/FilterBar.tsx \
    frontend/components/dashboard/LeadCard.tsx
  git commit -m "feat(design): dashboard leaf components — teal/green/lime brand palette"
  ```

---

## Task 7: LeadDrawer + ConfigPanel

**Files:**
- Modify: `frontend/components/dashboard/LeadDrawer.tsx`
- Modify: `frontend/components/dashboard/ConfigPanel.tsx`

- [ ] **7.1 — Atualizar `LeadDrawer.tsx`**

  Substituir `STAGE_STYLE`:
  ```tsx
  const STAGE_STYLE: Record<string, { label: string; color: string; bg: string; border: string }> = {
    REGISTERED:        { label: 'Inscrito',       color: 'text-brand-teal',  bg: 'bg-brand-teal/10',  border: 'border-brand-teal/30' },
    ENRICHED:          { label: 'Enriquecido',    color: 'text-brand-teal',  bg: 'bg-brand-teal/10',  border: 'border-brand-teal/30' },
    CONFIRMED:         { label: 'Confirmado',     color: 'text-brand-green', bg: 'bg-brand-green/10', border: 'border-brand-green/30' },
    ATTENDED:          { label: 'Presente',       color: 'text-brand-teal',  bg: 'bg-brand-teal/10',  border: 'border-brand-teal/30' },
    NO_SHOW:           { label: 'No-show',        color: 'text-red-500',     bg: 'bg-red-50',         border: 'border-red-200' },
    MEETING_SCHEDULED: { label: 'Reunião agend.', color: 'text-[#6b7a00]',  bg: 'bg-brand-lime/20',  border: 'border-brand-lime/50' },
    CONVERTED:         { label: 'Convertido',     color: 'text-brand-green', bg: 'bg-brand-green/10', border: 'border-brand-green/30' },
  }
  ```

  Substituir `getDrawerTags`:
  ```tsx
  function getDrawerTags(lead: RichLead) {
    const tags: Array<{ label: string; cls: string }> = []
    const role = (lead.role ?? '').toLowerCase()
    if (/ciso|cto|ceo|coo|cfo|\bvp\b|diretor|director|chief/.test(role)) {
      tags.push({ label: 'C-level', cls: 'bg-brand-teal/10 text-brand-teal' })
    }
    if (lead.enrichment?.is_decision_maker) {
      tags.push({ label: 'decisor', cls: 'bg-brand-lime/20 text-[#6b7a00]' })
    }
    return tags
  }
  ```

  Substituir `msgBorderColor`:
  ```tsx
  function msgBorderColor(msg: Message): string {
    if (msg.clicked_at) return 'border-brand-green'
    if (msg.opened_at) return 'border-brand-green/50'
    return 'border-brand-teal'
  }
  ```

  No JSX do drawer:
  - Overlay: manter inline `rgba(15, 42, 52, 0.2)` (já correto da spec)
  - Nome: `text-navy-950` → `text-brand-text font-extrabold`
  - Role/company: `text-slate-500` → `text-brand-muted`
  - Labels campos: `text-slate-400` → `text-brand-muted`
  - Valores campos: `text-navy-950` → `text-brand-text font-semibold`
  - Decisor sim: `text-green-600` → `text-brand-green`
  - Sinal seg sim: `text-green-600` → `text-brand-green`
  - Msg subject: `text-navy-950` → `text-brand-text font-bold`
  - Msg date: `text-slate-400` → `text-brand-muted`
  - Msg status: `text-slate-500` → `text-brand-muted`
  - Check verde: `text-green-600` (classe `msg-check`) → manter como está (inline no texto `✓`)
  - Botão "Rodar Agente": `bg-navy-950 hover:bg-navy-700` → `bg-brand-navy hover:bg-brand-teal`

- [ ] **7.2 — Atualizar `ConfigPanel.tsx`**

  Substituir todos os tokens de cor, preservando lógica:

  **STATUS_BADGE:**
  ```tsx
  const STATUS_BADGE: Record<string, { cls: string; label: string }> = {
    ok:       { cls: 'bg-brand-green/10 text-brand-green', label: '✓ Ativo' },
    warn:     { cls: 'bg-brand-lime/20 text-[#6b7a00]',   label: '⚠ Não configurado' },
    error:    { cls: 'bg-red-50 text-red-500',             label: '✗ Erro' },
    checking: { cls: 'bg-brand-bg text-brand-muted',       label: '⏳ Verificando…' },
  }
  ```

  **JOB_STATUS_BADGE:**
  ```tsx
  const JOB_STATUS_BADGE: Record<string, string> = {
    DONE:    'bg-brand-green/10 text-brand-green',
    PENDING: 'bg-brand-teal/10 text-brand-teal',
    RUNNING: 'bg-brand-lime/20 text-[#6b7a00]',
    FAILED:  'bg-red-50 text-red-500',
    SKIPPED: 'bg-brand-bg text-brand-muted',
  }
  ```

  No JSX:
  - Card evento: `border-t-navy-700` → `border-t-brand-teal`
  - Input focus: `focus:border-navy-700` → `focus:border-brand-teal`
  - Input background: `border-slate-200 rounded-md` → `border-brand-border rounded-[10px]`
  - Botão salvar: `bg-navy-950 hover:bg-navy-700` → `bg-brand-navy hover:bg-brand-teal rounded-[10px]`
  - saveMsg sucesso (`startsWith('✓')`): `text-green-600` → `text-brand-green`
  - saveMsg erro: `text-red-500` → manter
  - Barra progresso: `bg-navy-700` → `bg-brand-teal`
  - Barra fundo: `bg-slate-100` → `bg-brand-bg`
  - Texto progresso: `text-slate-500` → `text-brand-muted`
  - Cards serviços: `border-slate-200 rounded-lg` → `border-brand-border rounded-[14px]`
  - Nome serviço: `text-navy-950` → `text-brand-text`
  - Role serviço: `text-slate-500` → `text-brand-muted`
  - Detail serviço: `text-slate-400` → `text-brand-muted`
  - Botão verificar: `border-slate-200 text-slate-500 hover:border-navy-700 hover:text-navy-700` → `border-brand-border text-brand-muted hover:border-brand-teal hover:text-brand-teal rounded-[10px]`
  - Header tabela: `text-navy-950` → `text-brand-text`
  - Subtítulo tabela: `text-slate-400` → `text-brand-muted`
  - Cabeçalhos colunas: `text-slate-400` → `text-brand-muted`
  - `bg-slate-50` (hover row, th bg) → `bg-brand-bg`
  - `border-slate-100` → `border-brand-bg`
  - `border-slate-50` → `border-brand-bg`
  - Lead name: `text-navy-950` → `text-brand-text font-semibold`
  - Lead company: `text-slate-400` → `text-brand-muted`
  - Job type code: `bg-slate-100 text-slate-600` → `bg-brand-bg text-brand-muted`
  - runAt: `text-slate-500` → `text-brand-muted`
  - Botão ação (canRun): `text-navy-700 hover:border-navy-700` → `text-brand-teal hover:border-brand-teal`
  - Em branco (—): `text-slate-300` → `text-brand-border`

- [ ] **7.3 — Verificar TypeScript**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

- [ ] **7.4 — Commit**

  ```bash
  git add frontend/components/dashboard/LeadDrawer.tsx frontend/components/dashboard/ConfigPanel.tsx
  git commit -m "feat(design): LeadDrawer and ConfigPanel — brand tokens applied"
  ```

---

## Task 8: FunnelBoard (KPI strip, tab bar, kanban)

**Files:**
- Modify: `frontend/components/dashboard/FunnelBoard.tsx`

- [ ] **8.1 — Atualizar `STAGES` array (cores das colunas kanban)**

  Substituir o array `STAGES`:
  ```tsx
  const STAGES = [
    { key: 'REGISTERED',        label: 'Inscritos',        color: 'border-brand-teal',    titleColor: 'text-brand-teal'   },
    { key: 'ENRICHED',          label: 'Enriquecidos',     color: 'border-brand-teal',    titleColor: 'text-brand-teal'   },
    { key: 'CONFIRMED',         label: 'Confirmados',      color: 'border-brand-green',   titleColor: 'text-brand-green'  },
    { key: 'ATTENDED',          label: 'Presentes',        color: 'border-brand-teal',    titleColor: 'text-brand-teal'   },
    { key: 'NO_SHOW',           label: 'No-show',          color: 'border-red-400',       titleColor: 'text-red-400'      },
    { key: 'MEETING_SCHEDULED', label: 'Reunião agendada', color: 'border-brand-lime',    titleColor: 'text-[#6b7a00]'    },
    { key: 'CONVERTED',         label: 'Convertidos',      color: 'border-brand-green',   titleColor: 'text-brand-green'  },
  ] as const
  ```

- [ ] **8.2 — Atualizar KPI strip no JSX**

  Localizar o bloco `{/* KPI STRIP */}`. Substituir:

  - Container: `bg-white border-b border-slate-200 px-8 py-5 grid grid-cols-2 lg:grid-cols-4 gap-4` → `bg-brand-navy px-8 py-5 grid grid-cols-2 lg:grid-cols-4 gap-4`
  - Cards KPI: `bg-white border border-slate-200 [border-top-width:3px] ${kpi.accent} rounded-lg p-4` → `bg-white/[0.07] border border-white/[0.12] rounded-[12px] p-4`
  - Label KPI: `text-[10px] font-semibold text-slate-400 uppercase tracking-[0.08em] mb-2` → `text-[10px] font-semibold text-white/50 uppercase tracking-[0.08em] mb-2`
  - Valor KPI: remover `font-playfair font-black text-4xl` → `font-extrabold text-4xl tracking-tight`
  - Sub KPI: `text-slate-400 text-[11px] mt-1.5` → `text-white/40 text-[11px] mt-1.5`

  Atualizar o array de KPI cards:
  ```tsx
  {[
    {
      label: 'Total inscritos',
      value: String(total),
      sub: 'de 120 vagas',
      meta: null as string | null,
      metaColor: '',
      valueColor: 'text-brand-teal',
    },
    {
      label: 'Taxa de confirmação',
      value: `${confirmRate}%`,
      sub: 'meta: acima de 70%',
      meta: metaText,
      metaColor,
      valueColor: confirmRate >= 70 ? 'text-brand-green' : 'text-red-400',
    },
    {
      label: 'Reuniões agendadas',
      value: String(meetings),
      sub: 'via Cal.com',
      meta: meetingsDeltaWeek > 0 ? `+${meetingsDeltaWeek} essa semana` : null,
      metaColor: 'text-brand-lime',
      valueColor: 'text-brand-lime',
    },
    {
      label: 'No-show',
      value: String(noShow),
      sub: 'reengajamento ativo',
      meta: noShowEmailOpened > 0 ? `${noShowEmailOpened} com email aberto` : null,
      metaColor: 'text-brand-green',
      valueColor: 'text-red-400',
    },
  ].map(kpi => (
    <div key={kpi.label} className="bg-white/[0.07] border border-white/[0.12] rounded-[12px] p-4">
      <p className="text-[10px] font-semibold text-white/50 uppercase tracking-[0.08em] mb-2">{kpi.label}</p>
      <p className={`font-extrabold text-4xl leading-none tracking-tight ${kpi.valueColor}`}>{kpi.value}</p>
      <p className="text-white/40 text-[11px] mt-1.5">{kpi.sub}</p>
      {kpi.meta && (
        <p className={`text-[10px] font-semibold mt-0.5 ${kpi.metaColor}`}>{kpi.meta}</p>
      )}
    </div>
  ))}
  ```

  Também atualizar `metaColor` derivado de `metaDiff`:
  ```tsx
  const metaColor = metaDiff >= 0 ? 'text-brand-green' : 'text-red-400'
  ```

- [ ] **8.3 — Atualizar tab bar no JSX**

  Localizar `{/* TAB BAR */}`. Substituir:
  ```tsx
  {/* TAB BAR */}
  <div className="bg-brand-navy border-b border-white/10 px-8 flex gap-0">
    <button
      onClick={() => setActiveTab('funnel')}
      className={`py-3 px-5 text-xs font-semibold border-b-2 transition-colors -mb-px ${
        activeTab === 'funnel'
          ? 'border-brand-teal text-brand-teal'
          : 'border-transparent text-white/40 hover:text-white/70'
      }`}
    >
      📊 Funil de Leads
    </button>
    <button
      onClick={() => setActiveTab('config')}
      className={`py-3 px-5 text-xs font-semibold border-b-2 transition-colors -mb-px ${
        activeTab === 'config'
          ? 'border-brand-teal text-brand-teal'
          : 'border-transparent text-white/40 hover:text-white/70'
      }`}
    >
      ⚙ Configurações
    </button>
  </div>
  ```

- [ ] **8.4 — Atualizar middle row, kanban e labels**

  No bloco do funil (`{activeTab === 'funnel' && ...}`):

  - Middle row: remover `bg-white border-b border-slate-200` dos cards individuais → os cards são os próprios FunnelChart e ActivityFeed que já têm border própria
  - Título kanban: `font-playfair font-extrabold text-xl text-slate-900` → `font-extrabold text-xl text-brand-text`
  - Subtítulo kanban: `text-slate-400` → `text-brand-muted`
  - Badge data evento: `bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-slate-500 text-xs font-semibold` → `bg-white border border-brand-border rounded-[10px] px-3 py-1.5 text-brand-muted text-xs font-semibold`
  - Col header: `bg-white border border-b-0 border-slate-200 [border-top-width:3px] ${color} rounded-t-lg` → `bg-white border border-b-0 border-brand-border [border-top-width:3px] ${color} rounded-t-[10px]`
  - Col badge count: `bg-slate-100 text-slate-500 text-[10px] font-bold px-2 py-0.5 rounded-full` → `bg-brand-bg text-brand-muted text-[10px] font-bold px-2 py-0.5 rounded-full`
  - Col body: `bg-white border border-slate-200 rounded-b-lg` → `bg-white border border-brand-border rounded-b-[10px]`
  - Empty state: `text-slate-200` → `text-brand-border`

- [ ] **8.5 — Verificar build completo**

  ```bash
  cd frontend && npm run build 2>&1 | tail -20
  ```

  Esperado: build sem erros, todas as rotas compiladas.

- [ ] **8.6 — Commit e push**

  ```bash
  git add frontend/components/dashboard/FunnelBoard.tsx
  git commit -m "feat(design): FunnelBoard — dark KPI strip, brand tokens across dashboard"
  git push origin master
  ```

---

## Self-Review

**Spec coverage:**
- ✅ Design system tokens (tailwind.config.ts) — Task 1
- ✅ Remover Playfair Display — Task 1 (tailwind.config.ts) + Task 1.2 (layout.tsx) + Tasks 3, 5, 8 (font-playfair → font-extrabold)
- ✅ Navbar dark navy — Task 2
- ✅ Landing page completa — Task 3
- ✅ RegistrationForm + ChatbotWidget — Task 4
- ✅ Login + Deletion confirm — Task 5
- ✅ FunnelChart, ActivityFeed, FilterBar, LeadCard — Task 6
- ✅ LeadDrawer + ConfigPanel — Task 7
- ✅ FunnelBoard KPI strip dark + tab bar + kanban — Task 8
- ✅ Lime como CTA de destaque landing — Task 3 (botão "Ver programação")
- ✅ Lime como CTA navbar — Task 2

**Tokens consistentes em todos os tasks:**
- `brand-teal` = `#48C2C5` — accent primário em toda a spec ✅
- `brand-navy` = `#0F2A34` — fundo navbar, KPI strip, botões primários ✅
- `brand-lime` = `#DDEB4F` — CTAs de destaque (lime sobre navy = bom contraste) ✅
- `text-[#6b7a00]` — sempre usado quando lime é background (cor escura com contraste adequado) ✅
- Playfair eliminado: nenhum `font-playfair` restante após Tasks 1, 3, 5, 8 ✅
