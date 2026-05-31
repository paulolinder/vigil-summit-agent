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
