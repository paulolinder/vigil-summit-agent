import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.utils.tokens import sign_confirm_token, verify_confirm_token

TEST_API_KEY = "test-key-vigil"


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


@pytest.fixture(autouse=True)
def _patch_key(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "api_key", TEST_API_KEY)


@pytest.fixture
def client():
    with patch("app.scheduler.runner.start_scheduler"):
        from app.main import app
        return TestClient(app)


def test_confirm_valid_token_confirms_and_runs_agent(client):
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value.data = "OK"
    ran = []
    def fake_run(lead_id, trigger):  # TestClient não awaita BackgroundTasks; sync basta
        ran.append((lead_id, trigger))
    with patch("app.api.leads.get_supabase", return_value=sb), \
         patch("app.agent.orchestrator.run_agent", fake_run):
        tok = sign_confirm_token("lead-1")
        resp = client.post("/api/leads/confirm", json={"token": tok})
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"
    args = str(sb.rpc.call_args)
    assert "CONFIRMED" in args and "ENRICHED" in args


def test_confirm_invalid_token_404(client):
    resp = client.post("/api/leads/confirm", json={"token": "garbage"})
    assert resp.status_code == 404


def test_confirm_already_set_does_not_rerun_agent(client):
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value.data = "ALREADY_SET"
    ran = []
    def fake_run(lead_id, trigger):  # ALREADY_SET nem deve agendar o task; ran fica vazio
        ran.append((lead_id, trigger))
    with patch("app.api.leads.get_supabase", return_value=sb), \
         patch("app.agent.orchestrator.run_agent", fake_run):
        tok = sign_confirm_token("lead-1")
        resp = client.post("/api/leads/confirm", json={"token": tok})
    assert resp.status_code == 200
    assert resp.json()["status"] == "already_confirmed"
    assert ran == []
