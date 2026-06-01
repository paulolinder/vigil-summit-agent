# Emails HTML com Identidade Vigil — Design

**Data:** 2026-05-31
**Status:** Aprovado para planejamento
**Contexto:** Os 17 templates de email (`backend/app/services/resend_service.py`) são
enviados como **texto puro** (`resend.Emails.send({..., "text": body})`). O objetivo é
entregar cada email em **HTML estruturado e bonito**, com a identidade visual do Vigil
Summit, mantendo a personalização e a entregabilidade.

---

## 1. Objetivo

Transformar os 17 emails de texto puro em HTML com a marca Vigil, sem alterar a
lógica da régua, a personalização por setor, nem o registro em `messages`. Cada email
ganha header com logo textual, corpo estilizado, CTA contextual por fase e footer com
assinatura — preservando uma versão **texto como fallback** (entregabilidade/anti-spam)
e a robustez entre clientes de email (tabelas + CSS inline).

---

## 2. Decisões travadas (do brainstorming)

1. **Arquitetura:** shell HTML único (header/footer/CSS/botão) + miolo por template. DRY.
2. **Logo:** textual em HTML/CSS ("**Vigil** Summit" + bolinha teal), sem imagem hospedada
   (clientes bloqueiam imagens por padrão; texto sempre renderiza).
3. **Envio:** `html` + `text` (fallback) juntos no payload do Resend. `messages.body`
   continua guardando o **texto** (dashboard/drawer limpos).
4. **CTA:** contextual por template (cor + label + destino), mapeado em §5.

---

## 3. Identidade visual (do `tailwind.config.ts` + landing)

| Token | Hex | Uso no email |
|---|---|---|
| navy | `#0F2A34` | header, botão primário, texto de título |
| teal | `#48C2C5` | logo "Summit", eyebrows uppercase, borda-esquerda de listas |
| green | `#59BD75` | acentos de sucesso (opcional) |
| lime | `#DDEB4F` | botão secundário (texto navy) |
| bg | `#F7F9FB` | fundo do email |
| text | `#102A34` | corpo |
| muted | `#64748B` | footer, nota LGPD |
| border | `#E5EAF0` | divisores, borda do card |

Estilo herdado da landing: cantos arredondados (10px botões, 16px card), títulos
extrabold, eyebrows teal uppercase com `letter-spacing`, CTAs navy (primário) / lime
(secundário). Assinatura: "Ana Beatriz Costa · Account Executive, Vigil.AI".

---

## 4. Arquitetura — `app/services/email_templates.py` (NOVO)

Separa apresentação (HTML) da lógica de envio. `resend_service.py` mantém `TEMPLATES`
(texto), `_APOLLO_TO_SECTOR`, `_resolve_sector_content`, `send_email`.

```
app/services/email_templates.py
  _shell(inner_html: str, cta: dict | None) -> str   # envolve o miolo na marca Vigil
  _button(label: str, url: str, variant: str) -> str # tabela-botão (Outlook-safe)
  TEMPLATE_BODIES_HTML: dict[str, str]                # 17 miolos em HTML (mesmos {placeholders})
  CTA_MAP: dict[str, dict]                            # {template_key: {label, variant, dest}}
  render_html(template_key, ctx, cta_url=None) -> str # monta o email HTML completo
```

### O shell (`_shell`)
- Tabela externa (largura 100%, fundo `#F7F9FB`), tabela interna centralizada `max-width:600px`.
- **Header:** faixa navy, padding 24px, "● Vigil" branco extrabold + "Summit" teal.
- **Corpo:** card branco, borda `#E5EAF0`, cantos 16px, padding 32px. Texto `#102A34`,
  line-height ~1.6.
- **Chip de personalização** (condicional): se `ctx` tem role/sector reais, um chip
  discreto no topo do corpo (ex.: `CISO · Setor Financeiro`). Ausente sem enriquecimento.
- **CTA:** renderizado por `_button` se o template tem CTA (§5).
- **Footer:** fundo `#F7F9FB`, assinatura, dados do evento (São Paulo, 15 Ago 2026),
  nota LGPD/descadastro em `#64748B`.
