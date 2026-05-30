# Vigil Summit Agent

> **Agente autônomo de IA** que gerencia o funil completo de um evento B2B de cibersegurança — da inscrição na landing page até a reunião comercial agendada.

---

## Stack

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Claude_Sonnet-4.6-D97757?style=flat&logo=anthropic&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-14-000000?style=flat&logo=nextdotjs&logoColor=white" />
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=flat&logo=typescript&logoColor=white" />
  <img src="https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=flat&logo=supabase&logoColor=white" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-3-06B6D4?style=flat&logo=tailwindcss&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Resend-Email-000000?style=flat&logo=gmail&logoColor=white" />
  <img src="https://img.shields.io/badge/Apollo.io-Enrichment-4B75FF?style=flat&logo=apollo&logoColor=white" />
</p>

---

## O que é

O **Vigil Summit** é um evento presencial de cibersegurança para CISOs, CTOs e líderes de TI (120 vagas). Este sistema automatiza completamente o funil comercial do evento usando um **agente Claude Sonnet** com tool use nativo:

```
Inscrição → Enriquecimento → Engajamento pré-evento → Follow-up pós-evento → Reunião agendada
```

O agente raciocina sobre o estado de cada lead, decide autonomamente a próxima ação e persiste seu histórico de decisões para auditoria.

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND  (Next.js 14)                     │
│                                                              │
│   Landing Page                    Dashboard (protegido)      │
│   ├─ Formulário LGPD              ├─ Funil em tempo real     │
│   └─ Chatbot Claude Haiku         └─ Supabase Realtime       │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                   BACKEND  (FastAPI)                         │
│                                                              │
│   Agente Orquestrador (Claude Sonnet)                        │
│   ├─ enrich_lead()       → Apollo.io                        │
│   ├─ send_pre_event_msg() → Resend (email)                   │
│   ├─ check_engagement()  → Supabase                         │
│   ├─ send_whatsapp()     → Evolution API                     │
│   ├─ send_followup()     → Resend                            │
│   ├─ schedule_meeting()  → Cal.com                           │
│   ├─ schedule_job()      → APScheduler                      │
│   └─ update_lead_stage() → Supabase                         │
│                                                              │
│   APScheduler  │  Webhooks Resend  │  POST /api/leads        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Supabase (PostgreSQL)                       │
│   leads · messages · lead_enrichment · lead_memory           │
│   scheduled_jobs · events · agent_locks                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Funcionalidades

### Agente Autônomo
- Loop de raciocínio Claude Sonnet com até 10 iterações por trigger
- Mutex via `agent_locks` — evita race condition entre execuções paralelas
- Memória persistida por lead em `lead_memory` (histórico de decisões auditável)
- Retry exponencial automático para jobs com falha (5 → 10 → 20 min)

### Funil de 8 estágios
| Estágio | Descrição |
|---|---|
| `REGISTERED` | Lead inscrito, aguarda enriquecimento |
| `ENRICHED` | Perfil enriquecido via Apollo.io |
| `CONFIRMED` | Presença confirmada |
| `ATTENDED` | Check-in realizado no evento |
| `NO_SHOW` | Não compareceu |
| `MEETING_SCHEDULED` | Reunião agendada via Cal.com |
| `CONVERTED` | Oportunidade comercial aberta |
| `OPTED_OUT` | Lead removido (direito LGPD) |

### Régua de comunicação
**Pré-evento:** `D+0` boas-vindas personalizadas → `T-21` aquecimento por setor → `T-14` confirmação → `T-7` agenda → `T-3` logística → `D` lembrete

**Pós-evento (ATTENDED):** `D+1` agradecimento → `D+3` follow-up com demo → `D+5` WhatsApp (se opt-in) → `D+14` break-up

**Pós-evento (NO_SHOW):** `D+1` "sentimos sua falta" → `D+5` demo privada → `D+10` última tentativa

### Conformidade LGPD
- Consentimento explícito obrigatório com registro de `consent_at` + `consent_ip`
- Endpoint `POST /api/leads/deletion-request` — anonimização em cascata por todas as tabelas
- Opt-in separado para WhatsApp
- Agente nunca envia WhatsApp sem `whatsapp_consent_at`

---

## Estrutura do projeto

