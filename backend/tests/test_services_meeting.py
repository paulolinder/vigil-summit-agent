# backend/tests/test_services_meeting.py
from unittest.mock import patch, MagicMock
import pytest


@pytest.mark.asyncio
async def test_apply_booking_created_transitions_each_lead():
    from app.services.meeting import apply_booking_created

    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "lead-1"}, {"id": "lead-2"},
    ]
    rpc_calls = []
    def rpc(fn, params):
        rpc_calls.append((fn, params))
        return MagicMock(execute=MagicMock(return_value=MagicMock(data="OK")))
    sb.rpc = MagicMock(side_effect=rpc)

    with patch("app.services.meeting.get_supabase", return_value=sb):
        await apply_booking_created("ciso@bank.com")

    assert len(rpc_calls) == 2
    for fn, params in rpc_calls:
        assert fn == "atomic_transition_lead_stage"
        assert params["p_target_stage"] == "MEETING_SCHEDULED"
        assert params["p_valid_from_stages"] == ["ATTENDED", "NO_SHOW"]


@pytest.mark.asyncio
async def test_generate_meeting_link_mock_inserts_simulated_booking():
    from app.config import settings
    from app.services.meeting import generate_meeting_link

    sb = MagicMock()
    inserted = {}
    def capture_insert(row):
        inserted.update(row)
        return MagicMock(execute=MagicMock(return_value=MagicMock(data=[{"id": "job-xyz"}])))
    sb.table.return_value.insert.side_effect = capture_insert

    with patch.object(settings, "cal_api_key", ""), \
         patch.object(settings, "cal_event_type_id", ""), \
         patch("app.services.meeting.get_supabase", return_value=sb), \
         patch("app.scheduler.runner.add_job_to_scheduler") as mock_add:
        out = await generate_meeting_link({"id": "lead-1", "name": "Ana", "email": "ana@x.com"})

    assert "SIMULADO" in out["note"]
    assert out["booking_link"].startswith("https://cal.com/")
    assert inserted["job_type"] == "SIMULATED_BOOKING"
    assert inserted["status"] == "PENDING"
    mock_add.assert_called_once()
