# Multi-Provider LLM (Anthropic/OpenAI) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every LLM call in the project auto-select Anthropic or OpenAI based on which API key is present in the environment, with zero behavior change when only the Anthropic key is set.

**Architecture:** A new `backend/app/llm/` package isolates the agent orchestrator from provider dialects via hand-written adapters. Each adapter owns its native `messages` list and exposes a common interface (`init_messages`, `create_turn`, `append_assistant`, `append_tool_results`) returning normalized `Turn`/`ToolCall` types, so the tool-use loop is identical for both providers. The frontend chatbot (separate stack, streaming) gets its own provider branch but emits an identical SSE shape so the widget is untouched.

**Tech Stack:** FastAPI (Python 3.13), `anthropic==0.40.0`, `openai>=1.30.0`, Next.js 14 (TypeScript), `@anthropic-ai/sdk`, `openai` (npm), pytest (`asyncio_mode=auto`, `pythonpath=.`).

**Source spec:** `docs/superpowers/specs/2026-05-31-multi-provider-llm-design.md`

**Environment note:** Run all backend commands from `backend/` using the venv interpreter: `venv\Scripts\python.exe` (Windows). pytest is configured in `backend/pytest.ini` with `asyncio_mode = auto`, so `async def test_*` functions run automatically without a decorator.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/app/llm/__init__.py` | Package marker |
| `backend/app/llm/base.py` | Normalized types `ToolCall`, `Turn`; abstract `LLMAdapter` |
| `backend/app/llm/provider.py` | `detect_provider()`, `agent_model()`, `get_adapter()` factory |
| `backend/app/llm/anthropic_adapter.py` | Wraps `anthropic.AsyncAnthropic` |
| `backend/app/llm/openai_adapter.py` | Wraps `openai.AsyncOpenAI` |
| `backend/app/config.py` | LLM keys optional + OpenAI model settings + boot validator |
| `backend/app/agent/orchestrator.py` | Tool-use loop driven by the adapter (no inline message appends) |
| `backend/app/api/admin.py` | Provider-aware health ping + dynamic service row |
| `backend/requirements.txt` | Add `openai` |
| `backend/tests/test_config_validator.py` | Config validator unit tests (create) |
| `backend/tests/test_provider.py` | `detect_provider` unit tests (create — does not exist yet) |
| `backend/tests/test_llm_adapters.py` | Adapter conversion unit tests (create) |
| `backend/tests/test_agent.py` | UPDATE existing 8-test suite to use the adapter |
| `frontend/app/api/chat/route.ts` | Provider detection + OpenAI streaming branch (identical SSE out) |
| `frontend/package.json` | Add `openai` |
| `backend/.env.example`, `frontend/.env.example` | Document OpenAI vars |

**Verified pre-existing state (checked against the real repo):**
- `backend/tests/test_agent.py` is a **full, working 8-test suite** that patches `app.agent.orchestrator._get_client` and uses Anthropic-native `MagicMock` content blocks. The refactor removes `_get_client`, so the 4 tests that patch it will break; Task 7 updates them to patch `get_adapter` and use `Turn`/`ToolCall`, **preserving all 8 tests**.
- `backend/tests/test_provider.py` does **not** exist — Task 3 creates it.
- `openai` is **not** installed in the venv — Task 1 adds it to requirements and installs it.
- No `conftest.py`. Config is `backend/pytest.ini` (`asyncio_mode=auto`, `pythonpath=.`).

---

### Task 1: Dependencies + config (keys optional, OpenAI models, boot validator)

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`
- Test: `backend/tests/test_config_validator.py` (create)

- [ ] **Step 1: Add the openai dependency**

Edit `backend/requirements.txt` — add a line right after `anthropic==0.40.0`:

```
openai>=1.30.0,<2
```

- [ ] **Step 2: Install it into the venv**

Run: `cd backend && venv\Scripts\python.exe -m pip install "openai>=1.30.0,<2"`
Expected: `Successfully installed openai-...`. Confirms the adapter/tests in later tasks can import it.

- [ ] **Step 3: Write the failing test for the config validator**

Create `backend/tests/test_config_validator.py`:

```python
import importlib
import pytest


def _reload_config(monkeypatch, anthropic, openai):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    if anthropic is not None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", anthropic)
    if openai is not None:
        monkeypatch.setenv("OPENAI_API_KEY", openai)
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    import app.config as cfg
    importlib.reload(cfg)
    return cfg


def test_anthropic_only_boots(monkeypatch):
    cfg = _reload_config(monkeypatch, anthropic="sk-ant-x", openai=None)
    assert cfg.settings.anthropic_api_key == "sk-ant-x"
    assert cfg.settings.openai_api_key == ""


def test_openai_only_boots(monkeypatch):
    cfg = _reload_config(monkeypatch, anthropic=None, openai="sk-openai-x")
    assert cfg.settings.openai_api_key == "sk-openai-x"
    assert cfg.settings.openai_agent_model == "gpt-4.1"
    assert cfg.settings.openai_chat_model == "gpt-4.1-mini"


def test_no_llm_key_raises(monkeypatch):
    with pytest.raises(Exception):
        _reload_config(monkeypatch, anthropic=None, openai=None)
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `cd backend && venv\Scripts\python.exe -m pytest tests/test_config_validator.py -v`
Expected: FAIL — `anthropic_api_key` is required today (no default) so `test_openai_only_boots` raises ValidationError; no validator exists so `test_no_llm_key_raises` does not raise the way the test asserts.

- [ ] **Step 5: Update config.py**

Replace the entire contents of `backend/app/config.py` with:

```python
from pydantic_settings import BaseSettings
from pydantic import model_validator

