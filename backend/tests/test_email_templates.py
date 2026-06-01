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
    # botão não renderizado: nenhuma tabela-botão com a classe email-cta-button
    assert "email-cta-button" not in html


def test_perso_chip_renders_when_data_present():
    assert "CISO" in _perso_chip("CISO", "financial services")
    assert _perso_chip(None, None) == ""


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
    # Patch o settings que o módulo sob teste REALMENTE usa (email_templates.settings),
    # não app.config.settings — test_config_validator faz importlib.reload(app.config),
    # criando um novo objeto; render_html lê a referência presa no import deste módulo.
    from app.services import email_templates
    from app.services.email_templates import render_html
    monkeypatch.setattr(email_templates.settings, "frontend_url", "https://summit.vigil.ai")
    html = render_html("welcome", _min_ctx())
    assert "https://summit.vigil.ai" in html
    assert "Confirmar presença" in html


def test_render_calcom_cta_uses_cta_url():
    from app.services.email_templates import render_html
    html = render_html("demo_followup", _min_ctx(), cta_url="https://cal.com/vigil/x")
    assert "https://cal.com/vigil/x" in html
    assert "Agendar demonstração" in html


def test_render_calcom_without_url_falls_back_to_landing(monkeypatch):
    from app.services import email_templates
    from app.services.email_templates import render_html
    monkeypatch.setattr(email_templates.settings, "frontend_url", "https://summit.vigil.ai")
    html = render_html("thank_you", _min_ctx(), cta_url=None)
    assert "https://summit.vigil.ai" in html


def test_render_invalid_cta_url_falls_back(monkeypatch):
    from app.services import email_templates
    from app.services.email_templates import render_html
    monkeypatch.setattr(email_templates.settings, "frontend_url", "https://summit.vigil.ai")
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
