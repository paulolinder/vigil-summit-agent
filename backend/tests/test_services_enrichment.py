# backend/tests/test_services_enrichment.py
import pytest
from unittest.mock import patch, MagicMock


async def test_uses_mock_when_no_apollo_key():
    from app.config import settings
    from app.services.enrichment import enrich_lead_data
    with patch.object(settings, "apollo_api_key", ""):
        out = await enrich_lead_data({"email": "ciso@bank.com", "company": None, "role": "CISO"})
    assert out["source"] == "mock"
    assert out["is_decision_maker"] is True


async def test_uses_apollo_when_key_present():
    from app.config import settings
    from app.services.enrichment import enrich_lead_data

    apollo_json = {
        "person": {
            "title": "CISO",
            "seniority": "c_suite",
            "linkedin_url": "https://linkedin.com/in/real",
            "organization": {"name": "RealBank", "industry": "banking", "estimated_num_employees": 5000},
        }
    }
    fake_resp = MagicMock()
    fake_resp.json.return_value = apollo_json
    fake_resp.raise_for_status.return_value = None

    class _FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return fake_resp

    with patch.object(settings, "apollo_api_key", "real-key"), \
         patch("app.services.enrichment.httpx.AsyncClient", return_value=_FakeClient()):
        out = await enrich_lead_data({"email": "ciso@realbank.com", "company": "RealBank"})

    assert out["source"] == "apollo"
    assert out["real_role"] == "CISO"
    assert out["is_decision_maker"] is True
    assert out["company"] == "RealBank"


async def test_tool_executor_enrich_persists_and_transitions():
    """_enrich_lead chama o serviço, faz upsert e tenta a transição REGISTERED->ENRICHED."""
    from app.config import settings
    tables = {}

    def get_table(name):
        tables.setdefault(name, MagicMock())
        return tables[name]

    sb = MagicMock()
    sb.table.side_effect = get_table
    sb.rpc = MagicMock(return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data="OK"))))
    tables_lead = get_table("leads")
    tables_lead.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "email": "ciso@bank.com", "name": "Maria", "company": None,
    }
    get_table("lead_enrichment").upsert.return_value.execute.return_value = MagicMock()

    from app.agent.tool_executor import _enrich_lead
    with patch.object(settings, "apollo_api_key", ""):
        result = await _enrich_lead("lead-001", sb)

    assert "enriquecido" in result.lower()
    get_table("lead_enrichment").upsert.assert_called_once()
    sb.rpc.assert_called()  # atomic_transition_lead_stage