- Tudo com **CSS inline** (clientes ignoram `<style>`/`<link>` externos).

### `_button(label, url, variant)`
Tabela-botão (compatível com Outlook), cantos 10px. `variant="primary"` → navy/branco;
`variant="secondary"` → lime/navy.

### `TEMPLATE_BODIES_HTML`
Os 17 miolos, derivados dos textos atuais: parágrafos viram `<p>`, blocos multi-linha
(`{sector_content}`, `{event_highlights}`) viram `<ul>` com `<li>` ou linhas com
borda-esquerda teal. **Mesmos `{placeholders}`** do texto atual — o `ctx` não muda.

### `render_html(template_key, ctx, cta_url=None)`
1. Resolve o CTA via `CTA_MAP[template_key]`. Se `dest == "calcom"`, usa `cta_url`
   (validado http/https); se ausente/inválido → fallback `FRONTEND_URL` (landing). Se
   `dest == "landing"` → `FRONTEND_URL`. Se template sem CTA → nenhum botão.
2. **Escape HTML** de todos os valores de `ctx` antes de interpolar (defesa de injeção —
   ver §7).
3. `inner = TEMPLATE_BODIES_HTML[template_key].format(**escaped_ctx)`.
4. Retorna `_shell(inner, cta)`.

---

## 5. CTA contextual — `CTA_MAP`

| Template | Label | Variant | Destino |
|---|---|---|---|
| welcome | Confirmar presença | secondary (lime) | landing |
| confirmation_request | Confirmar minha vaga | secondary | landing |
| confirmation_followup | Confirmar antes que feche | secondary | landing |
| warmup | Ver a agenda | primary (navy) | landing |
| vip_briefing | Ver a agenda | primary | landing |
| agenda | Ver programação completa | primary | landing |
| logistics | _(sem botão)_ | — | — |
| day_reminder | _(sem botão)_ | — | — |
| thank_you | Agendar conversa | primary | calcom |
| demo_followup | Agendar demonstração | secondary | calcom |
| pain_point | _(sem botão)_ | — | — |
| breakup | _(sem botão)_ | — | — |
| no_show_missed | Quero a sessão privada | secondary | calcom |
| no_show_demo_offer | Agendar demo privada | secondary | calcom |
| no_show_final | Agendar (último convite) | primary | calcom |

`landing` = `settings.frontend_url`. `calcom` = `cta_url` passado a `send_email`
(fallback landing se ausente).

---

## 6. Integração com `send_email` e o tool_executor

### `send_email(lead, template_key, custom_note="", phase="pre_event", cta_url=None)`
- **Novo parâmetro** `cta_url: str | None = None` (default None → comportamento atual
  para chamadas que não passam link).
- Monta `text = template["body"].format(**ctx)` (como hoje) e
  `html = render_html(template_key, ctx, cta_url)`.
- Payload do Resend ganha `"html": html` além de `"text": text`.
- `messages.body` recebe o **`text`** (inalterado).
- **Fallback:** `render_html` envolto em try/except; se falhar, envia só `text` e loga —
  nunca bloqueia o envio.

### Fonte do `cta_url` (link Cal.com)
Hoje o link do Cal.com é gerado em `meeting.generate_meeting_link` e o agente o coloca
no `custom_note` (texto). Para o **botão** funcionar nos templates `calcom`:
- `tool_executor._send_followup` aceita/repassa um `cta_url` opcional a `send_email`.
- **MVP pragmático:** se o agente não fornecer `cta_url` estruturado, o botão cai no
  fallback (landing). O link em texto no `custom_note` continua visível no corpo. (Wire
  completo do link estruturado agente→botão pode ser uma melhoria posterior; o fallback
  garante que nada quebra.)

`send_pre_event_msg` (templates landing) não precisa de `cta_url`.

---

## 7. Segurança — escape HTML (defesa de injeção)

Valores de `ctx` carregam entrada externa: `name`, `company`, `role` (do lead) e
`custom_note` (texto livre gerado pelo LLM). Em texto puro isso era inócuo; em **HTML é
risco de injeção** (tags, `<script>`, atributos). Logo:

