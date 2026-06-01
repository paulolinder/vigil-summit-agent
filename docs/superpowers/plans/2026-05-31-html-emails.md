# Emails HTML com Identidade Vigil — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Converter os 17 emails de texto puro em HTML com a identidade visual do Vigil (shell único + miolo por template), mantendo personalização, fallback texto e o registro em `messages` inalterados.

**Architecture:** Novo módulo `app/services/email_templates.py` com um shell HTML único (header/footer/CSS inline/botão Outlook-safe), 17 miolos HTML reusando os mesmos `{placeholders}` do texto atual, e um `CTA_MAP` por template. `send_email` passa a montar `html` (via `render_html`) + `text` (fallback) e enviar ambos pelo Resend; `messages.body` continua texto. Todo valor de `ctx` é escapado (`html.escape`) antes de entrar no HTML (defesa de injeção).

**Tech Stack:** Python (FastAPI), Resend SDK, pytest. HTML de email = tabelas + CSS inline.

**Spec:** `docs/superpowers/specs/2026-05-31-html-emails-design.md`

**Como rodar testes:** a partir de `backend/`, use `./venv/Scripts/python.exe -m pytest tests/ -q` (o `python` global não tem pytest). Modo asyncio é `auto` — testes async usam `async def` puro, sem `@pytest.mark.asyncio`.

---

## Estrutura de arquivos

**Criar:**
- `backend/app/services/email_templates.py` — `_esc`, `_button`, `_shell`, `_perso_chip`, `CTA_MAP`, `TEMPLATE_BODIES_HTML`, `render_html`.
- `backend/tests/test_email_templates.py` — testes de render/escape/CTA.

**Modificar:**
- `backend/app/services/resend_service.py` — `send_email` ganha `cta_url`, monta `html`, envia html+text, fallback try/except.
- `backend/app/agent/tool_executor.py` — `_send_followup` repassa `cta_url=None` (MVP) a `send_email` (fallback landing).
- `CLAUDE.md` — nota sobre os emails HTML.

**Paleta (do tailwind.config.ts):** navy `#0F2A34`, teal `#48C2C5`, green `#59BD75`, lime `#DDEB4F`, bg `#F7F9FB`, text `#102A34`, muted `#64748B`, border `#E5EAF0`.

---

## Task 1: Infra do shell — `_esc`, `_button`, `_shell`, `_perso_chip`

**Files:**
- Create: `backend/app/services/email_templates.py`
- Test: `backend/tests/test_email_templates.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# backend/tests/test_email_templates.py
from app.services.email_templates import _esc, _button, _shell, _perso_chip


def test_esc_escapes_html():
    assert _esc("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert _esc(None) == ""


def test_button_primary_and_secondary():
    pri = _button("Confirmar", "https://x.com", "primary")
    assert "https://x.com" in pri and "#0F2A34" in pri
    sec = _button("Agendar", "https://y.com", "secondary")
    assert "#DDEB4F" in sec


def test_shell_wraps_inner_with_brand():
    html = _shell("<p>Olá</p>", cta=None, chip=None)
    assert "<p>Olá</p>" in html
    assert "Vigil" in html              # logo textual
    assert "#0F2A34" in html            # header navy
    assert "<table" in html.lower()     # tabela (Outlook-safe)
    assert "Ana Beatriz Costa" in html  # assinatura no footer


def test_shell_includes_button_when_cta_present():
    html = _shell("<p>x</p>", cta={"label": "Confirmar", "url": "https://x.com", "variant": "secondary"}, chip=None)
    assert "Confirmar" in html and "https://x.com" in html


def test_shell_omits_button_when_no_cta():
    html = _shell("<p>x</p>", cta=None, chip=None)
    assert "https://" not in html.split("footer")[0] or "cta" not in html.lower()
    # botão não renderizado: nenhuma tabela-botão com role=button
    assert "email-cta-button" not in html


def test_perso_chip_renders_when_data_present():
    assert "CISO" in _perso_chip("CISO", "financial services")
    assert _perso_chip(None, None) == ""
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_email_templates.py -q`
Expected: FAIL — `No module named 'app.services.email_templates'`

- [ ] **Step 3: Implementar a infra do shell**

