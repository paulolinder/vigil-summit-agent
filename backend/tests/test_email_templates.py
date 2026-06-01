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
