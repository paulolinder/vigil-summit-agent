# Documentação do Projeto no Notion — Design

**Data:** 2026-06-01
**Status:** Aprovado para planejamento
**Contexto:** O case da Pareto exige um **documento técnico** com 6 seções obrigatórias.
A ausência de documentação implica **reprovação automática** (`docs/03-requisitos-tecnicos.md`).
A documentação será criada no **Notion** (MCP configurado), em PT-BR, e compartilhada via
link público.

---

## 1. Objetivo

Produzir uma documentação clara, acessível e completa do Vigil Summit Agent no Notion,
que: (a) cubra os **6 entregáveis obrigatórios** do case; (b) permita que o avaliador
da Pareto **suba e teste** o projeto ponta-a-ponta; (c) seja suficiente para **outro
engenheiro continuar o trabalho** (critério de avaliação); e (d) explique as decisões
de produto/técnicas com racional honesto, incluindo o que é demo vs produção.

---

## 2. Decisões travadas (do brainstorming)

1. **Estrutura:** hub (página-mãe) + 8 sub-páginas por tema.
2. **Local no Notion:** ancorado na página **Vigil-Ai** do usuário
   (ID `3727dbb3ad7d8069bdebe7a00b652136`).
3. **Idioma/tom:** PT-BR, técnico mas didático (engenheiro continua o trabalho; avaliador
   de negócio acompanha).
4. **Diagramas:** Mermaid (code blocks com linguagem `mermaid`) para arquitetura, funil e
   sequência do webhook.
5. **Fase Presença/QR:** descrição honesta — separar o que **já existe** (endpoint
   `/checkin`, webhook, avanço automático de etapa, botão no dashboard) do que é **camada
   de UX planejada** (QR no evento → página de check-in por email).
6. **Compartilhamento:** o MCP cria as páginas; o **toggle de link público é manual** (o
   usuário ativa na página-mãe). A spec documenta o passo a passo.

---

## 3. Ferramenta e restrições do MCP do Notion

- O MCP cria páginas sob um **pai** (a página Vigil-Ai). Sub-páginas são criadas com
  `parent` = a página-mãe criada no passo anterior.
- **Não** é possível ativar "compartilhar via link público" pelo MCP — é um toggle de
  permissão na UI do Notion. A documentação final instrui o usuário a ativá-lo na
  página-mãe (sub-páginas herdam o acesso).
- Conteúdo é enviado como blocos Notion (headings, parágrafos, listas, tabelas, code
  blocks). Mermaid vai em code block com linguagem `mermaid`.
- A criação é **incremental e idempotente na prática**: criar a mãe primeiro, capturar o
  ID, depois cada sub-página. Se uma sub-página falhar, recriar só ela.

---

## 4. Estrutura das páginas

### Página-mãe: `Vigil Summit Agent — Documentação`
- **Resumo executivo** (1–2 parágrafos): o que é o sistema, o problema de negócio
  (funil de evento B2B, no-show, conversão).
- **Links:** demo em produção (`paulolinder.com.br`), repositório GitHub.
- **Índice navegável:** links para as 8 sub-páginas com 1 linha de descrição cada.
- **Aviso de acesso:** menção a `ramon@pareto.io` para acesso de teste.

### Sub-página 1 — Arquitetura da Solução *(Entregável 1)*
- Diagrama Mermaid das **camadas**: Frontend (Next.js: landing+form+chatbot, dashboard) →
  Backend (FastAPI: agente orquestrador, APScheduler, webhooks, API) → Serviços
  (`services/`: enrichment, whatsapp, meeting, email) → Banco (Supabase/Postgres) →
  Integrações externas (LLM, Resend, Apollo, Cal.com, Evolution).
- Diagrama Mermaid do **funil completo**: REGISTERED → ENRICHED → CONFIRMED → **ATTENDED
  (Presença)** / NO_SHOW → MEETING_SCHEDULED → CONVERTED, com OPTED_OUT como saída.
- Diagrama Mermaid de **sequência** do check-in/webhook (ver sub-página 8 p/ detalhe).
- **Fluxo de dados** entre componentes (prosa).
- **Onde cada fase do funil encaixa** (Captação/Enriquecimento/Engajamento/Follow-up)
  mapeada aos componentes.