class Settings(BaseSettings):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_agent_model: str = "gpt-4.1"
    openai_chat_model: str = "gpt-4.1-mini"
    supabase_url: str
    supabase_key: str
    resend_api_key: str
    resend_from_email: str = "Vigil Summit <noreply@vigil.ai>"
    resend_webhook_secret: str = ""
    apollo_api_key: str = ""
    evolution_api_url: str = ""
    evolution_api_key: str = ""
    evolution_instance_name: str = "vigil"
    cal_api_key: str = ""
    cal_event_type_id: str = ""
    cal_webhook_secret: str = ""
    api_key: str = ""  # Header X-API-Key para endpoints operacionais e de leitura
    stale_job_threshold_hours: int = 2
    frontend_url: str = "http://localhost:3030"
    # Origens permitidas pelo CORS — separadas por vírgula em produção
    cors_origins: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}

    @model_validator(mode="after")
    def _require_one_llm_key(self):
        if not self.anthropic_api_key and not self.openai_api_key:
            raise ValueError(
                "Nenhum provedor de LLM configurado: defina ANTHROPIC_API_KEY ou OPENAI_API_KEY"
            )
        return self

settings = Settings()
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd backend && venv\Scripts\python.exe -m pytest tests/test_config_validator.py -v`
Expected: PASS (3 passed)

- [ ] **Step 7: Document the new env vars**

Edit `backend/.env.example` — replace the `# Anthropic` comment and `ANTHROPIC_API_KEY=sk-ant-...` line with:

```
# LLM provider — set ONE. If both are set, Anthropic wins.
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=
# OpenAI model overrides (defaults shown). Verify exact IDs against the OpenAI API.
OPENAI_AGENT_MODEL=gpt-4.1
OPENAI_CHAT_MODEL=gpt-4.1-mini
```

- [ ] **Step 8: Commit**

```bash
git add backend/requirements.txt backend/app/config.py backend/.env.example backend/tests/test_config_validator.py
git commit -m "feat(llm): optional LLM keys + OpenAI model settings + boot validator"
```

---

### Task 2: Normalized types + adapter interface (`llm/base.py`)

**Files:**
- Create: `backend/app/llm/__init__.py`
- Create: `backend/app/llm/base.py`
- Test: `backend/tests/test_llm_adapters.py` (create — base shape only here)

- [ ] **Step 1: Create the package marker**

Create `backend/app/llm/__init__.py`:

```python
# LLM provider abstraction package
```

- [ ] **Step 2: Write the failing test for the normalized types**

Create `backend/tests/test_llm_adapters.py`:

```python
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
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd backend && venv\Scripts\python.exe -m pytest tests/test_llm_adapters.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.llm.base'`

- [ ] **Step 4: Create base.py**

Create `backend/app/llm/base.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolCall:
    """A normalized tool call. Field names (name/input/id) MUST match what
    app.agent.memory.save_memory reads off each item — do not rename."""
    id: str
    name: str
    input: dict


@dataclass
class Turn:
    """One assistant turn, normalized across providers."""
    text: str                  # assistant's text (may be "")
    tool_calls: list[ToolCall]
    stop_reason: str           # normalized: "end_turn" | "tool_use"


class LLMAdapter(ABC):
    """Each adapter owns the native `messages` list format for its provider.
    The orchestrator treats `messages` as opaque and only handles Turn/ToolCall."""

    @abstractmethod
    def init_messages(self, system: str, user_text: str) -> list:
        """Return the initial native messages list for one agent run."""

    @abstractmethod
    async def create_turn(self, system: str, messages: list, tools: list, max_tokens: int) -> Turn:
        """Call the provider and return a normalized Turn. Records whatever native
        state it needs internally so append_assistant can reconstruct the turn."""

    @abstractmethod
    def append_assistant(self, messages: list, turn: Turn) -> None:
        """Append the assistant turn to `messages` in native format."""

    @abstractmethod
    def append_tool_results(self, messages: list, results: list[tuple[str, str]]) -> None:
        """Append tool results (each a (tool_call_id, content) pair) in native format."""
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd backend && venv\Scripts\python.exe -m pytest tests/test_llm_adapters.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/llm/__init__.py backend/app/llm/base.py backend/tests/test_llm_adapters.py
git commit -m "feat(llm): normalized ToolCall/Turn types and LLMAdapter interface"
```

---

### Task 3: Provider detection + factory (`llm/provider.py`)

**Files:**
- Create: `backend/app/llm/provider.py`
- Test: `backend/tests/test_provider.py` (create)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_provider.py`:

```python
import pytest
from app.llm import provider


def test_anthropic_wins_when_both_present(monkeypatch):
    monkeypatch.setattr(provider.settings, "anthropic_api_key", "sk-ant", raising=False)
    monkeypatch.setattr(provider.settings, "openai_api_key", "sk-openai", raising=False)
    assert provider.detect_provider() == "anthropic"


