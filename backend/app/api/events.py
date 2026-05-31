import asyncio
from fastapi import APIRouter, HTTPException, Security
from app.db.client import get_supabase
from app.db.models import EventUpdate
from app.api.auth import require_api_key as _require_api_key

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/")
def list_events():
    sb = get_supabase()
    result = sb.table("events").select("*").order("event_date").execute()
    return result.data


@router.get("/{event_id}")
def get_event(event_id: str):
    sb = get_supabase()
    try:
        result = sb.table("events").select("*").eq("id", event_id).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Evento não encontrado")
        return result.data
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Evento não encontrado")


@router.put("/{event_id}", dependencies=[Security(_require_api_key)])
async def update_event(event_id: str, payload: EventUpdate):
    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum campo válido para atualizar")
    sb = get_supabase()
    result = await asyncio.to_thread(
        lambda: sb.table("events").update(update_data).eq("id", event_id).execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    return result.data[0]
