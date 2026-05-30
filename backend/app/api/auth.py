from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    if not settings.api_key or api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="API key inválida ou ausente")