```python
# backend/app/services/email_templates.py
"""Shell HTML único + miolos por template para os emails do Vigil Summit.

Email HTML robusto = tabelas + CSS inline (clientes ignoram <style>/<link>).
Todo valor interpolado vem de _esc() (defesa de injeção). O texto puro (fallback)
continua em resend_service.TEMPLATES; este módulo só cuida do HTML.
"""
import html as _html

# Paleta Vigil (tailwind.config.ts)
_NAVY = "#0F2A34"
_TEAL = "#48C2C5"
_LIME = "#DDEB4F"
_BG = "#F7F9FB"
_TEXT = "#102A34"
_MUTED = "#64748B"
_BORDER = "#E5EAF0"


def _esc(value) -> str:
    """Escape HTML de qualquer valor interpolado no email. None → ''."""
    if value is None:
        return ""
    return _html.escape(str(value))


def _button(label: str, url: str, variant: str) -> str:
    """Tabela-botão Outlook-safe. variant: 'primary' (navy) | 'secondary' (lime)."""
    if variant == "secondary":
        bg, fg = _LIME, _NAVY
    else:
        bg, fg = _NAVY, "#FFFFFF"
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'class="email-cta-button" style="margin:28px 0;"><tr>'
        f'<td align="center" bgcolor="{bg}" style="border-radius:10px;">'
        f'<a href="{_esc(url)}" target="_blank" '
        f'style="display:inline-block;padding:14px 28px;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:14px;font-weight:bold;color:{fg};text-decoration:none;border-radius:10px;">'
        f'{_esc(label)}</a></td></tr></table>'
    )


def _perso_chip(role: str | None, sector: str | None) -> str:
    """Chip discreto de personalização. Vazio se sem dados reais."""
    parts = [p for p in (role, sector) if p and p not in ("profissional", "tecnologia", "N/A")]
    if not parts:
        return ""
    label = " · ".join(_esc(p) for p in parts)
    return (
        f'<span style="display:inline-block;background:{_BG};border:1px solid {_BORDER};'
        f'border-radius:999px;padding:4px 12px;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:11px;font-weight:bold;color:{_TEAL};letter-spacing:0.04em;'
        f'text-transform:uppercase;margin-bottom:16px;">{label}</span>'
    )


def _shell(inner_html: str, cta: dict | None, chip: str | None) -> str:
    """Envolve o miolo na identidade Vigil. cta: {label,url,variant} ou None."""
    button = _button(cta["label"], cta["url"], cta.get("variant", "primary")) if cta else ""
    chip_html = chip or ""
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:{_BG};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{_BG};padding:24px 0;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;">

<!-- Header -->
<tr><td style="background:{_NAVY};border-radius:16px 16px 0 0;padding:24px 32px;font-family:Arial,Helvetica,sans-serif;">
<span style="display:inline-block;width:8px;height:8px;background:{_TEAL};border-radius:999px;margin-right:8px;vertical-align:middle;"></span>
<span style="font-size:18px;font-weight:800;color:#FFFFFF;vertical-align:middle;">Vigil </span>
<span style="font-size:18px;font-weight:800;color:{_TEAL};vertical-align:middle;">Summit</span>
</td></tr>

<!-- Corpo -->
<tr><td style="background:#FFFFFF;border-left:1px solid {_BORDER};border-right:1px solid {_BORDER};padding:32px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.6;color:{_TEXT};">
{chip_html}
{inner_html}
{button}
</td></tr>

<!-- Footer -->
<tr><td style="background:{_BG};border:1px solid {_BORDER};border-top:none;border-radius:0 0 16px 16px;padding:24px 32px;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.5;color:{_MUTED};">
<strong style="color:{_TEXT};">Ana Beatriz Costa</strong><br>
Account Executive · Vigil.AI<br><br>
Vigil Summit — 15 de agosto de 2026 · São Paulo<br>
<span style="color:{_MUTED};">Você recebe este email porque se inscreveu no Vigil Summit. Para não receber mais, responda com "sair".</span>
</td></tr>

</table>
</td></tr>
</table>
</body></html>"""
```

- [ ] **Step 4: Rodar o teste para confirmar que passa**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_email_templates.py -q`
Expected: PASS (6 testes)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/email_templates.py backend/tests/test_email_templates.py
git commit -m "feat(email): shell HTML Vigil + botão Outlook-safe + escape"
```

---

## Task 2: `CTA_MAP` + `render_html`