def test_openai_when_only_openai(monkeypatch):
    monkeypatch.setattr(provider.settings, "anthropic_api_key", "", raising=False)
    monkeypatch.setattr(provider.settings, "openai_api_key", "sk-openai", raising=False)
    assert provider.detect_provider() == "openai"


def test_anthropic_when_only_anthropic(monkeypatch):
    monkeypatch.setattr(provider.settings, "anthropic_api_key", "sk-ant", raising=False)
    monkeypatch.setattr(provider.settings, "openai_api_key", "", raising=False)
    assert provider.detect_provider() == "anthropic"


def test_raises_when_neither(monkeypatch):
    monkeypatch.setattr(provider.settings, "anthropic_api_key", "", raising=False)
    monkeypatch.setattr(provider.settings, "openai_api_key", "", raising=False)
    with pytest.raises(RuntimeError):
        provider.detect_provider()


def test_agent_model_matches_provider(monkeypatch):
    monkeypatch.setattr(provider.settings, "anthropic_api_key", "", raising=False)
    monkeypatch.setattr(provider.settings, "openai_api_key", "sk-openai", raising=False)
    monkeypatch.setattr(provider.settings, "openai_agent_model", "gpt-4.1", raising=False)
    assert provider.agent_model() == "gpt-4.1"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && venv\Scripts\python.exe -m pytest tests/test_provider.py -v`
Expected: FAIL with `AttributeError: module 'app.llm.provider' has no attribute 'detect_provider'`

- [ ] **Step 3: Create provider.py**

Create `backend/app/llm/provider.py`:

```python
from typing import Literal
from app.config import settings
from app.llm.base import LLMAdapter

Provider = Literal["anthropic", "openai"]


def detect_provider() -> Provider:
    """Anthropic wins if both keys are present. Raises if neither is set."""
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.openai_api_key:
        return "openai"
    raise RuntimeError(
        "Nenhum provedor de LLM configurado: defina ANTHROPIC_API_KEY ou OPENAI_API_KEY"
    )


def agent_model() -> str:
    """Model id for the orchestrator agent, per detected provider."""
    if detect_provider() == "anthropic":
        return "claude-sonnet-4-6"
    return settings.openai_agent_model


def get_adapter() -> LLMAdapter:
    """Factory: returns the adapter for the detected provider. Imports are local
    so the unused provider's SDK is never required at import time."""
    if detect_provider() == "anthropic":
        from app.llm.anthropic_adapter import AnthropicAdapter
        return AnthropicAdapter()
    from app.llm.openai_adapter import OpenAIAdapter
    return OpenAIAdapter()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && venv\Scripts\python.exe -m pytest tests/test_provider.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/provider.py backend/tests/test_provider.py
git commit -m "feat(llm): detect_provider + agent_model + get_adapter factory"
```

---

### Task 4: Anthropic adapter (`llm/anthropic_adapter.py`)

**Files:**
- Create: `backend/app/llm/anthropic_adapter.py`
- Test: `backend/tests/test_llm_adapters.py` (append)

- [ ] **Step 1: Write the failing test (append to the file)**

Append to `backend/tests/test_llm_adapters.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && venv\Scripts\python.exe -m pytest tests/test_llm_adapters.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.llm.anthropic_adapter'`

- [ ] **Step 3: Create anthropic_adapter.py**

Create `backend/app/llm/anthropic_adapter.py`:

```python
import anthropic
from app.config import settings
from app.llm.base import LLMAdapter, Turn, ToolCall


class AnthropicAdapter(LLMAdapter):
    def __init__(self):
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        # Maps id(turn) to the raw SDK content list, so append_assistant can
        # re-inject the exact native blocks Anthropic expects.
        self._raw_by_turn: dict[int, list] = {}

    def init_messages(self, system: str, user_text: str) -> list:
        # Anthropic takes `system` as a top-level param, not a message.
        return [{"role": "user", "content": user_text}]

    async def create_turn(self, system: str, messages: list, tools: list, max_tokens: int) -> Turn:
        resp = await self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            messages=messages,
        )
        text = ""
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, input=block.input))
        if resp.stop_reason == "end_turn":
            stop = "end_turn"
        elif resp.stop_reason == "tool_use":
            stop = "tool_use"
        else:
            stop = resp.stop_reason
        turn = Turn(text=text, tool_calls=tool_calls, stop_reason=stop)
        self._raw_by_turn[id(turn)] = resp.content
        return turn

    def append_assistant(self, messages: list, turn: Turn) -> None:
        messages.append({"role": "assistant", "content": self._raw_by_turn[id(turn)]})

    def append_tool_results(self, messages: list, results: list[tuple[str, str]]) -> None:
        content = [
            {"type": "tool_result", "tool_use_id": tid, "content": result}
            for tid, result in results
        ]
        messages.append({"role": "user", "content": content})
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && venv\Scripts\python.exe -m pytest tests/test_llm_adapters.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/anthropic_adapter.py backend/tests/test_llm_adapters.py
git commit -m "feat(llm): Anthropic adapter (native tool_use, owns message format)"
```

---

### Task 5: OpenAI adapter (`llm/openai_adapter.py`)

**Files:**
- Create: `backend/app/llm/openai_adapter.py`
- Test: `backend/tests/test_llm_adapters.py` (append)

