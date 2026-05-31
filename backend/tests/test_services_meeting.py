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
