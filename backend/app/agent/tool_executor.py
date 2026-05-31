import asyncio
import json
import httpx
from datetime import datetime, timezone
from urllib.parse import urlencode

from app.db.client import get_supabase
from app.config import settings
from app.services.resend_service import send_email


async def _db(fn):
    """Run a synchronous Supabase call in the thread pool — avoids blocking the event loop."""
    return await asyncio.to_thread(fn)


async def execute_tool(tool_name: str, tool_input: dict, lead_id: str) -> str:
    sb = get_supabase()

    # Security: reject if LLM specified a different lead_id than the authoritative one
    requested_lead_id = tool_input.get("lead_id")
    if requested_lead_id and requested_lead_id != lead_id:
        return (
            f"[BLOQUEADO] Tentativa de agir sobre lead '{requested_lead_id}' "
            f"no contexto do lead '{lead_id}'. Ignorado por segurança."
        )

    # Normalize: always use the authoritative lead_id
    tool_input = {**tool_input, "lead_id": lead_id}

    if tool_name == "enrich_lead":
        return await _enrich_lead(lead_id, sb)
    if tool_name == "send_pre_event_msg":
        return await _send_pre_event_msg(tool_input, sb)
    if tool_name == "check_engagement":
        return await _check_engagement(lead_id, sb)
    if tool_name == "send_whatsapp":
        return await _send_whatsapp(tool_input, sb)
    if tool_name == "send_followup":
        return await _send_followup(tool_input, sb)
    if tool_name == "update_lead_stage":
        return await _update_lead_stage(tool_input, sb)
    if tool_name == "schedule_job":
        return await _schedule_job(tool_input, sb)
    if tool_name == "schedule_meeting":
        return await _schedule_meeting(tool_input, sb)
    return f"Tool desconhecida: {tool_name}"


async def _enrich_lead(lead_id: str, sb) -> str:
    lead = await _db(lambda: sb.table("leads").select("email, name, company").eq("id", lead_id).single().execute().data)
    if not lead:
        return "Lead não encontrado"

    try:
        from app.services.enrichment import enrich_lead_data
        data = await enrich_lead_data(lead)
        enrichment = {**data, "lead_id": lead_id}

        await _db(lambda: sb.table("lead_enrichment").upsert(enrichment).execute())
        # Marca ENRICHED via o guard atômico (nunca UPDATE plano). Só REGISTERED→ENRICHED
        # é válido; se o lead já avançou, o RPC retorna ALREADY_SET/INVALID_TRANSITION
        # e o stage é corretamente preservado.
        await _db(lambda: sb.rpc("atomic_transition_lead_stage", {
            "p_lead_id": lead_id,
            "p_target_stage": "ENRICHED",
            "p_valid_from_stages": ["REGISTERED"],
        }).execute())

        return f"Lead enriquecido: {enrichment['enrichment_summary']}"
    except Exception as e:
        return f"Erro no enriquecimento: {e}"


async def _send_pre_event_msg(tool_input: dict, sb) -> str:
    lead_id = tool_input["lead_id"]
    template = tool_input.get("template", "welcome")
    custom_note = tool_input.get("custom_note", "")

    lead = await _db(lambda: sb.table("leads").select("*, lead_enrichment(*)").eq("id", lead_id).single().execute().data)
    if not lead:
        return "Lead não encontrado"

    enrichment = lead.get("lead_enrichment")
    if isinstance(enrichment, list):
        lead["lead_enrichment"] = enrichment[0] if enrichment else {}

    result = await send_email(lead, template, custom_note, phase="pre_event")
    if "error" in result:
        return f"Erro ao enviar email: {result['error']}"
    return f"Email '{template}' enviado. resend_id={result.get('id')}"


async def _check_engagement(lead_id: str, sb) -> str:
    msgs = await _db(lambda: (
        sb.table("messages")
        .select("opened_at, clicked_at, sent_at")
        .eq("lead_id", lead_id)
        .eq("direction", "OUT")
        .eq("channel", "EMAIL")
        .eq("status", "SENT")
        .order("sent_at", desc=True)
        .limit(1)
        .execute()
        .data
    ))

    if not msgs:
        return json.dumps({"opened": False, "clicked": False, "last_message_at": None})

    msg = msgs[0]
    return json.dumps({
        "opened": bool(msg.get("opened_at")),
        "clicked": bool(msg.get("clicked_at")),
        "last_message_at": msg.get("sent_at"),
    })


