import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

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


def _make_sb(lead_data=None, lock_insert_raises=False):
    """Build a per-table supabase mock for orchestrator tests."""
    tables = {}

    def get_table(name):
        if name not in tables:
            tables[name] = MagicMock()
        return tables[name]

    mock = MagicMock()
    mock.table.side_effect = get_table

    # rpc — atomic lock acquisition succeeds by default
    mock.rpc = MagicMock(
        return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data=True)))
    )

    # agent_locks — delete (cleanup) always succeeds
    tables["agent_locks"] = MagicMock()
    tables["agent_locks"].delete.return_value.eq.return_value.lt.return_value.execute.return_value = MagicMock()
    tables["agent_locks"].delete.return_value.eq.return_value.execute.return_value = MagicMock()

    if lock_insert_raises:
        tables["agent_locks"].insert.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )
    else:
        tables["agent_locks"].insert.return_value.execute.return_value = MagicMock()

    # leads — single row fetch
    tables["leads"] = MagicMock()
    tables["leads"].select.return_value.eq.return_value.single.return_value.execute.return_value.data = lead_data

    # lead_memory — insert
    tables["lead_memory"] = MagicMock()
    tables["lead_memory"].insert.return_value.execute.return_value = MagicMock()

    # messages — engagement fetch (empty by default)
    tables["messages"] = MagicMock()
    tables["messages"].select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

    return mock


_LEAD = {
    "id": "lead-001",
    "event_id": "event-001",
    "name": "Maria Santos",
    "email": "maria@banco.com",
    "company": "Banco Itararé",
    "role": "CISO",
    "stage": "REGISTERED",
    "has_companion": False,
    "whatsapp_consent_at": None,
    "lead_enrichment": None,
    "event": None,
}


async def test_run_agent_aborts_when_locked():
    """Mutex: if acquire_lock RPC returns False, run_agent aborts silently instead of running twice."""
    mock_sb = _make_sb(lock_insert_raises=False)  # lock_insert_raises no longer used
    mock_sb.rpc = MagicMock(
        return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data=False)))
    )
    with patch("app.agent.orchestrator.get_supabase", return_value=mock_sb), \
         patch("app.agent.lock_manager.get_supabase", return_value=mock_sb):
        from app.agent.orchestrator import run_agent
        result = await run_agent("lead-001", "TEST")
    from app.agent.orchestrator import LOCK_BUSY
    assert result == LOCK_BUSY


async def test_run_agent_lead_not_found():
    mock_sb = _make_sb(lead_data=None)
    with patch("app.agent.orchestrator.get_supabase", return_value=mock_sb), \
         patch("app.agent.lock_manager.get_supabase", return_value=mock_sb):
        from app.agent.orchestrator import run_agent
        result = await run_agent("nonexistent", "TEST")
    assert "não encontrado" in result


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


async def test_run_agent_aborts_when_lock_not_acquired():
    """If acquire_agent_lock RPC returns False, agent aborts instead of running."""
    mock_sb = _make_sb(lead_data=_LEAD)
    mock_sb.rpc = MagicMock(
        return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data=False)))
    )

    with patch("app.agent.orchestrator.get_supabase", return_value=mock_sb), \
         patch("app.agent.lock_manager.get_supabase", return_value=mock_sb):
        from app.agent.orchestrator import run_agent
        result = await run_agent("lead-001", "TEST")

    from app.agent.orchestrator import LOCK_BUSY
    assert result == LOCK_BUSY


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


async def test_tool_only_turn_is_saved_to_memory():
    """Turno com tool_calls mas texto vazio DEVE gerar memória (auditoria) — antes o
    guard `if turn.text` descartava tool-use turns sem texto."""
    mock_sb = _make_sb(lead_data=_LEAD)
    fake = _FakeAdapter([
        Turn(text="",  # turno tool-only: sem texto, só tool call
             tool_calls=[ToolCall(id="t1", name="enrich_lead", input={"lead_id": "lead-001"})],
             stop_reason="tool_use"),
        Turn(text="Pronto.", tool_calls=[], stop_reason="end_turn"),
    ])
    saved = []
    async def fake_save(lead_id, role, content, tool_calls=None):
        saved.append((role, content, tool_calls))

    with patch("app.agent.orchestrator.get_supabase", return_value=mock_sb), \
         patch("app.agent.lock_manager.get_supabase", return_value=mock_sb), \
         patch("app.agent.orchestrator.get_adapter", return_value=fake), \
         patch("app.agent.orchestrator.build_system_prompt", new=AsyncMock(return_value="sys")), \
         patch("app.agent.orchestrator.save_memory", new=fake_save), \
         patch("app.agent.orchestrator.execute_tool", new=AsyncMock(return_value="ok")):
        from app.agent.orchestrator import run_agent
        await run_agent("lead-001", "NEW_LEAD_REGISTERED")

    # deve haver um registro de assistant com a tool call (mesmo com content vazio)
    assistant_with_tool = [s for s in saved if s[0] == "assistant" and s[2]]
    assert assistant_with_tool, "tool-use turn sem texto não foi salvo na memória"


async def test_execute_tool_rejects_mismatched_lead_id():
    """Tool executor must refuse to act on a different lead than the authoritative one."""
    from app.agent.tool_executor import execute_tool
    result = await execute_tool(
        "update_lead_stage",
        {"lead_id": "DIFERENTE-UUID-9999", "stage": "OPTED_OUT"},
        lead_id="lead-001"
    )
    assert "BLOQUEADO" in result or "bloqueado" in result.lower()
