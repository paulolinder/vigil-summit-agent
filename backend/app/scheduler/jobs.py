import asyncio
from datetime import datetime, timezone, timedelta
from app.db.client import get_supabase
from app.agent.orchestrator import run_agent


async def _db(fn):
    return await asyncio.to_thread(fn)


async def check_and_run_job(job_id: str) -> None:
    sb = get_supabase()
    job = await _db(lambda: (
        sb.table("scheduled_jobs")
        .select("*")
        .eq("id", job_id)
        .eq("status", "PENDING")
        .single()
        .execute()
        .data
    ))
    if not job:
        return

    condition = job.get("condition") or {}
    lead_id = job["lead_id"]

    lead = await _db(lambda: sb.table("leads").select("stage").eq("id", lead_id).single().execute().data)
    if not lead:
        await _db(lambda: sb.table("scheduled_jobs").update({"status": "SKIPPED"}).eq("id", job_id).execute())
        return

    if lead["stage"] == "OPTED_OUT":
        await _db(lambda: sb.table("scheduled_jobs").update({"status": "SKIPPED"}).eq("id", job_id).execute())
        return

    if "only_if_stage" in condition:
        if lead["stage"] != condition["only_if_stage"]:
            await _db(lambda: sb.table("scheduled_jobs").update({"status": "SKIPPED"}).eq("id", job_id).execute())
            return

    if condition.get("skip_if_opened") or condition.get("only_if_not_clicked"):
        msgs = await _db(lambda: (
            sb.table("messages")
            .select("opened_at, clicked_at")
            .eq("lead_id", lead_id)
            .eq("direction", "OUT")
            .eq("channel", "EMAIL")
            .order("sent_at", desc=True)
            .limit(1)
            .execute()
            .data
        ))
        last_msg = msgs[0] if msgs else {}
        if condition.get("skip_if_opened") and last_msg.get("opened_at"):
            await _db(lambda: sb.table("scheduled_jobs").update({"status": "SKIPPED"}).eq("id", job_id).execute())
            return
        if condition.get("only_if_not_clicked") and last_msg.get("clicked_at"):
            await _db(lambda: sb.table("scheduled_jobs").update({"status": "SKIPPED"}).eq("id", job_id).execute())
            return

    try:
        await run_agent(lead_id, job["job_type"])
        await _db(lambda: sb.table("scheduled_jobs").update({"status": "DONE"}).eq("id", job_id).execute())
    except Exception as e:
        retry_count = (job.get("retry_count") or 0) + 1
        max_retries = job.get("max_retries") or 3

        if retry_count < max_retries:
            delay_minutes = 5 * (2 ** (retry_count - 1))
            next_run = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
            await _db(lambda: sb.table("scheduled_jobs").update({
                "error": str(e)[:500],
                "retry_count": retry_count,
                "run_at": next_run.isoformat(),
            }).eq("id", job_id).execute())
            from app.scheduler.runner import add_job_to_scheduler
            add_job_to_scheduler(job_id, next_run)
        else:
            await _db(lambda: sb.table("scheduled_jobs").update({
                "status": "FAILED",
                "error": str(e)[:500],
                "retry_count": retry_count,
            }).eq("id", job_id).execute())
