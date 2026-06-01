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
    """Remove tokens de exclusão para minimizar a janela em que o email (plaintext) fica
    armazenado. Dois critérios:
      1. tokens já USADOS (used_at preenchido) — não podem ser reusados, então saem 1h após o uso;
      2. tokens EXPIRADOS (expires_at < agora) — a janela útil de 24h já passou.
    NOTA: o email é guardado em plaintext porque o confirm precisa dele para achar os leads
    a anonimizar. Hash-at-rest exigiria refatorar o lookup do confirm — follow-up futuro.
    """
    sb = get_supabase()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    used_cutoff = (now - timedelta(hours=1)).isoformat()

    used = await _db(
        lambda: sb.table("deletion_tokens").delete()
        .not_("used_at", "is", "null").lt("used_at", used_cutoff).execute()
    )
    expired = await _db(
        lambda: sb.table("deletion_tokens").delete().lt("expires_at", now_iso).execute()
    )
    return (len(used.data) if used.data else 0) + (len(expired.data) if expired.data else 0)


async def run_all_cleanups() -> None:
    """Run all cleanup tasks. Called by the scheduler daily at 3am UTC."""
    mem = await cleanup_old_memory()
    jobs = await cleanup_terminal_jobs()
    tokens = await cleanup_used_deletion_tokens()
    print(f"[cleanup] lead_memory: {mem} rows, scheduled_jobs: {jobs} rows, deletion_tokens: {tokens} rows")
