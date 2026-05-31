from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Security
from app.db.client import get_supabase
from app.db.models import LeadCreate, LeadStage
from app.config import settings
from app.limiter import limiter
from app.api.auth import require_api_key as _require_api_key
from datetime import datetime, timezone, timedelta
import hashlib
import uuid
import asyncio
import secrets
import resend


def _get_real_ip(request: Request) -> str:
    """Extracts real client IP, respecting X-Forwarded-For from reverse proxies."""
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP", "")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


async def send_deletion_email(email: str, token: str) -> None:
    """Sends LGPD deletion confirmation email to the data subject."""
    from app.config import settings as _settings
    resend.api_key = _settings.resend_api_key
    confirm_url = f"{_settings.frontend_url}/deletion-confirm?token={token}"
    await asyncio.to_thread(lambda: resend.Emails.send({
        "from": _settings.resend_from_email,
        "to": [email],
        "subject": "Confirme sua solicitação de exclusão de dados — Vigil Summit",
        "text": (
            f"Recebemos sua solicitação de exclusão de dados do Vigil Summit.\n\n"
            f"Para confirmar, clique no link abaixo (válido por 24 horas):\n\n"
            f"{confirm_url}\n\n"
            f"Se você não fez esta solicitação, ignore este email.\n\n"
            f"Equipe Vigil.AI"
        ),
    }))


router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/", status_code=201)
@limiter.limit("10/minute")
def create_lead(lead_data: LeadCreate, request: Request, background_tasks: BackgroundTasks):
    sb = get_supabase()

    event_check = sb.table("events").select("id").eq("id", lead_data.event_id).single().execute()
    if not event_check.data:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    client_ip = _get_real_ip(request)

    data = lead_data.model_dump(exclude={"consent", "whatsapp_consent"})
    data["consent_at"] = datetime.now(timezone.utc).isoformat()
    data["consent_ip"] = client_ip
    data["consent_version"] = "v1.0"
    data["stage"] = LeadStage.REGISTERED.value
    if lead_data.whatsapp_consent:
        data["whatsapp_consent_at"] = data["consent_at"]

    try:
        result = sb.table("leads").insert(data).execute()
        lead = result.data[0]
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Email já cadastrado para este evento")
        raise HTTPException(status_code=500, detail="Erro ao criar lead")

    from app.agent.orchestrator import run_agent
    background_tasks.add_task(run_agent, lead["id"], "NEW_LEAD_REGISTERED")

    return {"id": lead["id"], "stage": lead["stage"]}


@router.post("/{lead_id}/checkin", dependencies=[Security(_require_api_key)])
async def checkin_lead(lead_id: str, background_tasks: BackgroundTasks):
    sb = get_supabase()
    result = await asyncio.to_thread(
        lambda: sb.rpc("atomic_transition_lead_stage", {
            "p_lead_id": lead_id,
            "p_target_stage": "ATTENDED",
            "p_valid_from_stages": ["REGISTERED", "ENRICHED", "CONFIRMED"],
        }).execute()
    )
    outcome = result.data
    if outcome == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    if outcome == "INVALID_TRANSITION":
        raise HTTPException(status_code=409, detail="Transição inválida para ATTENDED")
    if outcome == "OK":
        from app.agent.orchestrator import run_agent
        background_tasks.add_task(run_agent, lead_id, "LEAD_ATTENDED")
    return {"status": "checked_in" if outcome == "OK" else "already_checked_in"}


