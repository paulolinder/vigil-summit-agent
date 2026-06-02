import pytest
from app.utils.tokens import sign_confirm_token, verify_confirm_token


@pytest.fixture(autouse=True)
def _token_secret(monkeypatch):
    """Produção sempre tem api_key; o ambiente de teste não tem .env, então setamos
    um secret aqui. Patcheia o settings que tokens.py REALMENTE usa (não app.config.settings)
    — test_config_validator faz importlib.reload(app.config), trocando o objeto, então
    patchear app.config.settings não alcançaria a referência presa em tokens.py.
    O teste de fail-closed sobrescreve para vazio."""
    import app.utils.tokens as tok
    monkeypatch.setattr(tok.settings, "confirm_token_secret", "test-confirm-secret")


def test_token_roundtrip():
    lid = "abc-123-uuid"
    assert verify_confirm_token(sign_confirm_token(lid)) == lid


def test_empty_secret_fails_closed(monkeypatch):
    """Segurança: com secret vazio, verify NÃO pode aceitar um token (HMAC de chave vazia
    seria forjável). Deve rejeitar tudo (fail-closed) e sign deve recusar assinar."""
    import app.utils.tokens as tok
    # gera um token válido ANTES de zerar o secret
    valid = sign_confirm_token("lead-x")
    monkeypatch.setattr(tok.settings, "confirm_token_secret", "")
    monkeypatch.setattr(tok.settings, "api_key", "")
    # mesmo um token antes válido é rejeitado quando o secret está vazio
    assert verify_confirm_token(valid) is None
    # e um HMAC computado com chave vazia (forjável) também é rejeitado
    import hmac, hashlib
    forged_sig = hmac.new(b"", b"lead-x", hashlib.sha256).hexdigest()
    assert verify_confirm_token(f"lead-x.{forged_sig}") is None
    # sign recusa operar sem secret
    import pytest
    with pytest.raises(RuntimeError):
        tok.sign_confirm_token("lead-x")


def test_token_tampered_returns_none():
    tok = sign_confirm_token("abc-123-uuid")
    assert verify_confirm_token(tok + "x") is None


def test_token_malformed_returns_none():
    assert verify_confirm_token("no-dot") is None
    assert verify_confirm_token("") is None
    assert verify_confirm_token(None) is None
