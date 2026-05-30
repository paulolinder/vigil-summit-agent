import threading
from supabase import create_client, Client
from app.config import settings

_client: Client | None = None
_lock = threading.Lock()

def get_supabase() -> Client:
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client