@router.post("/{lead_id}/no-show", dependencies=[Security(_require_api_key)])
async def mark_no_show(lead_id: str, background_tasks: BackgroundTasks):
    sb = get_supabase()
    result = await asyncio.to_thread(
        lambda: sb.rpc("atomic_transition_lead_stage", {
            "p_lead_id": lead_id,
            "p_target_stage": "NO_SHOW",
            "p_valid_from_stages": ["REGISTERED", "ENRICHED", "CONFIRMED"],
        }).execute()
    )
    outcome = result.data
    if outcome == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    if outcome == "INVALID_TRANSITION":
        raise HTTPException(status_code=409, detail="Transição inválida para NO_SHOW")
    if outcome == "OK":
        from app.agent.orchestrator import run_agent
        background_tasks.add_task(run_agent, lead_id, "LEAD_NO_SHOW")
    return {"status": "marked_no_show" if outcome == "OK" else "already_no_show"}


@router.post("/{lead_id}/simulate-engagement", dependencies=[Security(_require_api_key)])
async def simulate_engagement(lead_id: str, payload: dict):
    """Demo: marca a última mensagem OUT/EMAIL do lead como aberta/clicada, espelhando
    o webhook do Resend. Permite ao avaliador dirigir o branching da régua na janela
    comprimida. Idempotente: só seta o que ainda é nulo (igual ao webhook)."""
    opened = bool(payload.get("opened"))
    clicked = bool(payload.get("clicked"))
    sb = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    msgs = await asyncio.to_thread(lambda: (
        sb.table("messages")
        .select("id")
        .eq("lead_id", lead_id)
        .eq("direction", "OUT")
        .eq("channel", "EMAIL")
        .order("sent_at", desc=True)
        .limit(1)
        .execute()
        .data
    ))
    if not msgs:
        raise HTTPException(status_code=404, detail="Nenhum email enviado para este lead")

    msg_id = msgs[0]["id"]

    # Um clique implica uma abertura — seta opened_at se opened OU clicked.
    if opened or clicked:
        await asyncio.to_thread(lambda: sb.table("messages")
            .update({"opened_at": now}).eq("id", msg_id).is_("opened_at", "null").execute())
    if clicked:
        await asyncio.to_thread(lambda: sb.table("messages")
            .update({"clicked_at": now}).eq("id", msg_id).is_("clicked_at", "null").execute())

    return {"status": "ok", "message_id": msg_id, "opened": opened, "clicked": clicked}


