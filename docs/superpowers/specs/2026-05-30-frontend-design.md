# Vigil Summit — Frontend Design Spec

**Data:** 2026-05-30
**Projeto:** Case AI Engineer — Pareto × Vigil.AI
**Escopo:** Redesign completo do frontend Next.js — Landing Page, Dashboard, Login, Chatbot Widget

---

## 1. Design System

### Paleta de cores

| Token | Hex | Uso |
|---|---|---|
| `navy-950` | `#0f172a` | Navbar, botões primários, footer, texto principal |
| `navy-700` | `#0369a1` | Accent — links, badges, bordas de destaque, eyebrow dots |
| `slate-100` | `#f1f5f9` | Background da página (fundo suave) |
| `slate-50` | `#f8fafc` | Background de cards internos |
| `white` | `#ffffff` | Cards, navbar, hero background |
| `slate-200` | `#e2e8f0` | Bordas, divisores |
| `slate-400` | `#94a3b8` | Labels, texto secundário |
| `slate-600` | `#475569` | Corpo de texto, subtítulos |
| `green-600` | `#16a34a` | KPI confirmação, tags "confirmado" |
| `amber-600` | `#d97706` | KPI reuniões, tags "decisor", "demo agendada" |
| `red-600` | `#dc2626` | KPI no-show, tags "no-show" |
| `emerald-600` | `#059669` | Coluna "Convertidos" |

### Tipografia

| Uso | Fonte | Peso | Tamanho referência |
|---|---|---|---|
| Títulos de página (H1, H2) | Playfair Display | 900 | 48–52px landing, 18–22px dashboard |
| Títulos de seção | Playfair Display | 700–800 | 28–32px |
| Números KPI | Playfair Display | 900 | 36px |
| Corpo, labels, botões, inputs | Inter | 400–700 | 11–17px |
| Eyebrow / badge text | Inter | 700 | 10–12px, letter-spacing 1.5px |

**Regra:** Playfair Display só em headings e números de destaque. Todo texto funcional (labels, botões, inputs, nav links, body) usa Inter.

### Espaçamento e bordas

- Border radius padrão: `4px` (botões, inputs) · `8px` (cards) · `12px` (cards grandes)
- Border padrão: `1px solid #e2e8f0`
- Accent border top (colunas kanban, KPI cards): `3px solid <cor-do-stage>`
- Box shadow de hover: `0 2px 8px rgba(3,105,161,0.08)`
- Padding de página: `32px` horizontal

---

## 2. Landing Page (`/`)

### Estrutura de seções (top → bottom)

```
┌─────────────────────────────────────┐
│  NAVBAR (sticky, white)             │
├─────────────────────────────────────┤
│  HERO (white, 2 colunas)            │
│  ├── esquerda: copy + stats         │
│  └── direita: form de inscrição     │
├─────────────────────────────────────┤
│  TRILHAS (slate-100, 3 cards)       │
├─────────────────────────────────────┤
│  PÚBLICO-ALVO (white, chips)        │
├─────────────────────────────────────┤
│  FOOTER (navy-950)                  │
└─────────────────────────────────────┘
```

### Navbar

- Background: `white`, `border-bottom: 1px solid #e2e8f0`, `position: sticky top-0 z-50`
- Logo: `VIGIL` em navy-950 + `.AI` em navy-700, Inter 900
- Links: Agenda · Speakers · Local — Inter 500, slate-600
- CTA: botão primário navy → `#inscricao` (scroll suave)
- Altura: `64px`

### Hero

- Background: `white`
- Grid: `grid-cols-2 gap-16` em desktop, stack em mobile
- **Coluna esquerda:**
  - Eyebrow: dot navy-700 + texto uppercase Inter 700 letra-spacing 2px (`"SÃO PAULO · 15 AGO 2026 · PRESENCIAL"`)
  - H1: Playfair Display 900, `52px`, `letter-spacing: -1.5px`
    - "Vigil Summit" em navy-950
    - "Segurança para a Era da IA" em navy-700
  - Descrição: Inter 400, `17px`, slate-600, `max-w-xl`
  - Botões: primário (navy-950) + secundário (borda slate-200)
  - Stats row: 3 números (120 vagas · 8h conteúdo · C-level) com Playfair Display 900
