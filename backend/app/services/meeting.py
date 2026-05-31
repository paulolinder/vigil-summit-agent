# backend/app/services/meeting.py
"""Fronteira de agendamento: Cal.com real se a chave existir, senão link simulado +
booking simulado. apply_booking_created é o núcleo de transição compartilhado com o
webhook real do Cal.com."""
import asyncio
from app.db.client import get_supabase


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
