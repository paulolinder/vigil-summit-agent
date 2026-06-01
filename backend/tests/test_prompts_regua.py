# backend/tests/test_prompts_regua.py
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock
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


def test_warmup_confirms_on_click():
    """WARMUP_T10 deve instruir o agente a marcar CONFIRMED quando o lead clicou no
    pedido de confirmação (o clique É a confirmação de presença)."""
    plan = _build_regua("WARMUP_T10", None, "ENRICHED", False, False)
    assert "CONFIRMED" in plan
    assert "update_lead_stage" in plan
    assert "clicked" in plan.lower() or "clicou" in plan.lower()


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


async def test_system_prompt_sanitizes_malicious_trigger():
    """O trigger (vindo do endpoint /run-agent) entra no prompt — control chars devem
    ser removidos por _safe, fechando a porta de injeção via trigger."""
    from app.agent.prompts import build_system_prompt
    lead = {
        "id": "lead-1", "stage": "REGISTERED", "lead_enrichment": None,
        "events": {}, "has_companion": False, "whatsapp_consent_at": None,
    }
    # trigger desconhecido + control chars → cai no fallback de _build_regua E na linha Trigger
    evil = "UNKNOWN\x00\x07INJECT"
    with patch("app.agent.prompts._fetch_last_engagement",
               new=AsyncMock(return_value=("N/A", "False", "False"))), \
         patch("app.agent.prompts._fetch_memory",
               new=AsyncMock(return_value="Sem histórico.")):
        prompt = await build_system_prompt(lead, evil)
    assert "\x00" not in prompt and "\x07" not in prompt


async def test_fetch_memory_sanitizes_content(monkeypatch):
    """Conteúdo de lead_memory (gerado por LLM) reentra no prompt — _safe remove control chars."""
    from app.agent import prompts
    rows = [{"role": "assistant", "content": "ok\x00\x07 INJECT", "created_at": "2026-05-31T00:00"}]
    sb = MagicMock()
    (sb.table.return_value.select.return_value.eq.return_value
        .order.return_value.limit.return_value.execute.return_value.data) = rows
    monkeypatch.setattr(prompts, "get_supabase", lambda: sb)
    out = await prompts._fetch_memory("lead-1")
    assert "\x00" not in out and "\x07" not in out
