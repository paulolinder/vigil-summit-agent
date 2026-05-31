from pydantic import BaseModel, EmailStr, field_validator
from enum import Enum
from typing import Optional
from datetime import datetime
import re

_CONTROL_CHARS = re.compile(r"[\r\n\x00-\x1f\x7f]")


class LeadStage(str, Enum):
    REGISTERED = "REGISTERED"
    ENRICHED = "ENRICHED"
    CONFIRMED = "CONFIRMED"
    ATTENDED = "ATTENDED"
    NO_SHOW = "NO_SHOW"
    MEETING_SCHEDULED = "MEETING_SCHEDULED"
    CONVERTED = "CONVERTED"
    OPTED_OUT = "OPTED_OUT"


class LeadCreate(BaseModel):
    event_id: str
    name: str
    email: EmailStr
    company: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    has_companion: bool = False
    companion_name: Optional[str] = None
    consent: bool
    whatsapp_consent: bool = False

    @field_validator("consent")
    @classmethod
    def must_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Consentimento LGPD é obrigatório para inscrição")
        return v

    @field_validator("name", "company", "role", "companion_name")
    @classmethod
    def reject_control_chars(cls, v: Optional[str]) -> Optional[str]:
        # Reject newlines/control chars and cap length — these fields flow into
        # the agent's system prompt; this is a prompt-injection boundary defense.
        if v is None:
            return v
        if _CONTROL_CHARS.search(v):
            raise ValueError("Campo contém caracteres de controle não permitidos")
        if len(v) > 150:
            raise ValueError("Campo excede o limite de 150 caracteres")
        return v.strip()


class EventUpdate(BaseModel):
    """Partial update for the event config. All fields optional; only provided ones
    are written. Validates types/format so malformed input is a 422, not an opaque 500."""
    name: Optional[str] = None
    event_date: Optional[str] = None
    capacity: Optional[int] = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if _CONTROL_CHARS.search(v):
            raise ValueError("Nome contém caracteres de controle não permitidos")
        if len(v) > 150:
            raise ValueError("Nome excede o limite de 150 caracteres")
        return v.strip()

    @field_validator("event_date")
    @classmethod
    def validate_event_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("event_date deve ser uma data ISO 8601 válida")
        return v

    @field_validator("capacity")
    @classmethod
    def validate_capacity(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if v <= 0:
            raise ValueError("capacity deve ser maior que zero")
        if v > 100000:
            raise ValueError("capacity excede o limite permitido")
        return v