- [ ] **Step 1: Write the failing test (append to the file)**

Append to `backend/tests/test_llm_adapters.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && venv\Scripts\python.exe -m pytest tests/test_llm_adapters.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.llm.openai_adapter'`

- [ ] **Step 3: Create openai_adapter.py**

Create `backend/app/llm/openai_adapter.py`:

```python
import json
from openai import AsyncOpenAI
from app.config import settings
from app.llm.base import LLMAdapter, Turn, ToolCall


class OpenAIAdapter(LLMAdapter):
    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_agent_model
        self._raw_by_turn: dict[int, dict] = {}

    @staticmethod
    def _to_openai_tools(tools: list) -> list:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t["input_schema"],
                },
            }
            for t in tools
        ]

    def init_messages(self, system: str, user_text: str) -> list:
        # OpenAI puts the system prompt as the first message.
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ]

    async def create_turn(self, system: str, messages: list, tools: list, max_tokens: int) -> Turn:
        resp = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=messages,
            tools=self._to_openai_tools(tools),
        )
        choice = resp.choices[0]
        msg = choice.message
        text = msg.content or ""
        tool_calls: list[ToolCall] = []
        raw_tool_calls = []
        for tc in (msg.tool_calls or []):
            try:
                parsed = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                parsed = {}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, input=parsed))
            raw_tool_calls.append({
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
            })
        if choice.finish_reason == "stop":
            stop = "end_turn"
        elif choice.finish_reason == "tool_calls":
            stop = "tool_use"
        else:
            stop = choice.finish_reason
        turn = Turn(text=text, tool_calls=tool_calls, stop_reason=stop)
        assistant_msg: dict = {"role": "assistant", "content": msg.content}
        if raw_tool_calls:
            assistant_msg["tool_calls"] = raw_tool_calls
        self._raw_by_turn[id(turn)] = assistant_msg
        return turn

    def append_assistant(self, messages: list, turn: Turn) -> None:
        messages.append(self._raw_by_turn[id(turn)])

    def append_tool_results(self, messages: list, results: list[tuple[str, str]]) -> None:
        for tid, result in results:
            messages.append({"role": "tool", "tool_call_id": tid, "content": result})
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && venv\Scripts\python.exe -m pytest tests/test_llm_adapters.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/openai_adapter.py backend/tests/test_llm_adapters.py
git commit -m "feat(llm): OpenAI adapter (tool translation, message format, turn normalization)"
```

---

### Task 6: Orchestrator uses the adapter

**Files:**
- Modify: `backend/app/agent/orchestrator.py` (full rewrite of the run loop)

- [ ] **Step 1: Rewrite orchestrator.py**

Replace the entire contents of `backend/app/agent/orchestrator.py` with:

```python
# backend/app/agent/orchestrator.py
import asyncio

from app.agent.tools import TOOLS
from app.agent.tool_executor import execute_tool
from app.agent.prompts import build_system_prompt
from app.agent.memory import save_memory
from app.agent.lock_manager import acquire_lock, release_lock, heartbeat_loop
from app.llm.provider import get_adapter
from app.db.client import get_supabase


async def run_agent(lead_id: str, trigger: str) -> str:
    acquired = await acquire_lock(lead_id)
    if not acquired:
        return f"Agent já em execução para lead {lead_id} — abortando"

    stop_heartbeat = asyncio.Event()
    heartbeat_task = asyncio.create_task(heartbeat_loop(lead_id, stop_heartbeat))

    try:
        sb = get_supabase()
        lead = await asyncio.to_thread(
            lambda: sb.table("leads")
            .select("*, lead_enrichment(*), events(*)")
            .eq("id", lead_id)
            .single()
            .execute()
            .data
        )
        if not lead:
            return f"Lead {lead_id} não encontrado"

        enrichment = lead.get("lead_enrichment")
        if isinstance(enrichment, list):
            lead["lead_enrichment"] = enrichment[0] if enrichment else {}

        adapter = get_adapter()
        system = await build_system_prompt(lead, trigger)
        user_text = f"Trigger recebido: {trigger}. Avalie o estado e tome a ação mais adequada."
        messages = adapter.init_messages(system, user_text)

        await save_memory(lead_id, "user", f"Trigger: {trigger}")

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            turn = await adapter.create_turn(system, messages, TOOLS, max_tokens=4096)

            if turn.text:
                await save_memory(lead_id, "assistant", turn.text, turn.tool_calls or None)

            if turn.stop_reason == "end_turn":
                break

            if turn.stop_reason == "tool_use" and turn.tool_calls:
                adapter.append_assistant(messages, turn)
                results: list[tuple[str, str]] = []
                for tc in turn.tool_calls:
                    result = await execute_tool(tc.name, tc.input, lead_id)
                    results.append((tc.id, result))
                adapter.append_tool_results(messages, results)
            else:
                break

        return f"Agente concluiu após {iteration} iterações."

    finally:
        stop_heartbeat.set()
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        await release_lock(lead_id)
```

- [ ] **Step 2: Verify it imports cleanly**

Run: `cd backend && venv\Scripts\python.exe -c "import app.agent.orchestrator"`
Expected: no output, exit 0. `_get_client` is gone; `save_memory` still receives objects with `.name/.input/.id` (now `ToolCall`).

