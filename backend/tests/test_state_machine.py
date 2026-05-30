# backend/tests/test_state_machine.py
from app.agent.state_machine import is_valid_transition, InvalidTransitionError, VALID_TRANSITIONS


def test_registered_to_enriched_is_valid():
    assert is_valid_transition("REGISTERED", "ENRICHED") is True

def test_converted_to_attended_is_invalid():
    assert is_valid_transition("CONVERTED", "ATTENDED") is False

def test_opted_out_has_no_valid_transitions():
    for target in ["REGISTERED", "ENRICHED", "CONFIRMED", "ATTENDED", "NO_SHOW",
                   "MEETING_SCHEDULED", "CONVERTED"]:
        assert is_valid_transition("OPTED_OUT", target) is False

def test_all_stages_can_transition_to_opted_out():
    for stage in VALID_TRANSITIONS:
        if stage != "OPTED_OUT":
            assert is_valid_transition(stage, "OPTED_OUT") is True, \
                f"{stage} → OPTED_OUT should be valid"

def test_invalid_transition_error_message():
    err = InvalidTransitionError("CONVERTED", "REGISTERED")
    assert "CONVERTED" in str(err)
    assert "REGISTERED" in str(err)
