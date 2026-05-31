import asyncio
import json
from datetime import datetime, timezone

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

    lead = await _db(lambda: sb.table("leads").select("id, phone, whatsapp_consent_at").eq("id", lead_id).single().execute().data)
    if not lead:
        return "Lead não encontrado"

    # Trava de consentimento LGPD — permanece no tool_executor, antes do serviço.
    if not lead.get("whatsapp_consent_at"):
        return "Lead não optou por WhatsApp — mensagem não enviada"
    if not lead.get("phone"):
        return "Telefone não cadastrado — mensagem não enviada"

    try:
        from app.services.whatsapp import send_whatsapp_message
        result = await send_whatsapp_message(lead, text, sb)
        if result.get("simulated"):
            return f"WhatsApp SIMULADO registrado para {lead['phone']}"
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

    lead = await _db(lambda: sb.table("leads").select("id, name, email, stage, event_id").eq("id", lead_id).single().execute().data)
    if not lead:
        return "Lead não encontrado"

    try:
        from app.services.meeting import generate_meeting_link
        result = await generate_meeting_link(lead)
        # Stage NÃO é alterado aqui. MEETING_SCHEDULED é setado por apply_booking_created
        # (webhook real do Cal.com OU booking simulado), origens ATTENDED/NO_SHOW.
        return (
            f"Link de agendamento gerado: {result['booking_link']}. {result['note']} "
            f"Stage permanece '{lead['stage']}' até a confirmação."
        )
    except Exception as e:
        return f"Erro ao gerar link de agendamento: {e}"
