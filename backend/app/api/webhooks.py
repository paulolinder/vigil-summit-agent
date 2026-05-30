import asyncio
import json
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
from datetime import datetime, timezone

from app.db.client import get_supabase
from app.config import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/resend")
async def resend_webhook(
    request: Request,
    svix_id: Optional[str] = Header(None, alias="svix-id"),
    svix_timestamp: Optional[str] = Header(None, alias="svix-timestamp"),
    svix_signature: Optional[str] = Header(None, alias="svix-signature"),
):
    payload = await request.body()

    if not settings.resend_webhook_secret:
        raise HTTPException(
            status_code=503,
            detail="RESEND_WEBHOOK_SECRET não configurado — webhook desabilitado por segurança",
        )

    try:
        from svix.webhooks import Webhook
        wh = Webhook(settings.resend_webhook_secret)
        wh.verify(payload, {
            "svix-id": svix_id or "",
            "svix-timestamp": svix_timestamp or "",
            "svix-signature": svix_signature or "",
        })
    except Exception:
        raise HTTPException(status_code=401, detail="Assinatura inválida")

    data = json.loads(payload)
    event_type = data.get("type", "")
    resend_id = (data.get("data") or {}).get("email_id")

    if not resend_id:
        return {"received": True}

    sb = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    if event_type == "email.opened":
        await asyncio.to_thread(
            lambda: sb.table("messages")
            .update({"opened_at": now})
            .eq("resend_id", resend_id)
            .is_("opened_at", "null")
            .execute()
        )
    elif event_type == "email.clicked":
        await asyncio.to_thread(
            lambda: sb.table("messages")
            .update({"clicked_at": now})
            .eq("resend_id", resend_id)
            .is_("clicked_at", "null")
            .execute()
        )

    return {"received": True}


@router.post("/calcom")
async def calcom_webhook(request: Request):
    """Receives Cal.com booking events and sets MEETING_SCHEDULED on the lead."""
    data = await request.json()
    event_type = data.get("triggerEvent", "")

    if event_type != "BOOKING_CREATED":
        return {"received": True}

    booking = data.get("payload", {})
    attendees = booking.get("attendees") or []
    attendee_email = attendees[0].get("email", "") if attendees else ""

    if not attendee_email:
        return {"received": True}

    sb = get_supabase()
    await asyncio.to_thread(
        lambda: sb.table("leads")
        .update({"stage": "MEETING_SCHEDULED"})
        .eq("email", attendee_email)
        .neq("stage", "OPTED_OUT")
        .execute()
    )

    return {"received": True}