@router.post("/{lead_id}/run-agent", dependencies=[Security(_require_api_key)])
async def run_agent_endpoint(
    lead_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    trigger = payload.get("trigger", "MANUAL_TRIGGER")
    if not isinstance(trigger, str):
        raise HTTPException(status_code=400, detail="trigger deve ser uma string")
    sb = get_supabase()
    try:
        lead = await asyncio.to_thread(
            lambda: sb.table("leads").select("id").eq("id", lead_id).single().execute().data
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    from app.agent.orchestrator import run_agent
    background_tasks.add_task(run_agent, lead_id, trigger)
    return {"status": "started", "lead_id": lead_id, "trigger": trigger}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _issue_deletion_token(email: str) -> None:
    """Inserts a hashed deletion token and sends the confirmation email.
    Creates its own Supabase client instance — never shares the singleton across concurrent tasks."""
    sb = get_supabase()
    # Invalidate any previous unused tokens for this email
    await asyncio.to_thread(lambda: sb.table("deletion_tokens").update(
        {"used_at": datetime.now(timezone.utc).isoformat()}
    ).eq("email", email).is_("used_at", "null").execute())

    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    await asyncio.to_thread(lambda: sb.table("deletion_tokens").insert({
        "email": email,
        "token_hash": token_hash,
        "expires_at": expires_at,
    }).execute())
    await send_deletion_email(email, token)


@router.post("/deletion-request", status_code=202)
@limiter.limit("5/minute")
async def deletion_request(request: Request, payload: dict, background_tasks: BackgroundTasks):
    """Step 1: receives email, sends confirmation token via background task.
    Returns 202 regardless of whether email exists (anti-enumeration + timing-safe)."""
    sb = get_supabase()
    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email é obrigatório")

    result = await asyncio.to_thread(
        lambda: sb.table("leads").select("id").eq("email", email).execute()
    )

    if result.data:
        # Use BackgroundTasks so both branches (found/not-found) return at the same time,
        # eliminating the timing side-channel that would reveal email existence.
        background_tasks.add_task(_issue_deletion_token, email)

    return {"status": "confirmation_sent"}


@router.post("/deletion-request/confirm")
@limiter.limit("10/minute")
async def deletion_confirm(request: Request, payload: dict):
    """Step 2: validates token from email body (not URL) and executes anonymization.
    Token is passed in request body to avoid URL logging / prefetch-triggered execution."""
    token = (payload.get("token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="token é obrigatório")

    token_hash = _hash_token(token)
    sb = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    token_row = await asyncio.to_thread(lambda: (
        sb.table("deletion_tokens")
        .select("*")
        .eq("token_hash", token_hash)
        .gt("expires_at", now)
        .is_("used_at", "null")
        .single()
        .execute()
        .data
    ))
    if not token_row:
        raise HTTPException(status_code=404, detail="Token inválido ou expirado")

    email = token_row["email"]

    # Mark token as used BEFORE anonymizing (idempotent)
    await asyncio.to_thread(lambda: (
        sb.table("deletion_tokens")
        .update({"used_at": now})
        .eq("id", token_row["id"])
        .execute()
    ))

    result = await asyncio.to_thread(
        lambda: sb.table("leads").select("id").eq("email", email).execute()
    )
    if not result.data:
        return {"status": "anonymized"}

    anon_now = datetime.now(timezone.utc).isoformat()
    for row in result.data:
        lead_id = row["id"]
        await asyncio.to_thread(lambda lid=lead_id: sb.table("leads").update({
            "name": "ANONIMIZADO",
            "email": str(uuid.uuid4()),
            "phone": None,
            "company": None,
            "role": None,
            "companion_name": None,
            "consent_ip": None,
            "whatsapp_consent_at": None,
            "stage": LeadStage.OPTED_OUT.value,
            "deletion_req_at": anon_now,
        }).eq("id", lid).execute())

        await asyncio.to_thread(lambda lid=lead_id: sb.table("scheduled_jobs").update(
            {"status": "SKIPPED"}
        ).eq("lead_id", lid).eq("status", "PENDING").execute())

        await asyncio.to_thread(lambda lid=lead_id: sb.table("lead_enrichment").update({
            "real_role": None, "company": None, "sector": None,
            "linkedin_url": None, "security_signals": None, "enrichment_summary": None,
        }).eq("lead_id", lid).execute())

        await asyncio.to_thread(lambda lid=lead_id: sb.table("messages").update(
            {"body": None, "subject": None}
        ).eq("lead_id", lid).execute())

        await asyncio.to_thread(lambda lid=lead_id: sb.table("lead_memory").delete(
        ).eq("lead_id", lid).execute())

    return {"status": "anonymized"}


@router.get("/", dependencies=[Security(_require_api_key)])
def list_leads(event_id: str | None = None, limit: int = 100, offset: int = 0):
    if limit > 500:
        raise HTTPException(status_code=400, detail="Parâmetro 'limit' máximo é 500")
    if limit < 1:
        raise HTTPException(status_code=400, detail="Parâmetro 'limit' mínimo é 1")
    sb = get_supabase()
    # Embed enrichment + messages no MESMO response (service_role, sem expor PII ao navegador).
    # O dashboard consome estes dados do proxy — nunca consulta lead_enrichment/messages
    # direto do browser (a RLS só libera service_role nessas tabelas).
    query = sb.table("leads").select(
        "*, lead_enrichment(*), "
        "messages(lead_id, sent_at, opened_at, clicked_at, subject, channel, status, direction)"
    )
    if event_id:
        query = query.eq("event_id", event_id)
    result = query.range(offset, offset + limit - 1).execute()
    return {"data": result.data, "limit": limit, "offset": offset, "count": len(result.data)}