async def _send_whatsapp(tool_input: dict, sb) -> str:
    lead_id = tool_input["lead_id"]
    text = tool_input.get("text", "")

    lead = await _db(lambda: sb.table("leads").select("phone, whatsapp_consent_at").eq("id", lead_id).single().execute().data)
    if not lead:
        return "Lead não encontrado"

    if not lead.get("whatsapp_consent_at"):
        return "Lead não optou por WhatsApp — mensagem não enviada"

    if not lead.get("phone"):
        return "Telefone não cadastrado — mensagem não enviada"

    if not settings.evolution_api_url or not settings.evolution_api_key:
        return "Evolution API não configurada"

    try:
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
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }).execute())

        return f"WhatsApp enviado para {lead['phone']}"
    except Exception as e:
        return f"Erro WhatsApp: {e}"


async def _send_followup(tool_input: dict, sb) -> str:
    lead_id = tool_input["lead_id"]
    template = tool_input.get("template", "thank_you")
    custom_note = tool_input.get("custom_note", "")

    lead = await _db(lambda: sb.table("leads").select("*, lead_enrichment(*)").eq("id", lead_id).single().execute().data)
    if not lead:
        return "Lead não encontrado"

    enrichment = lead.get("lead_enrichment")
    if isinstance(enrichment, list):
        lead["lead_enrichment"] = enrichment[0] if enrichment else {}

    result = await send_email(lead, template, custom_note, phase="post_event")
    if "error" in result:
        return f"Erro ao enviar followup: {result['error']}"
    return f"Followup '{template}' enviado. resend_id={result.get('id')}"


async def _update_lead_stage(tool_input: dict, sb) -> str:
    from app.agent.state_machine import VALID_TRANSITIONS

    lead_id = tool_input["lead_id"]
    new_stage = tool_input["stage"]

    if new_stage not in VALID_TRANSITIONS:
        return f"Stage inválido: {new_stage}"

    # Source stages from which new_stage is reachable, per the state machine.
    valid_from = [s for s, targets in VALID_TRANSITIONS.items() if new_stage in targets]

    # Authoritative DB-level CAS — never a plain UPDATE for stage changes (avoids the
    # read-then-write race with checkin/no-show/webhook writers).
    result = await _db(lambda: sb.rpc("atomic_transition_lead_stage", {
        "p_lead_id": lead_id,
        "p_target_stage": new_stage,
        "p_valid_from_stages": valid_from,
    }).execute())
    outcome = result.data

    if outcome == "OK":
        return f"Stage atualizado para {new_stage}"
    if outcome == "ALREADY_SET":
        return f"Stage já estava em {new_stage}. Nenhuma alteração feita."
    if outcome == "INVALID_TRANSITION":
        return f"Transição bloqueada para {new_stage} (origem não permitida). Nenhuma alteração feita."
    if outcome == "NOT_FOUND":
        return f"Lead {lead_id} não encontrado"
    return f"Resultado inesperado da transição: {outcome}"


async def _schedule_job(tool_input: dict, sb) -> str:
    from app.scheduler.runner import add_job_to_scheduler

    lead_id = tool_input["lead_id"]
    run_at_str = tool_input["run_at"]
    run_at = datetime.fromisoformat(run_at_str.replace("Z", "+00:00"))

    lead_row = await _db(lambda: sb.table("leads").select("event_id").eq("id", lead_id).single().execute().data)
    event_id = (lead_row or {}).get("event_id")

    job: dict = {
        "lead_id": lead_id,
        "job_type": tool_input["job_type"],
        "run_at": run_at_str,
        "condition": tool_input.get("condition", {}),
        "status": "PENDING",
        "event_id": event_id,
    }

    result = await _db(lambda: sb.table("scheduled_jobs").insert(job).execute())
    job_id = result.data[0]["id"]
    add_job_to_scheduler(job_id, run_at)

    return f"Job agendado: id={job_id}, run_at={run_at_str}"


async def _schedule_meeting(tool_input: dict, sb) -> str:
    lead_id = tool_input["lead_id"]
    context_note = tool_input.get("context_note", "")

    lead = await _db(lambda: sb.table("leads").select("name, email, stage").eq("id", lead_id).single().execute().data)
    if not lead:
        return "Lead não encontrado"

    if not settings.cal_api_key or not settings.cal_event_type_id:
        return "Cal.com não configurado (cal_api_key ou cal_event_type_id ausentes)"

    try:
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

        # Stage is intentionally NOT updated here.
        # MEETING_SCHEDULED is set only by /webhooks/calcom when the attendee
        # completes a real booking in Cal.com.

        return (
            f"Link de agendamento gerado: {booking_link}. "
            f"Stage permanece '{lead['stage']}' até confirmação real no Cal.com."
        )
    except Exception as e:
        return f"Erro Cal.com: {e}"