**Files:**
- Modify: `backend/app/services/email_templates.py`
- Test: `backend/tests/test_email_templates.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicione a `backend/tests/test_email_templates.py`:

```python
def _min_ctx():
    return {
        "name": "Ana", "role": "CISO", "company": "BankCo", "sector": "financial services",
        "sector_content": "Zero Trust. LGPD. Priorização.",
        "custom_note": "Nota.", "role_personalization": "Como CISO...",
        "event_context": "segurança", "demo_context": "a conversa",
        "demo_content": "conteúdo demo", "pain_point_content": "qual gargalo?",
        "event_highlights": "→ A\n→ B\n→ C", "demo_preview": "dashboard, priorização",
    }


def test_render_landing_cta_uses_frontend_url(monkeypatch):
    from app.config import settings
    from app.services.email_templates import render_html
    monkeypatch.setattr(settings, "frontend_url", "https://summit.vigil.ai")
    html = render_html("welcome", _min_ctx())
    assert "https://summit.vigil.ai" in html
    assert "Confirmar presença" in html


def test_render_calcom_cta_uses_cta_url():
    from app.services.email_templates import render_html
    html = render_html("demo_followup", _min_ctx(), cta_url="https://cal.com/vigil/x")
    assert "https://cal.com/vigil/x" in html
    assert "Agendar demonstração" in html


def test_render_calcom_without_url_falls_back_to_landing(monkeypatch):
    from app.config import settings
    from app.services.email_templates import render_html
    monkeypatch.setattr(settings, "frontend_url", "https://summit.vigil.ai")
    html = render_html("thank_you", _min_ctx(), cta_url=None)
    assert "https://summit.vigil.ai" in html


def test_render_invalid_cta_url_falls_back(monkeypatch):
    from app.config import settings
    from app.services.email_templates import render_html
    monkeypatch.setattr(settings, "frontend_url", "https://summit.vigil.ai")
    html = render_html("thank_you", _min_ctx(), cta_url="javascript:alert(1)")
    assert "javascript:" not in html
    assert "https://summit.vigil.ai" in html


def test_render_no_button_template():
    from app.services.email_templates import render_html
    html = render_html("logistics", _min_ctx())
    assert "email-cta-button" not in html


def test_render_escapes_custom_note():
    from app.services.email_templates import render_html
    ctx = _min_ctx()
    ctx["custom_note"] = "<script>alert(1)</script>"
    html = render_html("welcome", ctx)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_all_17_templates_render():
    from app.services.email_templates import render_html, TEMPLATE_BODIES_HTML
    for key in TEMPLATE_BODIES_HTML:
        html = render_html(key, _min_ctx(), cta_url="https://cal.com/x")
        assert "Vigil" in html and len(html) > 200
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_email_templates.py -k render -q`
Expected: FAIL — `cannot import name 'render_html'` / `TEMPLATE_BODIES_HTML`.

- [ ] **Step 3: Implementar `CTA_MAP` + `render_html`**

Adicione a `backend/app/services/email_templates.py` (após `_shell`). Nota: `TEMPLATE_BODIES_HTML` é importado de uma constante que será preenchida nas Tasks 3-5; para esta task, defina-o como dict vazio inicial e o teste `test_all_17_templates_render` só passará após a Task 5 — por isso, NESTA task, rode o pytest excluindo esse teste (`-k "render and not all_17"`). O teste `test_all_17` fica documentado e vira verde na Task 5.

```python
from app.config import settings

# {template_key: {"label": str, "variant": "primary"|"secondary", "dest": "landing"|"calcom"}}
# Templates sem botão NÃO aparecem aqui.
CTA_MAP: dict[str, dict] = {
    "welcome":               {"label": "Confirmar presença",          "variant": "secondary", "dest": "landing"},
    "confirmation_request":  {"label": "Confirmar minha vaga",        "variant": "secondary", "dest": "landing"},
    "confirmation_followup": {"label": "Confirmar antes que feche",   "variant": "secondary", "dest": "landing"},
    "warmup":                {"label": "Ver a agenda",                "variant": "primary",   "dest": "landing"},
    "vip_briefing":          {"label": "Ver a agenda",                "variant": "primary",   "dest": "landing"},
    "agenda":                {"label": "Ver programação completa",    "variant": "primary",   "dest": "landing"},
    "thank_you":             {"label": "Agendar conversa",            "variant": "primary",   "dest": "calcom"},
    "demo_followup":         {"label": "Agendar demonstração",        "variant": "secondary", "dest": "calcom"},
    "no_show_missed":        {"label": "Quero a sessão privada",      "variant": "secondary", "dest": "calcom"},
    "no_show_demo_offer":    {"label": "Agendar demo privada",        "variant": "secondary", "dest": "calcom"},
    "no_show_final":         {"label": "Agendar (último convite)",    "variant": "primary",   "dest": "calcom"},
}
# Sem botão: logistics, day_reminder, pain_point, breakup.


