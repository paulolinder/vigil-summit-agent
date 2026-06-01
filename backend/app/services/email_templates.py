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