- [ ] **Step 3: Commit**

```bash
git add backend/app/agent/orchestrator.py
git commit -m "refactor(agent): drive the tool-use loop through the LLM adapter"
```

---

### Task 7: Update the existing agent test suite to the adapter

**Files:**
- Modify: `backend/tests/test_agent.py`

The existing suite has 8 tests. Four are provider-agnostic and still pass unchanged (lock abort ×2, lead-not-found, execute_tool mismatch). Four patch `app.agent.orchestrator._get_client` (now removed) and build Anthropic-native `MagicMock` content blocks — those must be rewritten to patch `get_adapter` with a fake adapter returning `Turn`/`ToolCall`. This step preserves all 8 tests.

- [ ] **Step 1: Replace the four `_get_client`-based tests**

In `backend/tests/test_agent.py`, add this helper near the top (after the imports, before `_make_sb`):

```python
from app.llm.base import Turn, ToolCall


class _FakeAdapter:
    """Scripted adapter for orchestrator tests. Returns turns in order; records tool results."""
    def __init__(self, turns):
        self._turns = list(turns)
        self.tool_results = []

    def init_messages(self, system, user_text):
        return []

    async def create_turn(self, system, messages, tools, max_tokens):
        return self._turns.pop(0)

    def append_assistant(self, messages, turn):
        messages.append({"role": "assistant"})

    def append_tool_results(self, messages, results):
        self.tool_results.extend(results)
        messages.append({"role": "tool"})
```

Then replace the four tests that currently patch `_get_client`
(`test_run_agent_end_turn_single_iteration`, `test_run_agent_tool_use_then_end_turn`,
`test_run_agent_releases_lock_on_exception`, `test_run_agent_heartbeat_cancelled_on_completion`)
with these adapter-based versions:

```python
async def test_run_agent_end_turn_single_iteration():
    """Agent receives end_turn on first turn — completes in 1 iteration."""
    mock_sb = _make_sb(lead_data=_LEAD)
    fake = _FakeAdapter([Turn(text="Vou avaliar.", tool_calls=[], stop_reason="end_turn")])

    with patch("app.agent.orchestrator.get_supabase", return_value=mock_sb), \
         patch("app.agent.lock_manager.get_supabase", return_value=mock_sb), \
         patch("app.agent.orchestrator.get_adapter", return_value=fake), \
         patch("app.agent.orchestrator.build_system_prompt", new=AsyncMock(return_value="system")), \
         patch("app.agent.orchestrator.save_memory", new=AsyncMock()):

        from app.agent.orchestrator import run_agent
        result = await run_agent("lead-001", "NEW_LEAD_REGISTERED")

    assert "1 iterações" in result


async def test_run_agent_tool_use_then_end_turn():
    """Agent calls one tool, then ends on the next turn; tool result is round-tripped."""
    mock_sb = _make_sb(lead_data=_LEAD)
    fake = _FakeAdapter([
        Turn(text="Vou atualizar.",
             tool_calls=[ToolCall(id="tool-1", name="update_lead_stage", input={"lead_id": "lead-001", "stage": "ENRICHED"})],
             stop_reason="tool_use"),
        Turn(text="Feito.", tool_calls=[], stop_reason="end_turn"),
    ])

    with patch("app.agent.orchestrator.get_supabase", return_value=mock_sb), \
         patch("app.agent.lock_manager.get_supabase", return_value=mock_sb), \
         patch("app.agent.orchestrator.get_adapter", return_value=fake), \
         patch("app.agent.orchestrator.build_system_prompt", new=AsyncMock(return_value="system")), \
         patch("app.agent.orchestrator.save_memory", new=AsyncMock()), \
         patch("app.agent.orchestrator.execute_tool", new=AsyncMock(return_value="Stage atualizado")):

        from app.agent.orchestrator import run_agent
        result = await run_agent("lead-001", "NEW_LEAD_REGISTERED")

    assert "2 iterações" in result
    assert fake.tool_results == [("tool-1", "Stage atualizado")]


async def test_run_agent_releases_lock_on_exception():
    """Finally block releases the lock even when create_turn raises."""
    mock_sb = _make_sb(lead_data=_LEAD)

    class _BoomAdapter(_FakeAdapter):
        async def create_turn(self, system, messages, tools, max_tokens):
            raise RuntimeError("API offline")

    fake = _BoomAdapter([])
    deleted = []

    def track_delete():
        deleted.append(True)
        return MagicMock(eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=None))))

    mock_sb.table("agent_locks").delete.side_effect = lambda: track_delete()

    with patch("app.agent.orchestrator.get_supabase", return_value=mock_sb), \
         patch("app.agent.lock_manager.get_supabase", return_value=mock_sb), \
         patch("app.agent.orchestrator.get_adapter", return_value=fake), \
         patch("app.agent.orchestrator.build_system_prompt", new=AsyncMock(return_value="system")), \
         patch("app.agent.orchestrator.save_memory", new=AsyncMock()):

        from app.agent.orchestrator import run_agent
        with pytest.raises(RuntimeError):
            await run_agent("lead-001", "TEST")

    assert len(deleted) >= 1, "finally block must call delete to release the agent lock"


async def test_run_agent_heartbeat_cancelled_on_completion():
    """Heartbeat task is cancelled when the agent finishes normally."""
    mock_sb = _make_sb(lead_data=_LEAD)
    fake = _FakeAdapter([Turn(text="Done.", tool_calls=[], stop_reason="end_turn")])

    heartbeat_cancelled = []

    async def fake_heartbeat(lead_id, stop_event):
        try:
            await asyncio.sleep(9999)
        except asyncio.CancelledError:
            heartbeat_cancelled.append(True)
            raise

    with patch("app.agent.orchestrator.get_supabase", return_value=mock_sb), \
         patch("app.agent.lock_manager.get_supabase", return_value=mock_sb), \
         patch("app.agent.orchestrator.get_adapter", return_value=fake), \
         patch("app.agent.orchestrator.build_system_prompt", new=AsyncMock(return_value="sys")), \
         patch("app.agent.orchestrator.save_memory", new=AsyncMock()), \
         patch("app.agent.orchestrator.heartbeat_loop", fake_heartbeat):
        from app.agent.orchestrator import run_agent
        await run_agent("lead-001", "TEST")

    assert len(heartbeat_cancelled) == 1, "Heartbeat task must be cancelled after agent finishes"
```

