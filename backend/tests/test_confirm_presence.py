from app.utils.tokens import sign_confirm_token, verify_confirm_token


def test_token_roundtrip():
    lid = "abc-123-uuid"
    assert verify_confirm_token(sign_confirm_token(lid)) == lid


def test_token_tampered_returns_none():
    tok = sign_confirm_token("abc-123-uuid")
    assert verify_confirm_token(tok + "x") is None


def test_token_malformed_returns_none():
    assert verify_confirm_token("no-dot") is None
    assert verify_confirm_token("") is None
    assert verify_confirm_token(None) is None
