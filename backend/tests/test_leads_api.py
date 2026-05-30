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
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "lead-uuid-001"}
    ]
    mock_supabase.return_value.table.return_value.update.return_value.eq.return_value.execute.return_value = None

    resp = client.post("/api/leads/deletion-request", json={"email": "maria@banco.com.br"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "anonymized"