def _resolve_cta(template_key: str, cta_url: str | None) -> dict | None:
    spec = CTA_MAP.get(template_key)
    if not spec:
        return None
    if spec["dest"] == "calcom" and cta_url and cta_url.startswith(("http://", "https://")):
        url = cta_url
    else:
        url = settings.frontend_url
    return {"label": spec["label"], "url": url, "variant": spec["variant"]}


# Preenchido nas Tasks 3-5 (miolos HTML). Mantido aqui para import estável.
TEMPLATE_BODIES_HTML: dict[str, str] = {}


def render_html(template_key: str, ctx: dict, cta_url: str | None = None) -> str:
    """Monta o email HTML completo: escape do ctx → miolo → shell com CTA + chip."""
    escaped = {k: _esc(v) for k, v in ctx.items()}
    # event_highlights vira lista visual (split por linha, DEPOIS do escape)
    if "event_highlights" in escaped:
        lines = [ln.strip().lstrip("→").strip() for ln in escaped["event_highlights"].split("\n") if ln.strip()]
        escaped["event_highlights"] = "".join(
            f'<li style="margin-bottom:6px;">{ln}</li>' for ln in lines
        )
    inner_tpl = TEMPLATE_BODIES_HTML.get(template_key, "<p>{custom_note}</p>")
    inner = inner_tpl.format(**escaped)
    cta = _resolve_cta(template_key, cta_url)
    # _perso_chip recebe o ctx CRU (não-escapado) de propósito: ele já aplica _esc
    # internamente. NÃO passe `escaped` aqui (evita escape duplo).
    chip = _perso_chip(ctx.get("role"), ctx.get("sector"))
    return _shell(inner, cta, chip)
```

- [ ] **Step 4: Rodar para confirmar que passa (exceto all_17)**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_email_templates.py -k "render and not all_17" -q`
Expected: PASS (6 testes; `test_all_17_templates_render` ainda falha — vira verde na Task 5)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/email_templates.py backend/tests/test_email_templates.py
git commit -m "feat(email): CTA_MAP + render_html (escape, fallback landing)"
```

---

## Task 3: Miolos HTML — pré-evento (parte A: welcome, confirmation_request, confirmation_followup, warmup)

**Files:**
- Modify: `backend/app/services/email_templates.py` (preencher `TEMPLATE_BODIES_HTML`)

- [ ] **Step 1: Adicionar os 4 primeiros miolos**

Substitua `TEMPLATE_BODIES_HTML: dict[str, str] = {}` por um dict que começa com estes 4. Cada miolo usa os MESMOS `{placeholders}` do texto atual. Helper de parágrafo: use `<p style="margin:0 0 16px;">...</p>`; eyebrow de seção: `<p style="color:#48C2C5;font-size:12px;font-weight:bold;letter-spacing:0.1em;text-transform:uppercase;margin:0 0 8px;">...</p>`.

```python
_P = 'margin:0 0 16px;'
_EYEBROW = 'color:#48C2C5;font-size:12px;font-weight:bold;letter-spacing:0.1em;text-transform:uppercase;margin:0 0 8px;'
_SECTOR_BOX = 'border-left:3px solid #48C2C5;padding:8px 0 8px 16px;margin:0 0 16px;color:#102A34;'

