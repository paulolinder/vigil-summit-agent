from pydantic import BaseModel, EmailStr, field_validator
from enum import Enum
from typing import Optional


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
    company: str
    role: str
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