```
vigil-summit-agent/
├── backend/
│   ├── app/
│   │   ├── agent/          # Orchestrator, tools, prompts, memory
│   │   ├── api/            # leads, events, webhooks
│   │   ├── db/             # Supabase client, Pydantic models
│   │   ├── scheduler/      # APScheduler runner + jobs
│   │   └── services/       # Resend email templates
│   ├── migrations/         # SQL schema completo
│   ├── tests/              # 20 testes (agent, scheduler, API)
│   ├── scripts/            # seed_personas.py
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── api/chat/       # SSE endpoint Claude Haiku
│   │   ├── api/auth/       # Login dashboard (SHA-256 cookie)
│   │   ├── dashboard/      # Funil Kanban
│   │   └── login/
│   ├── components/
│   │   ├── landing/        # RegistrationForm + ChatbotWidget
│   │   └── dashboard/      # FunnelBoard + LeadCard
│   └── Dockerfile
├── docker-compose.yml
└── docs/
    └── superpowers/
        └── specs/          # Design spec completo
```

---

## Decisões técnicas

| Decisão | Escolha | Motivo |
|---|---|---|
| LLM | Claude Sonnet 4.6 (Anthropic SDK nativo) | Tool use com raciocínio auditável; preferência do avaliador |
| Agendamento | `AsyncIOScheduler` (APScheduler) | Integra com event loop do FastAPI sem `asyncio.run()` |
| I/O não-bloqueante | `asyncio.to_thread()` em todas as chamadas Supabase | SDK Python do Supabase é síncrono |
| Enriquecimento | Apollo.io People Match API | Melhor cobertura B2B brasileira vs Clearbit |
| Email | Resend + webhooks de abertura/clique | Tracking nativo de engajamento para decisões do agente |

---

## Como rodar localmente

### Pré-requisitos
- Python 3.11+, Node.js 20+, Docker

### Backend

```bash
cd backend
cp .env.example .env          # preencher com suas credenciais
python -m venv venv
venv\Scripts\activate         # Windows
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env.local    # preencher com suas credenciais
npm install
npm run dev
```

### Testes

```bash
cd backend
pytest tests/ -v
# 20 passed
```

### Docker Compose (produção local)

```bash
# Criar .env na raiz com as variáveis do docker-compose.yml
docker compose up --build
```

---

## Deploy (Dokploy)

1. Conectar repositório no Dokploy
2. Selecionar `docker-compose.yml` como método de deploy
3. Configurar variáveis de ambiente dos arquivos `backend/.env.example` e `frontend/.env.example`
4. Executar `backend/migrations/001_initial.sql` no Supabase SQL Editor
5. Habilitar Realtime para a tabela `leads` no painel Supabase
6. Configurar webhook Resend: `POST https://seu-dominio/api/webhooks/resend`

---

## Variáveis de ambiente

### Backend (`backend/.env.example`)
| Variável | Obrigatória | Descrição |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | API key Anthropic |
| `SUPABASE_URL` | ✅ | URL do projeto Supabase |
| `SUPABASE_KEY` | ✅ | Service role key |
| `RESEND_API_KEY` | ✅ | API key Resend |
| `API_KEY` | ✅ | Chave para endpoints operacionais (`X-API-Key`) |
| `CORS_ORIGINS` | ✅ | URL do frontend (separar múltiplos por vírgula) |
| `APOLLO_API_KEY` | — | Enriquecimento de leads (gracioso sem ela) |
| `EVOLUTION_API_URL` | — | WhatsApp via Evolution API |
| `CAL_API_KEY` | — | Agendamento via Cal.com |

### Frontend (`frontend/.env.example`)
| Variável | Descrição |
|---|---|
| `NEXT_PUBLIC_API_URL` | URL do backend |
| `NEXT_PUBLIC_API_KEY` | Mesma chave do `API_KEY` do backend |
| `NEXT_PUBLIC_SUPABASE_URL` | URL do Supabase (igual ao backend) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Chave anon (pública) do Supabase |
| `DASHBOARD_PASSWORD` | Senha para acessar o dashboard |
| `ANTHROPIC_API_KEY` | API key Anthropic (server-side, chatbot) |

---

## Personas de demonstração

```bash
cd backend
python scripts/seed_personas.py
```

Cria 3 leads sintéticos cobrindo todos os branches do funil:

| Persona | Cargo | Empresa | Cenário |
|---|---|---|---|
| Maria Santos | CISO | Banco Itararé | `ATTENDED` → follow-up comercial |
| Carlos Mendes | CTO | TechManufatura SA | `NO_SHOW` → reengajamento |
| Pedro Alves | Diretor de TI | Clínica São Paulo | `REGISTERED` → régua completa |

---

<p align="center">
  Construído com <a href="https://www.anthropic.com">Anthropic Claude</a> · <a href="https://fastapi.tiangolo.com">FastAPI</a> · <a href="https://nextjs.org">Next.js</a> · <a href="https://supabase.com">Supabase</a>
</p>
