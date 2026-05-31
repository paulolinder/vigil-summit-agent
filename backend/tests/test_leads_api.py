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
    # events table check (new validation)
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {"id": "event-uuid-001"}
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
    mock_supabase.return_value.rpc.return_value.execute.return_value.data = "NOT_FOUND"

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
    """Cal.com BOOKING_CREATED webhook sets MEETING_SCHEDULED when signature is valid."""
    import hashlib, hmac as hmac_lib, json as jsonlib
    from unittest.mock import AsyncMock
    secret = "test-valid-secret"
    payload_dict = {
        "triggerEvent": "BOOKING_CREATED",
        "payload": {"attendees": [{"email": "maria@banco.com.br", "name": "Maria Santos"}]}
    }
    body = jsonlib.dumps(payload_dict, separators=(',', ':')).encode()
    sig = "sha256=" + hmac_lib.new(secret.encode(), body, hashlib.sha256).hexdigest()

    with patch("app.api.webhooks.settings") as mock_settings, \
         patch("app.services.meeting.apply_booking_created", new=AsyncMock(return_value=None)) as mock_apply:
        mock_settings.cal_webhook_secret = secret
        resp = client.post(
            "/api/webhooks/calcom",
            content=body,
            headers={"content-type": "application/json", "X-Cal-Signature-256": sig},
        )
    assert resp.status_code == 200
    assert resp.json()["received"] is True
    mock_apply.assert_called_once_with("maria@banco.com.br")


def test_calcom_webhook_ignores_non_booking_events(client):
    """Cal.com webhook returns 200 without DB changes for non-BOOKING_CREATED events."""
    import hashlib, hmac as hmac_lib, json as jsonlib
    secret = "test-valid-secret"
    payload_dict = {"triggerEvent": "BOOKING_CANCELLED", "payload": {"attendees": [{"email": "test@test.com"}]}}
    body = jsonlib.dumps(payload_dict, separators=(',', ':')).encode()
    sig = "sha256=" + hmac_lib.new(secret.encode(), body, hashlib.sha256).hexdigest()

    with patch("app.api.webhooks.settings") as mock_settings:
        mock_settings.cal_webhook_secret = secret
        resp = client.post(
            "/api/webhooks/calcom",
            content=body,
            headers={"content-type": "application/json", "X-Cal-Signature-256": sig},
        )
    assert resp.status_code == 200


def test_deletion_request_returns_202_and_does_not_anonymize_immediately(client, mock_supabase):
    """Step 1: POST deletion-request returns 202. Side-effects run in background task."""
    from unittest.mock import patch, AsyncMock

    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "lead-uuid-001", "email": "maria@banco.com.br"}
    ]
    mock_supabase.return_value.table.return_value.insert.return_value.execute.return_value.data = [{"id": "tok-001"}]

    with patch("app.api.leads._issue_deletion_token", new=AsyncMock(return_value=None)):
        resp = client.post("/api/leads/deletion-request", json={"email": "maria@banco.com.br"})

    assert resp.status_code == 202
    assert resp.json()["status"] == "confirmation_sent"


def test_deletion_request_returns_202_for_unknown_email(client, mock_supabase):
    """Anti-enumeration: unknown email also returns 202 (not 404) and fires no background task."""
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    resp = client.post("/api/leads/deletion-request", json={"email": "unknown@test.com"})

    assert resp.status_code == 202
    assert resp.json()["status"] == "confirmation_sent"


def test_deletion_confirm_anonymizes_with_valid_token(client, mock_supabase):
    """Step 2: POST /confirm with token in body executes anonymization when token is valid."""
    import secrets
    from datetime import datetime, timezone, timedelta

    valid_token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    # deletion_tokens lookup — now keyed by token_hash, not plaintext token
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.gt.return_value.is_.return_value.single.return_value.execute.return_value.data = {
        "id": "tok-001",
        "email": "maria@banco.com.br",
        "token_hash": "irrelevant-in-mock",
        "expires_at": expires_at,
    }
    # mark token used
    mock_supabase.return_value.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    # leads lookup
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "lead-uuid-001"}
    ]

    # Token is now sent in POST body, not URL query string
    resp = client.post("/api/leads/deletion-request/confirm", json={"token": valid_token})
    assert resp.status_code == 200
    assert resp.json()["status"] == "anonymized"


def test_deletion_confirm_rejects_expired_or_invalid_token(client, mock_supabase):
    """Expired/invalid token returns 404."""
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.gt.return_value.is_.return_value.single.return_value.execute.return_value.data = None

    resp = client.post("/api/leads/deletion-request/confirm", json={"token": "invalid-token"})
    assert resp.status_code == 404


