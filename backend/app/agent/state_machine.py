# backend/app/agent/state_machine.py

VALID_TRANSITIONS: dict[str, set[str]] = {
    "REGISTERED":        {"ENRICHED", "OPTED_OUT"},
    "ENRICHED":          {"CONFIRMED", "NO_SHOW", "OPTED_OUT"},
    "CONFIRMED":         {"ATTENDED", "NO_SHOW", "OPTED_OUT"},
    "ATTENDED":          {"MEETING_SCHEDULED", "OPTED_OUT"},
    "NO_SHOW":           {"MEETING_SCHEDULED", "OPTED_OUT"},
    "MEETING_SCHEDULED": {"CONVERTED", "OPTED_OUT"},
    "CONVERTED":         {"OPTED_OUT"},
    "OPTED_OUT":         set(),
}


def is_valid_transition(from_stage: str, to_stage: str) -> bool:
    return to_stage in VALID_TRANSITIONS.get(from_stage, set())


class InvalidTransitionError(Exception):
    def __init__(self, from_stage: str, to_stage: str):
        super().__init__(f"Transição inválida de stage: {from_stage} → {to_stage}")
        self.from_stage = from_stage
        self.to_stage = to_stage
