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
