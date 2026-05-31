# backend/tests/test_services_mocks.py
from app.services.mocks import generate_enrichment
from app.services.resend_service import _APOLLO_TO_SECTOR


def test_deterministic_same_email_same_output():
    lead = {"email": "ciso@bigbank.com.br", "name": "Maria", "company": None, "role": None}
    a = generate_enrichment(lead)
    b = generate_enrichment(dict(lead))
    assert a == b


def test_sector_is_apollo_shaped():
    """sector DEVE ser uma chave de _APOLLO_TO_SECTOR — senão a personalização por setor degrada."""
    for local in ("a@x.com", "b@y.com.br", "c@z.io", "ciso@bank.com", "cto@health.org"):
        out = generate_enrichment({"email": local, "name": "X", "company": None, "role": None})
        assert out["sector"] in _APOLLO_TO_SECTOR, f"setor fora do mapa: {out['sector']}"


def test_role_keyword_implies_decision_maker():
    out = generate_enrichment({"email": "p@empresa.com", "name": "P", "company": "Empresa", "role": "CISO"})
    assert out["is_decision_maker"] is True


def test_generic_domain_gets_synthetic_company():
    out = generate_enrichment({"email": "alguem@gmail.com", "name": "A", "company": None, "role": None})
    assert out["company"] and out["company"].lower() != "gmail"


def test_output_has_parity_fields_no_security_signals():
    out = generate_enrichment({"email": "x@y.com", "name": "X", "company": None, "role": None})
    assert set(out.keys()) == {
        "real_role", "company", "sector", "company_size",
        "linkedin_url", "is_decision_maker", "enrichment_summary", "source",
    }
    assert out["source"] == "mock"
    assert "security_signals" not in out