Leave the other four tests (`test_run_agent_aborts_when_locked`, `test_run_agent_lead_not_found`,
`test_run_agent_aborts_when_lock_not_acquired`, `test_execute_tool_rejects_mismatched_lead_id`)
unchanged — they do not reference `_get_client` and remain valid.

- [ ] **Step 2: Run the full agent suite**

Run: `cd backend && venv\Scripts\python.exe -m pytest tests/test_agent.py -v`
Expected: PASS (8 passed). The four rewritten tests now drive the loop via the fake adapter; the four untouched tests still pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_agent.py
git commit -m "test(agent): drive loop tests through a fake adapter (preserve coverage)"
```

---

### Task 8: Provider-aware health check

**Files:**
- Modify: `backend/app/api/admin.py` (replace `_ping_anthropic`; update both service-builder functions)

- [ ] **Step 1: Replace `_ping_anthropic` with a provider-aware ping**

In `backend/app/api/admin.py`, replace the `_ping_anthropic` function (the `async def _ping_anthropic() -> str:` block) with:

```python
async def _ping_llm() -> tuple[str, str, str]:
    """Returns (status, service_name, detail) for the active LLM provider."""
    from app.llm.provider import detect_provider
    try:
        provider = detect_provider()
    except RuntimeError:
        return "warn", "LLM", "Nenhum provedor configurado"

    if provider == "anthropic":
        name, detail = "Claude (Anthropic)", "claude-sonnet-4-6"
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            await client.models.list()
            return "ok", name, detail
        except Exception:
            return "error", name, detail
    else:
        name, detail = "OpenAI", settings.openai_agent_model
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            await client.models.list()
            return "ok", name, detail
        except Exception:
            return "error", name, detail