- Antes de `.format`, aplicar `html.escape()` a TODOS os valores string de `ctx`.
- Os blocos multi-linha são **conteúdo controlado pelo sistema** (não entrada do
  usuário): `event_highlights` usa `→`+`\n` por linha; `sector_content`
  (`_resolve_sector_content`) é uma frase única com `. ` entre itens. Ambos passam pelo
  mesmo escape por segurança; a quebra visual (split por `\n` para `event_highlights`;
  manter parágrafo único para `sector_content`) ocorre DEPOIS do escape, sobre
  marcadores conhecidos — nunca sobre tags. O plano define a conversão exata por bloco.
- `cta_url`: validar que começa com `http://` ou `https://`; senão, fallback landing.
- O escape NÃO altera o `text` (fallback) — esse continua o texto puro de hoje.

Isto estende o padrão de sanitização já existente em `prompts._safe` (que protege o
system prompt) para a fronteira de saída de email.

---

## 8. Estratégia de testes (TDD)

Novo arquivo `backend/tests/test_email_templates.py`:

- **Shell presente:** `render_html("welcome", ctx)` contém marcadores do shell (texto
  "Vigil", cor `#0F2A34`, estrutura `<table`).
- **Escape de injeção:** `custom_note="<script>alert(1)</script>"` sai como
  `&lt;script&gt;` no HTML; chaves `{` `}` não quebram o `.format`.
- **CTA calcom com url:** `render_html("demo_followup", ctx, cta_url="https://cal.com/x")`
  → o href do botão é essa URL.
- **CTA calcom sem url:** mesmo template sem `cta_url` → href cai em `FRONTEND_URL`.
- **CTA inválida:** `cta_url="javascript:..."` → fallback landing (não injeta o esquema).
- **Template sem botão:** `render_html("logistics", ctx)` não contém o bloco de botão.
- **Todos os 17 renderizam:** loop sobre as chaves de `TEMPLATE_BODIES_HTML` com um `ctx`
  mínimo — nenhum lança `KeyError`/`IndexError` (garante paridade de placeholders).

Em `test_*` de `send_email` (existentes + novos):
- **html + text no payload:** o dict passado a `resend.Emails.send` tem `"html"` e
  `"text"`; `messages.body` recebe o texto (sem tags).
- **fallback:** se `render_html` lança, `send_email` ainda envia (só text) e grava a
  mensagem como SENT.
- Testes existentes de `send_email`/régua continuam passando (contrato externo intacto).

Rodar com `./venv/Scripts/python.exe -m pytest tests/ -q`.

---

## 9. Arquivos afetados

**Criar**
- `backend/app/services/email_templates.py` — shell, botão, 17 miolos HTML, CTA_MAP, render_html.
- `backend/tests/test_email_templates.py`.

**Modificar**
- `backend/app/services/resend_service.py` — `send_email` ganha `cta_url`, monta `html`,
  envia html+text, fallback try/except. `TEMPLATES` (texto) permanecem como fallback.
- `backend/app/agent/tool_executor.py` — `_send_followup` (e, se aplicável, `_send_pre_event_msg`)
  repassam `cta_url` opcional a `send_email` (MVP: pode ficar None → fallback landing).
- `CLAUDE.md` — nota sobre os emails HTML (shell único + text fallback + escape).

**Não muda**
- A régua (`prompts.py`), o registro em `messages` (body = texto), o dashboard, os RPCs,
  a lógica de personalização por setor.

---

## 10. Riscos & mitigações

- **Quebra entre clientes de email:** mitigado por tabelas + CSS inline + text fallback.
- **Injeção via custom_note/nome:** mitigado por `html.escape()` de todo o `ctx` (§7).
- **CTA apontando pro lugar errado:** CTA_MAP explícito por template + validação de
  `cta_url` + fallback landing.
- **Regressão no envio:** `render_html` em try/except → nunca impede o envio (cai p/ texto).
- **Drawer poluído com HTML:** evitado — `messages.body` guarda o texto, não o HTML.
