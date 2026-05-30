# backend/app/agent/orchestrator.py
import asyncio
import anthropic
from datetime import datetime, timezone

from app.config import settings
from app.agent.tools import TOOLS
from app.agent.tool_executor import execute_tool
from app.agent.prompts import build_system_prompt
from app.agent.memory import save_memory
from app.agent.lock_manager import acquire_lock, release_lock, heartbeat_loop
from app.db.client import get_supabase

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


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

        client = _get_client()
        system = await build_system_prompt(lead, trigger)
        messages = [{"role": "user", "content": f"Trigger recebido: {trigger}. Avalie o estado e tome a ação mais adequada."}]

        await save_memory(lead_id, "user", f"Trigger: {trigger}")

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system,
                tools=TOOLS,
                messages=messages,
            )

            assistant_text = ""
            tool_uses = []

            for block in response.content:
                if block.type == "text":
                    assistant_text = block.text
                elif block.type == "tool_use":
                    tool_uses.append(block)

            if assistant_text:
                await save_memory(lead_id, "assistant", assistant_text, tool_uses or None)

            if response.stop_reason == "end_turn":
                break

            if response.stop_reason == "tool_use" and tool_uses:
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for tool_use in tool_uses:
                    result = await execute_tool(tool_use.name, tool_use.input, lead_id)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result,
                    })
                messages.append({"role": "user", "content": tool_results})
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