```

- [ ] **Step 2: Make the config-only builder provider-aware**

In `_build_services_config_only()`, add this block at the very start of the function body (before `return [`):

```python
    from app.llm.provider import detect_provider
    try:
        _llm_provider = detect_provider()
    except RuntimeError:
        _llm_provider = None
    if _llm_provider == "anthropic":
        _llm_name, _llm_detail = "Claude (Anthropic)", "claude-sonnet-4-6"
    elif _llm_provider == "openai":
        _llm_name, _llm_detail = "OpenAI", settings.openai_agent_model
    else:
        _llm_name, _llm_detail = "LLM", "nenhum provedor configurado"
    _llm_status = "ok" if _llm_provider else "warn"
```

Then replace the first dict in the returned list (the `"Claude (Anthropic)"` entry) with:

```python
        {
            "name": _llm_name,
            "role": "Orquestrador do agente",
            "status": _llm_status,
            "detail": _llm_detail,
        },
```

- [ ] **Step 3: Make the live builder provider-aware**

In `_build_services_live()`, change the `asyncio.gather(...)` call and the first returned dict. Replace:

```python
    anthropic_s, resend_result, apollo_s, cal_s, evolution_s = await asyncio.gather(
        _ping_anthropic(),
        _ping_resend(),
        _ping_apollo(),
        _ping_cal(),
        _ping_evolution(),
    )
    resend_s, resend_detail = resend_result
    return [
        {"name": "Claude (Anthropic)", "role": "Orquestrador do agente", "status": anthropic_s, "detail": "claude-sonnet-4-6"},
```

with:

```python
    llm_result, resend_result, apollo_s, cal_s, evolution_s = await asyncio.gather(
        _ping_llm(),
        _ping_resend(),
        _ping_apollo(),
        _ping_cal(),
        _ping_evolution(),
    )
    llm_s, llm_name, llm_detail = llm_result
    resend_s, resend_detail = resend_result
    return [
        {"name": llm_name, "role": "Orquestrador do agente", "status": llm_s, "detail": llm_detail},
```

- [ ] **Step 4: Verify it imports**

Run: `cd backend && venv\Scripts\python.exe -c "import app.api.admin"`
Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/admin.py
git commit -m "feat(admin): provider-aware LLM health check (Anthropic or OpenAI)"
```

---

### Task 9: Frontend chatbot — OpenAI streaming branch

**Files:**
- Modify: `frontend/package.json` (add `openai`)
- Modify: `frontend/app/api/chat/route.ts` (provider detection + OpenAI branch)
- Modify: `frontend/.env.example`

- [ ] **Step 1: Add the openai npm dependency**

Edit `frontend/package.json` — add to `dependencies`, right after the `@anthropic-ai/sdk` line:

```json
    "openai": "^4.56.0",
```

- [ ] **Step 2: Install it**

Run: `cd frontend && npm install`
Expected: `openai` added; `package-lock.json` updated.

- [ ] **Step 3: Rewrite the chat route with a provider branch**

Replace the entire contents of `frontend/app/api/chat/route.ts` with:

```typescript
import Anthropic from '@anthropic-ai/sdk'
import OpenAI from 'openai'
import { NextRequest, NextResponse } from 'next/server'

type Provider = 'anthropic' | 'openai'

function detectProvider(): Provider | null {
  if (process.env.ANTHROPIC_API_KEY) return 'anthropic'
  if (process.env.OPENAI_API_KEY) return 'openai'
  return null
}

// Simple in-memory rate limiter: 20 requests per minute per IP.
const rateLimitMap = new Map<string, { count: number; resetAt: number }>()
const RATE_LIMIT = 20
const RATE_WINDOW_MS = 60_000

const MAX_MESSAGES = 20
const MAX_MESSAGE_LENGTH = 2000
const ALLOWED_ROLES = new Set(['user', 'assistant'])

function checkRateLimit(ip: string): boolean {
  const now = Date.now()
  if (rateLimitMap.size > 1000) {
    for (const [key, val] of rateLimitMap) {
      if (now > val.resetAt) rateLimitMap.delete(key)
    }
  }
  const entry = rateLimitMap.get(ip)
  if (!entry || now > entry.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_WINDOW_MS })
    return true
  }
  if (entry.count >= RATE_LIMIT) return false
  entry.count++
  return true
}

function systemPrompt(leadContext: string): string {
  return `Você é o assistente de inscrição do Vigil Summit — Segurança para a Era da IA.

Seu objetivo é ajudar executivos de segurança e TI a se inscreverem no evento e esclarecer dúvidas.

O evento:
- Data: em 30 dias
- Local: São Paulo, presencial
- Público: CISOs, CTOs, diretores de TI, gestores de risco
- Capacidade: 120 vagas
- Foco: cibersegurança, IA em segurança, conformidade (LGPD, ISO 27001, SOC 2)

Se o usuário quiser se inscrever, colete: nome, e-mail, empresa e cargo.
Seja conciso e profissional. Não invente informações sobre programação.

${leadContext ? `Contexto atual do lead: ${leadContext}` : ''}`
}

export async function POST(request: NextRequest) {
  const ip =
    request.headers.get('x-forwarded-for')?.split(',')[0].trim() ??
    request.headers.get('x-real-ip') ??
    'unknown'

  if (!checkRateLimit(ip)) {
    return NextResponse.json({ error: 'Muitas requisições. Tente novamente em breve.' }, { status: 429 })
  }

  const provider = detectProvider()
  if (!provider) {
    return NextResponse.json({ error: 'Nenhum provedor de LLM configurado' }, { status: 500 })
  }

  const { messages, leadContext: rawLeadContext } = await request.json()
  const leadContext = rawLeadContext ? String(rawLeadContext).slice(0, 300).replace(/[<>]/g, '') : ''

  if (!messages || !Array.isArray(messages) || messages.length === 0) {
    return NextResponse.json({ error: 'messages inválido' }, { status: 400 })
  }
  if (messages.length > MAX_MESSAGES) {
    return NextResponse.json({ error: `Máximo de ${MAX_MESSAGES} mensagens por requisição` }, { status: 400 })
  }
  for (const msg of messages) {
    if (!msg || typeof msg !== 'object') {
      return NextResponse.json({ error: 'Formato de mensagem inválido' }, { status: 400 })
    }
    if (!ALLOWED_ROLES.has(msg.role)) {
      return NextResponse.json({ error: `Role '${msg.role}' não permitido` }, { status: 400 })
    }
    if (typeof msg.content !== 'string') {
      return NextResponse.json({ error: 'Conteúdo de mensagem deve ser string' }, { status: 400 })
    }
    if (msg.content.length > MAX_MESSAGE_LENGTH) {
      return NextResponse.json({ error: `Mensagem excede ${MAX_MESSAGE_LENGTH} caracteres` }, { status: 400 })
    }
  }
  if (messages[0]?.role !== 'user') {
    return NextResponse.json({ error: 'A primeira mensagem deve ser do usuário' }, { status: 400 })
  }

  const encoder = new TextEncoder()
  const system = systemPrompt(leadContext)

  const stream = new ReadableStream({
    async start(controller) {
      const send = (text: string) =>
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ text })}\n\n`))
      try {
        if (provider === 'anthropic') {
          const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY! })
          const response = await client.messages.create({
            model: 'claude-haiku-4-5-20251001',
            max_tokens: 1024,
            stream: true,
            system,
            messages,
          })
          for await (const chunk of response) {
            if (chunk.type === 'content_block_delta' && chunk.delta.type === 'text_delta') {
              send(chunk.delta.text)
            }
          }
        } else {
          const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY! })
          const response = await client.chat.completions.create({
            model: process.env.OPENAI_CHAT_MODEL || 'gpt-4.1-mini',
            max_tokens: 1024,
            stream: true,
            messages: [{ role: 'system', content: system }, ...messages],
          })
          for await (const chunk of response) {
            const delta = chunk.choices[0]?.delta?.content
            if (delta) send(delta)
          }
        }
        controller.enqueue(encoder.encode('data: [DONE]\n\n'))
        controller.close()
      } catch (error) {
        const errMsg = error instanceof Error ? error.message : 'Erro interno'
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ error: errMsg })}\n\n`))
        controller.enqueue(encoder.encode('data: [DONE]\n\n'))
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  })
}
```

