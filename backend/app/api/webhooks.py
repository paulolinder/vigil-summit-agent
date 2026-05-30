import asyncio
import hashlib
import hmac as hmac_lib
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
async def calcom_webhook(
    request: Request,
    x_cal_signature: Optional[str] = Header(None, alias="X-Cal-Signature-256"),
):
    """Receives Cal.com booking events. Requires HMAC-SHA256 signing secret."""
    if not settings.cal_webhook_secret:
        raise HTTPException(
            status_code=503,
            detail="CAL_WEBHOOK_SECRET não configurado — webhook desabilitado por segurança",
        )

    payload = await request.body()

    expected_sig = "sha256=" + hmac_lib.new(
        settings.cal_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    if not x_cal_signature or not hmac_lib.compare_digest(x_cal_signature, expected_sig):
        raise HTTPException(status_code=401, detail="Assinatura Cal.com inválida")

    data = json.loads(payload)
    event_type = data.get("triggerEvent", "")

    if event_type != "BOOKING_CREATED":
        return {"received": True}

    booking = data.get("payload", {})
    attendees = booking.get("attendees") or []
    attendee_email = attendees[0].get("email", "") if attendees else ""

    if not attendee_email:
        return {"received": True}

    sb = get_supabase()
    # Only valid source stages for MEETING_SCHEDULED: ATTENDED or NO_SHOW
    await asyncio.to_thread(
        lambda: sb.table("leads")
        .update({"stage": "MEETING_SCHEDULED"})
        .eq("email", attendee_email)
        .in_("stage", ["ATTENDED", "NO_SHOW"])
        .execute()
    )

    return {"received": True}