def test_create_lead_captures_real_ip_from_forwarded_for(client, mock_supabase, mock_bg_task):
    """consent_ip must be the first IP from X-Forwarded-For, not the proxy IP."""
    captured = {}
    original_insert = mock_supabase.return_value.table.return_value.insert

    def capture(data):
        captured.update(data)
        return original_insert.return_value

    mock_supabase.return_value.table.return_value.insert.side_effect = capture
    mock_supabase.return_value.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "lead-uuid-001", "stage": "REGISTERED"}
    ]
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {"id": "event-001"}

    resp = client.post(
        "/api/leads/",
        json={
            "event_id": "event-001",
            "name": "Test User",
            "email": "test@example.com",
            "company": "Test Co",
            "role": "CTO",
            "consent": True,
        },
        headers={"X-Forwarded-For": "203.0.113.42, 10.0.0.1"},
    )
    assert resp.status_code == 201
    assert captured.get("consent_ip") == "203.0.113.42"


def test_create_lead_rejects_invalid_event_id(client, mock_supabase):
    """Lead creation must return 404 if event_id doesn't exist."""
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

    resp = client.post("/api/leads/", json={
        "event_id": "evento-inexistente",
        "name": "Test",
        "email": "test@example.com",
        "company": "Co",
        "role": "CTO",
        "consent": True,
    })
    assert resp.status_code == 404


def test_list_leads_accepts_pagination_params(client, mock_supabase):
    """GET /api/leads/ must pass limit/offset to the query."""
    mock_supabase.return_value.table.return_value.select.return_value.range.return_value.execute.return_value.data = []

    resp = client.get(
        "/api/leads/?limit=50&offset=100",
        headers={"X-API-Key": TEST_API_KEY}
    )
    assert resp.status_code == 200


def test_list_leads_rejects_limit_over_500(client):
    """limit > 500 must return 400."""
    resp = client.get(
        "/api/leads/?limit=501",
        headers={"X-API-Key": TEST_API_KEY}
    )
    assert resp.status_code == 400


def test_calcom_webhook_returns_503_when_secret_not_configured(client):
    """Webhook returns 503 when CAL_WEBHOOK_SECRET is not set."""
    with patch("app.api.webhooks.settings") as mock_settings:
        mock_settings.cal_webhook_secret = ""
        resp = client.post("/api/webhooks/calcom", json={
            "triggerEvent": "BOOKING_CREATED",
            "payload": {"attendees": [{"email": "test@test.com"}]}
        })
    assert resp.status_code == 503


def test_calcom_webhook_returns_401_without_signature(client):
    """Webhook returns 401 when X-Cal-Signature-256 header is missing."""
    with patch("app.api.webhooks.settings") as mock_settings:
        mock_settings.cal_webhook_secret = "test-secret-for-calcom"
        resp = client.post("/api/webhooks/calcom", json={
            "triggerEvent": "BOOKING_CREATED",
            "payload": {"attendees": [{"email": "test@test.com"}]}
        })
    assert resp.status_code == 401


def test_calcom_webhook_accepts_valid_signature(client):
    """Webhook accepts request with valid HMAC-SHA256 signature."""
    import hashlib, hmac as hmac_lib, json as jsonlib
    from unittest.mock import AsyncMock
    secret = "test-secret-for-calcom-valid"
    payload_dict = {
        "triggerEvent": "BOOKING_CREATED",
        "payload": {"attendees": [{"email": "t@t.com"}]}
    }
    body = jsonlib.dumps(payload_dict, separators=(',', ':')).encode()
    sig = "sha256=" + hmac_lib.new(secret.encode(), body, hashlib.sha256).hexdigest()

    with patch("app.api.webhooks.settings") as mock_settings, \
         patch("app.services.meeting.apply_booking_created", new=AsyncMock(return_value=None)):
        mock_settings.cal_webhook_secret = secret
        resp = client.post(
            "/api/webhooks/calcom",
            content=body,
            headers={"content-type": "application/json", "X-Cal-Signature-256": sig},
        )
    assert resp.status_code == 200
    assert resp.json()["received"] is True


def test_checkin_lead_success(client, mock_supabase, mock_bg_task):
    """Successful checkin returns checked_in status."""
    mock_supabase.return_value.rpc.return_value.execute.return_value.data = "OK"

    resp = client.post(
        "/api/leads/lead-001/checkin",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "checked_in"


def test_checkin_lead_idempotent(client, mock_supabase):
    """Second checkin returns already_checked_in (idempotent)."""
    mock_supabase.return_value.rpc.return_value.execute.return_value.data = "ALREADY_SET"

    resp = client.post(
        "/api/leads/lead-001/checkin",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "already_checked_in"


def test_checkin_lead_invalid_transition(client, mock_supabase):
    """Checkin on OPTED_OUT or CONVERTED lead returns 409."""
    mock_supabase.return_value.rpc.return_value.execute.return_value.data = "INVALID_TRANSITION"

    resp = client.post(
        "/api/leads/lead-001/checkin",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert resp.status_code == 409
