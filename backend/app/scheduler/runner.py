import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timezone
from app.db.client import get_supabase
from app.scheduler.jobs import check_and_run_job

scheduler = AsyncIOScheduler()


async def start_scheduler() -> None:
    await _reload_pending_jobs()
    scheduler.add_job(
        _reload_pending_jobs,
        "interval",
        minutes=5,
        id="reload_jobs",
        replace_existing=True,
    )
    if not scheduler.running:
        scheduler.start()


async def _reload_pending_jobs() -> None:
    sb = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    await asyncio.to_thread(
        lambda: sb.table("agent_locks").delete().lt("expires_at", now).execute()
    )

    pending = await asyncio.to_thread(lambda: (
        sb.table("scheduled_jobs")
        .select("id, run_at")
        .eq("status", "PENDING")
        .lte("run_at", now)
        .execute()
    ))
    for job in pending.data:
        job_id = job["id"]
        scheduler_id = f"job_{job_id}"
        if not scheduler.get_job(scheduler_id):
            scheduler.add_job(
                check_and_run_job,
                trigger=DateTrigger(run_date=datetime.now(timezone.utc)),
                args=[job_id],
                id=scheduler_id,
                replace_existing=True,
            )

    future_pending = await asyncio.to_thread(lambda: (
        sb.table("scheduled_jobs")
        .select("id, run_at")
        .eq("status", "PENDING")
        .gt("run_at", now)
        .execute()
    ))
    for job in future_pending.data:
        job_id = job["id"]
        scheduler_id = f"job_{job_id}"
        if not scheduler.get_job(scheduler_id):
            run_at = datetime.fromisoformat(job["run_at"].replace("Z", "+00:00"))
            scheduler.add_job(
                check_and_run_job,
                trigger=DateTrigger(run_date=run_at),
                args=[job_id],
                id=scheduler_id,
                replace_existing=True,
            )


def add_job_to_scheduler(job_id: str, run_at: datetime) -> None:
    scheduler_id = f"job_{job_id}"
    scheduler.add_job(
        check_and_run_job,
        trigger=DateTrigger(run_date=run_at),
        args=[job_id],
        id=scheduler_id,
        replace_existing=True,
    )