- **Coluna direita (form card):**
  - Card branco, `border: 1px solid #e2e8f0`, `border-radius: 12px`, shadow suave
  - Título: Inter 800, H2 pequeno ("Garanta sua vaga")
  - Subtítulo: "Inscrições limitadas a 120 participantes."
  - Inputs: `border: 1.5px solid #e2e8f0`, focus `border-color: #0369a1`
  - Botão: navy-950 full-width
  - Texto LGPD: Inter 400, 11px, slate-400 — com link para política de privacidade
  - Manter toda lógica existente de `RegistrationForm.tsx` (companion, consent, duplicate check)

### Seção Trilhas

- Background: `#f8fafc`
- 3 cards com `border-top: 3px solid #0369a1`
- Label: "Track 01/02/03" em navy-700, Inter 700, uppercase
- Título: Inter 800, navy-950
- Descrição: Inter 400, slate-600

### Seção Público-Alvo

- Background: `white`
- Section label: linha horizontal navy-700 + texto uppercase navy-700
- Título: Playfair Display 800
- Chips: `border: 1.5px solid #e2e8f0` para cargos gerais; `border-color: #0369a1; background: #f0f9ff; color: #0369a1` para CISOs e CTOs (highlight)

### Footer

- Background: `navy-950`
- Texto: slate-400 (texto secundário) + white (nome do evento)
- Link política de privacidade: `#38bdf8` (azul claro sobre fundo escuro)

---

## 3. Dashboard (`/dashboard`)

### Estrutura

```
┌─────────────────────────────────────┐
│  TOPBAR (white, sticky)             │
├─────────────────────────────────────┤
│  KPI STRIP (white, 4 cards)         │
├─────────────────────────────────────┤
│  KANBAN (slate-100, scroll-x)       │
│  · 7 colunas                        │
│  · cards ricos por lead             │
└─────────────────────────────────────┘
```

### Topbar

- Mesmo padrão da navbar da landing: `white`, sticky, `56px`
- Esquerda: logo `VIGIL.AI` + divisor vertical + título Playfair Display ("Vigil Summit — Funil de Leads")
- Direita:
  - Badge "● Ao vivo" — background `#f0fdf4`, border `#bbf7d0`, texto `#16a34a`, dot animado com pulse
  - Link "← Landing page"
- **Sem mencionar "Supabase Realtime" ou qualquer tecnologia interna**

### KPI Strip

4 cards lado a lado (`grid-cols-4`), cada um com `border-top: 3px solid <cor>`:

| Card | Cor | Valor | Sub | Meta |
|---|---|---|---|---|
| Total inscritos | navy-700 | número total | "de 120 vagas" | — |
| Taxa de confirmação | green-600 | `X%` | "meta: acima de 70%" | texto "X% abaixo da meta" em red-600 se < 70%; "X% acima da meta" em green-600 se ≥ 70% |
| Reuniões agendadas | amber-600 | número | "via Cal.com" | delta semana |
| No-show | red-600 | número | "reengajamento ativo" | "X com email aberto" |

- Número principal: Playfair Display 900, `36px`, cor do accent
- Label: Inter 600, `10px`, uppercase, slate-400
- Sub/meta: Inter 400–600, `11px`

### Kanban — Colunas

7 colunas na ordem do funil:

| Stage | Cor accent | Label |
|---|---|---|
| REGISTERED | navy-700 | Inscritos |
| ENRICHED | navy-700 | Enriquecidos |
| CONFIRMED | green-600 | Confirmados |
| ATTENDED | navy-700 | Presentes |
| NO_SHOW | red-600 | No-show |
| MEETING_SCHEDULED | amber-600 | Reunião agendada |
| CONVERTED | emerald-600 | Convertidos |

- Largura da coluna: `220px`, `flex-shrink: 0`
- Header: `border-top: 3px solid <cor>`, título uppercase Inter 700 com cor do stage, badge de contagem
- Body: fundo branco, padding 8px, `min-height: 100px`
- Coluna "Presentes": mensagem de placeholder "Dia do evento · DD Mmm"

### Lead Card (rico)

Cada card exibe:
1. **Nome** — Inter 700, 12px, navy-950
2. **Cargo enriquecido · Empresa · Tamanho** — Inter 400, 10px, slate-600 (dados do Apollo.io via `lead_enrichment`)
3. **Tags** — máximo 3:
   - `C-level` (navy tag) se cargo for CISO/CTO/VP/CEO/Diretor
   - Setor (slate tag): financeiro · manufatura · saúde · tecnologia · etc.
   - Status tag (green/amber/red): confirmado · decisor · no-show · demo agendada
