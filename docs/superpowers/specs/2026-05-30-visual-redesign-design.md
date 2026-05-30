# Redesign Visual — SaaS B2B Identity Spec

**Data:** 2026-05-30
**Projeto:** Case AI Engineer — Pareto × Vigil.AI
**Escopo:** Migração completa da identidade visual de Navy Slate para paleta SaaS B2B moderna — landing page, dashboard, login, deletion-confirm e todos os componentes compartilhados.

---

## 1. Decisões Aprovadas

| Decisão | Escolha |
|---|---|
| Tipografia | Inter puro em todos os contextos — eliminar Playfair Display completamente |
| Cor primária | `#0F2A34` (navy escuro) — replace `#0f172a` atual |
| Cor accent | `#48C2C5` (teal) — replace `#0369a1` (sky-700/navy-700) atual |
| Cor sucesso | `#59BD75` (green) — replace `#16a34a` (green-600) |
| Cor destaque/CTA | `#DDEB4F` (lime) — novo, sem equivalente atual |
| Cor fundo página | `#F7F9FB` — replace `slate-100` (#f1f5f9) |
| Cor borda | `#E5EAF0` — mantém quase igual ao `slate-200` atual |
| Cor texto secundário | `#64748B` — mantém igual ao `slate-500` atual |
| Navbar landing + dashboard | **Fundo navy escuro** (#0F2A34) — replace navbar branca atual |
| KPI strip dashboard | **Fundo navy escuro** com valores em teal/green/lime — replace fundo branco atual |
| Border radius botões | `10px` — replace `4px` atual |
| Border radius cards | `20px` — replace `8px` atual |
| Sombra cards | `0 16px 40px rgba(15,42,52,0.08)` — replace shadow atual |

---

## 2. Design System — Tailwind Config

Substituir o bloco `colors` em `frontend/tailwind.config.ts`:

```ts
colors: {
  brand: {
    navy:  '#0F2A34',
    teal:  '#48C2C5',
    green: '#59BD75',
    lime:  '#DDEB4F',
    bg:    '#F7F9FB',
    border:'#E5EAF0',
    muted: '#64748B',
    text:  '#102A34',
  },
},
```

Remover o token `navy: { 700, 950 }` existente — substituído por `brand.navy` e `brand.teal`.

Remover `playfair` de `fontFamily.extend` — Inter é o único `sans` do projeto agora.

O `font-sans` existente já aponta para `var(--font-inter)` — apenas remover a referência ao Playfair.

---

## 3. Layout — `app/layout.tsx`

- Remover import e instanciação de `Playfair_Display`
- Remover `${playfair.variable}` do className do `<body>`
- `bg-slate-100` → `bg-[#F7F9FB]`

---

## 4. Navbar (`components/ui/Navbar.tsx`)

**Ambos os variants (landing e dashboard):**

| Elemento | Atual | Novo |
|---|---|---|
| Background | `bg-white border-b border-slate-200` | `bg-brand-navy` (sem borda) |
| Logo "VIGIL" | `text-slate-900` | `text-white` |
| Logo ".AI" | `text-sky-700` | `text-brand-teal` |
| Links nav (landing) | `text-slate-500 hover:text-slate-900` | `text-white/60 hover:text-white` |
| Botão CTA (landing) | `bg-slate-900 hover:bg-sky-700` | `bg-brand-lime text-brand-navy hover:bg-brand-lime/90` |
| Título dashboard (divisor) | `text-slate-500` | `text-white/70` |
| Divisor vertical | `bg-slate-200` | `bg-white/20` |
| Badge "Ao vivo" | `bg-green-50 border-green-200 text-green-700` | `bg-brand-teal/20 border-brand-teal/40 text-brand-teal` |
| Link "← Landing page" | `text-slate-400` | `text-white/50 hover:text-white/80` |

---

## 5. Landing Page (`app/page.tsx`)

### Hero
| Elemento | Atual | Novo |
|---|---|---|
| Eyebrow dot | `bg-sky-700` | `bg-brand-teal` |
| Eyebrow texto | `text-sky-700` | `text-brand-teal` |
| H1 principal | `font-playfair font-black text-5xl text-slate-900` | `font-extrabold text-5xl text-brand-text tracking-tight` |
| H1 span colorido | `text-sky-700` | `text-brand-teal` |
| Descrição | `text-slate-500` | `text-brand-muted` |
| Botão primário | `bg-slate-900 hover:bg-sky-700 rounded` | `bg-brand-navy hover:bg-brand-navy/90 rounded-[10px]` |
| Botão secundário | `border-slate-200 text-slate-500 rounded` | `bg-brand-lime text-brand-navy font-bold rounded-[10px]` |
| Stats números | `font-playfair font-black text-3xl text-slate-900` | `font-extrabold text-3xl text-brand-text tracking-tight` |
| Stats labels | `text-slate-400` | `text-brand-muted` |
| Form card border | `border-slate-200` | `border-brand-border` |
| Form card radius | `rounded-xl` | `rounded-[20px]` |
| Form card shadow | `shadow-md` | `shadow-[0_16px_40px_rgba(15,42,52,0.08)]` |

### Seção Trilhas
| Elemento | Atual | Novo |
|---|---|---|
| Background seção | `bg-slate-50` | `bg-brand-bg` |
| Card border-top | `border-t-sky-700` | `border-t-brand-teal` |
| Track label | `text-sky-700` | `text-brand-teal` |
| Card title | `text-slate-900` | `text-brand-text` |
| Card desc | `text-slate-500` | `text-brand-muted` |
| Card radius | `rounded-lg` | `rounded-[16px]` |

### Seção Público-Alvo
| Elemento | Atual | Novo |
|---|---|---|
| Linha decorativa | `bg-sky-700` | `bg-brand-teal` |
| Label seção | `text-sky-700` | `text-brand-teal` |
| H2 | `font-playfair font-black text-3xl text-slate-900` | `font-extrabold text-3xl text-brand-text tracking-tight` |
| Chips highlight | `border-sky-700 text-sky-700 bg-sky-50` | `border-brand-teal text-brand-teal bg-brand-teal/10` |
| Chips normais | `border-slate-200 text-slate-600` | `border-brand-border text-brand-muted` |

### Footer
| Elemento | Atual | Novo |
|---|---|---|
| Background | `bg-slate-900` | `bg-brand-navy` |

---

## 6. Dashboard — FunnelBoard (`components/dashboard/FunnelBoard.tsx`)

### KPI Strip
| Elemento | Atual | Novo |
|---|---|---|
| Background container | `bg-white border-b border-slate-200` | `bg-brand-navy` (sem borda) |
| Cards individuais | `bg-white border border-slate-200 [border-top-width:3px]` | `bg-white/[0.07] border border-white/[0.12] rounded-[12px]` |
| Label KPI | `text-slate-400` | `text-white/50` |
| Valor KPI (total) | `text-navy-700` / `text-slate-900` | `text-brand-teal` |
| Valor KPI (confirmação ok) | `text-green-600` | `text-brand-green` |
| Valor KPI (reuniões) | `text-amber-600` | `text-brand-lime` |
| Valor KPI (no-show) | `text-red-600` | `text-[#f87171]` |
| Sub-label KPI | `text-slate-400` | `text-white/40` |
| Meta text | `text-green-600` / `text-red-600` | `text-brand-green` / `text-[#f87171]` |
| font-playfair | sim | **remover** — usar `font-extrabold` |

### Tab Bar
| Elemento | Atual | Novo |
|---|---|---|
| Background | `bg-white border-b border-slate-200` | `bg-brand-navy border-b border-white/10` |
| Tab inativo | `text-slate-400 hover:text-slate-600` | `text-white/40 hover:text-white/70` |
| Tab ativo | `border-navy-700 text-navy-700` | `border-brand-teal text-brand-teal` |

### Middle Row (FunnelChart + ActivityFeed)
| Elemento | Atual | Novo |
|---|---|---|
| Background seção | `bg-slate-100` (herdado do body) | `bg-brand-bg` |
| Cards (FunnelChart, ActivityFeed) | `border-slate-200 rounded-lg` | `border-brand-border rounded-[16px]` |

### Kanban
| Elemento | Atual | Novo |
|---|---|---|
| Título "Funil de Leads" | `font-playfair font-extrabold text-xl text-slate-900` | `font-extrabold text-xl text-brand-text` |
| Subtítulo | `text-slate-400` | `text-brand-muted` |
| Coluna header (border-top REGISTERED/ENRICHED/ATTENDED) | `border-navy-700` | `border-brand-teal` |
| Col title color (navy) | `text-navy-700` | `text-brand-teal` |
| Col body radius | `rounded-b-lg` | `rounded-b-[12px]` |

---

## 7. LeadCard (`components/dashboard/LeadCard.tsx`)

| Elemento | Atual | Novo |
|---|---|---|
| Card background | `bg-slate-50` | `bg-white` |
| Card border hover | `hover:border-navy-700` | `hover:border-brand-teal` |
| Card radius | `rounded-md` | `rounded-[10px]` |
| Nome | `text-slate-900` | `text-brand-text` |
| Role | `text-slate-500` | `text-brand-muted` |
| Tag navy (C-level) | `bg-blue-50 text-blue-700` | `bg-brand-teal/10 text-brand-teal` |
| Tag green | `bg-green-50 text-green-700` | `bg-brand-green/10 text-brand-green` |
| Tag amber | `bg-amber-50 text-amber-700` | `bg-brand-lime/20 text-[#6b7a00]` |
| Signal dot green | `bg-green-500` | `bg-brand-green` |
| Signal dot amber | `bg-amber-500` | `bg-brand-lime` |

---

## 8. LeadDrawer (`components/dashboard/LeadDrawer.tsx`)

| Elemento | Atual | Novo |
|---|---|---|
| Overlay | `rgba(15,23,42,0.1)` inline | `rgba(15,42,52,0.2)` inline |
| Nome | `text-navy-950` | `text-brand-navy` |
| Stage bar REGISTERED/ENRICHED | `text-navy-700 bg-blue-50 border-blue-200` | `text-brand-teal bg-brand-teal/10 border-brand-teal/30` |
| Stage bar CONFIRMED | `text-green-700 bg-green-50 border-green-200` | `text-brand-green bg-brand-green/10 border-brand-green/30` |
| Stage bar MEETING | `text-amber-700 bg-amber-50 border-amber-200` | `text-[#6b7a00] bg-brand-lime/20 border-brand-lime/50` |
| Enrichment values | `text-navy-950` | `text-brand-text` |
| Msg border clicked/opened | `border-green-500 / border-green-300` | `border-brand-green` |
| Msg border sent | `border-navy-700` | `border-brand-teal` |
| Botão "Rodar Agente" | `bg-navy-950 hover:bg-navy-700` | `bg-brand-navy hover:bg-brand-teal` |

---

## 9. ConfigPanel (`components/dashboard/ConfigPanel.tsx`)

| Elemento | Atual | Novo |
|---|---|---|
| Card evento border-top | `border-t-navy-700` | `border-t-brand-teal` |
| Input focus | `focus:border-navy-700` | `focus:border-brand-teal` |
| Botão salvar | `bg-navy-950 hover:bg-navy-700` | `bg-brand-navy hover:bg-brand-teal` |
| Barra progresso | `bg-navy-700` | `bg-brand-teal` |
| Badge ok serviços | `bg-green-50 text-green-700` | `bg-brand-green/10 text-brand-green` |
| Badge warn | `bg-amber-50 text-amber-700` | `bg-brand-lime/20 text-[#6b7a00]` |
| Badge error | `bg-red-50 text-red-600` | `bg-red-50 text-red-500` |
| Job badge PENDING | `bg-blue-50 text-blue-700` | `bg-brand-teal/10 text-brand-teal` |
| Job badge DONE | `bg-green-50 text-green-700` | `bg-brand-green/10 text-brand-green` |
| Job badge RUNNING | `bg-amber-50 text-amber-700` | `bg-brand-lime/20 text-[#6b7a00]` |
| Botão ação job | `text-navy-700 hover:border-navy-700` | `text-brand-teal hover:border-brand-teal` |
| Job lead name | `text-navy-950` | `text-brand-text` |
| Título tabela | `text-navy-950` | `text-brand-text` |
| Verificar botão hover | `hover:border-navy-700 hover:text-navy-700` | `hover:border-brand-teal hover:text-brand-teal` |

---

## 10. FunnelChart (`components/dashboard/FunnelChart.tsx`)

| Elemento | Atual | Novo |
|---|---|---|
| Cor barra REGISTERED/ENRICHED/ATTENDED | `#0369a1` | `#48C2C5` (brand.teal) |
| Cor barra CONFIRMED | `#16a34a` | `#59BD75` (brand.green) |
| Cor barra MEETING_SCHEDULED | `#d97706` | `#DDEB4F` (brand.lime) |
| Cor barra CONVERTED | `#059669` | `#59BD75` (brand.green) |
| Cor barra NO_SHOW | `#dc2626` | `#f87171` |
| Fundo barra | `bg-slate-100` | `bg-brand-bg` |
| rateColor verde | `text-green-600` | `text-brand-green` |
| rateColor âmbar | `text-amber-600` | `text-[#6b7a00]` |
| rateColor vermelho | `text-red-500` | `text-red-400` |
| Texto rodapé | `text-slate-700` bold, `text-slate-400` | `text-brand-text` bold, `text-brand-muted` |
| ✓ meta | `text-green-600` | `text-brand-green` |
| abaixo da meta | `text-red-500` | `text-red-400` |

---

## 11. ActivityFeed (`components/dashboard/ActivityFeed.tsx`)

| Elemento | Atual | Novo |
|---|---|---|
| Dot clicked | `bg-amber-500` | `bg-brand-lime` |
| Dot opened | `bg-green-500` | `bg-brand-green` |
| Dot sent | `bg-navy-700` | `bg-brand-teal` |
| Lead name | `text-slate-800` | `text-brand-text` |
| Texto evento | `text-slate-500` | `text-brand-muted` |
| Tempo relativo | `text-slate-300` | `text-brand-border` |

---

## 12. FilterBar (`components/dashboard/FilterBar.tsx`)

| Elemento | Atual | Novo |
|---|---|---|
| Input focus | `focus:border-navy-700` | `focus:border-brand-teal` |
| Chip setor ativo | `bg-blue-50 border-navy-700 text-navy-700` | `bg-brand-teal/10 border-brand-teal text-brand-teal` |
| Chip setor hover | `hover:border-slate-300` | `hover:border-brand-border` |
| Chip decisores ativo | `bg-blue-50 border-navy-700 text-navy-700` | `bg-brand-teal/10 border-brand-teal text-brand-teal` |
| Chip selecionado dropdown | `text-navy-700 font-semibold` | `text-brand-teal font-semibold` |

---

## 13. Login (`app/login/page.tsx`)

| Elemento | Atual | Novo |
|---|---|---|
| Background página | `bg-slate-100` | `bg-brand-bg` |
| Card radius | `rounded-xl` | `rounded-[20px]` |
| Card shadow | `shadow-sm` | `shadow-[0_16px_40px_rgba(15,42,52,0.08)]` |
| Logo ".AI" | `text-sky-700` | `text-brand-teal` |
| H1 | `font-playfair font-bold text-2xl text-slate-900` | `font-bold text-2xl text-brand-text` |
| Input focus | `focus:border-sky-700` | `focus:border-brand-teal` |
| Botão | `bg-slate-900 hover:bg-sky-700` | `bg-brand-navy hover:bg-brand-teal rounded-[10px]` |

---

## 14. Deletion Confirm (`app/deletion-confirm/page.tsx`)

| Elemento | Atual | Novo |
|---|---|---|
| Background | `bg-slate-100` | `bg-brand-bg` |
| Card radius | `rounded-xl` | `rounded-[20px]` |
| Logo ".AI" | `text-sky-700` | `text-brand-teal` |
| H1 | `font-playfair font-bold text-xl text-slate-900` | `font-bold text-xl text-brand-text` |
| Link email | `text-sky-700` | `text-brand-teal` |
| Texto sucesso | `text-green-700` | `text-brand-green` |

---

## 15. RegistrationForm e ChatbotWidget

### RegistrationForm (`components/landing/RegistrationForm.tsx`)
- Inputs: `focus:border-*` → `focus:border-brand-teal`
- Botão submit: `bg-slate-900 hover:bg-sky-700` → `bg-brand-navy hover:bg-brand-teal rounded-[10px]`
- Links e destaques `text-sky-700` → `text-brand-teal`

### ChatbotWidget (`components/landing/ChatbotWidget.tsx`)
- Botão bolha: `bg-*-navy` / atual → `bg-brand-navy hover:bg-brand-teal`
- Header chat: `bg-brand-navy` (já está em navy — mantém)
- Mensagens usuário: atual purple/blue → `bg-brand-teal`
- Mensagens assistente: manter `bg-[#f1f5f9]`

---

## 16. Restrições e Decisões

- **Playfair Display removido completamente** — `font-playfair` deixa de existir. Todos os `font-playfair` substituídos por `font-extrabold` ou `font-bold` Inter com `tracking-tight` e `letter-spacing: -0.02em`.
- **`navy-700` e `navy-950` aposentados** — substituídos por `brand.teal` e `brand.navy` respectivamente. Todos os usos migram.
- **`sky-700`, `sky-50`, `sky-200`, `sky-300` eliminados** — eram a cor accent do design anterior, substituídos por `brand-teal`.
- **Lime `#DDEB4F` como CTA de destaque** — usado para botão secundário na landing e botão accent em geral. Nunca usado como cor de texto sobre fundo branco (contraste insuficiente — usar `text-brand-navy` ou `text-[#6b7a00]` sobre lime).
- **Amber eliminado** — `amber-500`, `amber-600` substituídos por `brand-lime` nos dots e badges.
- **`slate-900` nos footers** → `bg-brand-navy` (mesma intenção, nova cor).
- **Toda lógica de negócio preservada** — zero mudança em endpoints, estados, hooks ou API calls.

---

*Documento gerado em 2026-05-30 — aprovado em sessão de brainstorming com o usuário*
