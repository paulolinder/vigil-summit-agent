from pydantic_settings import BaseSettings
from pydantic import model_validator

class Settings(BaseSettings):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_agent_model: str = "gpt-4.1"
    openai_chat_model: str = "gpt-4.1-mini"
    supabase_url: str
    supabase_key: str
    resend_api_key: str
    resend_from_email: str = "Vigil Summit <noreply@vigil.ai>"
    resend_webhook_secret: str = ""
    apollo_api_key: str = ""
    evolution_api_url: str = ""
    evolution_api_key: str = ""
    evolution_instance_name: str = "vigil"
    cal_api_key: str = ""
    cal_event_type_id: str = ""
    cal_webhook_secret: str = ""
    api_key: str = ""  # Header X-API-Key para endpoints operacionais e de leitura
    stale_job_threshold_hours: int = 2
    frontend_url: str = "http://localhost:3030"
    # Origens permitidas pelo CORS — separadas por vírgula em produção
    cors_origins: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}

    @model_validator(mode="after")
    def _require_one_llm_key(self):
        if not self.anthropic_api_key and not self.openai_api_key:
            raise ValueError(
                "Nenhum provedor de LLM configurado: defina ANTHROPIC_API_KEY ou OPENAI_API_KEY"
            )
        return self

settings = Settings()
