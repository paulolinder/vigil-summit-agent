# backend/app/services/enrichment.py
"""Fronteira de enriquecimento: Apollo real se a chave existir, senão mock determinístico.
Retorna um dict normalizado (SEM lead_id) — quem persiste/transita é o tool_executor."""
import httpx
from app.config import settings
from app.services.mocks import generate_enrichment

_DM_SENIORITIES = {"director", "vp", "c_suite", "owner", "partner", "founder"}


async def enrich_lead_data(lead: dict) -> dict:
    if settings.apollo_api_key:
        return await _enrich_via_apollo(lead)
    return generate_enrichment(lead)


async def _enrich_via_apollo(lead: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.apollo.io/api/v1/people/match",
            headers={"x-api-key": settings.apollo_api_key, "Content-Type": "application/json"},
            params={"email": lead["email"], "organization_name": lead.get("company")},
        )
        resp.raise_for_status()
        data = resp.json()

    person = data.get("person") or {}
    org = person.get("organization") or {}
    is_dm = person.get("seniority", "") in _DM_SENIORITIES

    return {
        "real_role": person.get("title"),
        "company": org.get("name") or lead.get("company"),
        "sector": org.get("industry"),
        "company_size": str(org.get("estimated_num_employees", "")),
        "linkedin_url": person.get("linkedin_url"),
        "is_decision_maker": is_dm,
        "enrichment_summary": (
            f"{person.get('title', 'profissional')} na {org.get('name', lead.get('company', ''))}. "
            f"Setor: {org.get('industry', 'N/A')}. "
            f"Tamanho: {org.get('estimated_num_employees', 'N/A')} funcionários."
        ),
        "source": "apollo",
    }