### Sub-página 2 — Stack Tecnológico Justificado *(Entregável 2)*
Tabela tecnologia → justificativa:
- **LLM:** preferência **Anthropic (Claude)** pelo SDK e tool-use/raciocínio estruturado;
  **decisão de usar OpenAI** no momento (sem chave Anthropic disponível), com o sistema
  **multi-provider** (`llm/provider.py`) pronto para alternar só trocando a env key — a
  OpenAI (gpt-4.1) "se saiu muito bem" na configuração atual.
- **Framework de agente:** SDK nativo (loop de tool-use próprio no orquestrador), não
  LangChain/CrewAI — justificativa de controle e simplicidade.
- **Banco:** Supabase/Postgres (RLS, Realtime, RPCs atômicas).
- **Orquestração:** APScheduler (AsyncIOScheduler) para a régua temporal.
- **Canais:** email (Resend, real) como canal principal justificado para executivos B2B;
  WhatsApp (Evolution) como canal complementar.
- **Deploy:** backend Railway, frontend Vercel/Dokploy, banco Supabase.

### Sub-página 3 — Réguas de Comunicação *(Entregável 3)*
- **Régua pré-evento:** welcome → confirmation_request (T-14) → warmup/confirmation_followup
  (T-10) → vip_briefing/agenda (T-7) → agenda (T-3) → logistics (T-1) → day_reminder (T-0),
  com gatilhos, condições (`skip_if_opened`, `only_if_stage=CONFIRMED`) e timing.
- **Régua pós-evento:** ATTENDED → thank_you + follow-ups (D+3/D+7/D+14); NO_SHOW →
  no_show_missed + reengajamento.
- **Branching por engajamento:** clique no confirmation_request → CONFIRMED (decisão do
  agente).
- **Personalização dinâmica (ponto-chave):** os emails **NÃO são fixos/padrão** — o corpo
  é montado a partir do **enriquecimento do lead** (cargo, setor, porte, sinais de
  segurança). Mostrar **um exemplo personalizado por régua** (ex.: CISO de banco vs.
  gestor de TI de varejo), demonstrando o uso do dado enriquecido.

### Sub-página 4 — Estratégia de Dados e LGPD *(Entregável 4)*
- **Coleta:** formulário público com consentimento explícito (LGPD); campos coletados.
- **Armazenamento:** tabelas `leads`, `lead_enrichment`, `messages`, `lead_memory`,
  `scheduled_jobs` — modelo de dados resumido.
- **Enriquecimento na prática:** Apollo.io (real) ↔ mock determinístico por email
  ("Apollo-shaped"); como o dado enriquecido alimenta a personalização e a memória do agente.
- **LGPD:** consentimento + IP + versão; exclusão em **dois passos** (token por email →
  confirmação); **anonimização** (email→uuid, limpeza de PII e dados derivados); retenção
  de tokens minimizada.

### Sub-página 5 — Decisões Estratégicas e Racional *(Entregável 5)*
As **3 principais decisões** + alternativas descartadas + referências:
1. **Agente autônomo (tool-use) vs. scripts/workflow rígido** — por que o agente decide,
   não executa roteiro fixo (critério central da Pareto).
2. **LLM: Anthropic (preferido) vs. OpenAI (usado agora)** — racional do multi-provider e
   por que OpenAI no momento; arquitetura pronta para Claude.
3. **Email como canal principal** — justificativa pelo perfil executivo B2B vs.
   WhatsApp/Telegram.
(Mencionar mocks/modo demo como decisão de testabilidade.)

### Sub-página 6 — Plano dos Primeiros 5 Dias *(Entregável 6)*
- Dia a dia: o que provisionar primeiro (banco/auth → captação → enriquecimento →
  régua → follow-up), qual fase atacar primeiro e por quê.

### Sub-página 7 — Como Rodar o Projeto
- **Pré-requisitos** (Docker, ou Python 3.11 + Node 20).
- **Subir com Docker Compose** (caminho recomendado) e/ou **manual** (backend
  `uvicorn`, frontend `npm run dev`).