TEMPLATE_BODIES_HTML: dict[str, str] = {

    "welcome": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}">Sua inscrição no <strong>Vigil Summit — Segurança para a Era da IA</strong> foi confirmada. '
        f'Estamos reservando sua vaga entre as 120 disponíveis.</p>'
        f'<p style="{_P}">O Summit acontece em <strong>15 de agosto de 2026</strong>, em São Paulo, com foco em três temas:</p>'
        f'<ul style="margin:0 0 16px;padding-left:20px;">'
        f'<li style="margin-bottom:6px;">Zero Trust na prática para ambientes híbridos e multicloud</li>'
        f'<li style="margin-bottom:6px;">IA aplicada à detecção de ameaças e resposta a incidentes</li>'
        f'<li style="margin-bottom:6px;">Conformidade automatizada: LGPD, ISO 27001 e SOC 2</li>'
        f'</ul>'
        f'<p style="{_P}">{{role_personalization}}</p>'
        f'<p style="{_P}">{{custom_note}}</p>'
    ),

    "confirmation_request": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}">Faltam <strong>14 dias</strong> para o Vigil Summit e sua vaga ainda não foi confirmada.</p>'
        f'<p style="{_P}">Com 120 participantes e lista de espera ativa, preciso da sua confirmação para garantir '
        f'o credenciamento e o kit exclusivo do evento.</p>'
        f'<p style="{_EYEBROW}">Por que vale a presença</p>'
        f'<div style="{_SECTOR_BOX}">{{sector_content}}</div>'
        f'<p style="{_P}">{{custom_note}}</p>'
    ),

    "confirmation_followup": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}">Ainda não recebi sua confirmação para o Vigil Summit, que acontece em <strong>10 dias</strong>.</p>'
        f'<p style="{_P}">Entendo que a agenda de {{role}} é intensa. Por isso serei direto: este é o evento onde '
        f'CISOs e CTOs de empresas como a {{company}} vão decidir o roadmap de segurança de 2027.</p>'
        f'<p style="{_EYEBROW}">O que você vai encontrar lá</p>'
        f'<div style="{_SECTOR_BOX}">{{sector_content}}</div>'
        f'<p style="{_P}">{{custom_note}}</p>'
    ),

    "warmup": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}">Com 10 dias para o Vigil Summit, quero garantir que você aproveite cada hora do evento.</p>'
        f'<p style="{_EYEBROW}">Sessões mais estratégicas para você</p>'
        f'<div style="{_SECTOR_BOX}">{{sector_content}}</div>'
        f'<p style="{_P}">{{custom_note}}</p>'
    ),
}
```

- [ ] **Step 2: Verificar que renderizam sem erro**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_email_templates.py -k "render and not all_17" -q`
Expected: PASS (os 4 já cobertos por welcome/landing nos testes da Task 2; sem KeyError)

Sanity manual:
Run: `cd backend && ./venv/Scripts/python.exe -c "from app.services.email_templates import render_html; [render_html(k, {'name':'A','role':'CISO','company':'C','sector':'financial services','sector_content':'X','custom_note':'N','role_personalization':'R'}) for k in ('welcome','confirmation_request','confirmation_followup','warmup')]; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/email_templates.py
git commit -m "feat(email): miolos HTML pré-evento A (welcome, confirmation, warmup)"
```

---

## Task 4: Miolos HTML — pré-evento (parte B: vip_briefing, agenda, logistics, day_reminder)

**Files:**
- Modify: `backend/app/services/email_templates.py`

- [ ] **Step 1: Adicionar os 4 miolos ao dict `TEMPLATE_BODIES_HTML`**

Insira estas entradas dentro do dict (antes do `}` de fechamento):

```python
    "vip_briefing": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}">Preparei um briefing exclusivo para os executivos de segurança confirmados no Vigil Summit.</p>'
        f'<p style="{_P}">Como {{role}}, você lidera decisões que impactam diretamente o que discutiremos no dia 15.</p>'
        f'<p style="{_EYEBROW}">O que está em pauta para o seu setor</p>'
        f'<div style="{_SECTOR_BOX}">{{sector_content}}</div>'
        f'<p style="{_P}">Reservamos um espaço exclusivo para decisores — uma conversa direta com o time técnico '
        f'da Vigil.AI sobre casos reais de implementação.</p>'
        f'<p style="{_P}">{{custom_note}}</p>'
    ),

    "agenda": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}">O Vigil Summit acontece em <strong>3 dias</strong>. Selecionei as sessões mais relevantes '
        f'para o seu perfil:</p>'
        f'<div style="{_SECTOR_BOX}">{{sector_content}}</div>'
        f'<p style="{_P}">{{custom_note}}</p>'
        f'<p style="{_EYEBROW}">Programação</p>'
        f'<ul style="margin:0 0 16px;padding-left:20px;">'
        f'<li style="margin-bottom:6px;">8h30 — Credenciamento e café</li>'
        f'<li style="margin-bottom:6px;">9h00 — Abertura: IA e o novo perímetro de segurança</li>'
        f'<li style="margin-bottom:6px;">10h30 — Tracks: Zero Trust · IA em Segurança · Conformidade</li>'
        f'<li style="margin-bottom:6px;">12h30 — Almoço executivo</li>'
        f'<li style="margin-bottom:6px;">14h00 — Mesas redondas por setor</li>'
        f'<li style="margin-bottom:6px;">16h30 — Encerramento e networking</li>'
        f'</ul>'
    ),

    "logistics": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}"><strong>Amanhã é o dia.</strong> Aqui estão as informações de acesso:</p>'
        f'<ul style="margin:0 0 16px;padding-left:20px;">'
        f'<li style="margin-bottom:6px;">📍 Centro de Convenções Rebouças — Av. Dr. Enéas de Carvalho Aguiar, 23, Pinheiros, São Paulo</li>'
        f'<li style="margin-bottom:6px;">🕘 Credenciamento 8h30 · Início 9h00</li>'
        f'<li style="margin-bottom:6px;">🎫 Leve documento com foto</li>'
        f'<li style="margin-bottom:6px;">🚗 Estacionamento validado no local</li>'
        f'<li style="margin-bottom:6px;">🍽️ Almoço incluído para confirmados</li>'
        f'</ul>'
        f'<p style="{_P}">{{custom_note}}</p>'
    ),

    "day_reminder": (
        f'<p style="{_P}">Bom dia, <strong>{{name}}</strong>!</p>'
        f'<p style="{_P}">O Vigil Summit começa <strong>hoje</strong>. Credenciamento a partir das 8h30 no '
        f'Centro de Convenções Rebouças.</p>'
        f'<p style="{_P}">{{custom_note}}</p>'
    ),
```

