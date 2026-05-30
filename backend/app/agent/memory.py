import asyncio
from app.db.client import get_supabase
from datetime import datetime, timezone


async def save_memory(lead_id: str, role: str, content: str, tool_uses=None) -> None:
    sb = get_supabase()

    tool_use_data = None
    if tool_uses:
        tool_use_data = [
            {"name": t.name, "input": t.input, "id": t.id}
            for t in tool_uses
        ]

    row = {
        "lead_id": lead_id,
        "role": role,
        "content": content,
        "tool_use": tool_use_data,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await asyncio.to_thread(lambda: sb.table("lead_memory").insert(row).execute())
