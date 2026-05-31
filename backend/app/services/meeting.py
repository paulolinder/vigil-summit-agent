# backend/app/services/meeting.py
"""Fronteira de agendamento: Cal.com real se a chave existir, senão link simulado +
booking simulado. apply_booking_created é o núcleo de transição compartilhado com o
webhook real do Cal.com."""
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from app.config import settings
from app.db.client import get_supabase

# Atraso curto do booking simulado — não colide com o lock do run_agent que o criou
# (apply_booking_created não adquire lock de agente).
_SIMULATED_BOOKING_DELAY_SECONDS = 30


async def _db(fn):
    return await asyncio.to_thread(fn)


async def apply_booking_created(email: str) -> None:
    """Transita cada lead deste email ATTENDED/NO_SHOW -> MEETING_SCHEDULED.
    Núcleo compartilhado: usado pelo webhook real do Cal.com E pelo booking simulado."""
    sb = get_supabase()
    rows = await _db(lambda: sb.table("leads").select("id").eq("email", email).execute().data)
    for row in rows or []:
        await _db(lambda lid=row["id"]: sb.rpc("atomic_transition_lead_stage", {
            "p_lead_id": lid,
            "p_target_stage": "MEETING_SCHEDULED",
            "p_valid_from_stages": ["ATTENDED", "NO_SHOW"],
        }).execute())


async def generate_meeting_link(lead: dict) -> dict:
    if settings.cal_api_key and settings.cal_event_type_id:
        return await _real_meeting_link(lead)
    return await _mock_meeting_link(lead)


async def _real_meeting_link(lead: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"https://api.cal.com/v1/event-types/{settings.cal_event_type_id}",
            headers={"Authorization": f"Bearer {settings.cal_api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
    event_type = data.get("event_type", {})
    slug = event_type.get("slug", "demo-vigil")
    username = (event_type.get("team") or {}).get("slug", "vigil")
    booking_link = (
        f"https://cal.com/{username}/{slug}"
        f"?{urlencode({'name': lead['name'], 'email': lead['email']})}"
    )
    return {"booking_link": booking_link, "note": "Link real do Cal.com gerado."}


async def _mock_meeting_link(lead: dict) -> dict:
    booking_link = (
        f"https://cal.com/vigil/demo-vigil"
        f"?{urlencode({'name': lead['name'], 'email': lead['email']})}"
    )
    run_at = datetime.now(timezone.utc) + timedelta(seconds=_SIMULATED_BOOKING_DELAY_SECONDS)
    sb = get_supabase()
    result = await _db(lambda: sb.table("scheduled_jobs").insert({
        "lead_id": lead["id"],
        "job_type": "SIMULATED_BOOKING",
        "run_at": run_at.isoformat(),
        "condition": {},
        "status": "PENDING",
        "event_id": lead.get("event_id"),
    }).execute())
    job_id = result.data[0]["id"]
    from app.scheduler.runner import add_job_to_scheduler
    add_job_to_scheduler(job_id, run_at)
    return {
        "booking_link": booking_link,
        "note": "[SIMULADO] reunião será confirmada automaticamente em segundos.",
    }
