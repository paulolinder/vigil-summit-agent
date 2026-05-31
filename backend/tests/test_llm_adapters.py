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


class _ABlock:
    def __init__(self, type, text=None, name=None, input=None, id=None):
        self.type = type
        self.text = text
        self.name = name
        self.input = input
        self.id = id


class _AResp:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


async def test_anthropic_adapter_normalizes_turn(monkeypatch):
    from app.llm.anthropic_adapter import AnthropicAdapter
    adapter = AnthropicAdapter()

    blocks = [
        _ABlock("text", text="raciocinio"),
        _ABlock("tool_use", name="enrich_lead", input={"lead_id": "x"}, id="toolu_1"),
    ]

    async def fake_create(**kwargs):
        return _AResp(blocks, "tool_use")

    class _Msgs:
        create = staticmethod(fake_create)

    class _Client:
        messages = _Msgs()

    monkeypatch.setattr(adapter, "_client", _Client(), raising=False)

    turn = await adapter.create_turn("sys", [], [], 4096)
    assert turn.text == "raciocinio"
    assert turn.stop_reason == "tool_use"
    assert turn.tool_calls[0].name == "enrich_lead"
    assert turn.tool_calls[0].id == "toolu_1"
    assert turn.tool_calls[0].input == {"lead_id": "x"}


def test_anthropic_append_tool_results_shape():
    from app.llm.anthropic_adapter import AnthropicAdapter
    adapter = AnthropicAdapter()
    messages = []
    adapter.append_tool_results(messages, [("toolu_1", "resultado")])
    assert messages[0]["role"] == "user"
    block = messages[0]["content"][0]
    assert block["type"] == "tool_result"
    assert block["tool_use_id"] == "toolu_1"
    assert block["content"] == "resultado"


def test_openai_tools_translation():
    from app.llm.openai_adapter import OpenAIAdapter
    adapter = OpenAIAdapter()
    anthropic_tools = [{
        "name": "enrich_lead",
        "description": "Enriquece o lead",
        "input_schema": {"type": "object", "properties": {"lead_id": {"type": "string"}}, "required": ["lead_id"]},
    }]
    out = adapter._to_openai_tools(anthropic_tools)
    assert out[0]["type"] == "function"
    assert out[0]["function"]["name"] == "enrich_lead"
    assert out[0]["function"]["description"] == "Enriquece o lead"
    assert out[0]["function"]["parameters"] == anthropic_tools[0]["input_schema"]


def test_openai_init_messages_has_system_first():
    from app.llm.openai_adapter import OpenAIAdapter
    adapter = OpenAIAdapter()
    msgs = adapter.init_messages("voce e um agente", "Trigger: NEW_LEAD")
    assert msgs[0] == {"role": "system", "content": "voce e um agente"}
    assert msgs[1] == {"role": "user", "content": "Trigger: NEW_LEAD"}


def test_openai_append_tool_results_shape():
    from app.llm.openai_adapter import OpenAIAdapter
    adapter = OpenAIAdapter()
    messages = []
    adapter.append_tool_results(messages, [("call_1", "resultado")])
    assert messages[0] == {"role": "tool", "tool_call_id": "call_1", "content": "resultado"}


async def test_openai_adapter_normalizes_turn(monkeypatch):
    from app.llm.openai_adapter import OpenAIAdapter
    adapter = OpenAIAdapter()

    class _Fn:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = arguments

    class _TC:
        def __init__(self, id, name, arguments):
            self.id = id
            self.type = "function"
            self.function = _Fn(name, arguments)

    class _Msg:
        content = "raciocinio"
        tool_calls = [_TC("call_1", "enrich_lead", '{"lead_id": "x"}')]

    class _Choice:
        message = _Msg()
        finish_reason = "tool_calls"

    class _Resp:
        choices = [_Choice()]

    async def fake_create(**kwargs):
        return _Resp()

    class _Compl:
        create = staticmethod(fake_create)

    class _Chat:
        completions = _Compl()

    class _Client:
        chat = _Chat()

    monkeypatch.setattr(adapter, "_client", _Client(), raising=False)

    turn = await adapter.create_turn("sys", [], [], 4096)
    assert turn.text == "raciocinio"
    assert turn.stop_reason == "tool_use"
    assert turn.tool_calls[0].name == "enrich_lead"
    assert turn.tool_calls[0].id == "call_1"
    assert turn.tool_calls[0].input == {"lead_id": "x"}