4. **Sinal do agente** — linha separada por borda top, dot colorido + texto descrevendo último ato:
   - Verde: email aberto, confirmou presença, Cal.com clicado
   - Âmbar: email enviado mas não aberto, aguardando enriquecimento, VIP Briefing enviado
   - Cinza: inscrito recentemente, sem ação ainda
   - Vermelho: no-show, múltiplos emails sem resposta

**Hover:** `border-color: #0369a1`, shadow suave, background white

**Fonte dos dados do sinal:** último registro de `messages` (direction='OUT', ordered by sent_at DESC) + `opened_at`/`clicked_at` + `stage` do lead. Construído no componente a partir dos dados do `/api/leads`.

---

## 4. Login (`/login`)

Mesma identidade visual do site — não uma página genérica:

- Background: `#f1f5f9` (slate-100, igual ao resto do site)
- Card centralizado: branco, `border: 1px solid #e2e8f0`, `border-radius: 12px`, shadow suave
- Logo no topo do card: `VIGIL.AI` com o mesmo estilo da navbar
- Título: Playfair Display 800 ("Acesso ao Dashboard")
- Subtítulo: Inter 400, slate-500 ("Restrito à equipe Vigil.AI")
- Input de senha: mesmo estilo dos inputs da landing (borda slate, focus navy-700)
- Botão: navy-950 full-width, Inter 700
- Erro: Inter 400, red-600, `text-sm`

---

## 5. Chatbot Widget

Manter o comportamento atual (bolha flutuante no canto inferior direito, janela expansível).
Apenas restyle para identidade navy:

- Botão da bolha: `background: #0f172a` (navy-950), hover `#0369a1`
- Ícone: substituir emoji 💬 por ícone SVG de chat (mais profissional)
- Janela do chat:
  - Header: background navy-950, título Inter 600 white ("Assistente Vigil Summit"), subtítulo "Resposta imediata" slate-400
  - Mensagens do assistente: `background: #f1f5f9`, texto slate-700
  - Mensagens do usuário: `background: #0369a1` (navy-700, não mais roxo), texto white
  - Input: border slate-200, focus navy-700
  - Botão enviar: navy-950, hover navy-700
- Border do popup: `border: 1px solid #e2e8f0` (sem mais border-gray-700)
- Background do popup: white (sem mais gray-900)

---

## 6. Componentes a criar / modificar

| Arquivo | Ação | O que muda |
|---|---|---|
| `app/globals.css` | modificar | importar Playfair Display + Inter do Google Fonts; definir CSS variables de cor |
| `tailwind.config.ts` | modificar | adicionar cores customizadas do design system (`navy`, `slate` extendidos) |
| `app/page.tsx` | reescrever | nova estrutura de seções (Navbar, Hero 2-col, Trilhas, Público, Footer) |
| `app/layout.tsx` | modificar | adicionar font imports, atualizar metadata |
| `app/login/page.tsx` | reescrever | identidade visual navy slate |
| `app/dashboard/page.tsx` | modificar | remover texto "Supabase Realtime", ajustar layout wrapper |
| `components/landing/RegistrationForm.tsx` | modificar | restyle inputs/botão para navy slate; manter toda lógica |
| `components/landing/ChatbotWidget.tsx` | modificar | restyle navy (cores, ícone SVG); manter toda lógica de streaming |
| `components/dashboard/FunnelBoard.tsx` | reescrever | KPI strip + kanban restyle + busca de dados enriquecidos |
| `components/dashboard/LeadCard.tsx` | reescrever | card rico com tags, sinal do agente, dados do Apollo.io |
| `components/ui/Navbar.tsx` | criar | componente compartilhado entre landing e dashboard |
| `app/deletion-confirm/page.tsx` | modificar | restyle para identidade visual navy slate (card centralizado, mesma estrutura do login) |

---

## 7. Restrições e decisões

- **Sem mencionar tecnologias internas na UI** (Supabase, Apollo.io, Resend, Cal.com)
- **Sem roxo** em nenhuma página — toda cor accent migra de purple-* para navy-700 (`#0369a1`) ou navy-950 (`#0f172a`)
- **Playfair Display apenas em headings e números KPI** — nunca em labels, botões ou inputs
- **Toda lógica de negócio existente é preservada** — apenas o visual muda. Nenhum endpoint, hook ou estado é alterado
- **Identidade visual consistente em todas as páginas** — login, landing, dashboard e chatbot usam os mesmos tokens de cor e fonte
- **Mobile:** o hero da landing empilha as colunas. O kanban mantém scroll horizontal

---

*Documento gerado em 2026-05-30 — aprovado em sessão de brainstorming com o usuário*
