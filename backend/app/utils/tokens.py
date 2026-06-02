"""Token HMAC stateless para confirmação de presença por clique no email.
Módulo neutro (só hmac + settings) para evitar import circular entre
resend_service (gera o link) e api/leads (valida)."""
import hashlib
import hmac

from app.config import settings


def _confirm_secret() -> str:
    return settings.confirm_token_secret or settings.api_key


def sign_confirm_token(lead_id: str) -> str:
    """HMAC-SHA256 stateless do lead_id. Sem tabela, sem expiração."""
    sig = hmac.new(_confirm_secret().encode(), lead_id.encode(), hashlib.sha256).hexdigest()
    return f"{lead_id}.{sig}"


def verify_confirm_token(token: str | None) -> str | None:
    """Valida via compare_digest; retorna lead_id se ok, senão None."""
    if not token or "." not in token:
        return None
    lead_id, _, sig = token.rpartition(".")
    if not lead_id:
        return None
    expected = hmac.new(_confirm_secret().encode(), lead_id.encode(), hashlib.sha256).hexdigest()
    return lead_id if hmac.compare_digest(sig, expected) else None