- [ ] **Step 2: Verificar render**

Run: `cd backend && ./venv/Scripts/python.exe -c "from app.services.email_templates import render_html; [render_html(k, {'name':'A','role':'CISO','company':'C','sector':'financial services','sector_content':'X','custom_note':'N'}) for k in ('vip_briefing','agenda','logistics','day_reminder')]; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/email_templates.py
git commit -m "feat(email): miolos HTML pré-evento B (vip, agenda, logistics, day)"
```

---

## Task 5: Miolos HTML — pós-evento (thank_you, demo_followup, pain_point, breakup, no_show_missed, no_show_demo_offer, no_show_final)

**Files:**
- Modify: `backend/app/services/email_templates.py`
- Test: `backend/tests/test_email_templates.py` (o `test_all_17` vira verde aqui)

- [ ] **Step 1: Adicionar os 7 miolos pós-evento ao dict**

```python
    "thank_you": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}">Obrigada por ter estado conosco no Vigil Summit.</p>'
        f'<p style="{_P}">As discussões foram densas — especialmente as mesas sobre {{event_context}}. '
        f'Gostaria de continuar a conversa sobre como a Vigil.AI se aplica à realidade da {{company}}.</p>'
        f'<p style="{_P}">{{custom_note}}</p>'
    ),

    "demo_followup": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}">{{demo_content}}</p>'
        f'<p style="{_P}">A Vigil.AI resolve o que foi discutido: visibilidade contínua de postura, '
        f'priorização inteligente de riscos e relatórios automáticos de conformidade — integrados ao seu ambiente.</p>'
        f'<p style="{_P}">Consigo mostrar isso em 30 minutos, no ambiente de vocês.</p>'
        f'<p style="{_P}">{{custom_note}}</p>'
    ),

    "pain_point": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}">Após o Vigil Summit, ficou uma pergunta que quero trazer diretamente para você:</p>'
        f'<div style="{_SECTOR_BOX}">{{pain_point_content}}</div>'
        f'<p style="{_P}">Não estou pedindo para agendar uma demo agora — só quero entender se estou mapeando '
        f'o problema certo. Me responde em duas linhas?</p>'
        f'<p style="{_P}">{{custom_note}}</p>'
    ),

    "breakup": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}">Tentei contato algumas vezes desde o Vigil Summit, mas entendo que o timing pode não ser ideal.</p>'
        f'<p style="{_P}">Vou deixar o espaço livre por enquanto. Se em algum momento fizer sentido conversar sobre '
        f'como empresas do setor de {{sector}} estão resolvendo esses desafios, é só responder este email.</p>'
        f'<p style="{_P}">{{custom_note}}</p>'
    ),

    "no_show_missed": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}">Notamos que você não pôde comparecer ao Vigil Summit. Imprevistos acontecem.</p>'
        f'<p style="{_EYEBROW}">Resumo dos principais pontos</p>'
        f'<ul style="margin:0 0 16px;padding-left:20px;">{{event_highlights}}</ul>'
        f'<p style="{_P}">{{custom_note}}</p>'
        f'<p style="{_P}">Posso fazer uma sessão privada para você com os mesmos temas. Sem custo, sem compromisso.</p>'
    ),

    "no_show_demo_offer": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}">Preparei uma sessão exclusiva para quem não pôde comparecer ao Vigil Summit. Em 30 minutos:</p>'
        f'<div style="{_SECTOR_BOX}">{{demo_preview}}</div>'
        f'<p style="{_P}">Tudo adaptado para o contexto de {{company}} no setor de {{sector}}.</p>'
        f'<p style="{_P}">{{custom_note}}</p>'
    ),

    "no_show_final": (
        f'<p style="{_P}">Olá <strong>{{name}}</strong>,</p>'
        f'<p style="{_P}">Esta é minha última tentativa de contato.</p>'
        f'<p style="{_P}">Se quiser ver como a Vigil.AI funciona para empresas como a {{company}} — detecção de '
        f'vulnerabilidades, dashboard de postura e conformidade automatizada — o botão abaixo agenda em 1 clique.</p>'
        f'<p style="{_P}">{{custom_note}}</p>'
    ),
```

