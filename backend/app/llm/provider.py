from typing import Literal
from app.config import settings
from app.llm.base import LLMAdapter

Provider = Literal["anthropic", "openai"]


def detect_provider() -> Provider:
    """Anthropic wins if both keys are present. Raises if neither is set."""
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.openai_api_key:
        return "openai"
    raise RuntimeError(
        "Nenhum provedor de LLM configurado: defina ANTHROPIC_API_KEY ou OPENAI_API_KEY"
    )


def agent_model() -> str:
    """Model id for the orchestrator agent, per detected provider."""
    if detect_provider() == "anthropic":
        return "claude-sonnet-4-6"
    return settings.openai_agent_model


def get_adapter() -> LLMAdapter:
    """Factory: returns the adapter for the detected provider. Imports are local
    so the unused provider's SDK is never required at import time."""
    if detect_provider() == "anthropic":
        from app.llm.anthropic_adapter import AnthropicAdapter
        return AnthropicAdapter()
    from app.llm.openai_adapter import OpenAIAdapter
    return OpenAIAdapter()
