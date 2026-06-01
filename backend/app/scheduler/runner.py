import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timezone, timedelta
from app.db.client import get_supabase
from app.config import settings
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
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # Recovery: reset jobs stuck in RUNNING for more than 30 minutes (worker crash assumed)
    stuck_cutoff = (now - timedelta(minutes=30)).isoformat()
    stuck_running = await asyncio.to_thread(lambda: (
        sb.table("scheduled_jobs")
        .select("id")
        .eq("status", "RUNNING")
        .lt("started_at", stuck_cutoff)
        .execute()
    ))
    for job in stuck_running.data:
        job_id = job["id"]
        await asyncio.to_thread(lambda jid=job_id: (
            sb.table("scheduled_jobs")
            .update({
                "status": "PENDING",
                # Zera contention_count: recuperação de crash NÃO é contenção de lock,
                # então não deve consumir o teto MAX_CONTENTION de re-enfileiramento.
                "contention_count": 0,
                "error": "Recovered: stuck in RUNNING for >30min (worker crash assumed)",
            })
            .eq("id", jid)
            .execute()
        ))

    await asyncio.to_thread(
        lambda: sb.table("agent_locks").delete().lt("expires_at", now_iso).execute()
    )

    stale_cutoff = (now - timedelta(hours=settings.stale_job_threshold_hours)).isoformat()

    # Mark stale overdue jobs as SKIPPED — prevents burst of old emails after long downtime
    stale = await asyncio.to_thread(lambda: (
        sb.table("scheduled_jobs")
        .select("id")
        .eq("status", "PENDING")
        .lt("run_at", stale_cutoff)
        .execute()
    ))
    for job in stale.data:
        job_id = job["id"]
        await asyncio.to_thread(lambda jid=job_id: (
            sb.table("scheduled_jobs")
            .update({"status": "SKIPPED", "error": f"Stale: skipped after restart (>{settings.stale_job_threshold_hours}h overdue)"})
            .eq("id", jid)
            .execute()
        ))

    # Schedule overdue jobs within threshold
    pending = await asyncio.to_thread(lambda: (
        sb.table("scheduled_jobs")
        .select("id, run_at")
        .eq("status", "PENDING")
        .lte("run_at", now_iso)
        .gte("run_at", stale_cutoff)
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

    # Schedule future jobs
    future_pending = await asyncio.to_thread(lambda: (
        sb.table("scheduled_jobs")
        .select("id, run_at")
        .eq("status", "PENDING")
        .gt("run_at", now_iso)
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
