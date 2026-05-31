import asyncio
import random
from datetime import datetime, timezone, timedelta
from app.db.client import get_supabase
from app.agent.orchestrator import run_agent


async def _db(fn):
    return await asyncio.to_thread(fn)


async def check_and_run_job(job_id: str) -> None:
    sb = get_supabase()

    # Atomic claim: UPDATE status='RUNNING' WHERE status='PENDING'
    # Returns True if this worker claimed the job; False means another worker got it first.
    claimed = await _db(
        lambda: sb.rpc("claim_scheduled_job", {"p_job_id": job_id}).execute().data
    )
    if not claimed:
        return

    # Fetch full job details now that we own it
    job = await _db(lambda: (
        sb.table("scheduled_jobs")
        .select("*")
        .eq("id", job_id)
        .single()
        .execute()
        .data
    ))
    if not job:
        return

    condition = job.get("condition") or {}
    lead_id = job["lead_id"]

    # Booking simulado (modo demo): transita via o MESMO caminho do webhook real do
    # Cal.com. Não passa pelo agente nem pelas condições — é resolução direta de stage.
    if job["job_type"] == "SIMULATED_BOOKING":
        lead_row = await _db(lambda: sb.table("leads").select("email").eq("id", lead_id).single().execute().data)
        email = (lead_row or {}).get("email")
        if email:
            from app.services.meeting import apply_booking_created
            await apply_booking_created(email)
        await _db(lambda: sb.table("scheduled_jobs").update({"status": "DONE"}).eq("id", job_id).execute())
        return

    lead = await _db(
        lambda: sb.table("leads").select("stage").eq("id", lead_id).single().execute().data
    )
    if not lead:
        await _db(
            lambda: sb.table("scheduled_jobs").update({"status": "SKIPPED"}).eq("id", job_id).execute()
        )
        return

    if lead["stage"] == "OPTED_OUT":
        await _db(
            lambda: sb.table("scheduled_jobs").update({"status": "SKIPPED"}).eq("id", job_id).execute()
        )
        return

    if "only_if_stage" in condition:
        if lead["stage"] != condition["only_if_stage"]:
            await _db(
                lambda: sb.table("scheduled_jobs").update({"status": "SKIPPED"}).eq("id", job_id).execute()
            )
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
            await _db(
                lambda: sb.table("scheduled_jobs").update({"status": "SKIPPED"}).eq("id", job_id).execute()
            )
            return
        if condition.get("only_if_not_clicked") and last_msg.get("clicked_at"):
            await _db(
                lambda: sb.table("scheduled_jobs").update({"status": "SKIPPED"}).eq("id", job_id).execute()
            )
            return

    try:
        await run_agent(lead_id, job["job_type"])
        await _db(
            lambda: sb.table("scheduled_jobs").update({"status": "DONE"}).eq("id", job_id).execute()
        )
    except Exception as e:
        retry_count = (job.get("retry_count") or 0) + 1
        max_retries = job.get("max_retries") or 3

        if retry_count < max_retries:
            # Exponential backoff with jitter to avoid thundering herd
            base_delay = 5 * (2 ** (retry_count - 1))
            jitter = random.uniform(0, base_delay * 0.2)
            delay_minutes = base_delay + jitter
            next_run = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
            await _db(lambda: sb.table("scheduled_jobs").update({
                "status": "PENDING",
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