- [ ] **Step 2: Rodar a suíte de templates inteira (agora `test_all_17` passa)**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_email_templates.py -q`
Expected: PASS (todos, incl. `test_all_17_templates_render`)

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/email_templates.py
git commit -m "feat(email): miolos HTML pós-evento (thank_you, demo, pain, breakup, no-show)"
```

---

## Task 6: Wire em `send_email` (html + text + fallback)

**Files:**
- Modify: `backend/app/services/resend_service.py:429-524`
- Test: `backend/tests/` (novo arquivo `test_send_email_html.py` ou append ao existente)

- [ ] **Step 1: Escrever o teste que falha**

Crie `backend/tests/test_send_email_html.py`:

```python
from unittest.mock import patch, MagicMock


def _lead():
    return {"id": "lead-1", "email": "a@b.com", "name": "Ana", "company": "BankCo",
            "role": "CISO", "stage": "REGISTERED", "event_id": "ev-1",
            "lead_enrichment": {"sector": "financial services", "real_role": "CISO", "company": "BankCo"}}


def _sb():
    sb = MagicMock()
    sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": "msg-1"}]
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    return sb


async def test_send_email_sends_html_and_text_and_stores_text():
    from app.services import resend_service
    sb = _sb()
    sent = {}
    def fake_send(payload):
        sent.update(payload)
        return {"id": "resend-1"}
    with patch.object(resend_service, "get_supabase", return_value=sb), \
         patch.object(resend_service.resend.Emails, "send", side_effect=fake_send):
        await resend_service.send_email(_lead(), "welcome", custom_note="Olá", phase="pre_event")

    assert "html" in sent and "text" in sent
    assert "<table" in sent["html"].lower()       # HTML real
    assert "<table" not in sent["text"].lower()   # text puro
    # messages.body recebeu TEXTO (não HTML): procura a chamada de insert
    insert_args = str(sb.table.return_value.insert.call_args)
    assert "<table" not in insert_args


async def test_send_email_falls_back_to_text_if_render_raises():
    from app.services import resend_service
    sb = _sb()
    sent = {}
    with patch.object(resend_service, "get_supabase", return_value=sb), \
         patch.object(resend_service, "render_html", side_effect=RuntimeError("boom")), \
         patch.object(resend_service.resend.Emails, "send", side_effect=lambda p: sent.update(p) or {"id": "r"}):
        result = await resend_service.send_email(_lead(), "welcome", custom_note="x")

    assert "text" in sent           # ainda enviou
    assert "error" not in result    # não falhou
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_send_email_html.py -q`
Expected: FAIL — `send_email` ainda não envia `html` / `render_html` não importado em `resend_service`.

- [ ] **Step 3: Modificar `send_email`**

Em `backend/app/services/resend_service.py`:

(a) No topo, adicione o import:
```python
from app.services.email_templates import render_html
```

(b) Mude a assinatura (linha ~429):
```python
async def send_email(lead: dict, template_key: str, custom_note: str = "", phase: str = "pre_event", cta_url: str | None = None) -> dict:
```

(c) Após `body = template["body"].format(**ctx)` (linha ~485), monte o HTML com fallback:
```python
    subject = template["subject"].format(**ctx)
    body = template["body"].format(**ctx)

    # HTML é best-effort: se render falhar, envia só texto (nunca bloqueia o envio).
    try:
        html_body = render_html(template_key, ctx, cta_url)
    except Exception:
        html_body = None
```

