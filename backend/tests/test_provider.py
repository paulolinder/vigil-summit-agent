import pytest
from app.llm import provider


def test_anthropic_wins_when_both_present(monkeypatch):
    monkeypatch.setattr(provider.settings, "anthropic_api_key", "sk-ant", raising=False)
    monkeypatch.setattr(provider.settings, "openai_api_key", "sk-openai", raising=False)
    assert provider.detect_provider() == "anthropic"


def test_openai_when_only_openai(monkeypatch):
    monkeypatch.setattr(provider.settings, "anthropic_api_key", "", raising=False)
    monkeypatch.setattr(provider.settings, "openai_api_key", "sk-openai", raising=False)
    assert provider.detect_provider() == "openai"


def test_anthropic_when_only_anthropic(monkeypatch):
    monkeypatch.setattr(provider.settings, "anthropic_api_key", "sk-ant", raising=False)
    monkeypatch.setattr(provider.settings, "openai_api_key", "", raising=False)
    assert provider.detect_provider() == "anthropic"


def test_raises_when_neither(monkeypatch):
    monkeypatch.setattr(provider.settings, "anthropic_api_key", "", raising=False)
    monkeypatch.setattr(provider.settings, "openai_api_key", "", raising=False)
    with pytest.raises(RuntimeError):
        provider.detect_provider()


def test_agent_model_matches_provider(monkeypatch):
    monkeypatch.setattr(provider.settings, "anthropic_api_key", "", raising=False)
    monkeypatch.setattr(provider.settings, "openai_api_key", "sk-openai", raising=False)
    monkeypatch.setattr(provider.settings, "openai_agent_model", "gpt-4.1", raising=False)
    assert provider.agent_model() == "gpt-4.1"
