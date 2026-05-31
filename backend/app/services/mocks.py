# backend/app/services/mocks.py
"""Geradores determinísticos para o modo demo (sem chaves de API pagas).

O enrichment é uma função pura de `email`: o mesmo email sempre produz o mesmo
perfil. O campo `sector` sai no vocabulário de indústria do Apollo (chaves de
`_APOLLO_TO_SECTOR` em resend_service.py) para casar com a personalização por setor.
"""
import hashlib

# Setores: subconjunto EXPLÍCITO das chaves de _APOLLO_TO_SECTOR (resend_service.py).
# Teste anti-drift garante que todos pertencem ao mapa.
_SECTOR_POOL = [
    "financial services",
    "computer software",
    "hospital & health care",
    "manufacturing",
    "government administration",
    "telecommunications",
    "retail",
    "oil & energy",
]

_DM_TITLES = [
    "Chief Information Security Officer",
    "Chief Technology Officer",
    "VP of Information Security",
    "Diretor de Tecnologia da Informação",
    "Head of Cybersecurity",
]
_NON_DM_TITLES = [
    "Security Analyst",
    "IT Manager",
    "Infrastructure Engineer",
    "Risk & Compliance Analyst",
]
_COMPANY_SIZE_POOL = ["180", "650", "1200", "3400", "8000"]
_SECURITY_SIGNALS_POOL = [
    "pesquisou soluções de Zero Trust nos últimos 30 dias",
    "baixou um whitepaper sobre conformidade LGPD",
    "participou de um webinar sobre detecção de ameaças com IA",
    "visitou páginas sobre resposta a incidentes",
]

_GENERIC_DOMAINS = {
    "gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "live.com",
}
_SYNTHETIC_COMPANIES = ["Acme Security", "Nimbus Tech", "Fortaleza Digital", "Vértice Sistemas"]
_DM_KEYWORDS = ("ciso", "cto", "cio", "diretor", "head", "vp", "chief", "gerente de risco")


def _seed(email: str) -> int:
    return int(hashlib.sha256(email.lower().encode()).hexdigest(), 16)


def _pick(pool: list, seed: int, shift: int):
    """Índice determinístico decorrelacionado por deslocamento de bits do seed."""
    return pool[(seed >> shift) % len(pool)]


def generate_enrichment(lead: dict) -> dict:
    email = (lead.get("email") or "").lower()
    seed = _seed(email)
    domain = email.split("@")[1] if "@" in email else "exemplo.com"

    company = lead.get("company")
    if not company:
        if domain in _GENERIC_DOMAINS:
            company = _pick(_SYNTHETIC_COMPANIES, seed, 0)
        else:
            company = domain.split(".")[0].capitalize()

    role = (lead.get("role") or "").lower()
    if role:
        is_dm = any(k in role for k in _DM_KEYWORDS)
    else:
        is_dm = ((seed >> 4) % 2) == 0
    title = _pick(_DM_TITLES if is_dm else _NON_DM_TITLES, seed, 8)

    sector = _pick(_SECTOR_POOL, seed, 16)
    company_size = _pick(_COMPANY_SIZE_POOL, seed, 24)
    signal = _pick(_SECURITY_SIGNALS_POOL, seed, 32)

    slug = (email.split("@")[0] or "lead").replace(".", "-")
    linkedin_url = f"https://linkedin.com/in/{slug}"

    summary = (
        f"{title} na {company}. Setor: {sector}. "
        f"Porte: {company_size} funcionários. "
        f"Sinal de interesse em segurança: {signal}."
    )

    return {
        "real_role": title,
        "company": company,
        "sector": sector,
        "company_size": company_size,
        "linkedin_url": linkedin_url,
        "is_decision_maker": is_dm,
        "enrichment_summary": summary,
        "source": "mock",
    }
