# backend/app/services/email_templates.py
"""Shell HTML único + miolos por template para os emails do Vigil Summit.

Email HTML robusto = tabelas + CSS inline (clientes ignoram <style>/<link>).
Todo valor interpolado vem de _esc() (defesa de injeção). O texto puro (fallback)
continua em resend_service.TEMPLATES; este módulo só cuida do HTML.
"""
import html as _html

from app.config import settings

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
}


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
