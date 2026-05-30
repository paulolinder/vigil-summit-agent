import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

TEST_API_KEY = "test-key-vigil"

@pytest.fixture(autouse=True)
def patch_api_key(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "api_key", TEST_API_KEY)

@pytest.fixture
def client():
    # mock start_scheduler para evitar conexão real ao Supabase no lifespan
    with patch("app.scheduler.runner.start_scheduler"):
        from app.main import app
        return TestClient(app)

@pytest.fixture
def mock_supabase():
    with patch("app.api.leads.get_supabase") as mock:
        yield mock

@pytest.fixture
def mock_bg_task():
    # patch no módulo onde run_agent é definido, não onde é importado localmente
    with patch("app.agent.orchestrator.run_agent") as mock:
        mock.return_value = None
        yield mock

def test_create_lead_success(client, mock_supabase, mock_bg_task):
    mock_supabase.return_value.table.return_value.insert.return_value.execute.return_value.data = [{
        "id": "lead-uuid-001",
        "stage": "REGISTERED"
    }]

    resp = client.post("/api/leads/", json={
        "event_id": "event-uuid-001",
        "name": "Maria Santos",
        "email": "maria@banco.com.br",
        "company": "Banco Itararé",
        "role": "CISO",
        "consent": True
    })

    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "lead-uuid-001"
    assert data["stage"] == "REGISTERED"

def test_create_lead_without_consent_rejected(client):
    resp = client.post("/api/leads/", json={
        "event_id": "event-uuid-001",
        "name": "Carlos Mendes",
        "email": "carlos@empresa.com",
        "company": "Empresa SA",
        "role": "CTO",
        "consent": False
    })

    assert resp.status_code == 422
    body = resp.json()
    assert any("Consentimento LGPD" in str(e) for e in body.get("detail", []))

def test_create_lead_invalid_email_rejected(client):
    resp = client.post("/api/leads/", json={
        "event_id": "event-uuid-001",
        "name": "Pedro Alves",
        "email": "nao-e-um-email",
        "company": "Empresa SA",
        "role": "Diretor",
        "consent": True
    })

    assert resp.status_code == 422

def test_checkin_lead_not_found(client, mock_supabase):
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

    resp = client.post(
        "/api/leads/lead-inexistente/checkin",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert resp.status_code == 404

def test_deletion_request_anonymizes(client, mock_supabase):
    """POST deletion-request now returns 202 (sends email token, does not anonymize directly)."""
    from unittest.mock import patch, AsyncMock
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "lead-uuid-001", "email": "maria@banco.com.br"}
    ]
    mock_supabase.return_value.table.return_value.insert.return_value.execute.return_value.data = [{"id": "tok-001"}]

    with patch("app.api.leads.send_deletion_email", new=AsyncMock(return_value=None)):
        resp = client.post("/api/leads/deletion-request", json={"email": "maria@banco.com.br"})

    assert resp.status_code == 202
    assert resp.json()["status"] == "confirmation_sent"


def test_resend_webhook_returns_503_when_secret_not_configured(client):
    """Webhook must return 503 (not 200) when RESEND_WEBHOOK_SECRET is not set."""
    from unittest.mock import patch
    with patch("app.api.webhooks.settings") as mock_settings:
        mock_settings.resend_webhook_secret = ""
        resp = client.post(
            "/api/webhooks/resend",
            json={"type": "email.opened", "data": {"email_id": "abc123"}},
        )
    assert resp.status_code == 503


def test_resend_webhook_returns_401_without_svix_headers(client):
    """Webhook must reject requests missing Svix headers when secret IS configured."""
    from unittest.mock import patch
    with patch("app.api.webhooks.settings") as mock_settings:
        mock_settings.resend_webhook_secret = "whsec_testkey1234567890testkey12345678"
        resp = client.post(
            "/api/webhooks/resend",
            json={"type": "email.opened", "data": {"email_id": "abc123"}},
        )
    assert resp.status_code == 401


def test_calcom_webhook_updates_lead_stage_on_booking_created(client):
    """Cal.com BOOKING_CREATED webhook must update matching lead stage to MEETING_SCHEDULED."""
    with patch("app.api.webhooks.get_supabase") as mock_sb:
        mock_sb.return_value.table.return_value.update.return_value.eq.return_value.neq.return_value.execute.return_value = None

        resp = client.post("/api/webhooks/calcom", json={
            "triggerEvent": "BOOKING_CREATED",
            "payload": {
                "attendees": [{"email": "maria@banco.com.br", "name": "Maria Santos"}]
            }
        })
    assert resp.status_code == 200
    assert resp.json()["received"] is True


def test_calcom_webhook_ignores_non_booking_events(client):
    """Cal.com webhook must return 200 without DB changes for non-BOOKING_CREATED events."""
    resp = client.post("/api/webhooks/calcom", json={
        "triggerEvent": "BOOKING_CANCELLED",
        "payload": {"attendees": [{"email": "test@test.com"}]}
    })
    assert resp.status_code == 200


def test_deletion_request_returns_202_and_does_not_anonymize_immediately(client, mock_supabase):
    """Step 1: POST deletion-request sends email token, returns 202, does NOT anonymize yet."""
    from unittest.mock import patch, AsyncMock

    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "lead-uuid-001", "email": "maria@banco.com.br"}
    ]
    mock_supabase.return_value.table.return_value.insert.return_value.execute.return_value.data = [{"id": "tok-001"}]

    with patch("app.api.leads.send_deletion_email", new=AsyncMock(return_value=None)):
        resp = client.post("/api/leads/deletion-request", json={"email": "maria@banco.com.br"})

    assert resp.status_code == 202
    assert resp.json()["status"] == "confirmation_sent"
    # MUST NOT have anonymized anything
    mock_supabase.return_value.table.return_value.update.assert_not_called()


def test_deletion_request_returns_202_for_unknown_email(client, mock_supabase):
    """Anti-enumeration: unknown email also returns 202 (not 404)."""
    from unittest.mock import patch, AsyncMock

    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with patch("app.api.leads.send_deletion_email", new=AsyncMock(return_value=None)):
        resp = client.post("/api/leads/deletion-request", json={"email": "unknown@test.com"})

    assert resp.status_code == 202
    assert resp.json()["status"] == "confirmation_sent"


def test_deletion_confirm_anonymizes_with_valid_token(client, mock_supabase):
    """Step 2: GET confirm?token= executes anonymization when token is valid."""
    import secrets
    from datetime import datetime, timezone, timedelta

    valid_token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    # deletion_tokens lookup
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.gt.return_value.is_.return_value.single.return_value.execute.return_value.data = {
        "id": "tok-001",
        "email": "maria@banco.com.br",
        "token": valid_token,
        "expires_at": expires_at,
    }
    # mark token used
    mock_supabase.return_value.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    # leads lookup
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "lead-uuid-001"}
    ]

    resp = client.get(f"/api/leads/deletion-request/confirm?token={valid_token}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "anonymized"


def test_deletion_confirm_rejects_expired_or_invalid_token(client, mock_supabase):
    """Expired/invalid token returns 404."""
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.gt.return_value.is_.return_value.single.return_value.execute.return_value.data = None

    resp = client.get("/api/leads/deletion-request/confirm?token=invalid-token")
    assert resp.status_code == 404
