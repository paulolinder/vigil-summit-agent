# backend/tests/test_prompts_regua.py
from datetime import datetime, timezone
from unittest.mock import patch
from app.agent.prompts import _build_regua


def test_fast_forward_uses_minutes_from_now():
    from app.config import settings
    with patch.object(settings, "demo_fast_forward", True):
        plan = _build_regua("NEW_LEAD_REGISTERED", None, "REGISTERED", False, False)
    today = datetime.now(timezone.utc).date().isoformat()
    assert today in plan          # âncoras são hoje + minutos
    assert "2026-08" not in plan  # NÃO usa as datas-calendário do evento


def test_normal_mode_uses_event_calendar_dates():
    from app.config import settings
    with patch.object(settings, "demo_fast_forward", False):
        plan = _build_regua("NEW_LEAD_REGISTERED", None, "REGISTERED", False, False)
    assert "2026-08" in plan      # t14/t10/... derivados do evento (15 Ago 2026)


async def test_system_prompt_includes_lead_id():
    """O lead_id autoritativo DEVE aparecer no prompt — senão o agente inventa um
    placeholder, a trava de segurança bloqueia o enrich e o funil trava em REGISTERED."""
    from unittest.mock import AsyncMock
    from app.agent.prompts import build_system_prompt

    lead = {
        "id": "abc-123-real-uuid",
        "stage": "REGISTERED",
        "lead_enrichment": None,
        "events": {"event_date": "2026-08-15T12:00:00+00:00"},
        "has_companion": False,
        "whatsapp_consent_at": None,
        "role": "CISO",
        "company": "BankCo",
    }
    with patch("app.agent.prompts._fetch_last_engagement",
               new=AsyncMock(return_value=("N/A", "False", "False"))), \
         patch("app.agent.prompts._fetch_memory",
               new=AsyncMock(return_value="Sem histórico.")):
        prompt = await build_system_prompt(lead, "NEW_LEAD_REGISTERED")

    assert "abc-123-real-uuid" in prompt