- [ ] **Step 4: Document the frontend env vars**

Edit `frontend/.env.example` — replace the existing `ANTHROPIC_API_KEY=sk-ant-...` line (and the comment above it) with:

```
# LLM provider for the chatbot — set ONE. If both set, Anthropic wins.
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-4.1-mini
```

- [ ] **Step 5: Verify the build compiles**

Run: `cd frontend && npm run build`
Expected: `✓ Compiled successfully`, `ƒ /api/chat` in the route list, exit 0.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/app/api/chat/route.ts frontend/.env.example
git commit -m "feat(chat): OpenAI streaming branch with identical SSE output"
```

---

### Task 10: Full backend test run + CLAUDE.md note

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Run the full backend suite**

Run: `cd backend && venv\Scripts\python.exe -m pytest -v`
Expected: all tests pass — existing suites (`test_leads_api`, `test_scheduler`, `test_state_machine`) plus the updated `test_agent.py` and the new `test_provider.py`, `test_llm_adapters.py`, `test_config_validator.py`.

- [ ] **Step 2: Add a multi-provider note to CLAUDE.md**

In `CLAUDE.md`, under the "Key Invariants" section, add this paragraph:

```markdown
**LLM provider auto-detection:** `backend/app/llm/provider.py` `detect_provider()` picks the LLM by env key — `ANTHROPIC_API_KEY` wins if both are set, else `OPENAI_API_KEY`, else a clear boot error (also enforced by the `config.py` validator). The orchestrator drives its tool-use loop through `get_adapter()` (an `LLMAdapter`), so the loop is provider-agnostic; each adapter owns its native `messages` format and returns normalized `Turn`/`ToolCall`. `ToolCall` fields (`name`/`input`/`id`) are load-bearing — `agent/memory.py` reads them directly. The frontend chatbot (`app/api/chat/route.ts`) has its own detection with the same rule and emits an identical SSE shape regardless of provider, so `ChatbotWidget.tsx` is untouched. OpenAI model ids come from `OPENAI_AGENT_MODEL` / `OPENAI_CHAT_MODEL` (defaults `gpt-4.1` / `gpt-4.1-mini`).
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document LLM provider auto-detection invariant"
```

---

## Live Verification (manual, after merge + deploy — per the spec's "teste vivo manual")

1. **Anthropic regression:** with only `ANTHROPIC_API_KEY` set, trigger the agent on a test lead → confirm enrich + messaging as before. Health panel shows "Claude (Anthropic) · ✓ Ativo".
2. **OpenAI path:** set only `OPENAI_API_KEY` (first verify `OPENAI_AGENT_MODEL` is a valid id via `openai.models.list()`), redeploy backend on Railway, trigger the agent → confirm the tool-use loop runs (enrich → message → schedule). Health panel shows "OpenAI · ✓ Ativo".
3. **Chatbot, both providers:** send a message in the landing widget with each key set → streaming reply works, no widget changes.
4. **Boot guard:** with neither key set, backend fails to start with the clear error; chat route returns 500 "Nenhum provedor de LLM configurado".

**Deploy note:** backend runs on Railway and requires a **manual redeploy** to pick up the code; the frontend auto-deploys on push to Vercel.

---

## Self-Review

**Spec coverage:** detect-by-key (Task 3) ✓; Anthropic-wins tie (Task 3 test) ✓; agent gpt-4.1 / chat gpt-4.1-mini via env (Tasks 1, 5, 9) ✓; hand-written adapters (Tasks 2,4,5) ✓; everything-scope = orchestrator (6) + health (8) + chatbot (9) ✓; config optional + validator (1) ✓; deps openai py+npm (1,9) ✓; tests: update existing + new detection (3,7) ✓. No gaps.

**Type consistency:** `ToolCall(id,name,input)` and `Turn(text,tool_calls,stop_reason)` are used identically in base.py, both adapters, orchestrator, and test_agent.py. `LLMAdapter` methods (`init_messages`, `create_turn`, `append_assistant`, `append_tool_results`) match across base, both adapters, the fake adapters in tests, and the orchestrator call sites. `get_adapter`/`detect_provider`/`agent_model` names consistent between provider.py, admin.py, orchestrator.py, and tests.

## Out of Scope (from spec)

- Providers other than Anthropic/OpenAI.
- Runtime provider switching (detection is at boot/per-request; changing keys needs redeploy).
- Behavioral parity between models (tool-use quality may differ between Sonnet and gpt-4.1).
- Streaming in the agent (stays non-streaming; only the chatbot streams).
