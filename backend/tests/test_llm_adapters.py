from app.llm.base import ToolCall, Turn


def test_toolcall_has_name_input_id():
    # memory.py reads t.name / t.input / t.id — these field names are load-bearing
    tc = ToolCall(id="call_1", name="enrich_lead", input={"lead_id": "x"})
    assert tc.name == "enrich_lead"
    assert tc.input == {"lead_id": "x"}
    assert tc.id == "call_1"


def test_turn_carries_text_toolcalls_stopreason():
    turn = Turn(text="pensando", tool_calls=[], stop_reason="end_turn")
    assert turn.text == "pensando"
    assert turn.tool_calls == []
    assert turn.stop_reason == "end_turn"
