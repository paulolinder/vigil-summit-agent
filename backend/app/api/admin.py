import asyncio
import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Security
from app.api.auth import require_api_key as _require_api_key
from app.config import settings
from app.db.client import get_supabase

router = APIRouter(prefix="/admin", tags=["admin"])


async def _db(fn):
    return await asyncio.to_thread(fn)


# ── Health check ────────────────────────────────────────────────────────────

def _env_status(key: str) -> str:
    return "ok" if key else "warn"


async def _ping_anthropic() -> str:
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        await client.models.list()
        return "ok"
    except Exception:
        return "error"


async def _ping_resend() -> tuple[str, str]:
    """Returns (status, detail)."""
    if not settings.resend_api_key:
        return "warn", "RESEND_API_KEY ausente"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                "https://api.resend.com/domains",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            )
            if r.status_code == 401:
                return "error", f"Chave inválida (HTTP {r.status_code})"
            return "ok", settings.resend_from_email
    except httpx.TimeoutException:
        return "warn", "Timeout ao conectar (API pode estar lenta)"
    except Exception as e:
        return "error", f"Erro de conexão: {type(e).__name__}"


async def _ping_apollo() -> str:
    if not settings.apollo_api_key:
        return "warn"
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(
                "https://api.apollo.io/api/v1/auth/health",
                headers={"x-api-key": settings.apollo_api_key},
            )
            return "ok" if r.status_code == 200 else "error"
    except Exception:
        return "error"


async def _ping_cal() -> str:
    if not settings.cal_api_key:
        return "warn"
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            # Cal.com v2 supports Bearer header — avoids key exposure in URL/logs
            r = await c.get(
                "https://api.cal.com/v2/me",
                headers={"Authorization": f"Bearer {settings.cal_api_key}"},
            )
            return "ok" if r.status_code == 200 else "error"
    except Exception:
        return "error"


async def _ping_evolution() -> str:
    if not settings.evolution_api_url or not settings.evolution_api_key:
        return "warn"
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(
                f"{settings.evolution_api_url}/instance/fetchInstances",
                headers={"apikey": settings.evolution_api_key},
            )
            return "ok" if r.status_code == 200 else "error"
    except Exception:
        return "error"


def _build_services_config_only() -> list[dict]:
    return [
        {
            "name": "Claude (Anthropic)",
            "role": "Orquestrador do agente",
            "status": _env_status(settings.anthropic_api_key),
            "detail": "claude-sonnet-4-6" if settings.anthropic_api_key else "ANTHROPIC_API_KEY ausente",
        },
        {
            "name": "Resend",
            "role": "Envio de emails",
            "status": _env_status(settings.resend_api_key),
            "detail": settings.resend_from_email if settings.resend_api_key else "RESEND_API_KEY ausente",
        },
        {
            "name": "Apollo.io",
            "role": "Enriquecimento de leads",
            "status": _env_status(settings.apollo_api_key),
            "detail": "people/match API" if settings.apollo_api_key else "APOLLO_API_KEY ausente",
        },
        {
            "name": "Cal.com",
            "role": "Agendamento de reuniões",
            "status": _env_status(settings.cal_api_key),
            "detail": f"event type {settings.cal_event_type_id}" if settings.cal_api_key else "CAL_API_KEY ausente",
        },
        {
            "name": "Supabase",
            "role": "Banco de dados + Realtime",
            "status": "ok",
            "detail": "PostgreSQL · RLS ativo",
        },
        {
            "name": "WhatsApp (Evolution)",
            "role": "Mensagens WhatsApp",
            "status": _env_status(settings.evolution_api_url),
            "detail": settings.evolution_instance_name if settings.evolution_api_url else "EVOLUTION_API_URL ausente",
        },
    ]


async def _build_services_live() -> list[dict]:
    anthropic_s, resend_result, apollo_s, cal_s, evolution_s = await asyncio.gather(
        _ping_anthropic(),
        _ping_resend(),
        _ping_apollo(),
        _ping_cal(),
        _ping_evolution(),
    )
    resend_s, resend_detail = resend_result
    return [
        {"name": "Claude (Anthropic)", "role": "Orquestrador do agente", "status": anthropic_s, "detail": "claude-sonnet-4-6"},
        {"name": "Resend", "role": "Envio de emails", "status": resend_s, "detail": resend_detail},
        {"name": "Apollo.io", "role": "Enriquecimento de leads", "status": apollo_s, "detail": "people/match API"},
        {"name": "Cal.com", "role": "Agendamento de reuniões", "status": cal_s, "detail": f"event type {settings.cal_event_type_id}"},
        {"name": "Supabase", "role": "Banco de dados + Realtime", "status": "ok", "detail": "PostgreSQL · RLS ativo"},
        {"name": "WhatsApp (Evolution)", "role": "Mensagens WhatsApp", "status": evolution_s, "detail": settings.evolution_instance_name or "não configurado"},
    ]


@router.get("/health", dependencies=[Security(_require_api_key)])
async def health_check(live: bool = False):
    if live:
        services = await _build_services_live()
    else:
        services = _build_services_config_only()
    return {"services": services}


# ── Jobs queue ───────────────────────────────────────────────────────────────

@router.get("/jobs", dependencies=[Security(_require_api_key)])
async def list_jobs(limit: int = 20):
    if limit > 100:
        limit = 100
    sb = get_supabase()
    rows = await _db(lambda: (
        sb.table("scheduled_jobs")
        .select("*, leads(name, company, role)")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    ))
    return {"data": rows or []}


@router.post("/jobs/{job_id}/run", dependencies=[Security(_require_api_key)])
async def run_job_now(job_id: str, background_tasks: BackgroundTasks):
    sb = get_supabase()
    try:
        job = await _db(
            lambda: sb.table("scheduled_jobs").select("id, status").eq("id", job_id).single().execute().data
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job["status"] not in ("PENDING", "FAILED"):
        raise HTTPException(
            status_code=409,
            detail=f"Job está em status '{job['status']}' — só PENDING ou FAILED podem ser re-executados",
        )
    if job["status"] == "FAILED":
        await _db(lambda: (
            sb.table("scheduled_jobs")
            .update({"status": "PENDING", "error": None})
            .eq("id", job_id)
            .execute()
        ))
    from app.scheduler.jobs import check_and_run_job
    background_tasks.add_task(check_and_run_job, job_id)
    return {"status": "triggered", "job_id": job_id}