(d) No payload do Resend (linha ~506), inclua o html quando houver:
```python
        payload = {
            "from": settings.resend_from_email,
            "to": [lead["email"]],
            "subject": subject,
            "text": body,
        }
        if html_body:
            payload["html"] = html_body
        response = await asyncio.to_thread(lambda: resend.Emails.send(payload))
```

O `messages.insert` com `body=body` (texto) permanece inalterado.

- [ ] **Step 4: Rodar os testes (novos + existentes de send_email/régua)**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_send_email_html.py tests/ -q`
Expected: PASS (todos; o contrato externo de `send_email` segue compatível — `cta_url` tem default)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/resend_service.py backend/tests/test_send_email_html.py
git commit -m "feat(email): send_email envia html+text com fallback; body segue texto"
```

---

## Task 7: Repassar `cta_url` no tool_executor (MVP: None → fallback landing)

**Files:**
- Modify: `backend/app/agent/tool_executor.py` (`_send_followup`, `_send_pre_event_msg`)

- [ ] **Step 1: Confirmar o estado atual das funções**

Leia `backend/app/agent/tool_executor.py` e localize `_send_pre_event_msg` e `_send_followup`. Ambas chamam `send_email(lead, template, custom_note, phase=...)`. Como `cta_url` tem default `None` em `send_email` (Task 6), **nenhuma mudança é estritamente necessária** para o MVP — o botão calcom cai no fallback landing automaticamente.

- [ ] **Step 2: Tornar explícito (documentar a intenção do MVP)**

Para deixar claro no código que o wire estruturado é uma melhoria futura, adicione um comentário em `_send_followup`, logo antes da chamada a `send_email`:

```python
    # MVP: o link do Cal.com vai no custom_note (texto). O botão "Agendar" do HTML cai
    # no fallback landing (cta_url=None). Wire estruturado agente→botão = melhoria futura.
    result = await send_email(lead, template, custom_note, phase="post_event")
```

(Não altere a lógica — apenas o comentário. Se preferir, pode pular esta task; ela é puramente documental. Marque o checkbox se decidir não mexer.)

- [ ] **Step 3: Rodar a suíte de agente**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_agent.py -q`
Expected: PASS

- [ ] **Step 4: Commit (se houve mudança)**

```bash
git add backend/app/agent/tool_executor.py
git commit -m "docs(email): nota MVP sobre cta_url no follow-up"
```

---

## Task 8: Documentação — `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Adicionar a nota no `CLAUDE.md`**

Na seção de invariantes (após a nota dos emails/régua existente, perto do bloco de `resend_service`), adicione:

```markdown
**Emails HTML (identidade Vigil):** o corpo dos emails é renderizado em HTML por
`app/services/email_templates.py` — um shell único (header navy "Vigil Summit", card
branco, footer com assinatura, CSS inline + tabelas Outlook-safe) + 17 miolos em
`TEMPLATE_BODIES_HTML` que reusam os mesmos `{placeholders}` dos textos em
`resend_service.TEMPLATES`. `send_email` envia `html` E `text` (fallback de
entregabilidade); `messages.body` guarda o TEXTO (dashboard limpo). Todo valor de `ctx`
passa por `_esc` (`html.escape`) antes de entrar no HTML — defesa de injeção via
nome/empresa/custom_note. O CTA é contextual por template (`CTA_MAP`): pré-evento →
landing (`FRONTEND_URL`), pós-evento/no-show → link Cal.com (`cta_url`), com fallback
landing se ausente/inválido. `render_html` é best-effort: se falhar, `send_email` envia
só texto (nunca bloqueia o envio). Mudança de template HTML exige redeploy do Railway.
```

- [ ] **Step 2: Rodar a suíte completa (regressão final)**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS (toda a suíte)

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: emails HTML (shell Vigil, html+text, escape, CTA contextual)"
```

---

## Verificação final (após todas as tasks)

- [ ] `cd backend && ./venv/Scripts/python.exe -m pytest tests/ -q` → tudo verde
- [ ] Sanity de render dos 17: nenhum `KeyError` de placeholder (coberto por `test_all_17_templates_render`)
- [ ] Smoke manual (após redeploy do Railway): cadastrar lead em modo demo → abrir o email de boas-vindas recebido → confirmar header Vigil, corpo estilizado, botão "Confirmar presença", footer com assinatura. Verificar no dashboard/drawer que `messages.body` segue legível (texto, sem tags).
