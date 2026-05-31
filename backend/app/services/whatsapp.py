# backend/app/services/whatsapp.py
"""Fronteira de WhatsApp: Evolution real se a chave existir, senão grava uma mensagem
SIMULATED visível no dashboard. A trava de consentimento LGPD fica no tool_executor."""
import asyncio
import httpx
from datetime import datetime, timezone
from app.config import settings


async def _db(fn):
    return await asyncio.to_thread(fn)


async def send_whatsapp_message(lead: dict, text: str, sb) -> dict:
    lead_id = lead["id"]
    now = datetime.now(timezone.utc).isoformat()

    if not settings.evolution_api_url or not settings.evolution_api_key:
        # MOCK — registra mensagem simulada (visível no dashboard como WhatsApp enviado)
        await _db(lambda: sb.table("messages").insert({
            "lead_id": lead_id,
            "channel": "WHATSAPP",
            "direction": "OUT",
            "body": text,
            "status": "SIMULATED",
            "sent_at": now,
        }).execute())
        return {"simulated": True}

    # REAL — Evolution API
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{settings.evolution_api_url}/message/sendText/{settings.evolution_instance_name}",
            headers={"apikey": settings.evolution_api_key},
            json={"number": lead["phone"], "text": text},
        )
        resp.raise_for_status()

    await _db(lambda: sb.table("messages").insert({
        "lead_id": lead_id,
        "channel": "WHATSAPP",
        "direction": "OUT",
        "body": text,
        "status": "SENT",
        "sent_at": now,
    }).execute())
    return {"sent": True}
