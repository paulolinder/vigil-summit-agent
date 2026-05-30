import asyncio
from datetime import datetime, timezone, timedelta
from app.db.client import get_supabase


async def _db(fn):
    return await asyncio.to_thread(fn)


async def cleanup_old_memory() -> int:
    """Delete lead_memory rows older than 90 days. Returns count of deleted rows."""
    sb = get_supabase()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    result = await _db(
        lambda: sb.table("lead_memory").delete().lt("created_at", cutoff).execute()
    )
    return len(result.data) if result.data else 0


async def cleanup_terminal_jobs() -> int:
    """Delete DONE/FAILED/SKIPPED scheduled_jobs older than 30 days."""
    sb = get_supabase()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    total = 0
    for status in ("DONE", "FAILED", "SKIPPED"):
        result = await _db(
            lambda s=status: sb.table("scheduled_jobs")
            .delete()
            .eq("status", s)
            .lt("run_at", cutoff)
            .execute()
        )
        total += len(result.data) if result.data else 0
    return total


async def cleanup_used_deletion_tokens() -> int:
    """Delete used or expired deletion tokens older than 48 hours."""
    sb = get_supabase()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    result = await _db(
        lambda: sb.table("deletion_tokens").delete().lt("expires_at", cutoff).execute()
    )
    return len(result.data) if result.data else 0


async def run_all_cleanups() -> None:
    """Run all cleanup tasks. Called by the scheduler daily at 3am UTC."""
    mem = await cleanup_old_memory()
    jobs = await cleanup_terminal_jobs()
    tokens = await cleanup_used_deletion_tokens()
    print(f"[cleanup] lead_memory: {mem} rows, scheduled_jobs: {jobs} rows, deletion_tokens: {tokens} rows")