- **Variáveis de ambiente:** o que é obrigatório (Supabase, uma chave de LLM, Resend) e
  o que é opcional (Apollo/Cal/Evolution → ativam mock se vazias).
- **Migrações Supabase** a aplicar (incl. `003_demo_mode`, `004_fix_stage_transition`).
- Nota de deploy: backend Railway exige redeploy manual; frontend auto-deploy.

### Sub-página 8 — Guia de Teste & Modo Demo
- **Acesso:** login do dashboard; `ramon@pareto.io` para acesso temporário.
- **Fluxo ponta-a-ponta** (modo demo, `DEMO_FAST_FORWARD`): cadastrar lead → ENRICHED +
  welcome → régua comprimida → simular engajamento → CONFIRMED → check-in → follow-up →
  MEETING_SCHEDULED.
- **Por que dados fictícios:** facilitar entendimento e teste sem chaves pagas. **Sistema
  pronto para variáveis reais:** basta preencher as chaves no `.env` e o mesmo código usa
  as APIs reais (mesmo padrão do multi-provider de LLM). O que é sempre real (email, LLM)
  vs. mockável (Apollo, Cal.com, WhatsApp).
- **Botões "Simular abertura" / "Simular clique":** existem **apenas para teste/
  demonstração** — na janela comprimida o webhook do Resend não chega a tempo. **Em
  produção o agente é automático**: o engajamento real vem dos webhooks do Resend.
- **Fase Presença (ATTENDED) — implementado vs planejado:**
  - **Já existe e funciona:** endpoint `/checkin`, transição atômica de etapa, o webhook
    de booking, o botão "Check-in" no dashboard, e o avanço automático para a régua
    pós-evento (follow-ups/reunião).
  - **Camada de UX planejada (não feita por tempo):** **QR code** exibido no dia do
    evento → página de check-in que pede o **email** → ao enviar, dispara um **webhook**
    para o sistema → o lead **avança de etapa automaticamente** para ATTENDED, acionando
    follow-ups e o fluxo de reunião. A lógica de backend está pronta; falta só a tela.
  - **Como simular hoje:** botão "Check-in" no LeadDrawer (equivale ao que o QR faria).

---

## 5. Como compartilhar (instrução final ao usuário)

Após a criação, a documentação instrui (e a mensagem final ao usuário repete):
1. Abrir a página-mãe no Notion.
2. Botão **Share** → **Publish** (ou "Compartilhar na web") → copiar o link público.
3. Sub-páginas herdam o acesso. Enviar o link à Pareto.

---

## 6. Fonte de conteúdo

Reaproveitar (com atualização) o material existente:
- `README.md` (arquitetura, diagramas — **atualizar**: hoje roda OpenAI + mocks, não
  Claude/Apollo fixos).
- `CLAUDE.md` (invariantes, modo demo, régua, multi-provider — fonte rica e atual).
- `docs/superpowers/specs/*` (decisões de cada feature).
- Os 6 docs do case (`docs/01`–`06`) para alinhar linguagem aos entregáveis.

O conteúdo é **escrito de novo para o Notion** (não copiado cru), consolidando e
atualizando — mas ancorado nesses fatos verificados no código.

---

## 7. Arquivos afetados

- **Notion:** 1 página-mãe + 8 sub-páginas (criadas via MCP).
- **Repo:** opcionalmente, um `docs/README-notion.md` com o link final + sumário (decidir
  no plano). Atualizar o `README.md` da raiz se houver divergência factual relevante
  (OpenAI vs Claude) — escopo a confirmar no plano.

---

## 8. Riscos & mitigações

- **MCP não ativa link público:** documentado como passo manual (§5).
- **Conteúdo desatualizado no README:** a doc é reescrita a partir do estado **atual** do
  código (OpenAI ativo, mocks por ausência de chave), não copiada cru.
- **Mermaid não renderizar:** se o Notion não renderizar algum diagrama, cai em
  fallback de descrição textual (não bloqueia).
- **Honestidade demo vs produção:** explicitar sempre o que é simulado (botões, mocks,
  QR não-implementado) para o avaliador confiar na entrega.
- **Falha parcial na criação das páginas:** criar mãe → capturar ID → sub-páginas uma a
  uma; recriar só a que falhar.
