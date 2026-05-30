from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Security
from fastapi.security import APIKeyHeader
from app.db.client import get_supabase
from app.db.models import LeadCreate, LeadStage
from app.config import settings
from app.limiter import limiter
from datetime import datetime, timezone
import uuid

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    if not settings.api_key or api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="API key inválida ou ausente")


router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/", status_code=201)
@limiter.limit("10/minute")
def create_lead(lead_data: LeadCreate, request: Request, background_tasks: BackgroundTasks):
    sb = get_supabase()
    client_ip = request.client.host if request.client else "unknown"

    data = lead_data.model_dump(exclude={"consent", "whatsapp_consent"})
    data["consent_at"] = datetime.now(timezone.utc).isoformat()
    data["consent_ip"] = client_ip
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
    sb = get_supabase()
    result = sb.table("leads").select("id, stage").eq("id", lead_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    sb.table("leads").update({"stage": LeadStage.ATTENDED.value}).eq("id", lead_id).execute()

    from app.agent.orchestrator import run_agent
    background_tasks.add_task(run_agent, lead_id, "LEAD_ATTENDED")

    return {"status": "checked_in"}


@router.post("/{lead_id}/no-show", dependencies=[Security(_require_api_key)])
def mark_no_show(lead_id: str, background_tasks: BackgroundTasks):
    sb = get_supabase()
    result = sb.table("leads").select("id").eq("id", lead_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    sb.table("leads").update({"stage": LeadStage.NO_SHOW.value}).eq("id", lead_id).execute()

    from app.agent.orchestrator import run_agent
    background_tasks.add_task(run_agent, lead_id, "LEAD_NO_SHOW")

    return {"status": "marked_no_show"}


@router.post("/deletion-request")
@limiter.limit("5/minute")
def deletion_request(request: Request, payload: dict):
    sb = get_supabase()
    email = payload.get("email", "")
    if not email:
        raise HTTPException(status_code=400, detail="email é obrigatório")

    result = sb.table("leads").select("id").eq("email", email).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    now = datetime.now(timezone.utc).isoformat()

    # Itera todos os registros: o mesmo email pode estar em múltiplos eventos (event_id universal).
    # LGPD exige anonimização de TODOS os dados do titular, não apenas o primeiro registro encontrado.
    for row in result.data:
        lead_id = row["id"]

        sb.table("leads").update({
            "name": "ANONIMIZADO",
            "email": str(uuid.uuid4()),
            "phone": None,
            "company": None,
            "role": None,
            "companion_name": None,
            "consent_ip": None,
            "whatsapp_consent_at": None,
            "stage": LeadStage.OPTED_OUT.value,
            "deletion_req_at": now,
        }).eq("id", lead_id).execute()

        sb.table("scheduled_jobs").update({"status": "SKIPPED"}).eq("lead_id", lead_id).eq("status", "PENDING").execute()

        # lead_enrichment: PII mais densa — UPDATE em vez de DELETE para preservar integridade referencial
        sb.table("lead_enrichment").update({
            "real_role": None,
            "company": None,
            "sector": None,
            "linkedin_url": None,
            "security_signals": None,
            "enrichment_summary": None,
        }).eq("lead_id", lead_id).execute()

        # messages: nula body e subject (PII direta); mantém metadados para métricas
        sb.table("messages").update({"body": None, "subject": None}).eq("lead_id", lead_id).execute()

        # lead_memory: PII indireta nas mensagens do agente — deletar imediatamente
        sb.table("lead_memory").delete().eq("lead_id", lead_id).execute()

    return {"status": "anonymized"}


@router.get("/", dependencies=[Security(_require_api_key)])
def list_leads(event_id: str | None = None):
    sb = get_supabase()
    query = sb.table("leads").select("*, lead_enrichment(*)")
    if event_id:
        query = query.eq("event_id", event_id)
    result = query.execute()
    return result.data
