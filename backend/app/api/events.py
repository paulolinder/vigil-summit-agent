import asyncio
from fastapi import APIRouter, HTTPException, Security
from app.db.client import get_supabase
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
