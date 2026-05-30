# backend/app/agent/lock_manager.py
import asyncio
from app.db.client import get_supabase


async def _db(fn):
    return await asyncio.to_thread(fn)


async def acquire_lock(lead_id: str) -> bool:
    """Atomic lock acquisition via Postgres RPC. Returns True if lock was acquired."""
    sb = get_supabase()
    result = await _db(
        lambda: sb.rpc("acquire_agent_lock", {"p_lead_id": lead_id, "p_expires_minutes": 5}).execute()
    )
    return bool(result.data)


async def release_lock(lead_id: str) -> None:
    """Releases the agent lock for a lead."""
    sb = get_supabase()
    await _db(
        lambda: sb.table("agent_locks").delete().eq("lead_id", lead_id).execute()
    )


async def heartbeat_loop(lead_id: str, stop_event: asyncio.Event) -> None:
    """Renews the lock every 2 minutes while the agent is running.
    Runs until stop_event is set or task is cancelled."""
    sb = get_supabase()
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=120.0)
        except asyncio.TimeoutError:
            pass
        if stop_event.is_set():
            break
        try:
            await _db(
                lambda: sb.rpc("renew_agent_lock", {
                    "p_lead_id": lead_id, "p_extend_minutes": 3
                }).execute()
            )
        except Exception:
            pass  # Non-critical — lock may expire but cleanup handles it
