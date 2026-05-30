from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str
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
    api_key: str = ""  # Header X-API-Key para endpoints operacionais e de leitura
    frontend_url: str = "http://localhost:3030"
    # Origens permitidas pelo CORS — separadas por vírgula em produção
    # Ex: CORS_ORIGINS=https://meuservidor.com,https://www.meuservidor.com
    cors_origins: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}

settings = Settings()
