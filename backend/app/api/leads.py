from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Security
from fastapi.security import APIKeyHeader
from app.db.client import get_supabase
from app.db.models import LeadCreate, LeadStage
from app.config import settings
from app.limiter import limiter
from datetime import datetime, timezone, timedelta
import hashlib
import uuid
import asyncio
import secrets
import resend

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


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


def _require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    if not settings.api_key or api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="API key inválida ou ausente")


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
def checkin_lead(lead_id: str, background_tasks: BackgroundTasks):
    from app.agent.state_machine import is_valid_transition
    sb = get_supabase()

    result = sb.table("leads").select("id, stage").eq("id", lead_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    current_stage = result.data["stage"]

    if current_stage == LeadStage.ATTENDED.value:
        return {"status": "already_checked_in"}

    if not is_valid_transition(current_stage, LeadStage.ATTENDED.value):
        raise HTTPException(
            status_code=409,
            detail=f"Transição inválida: {current_stage} → ATTENDED"
        )

    sb.table("leads").update({"stage": LeadStage.ATTENDED.value}).eq("id", lead_id).execute()

    from app.agent.orchestrator import run_agent
    background_tasks.add_task(run_agent, lead_id, "LEAD_ATTENDED")
    return {"status": "checked_in"}


@router.post("/{lead_id}/no-show", dependencies=[Security(_require_api_key)])
def mark_no_show(lead_id: str, background_tasks: BackgroundTasks):
    from app.agent.state_machine import is_valid_transition
    sb = get_supabase()

    result = sb.table("leads").select("id, stage").eq("id", lead_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    current_stage = result.data["stage"]

    if current_stage == LeadStage.NO_SHOW.value:
        return {"status": "already_no_show"}

    if not is_valid_transition(current_stage, LeadStage.NO_SHOW.value):
        raise HTTPException(
            status_code=409,
            detail=f"Transição inválida: {current_stage} → NO_SHOW"
        )

    sb.table("leads").update({"stage": LeadStage.NO_SHOW.value}).eq("id", lead_id).execute()

    from app.agent.orchestrator import run_agent
    background_tasks.add_task(run_agent, lead_id, "LEAD_NO_SHOW")
    return {"status": "marked_no_show"}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _issue_deletion_token(sb, email: str) -> None:
    """Inserts a hashed deletion token and sends the confirmation email.
    Only called when the email exists — runs as a background task so the
    response time is identical for existing and non-existing emails."""
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
        background_tasks.add_task(_issue_deletion_token, sb, email)

    return {"status": "confirmation_sent"}


@router.post("/deletion-request/confirm")
async def deletion_confirm(payload: dict):
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
    query = sb.table("leads").select("*, lead_enrichment(*)")
    if event_id:
        query = query.eq("event_id", event_id)
    result = query.range(offset, offset + limit - 1).execute()
    return {"data": result.data, "limit": limit, "offset": offset, "count": len(result.data)}
