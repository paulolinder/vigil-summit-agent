import importlib
import pytest


def _reload_config(monkeypatch, anthropic, openai):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    if anthropic is not None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", anthropic)
    if openai is not None:
        monkeypatch.setenv("OPENAI_API_KEY", openai)
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    import app.config as cfg
    importlib.reload(cfg)
    return cfg


def test_anthropic_only_boots(monkeypatch):
    cfg = _reload_config(monkeypatch, anthropic="sk-ant-x", openai=None)
    assert cfg.settings.anthropic_api_key == "sk-ant-x"
    assert cfg.settings.openai_api_key == ""


def test_openai_only_boots(monkeypatch):
    cfg = _reload_config(monkeypatch, anthropic=None, openai="sk-openai-x")
    assert cfg.settings.openai_api_key == "sk-openai-x"
    assert cfg.settings.openai_agent_model == "gpt-4.1"
    assert cfg.settings.openai_chat_model == "gpt-4.1-mini"


def test_no_llm_key_raises(monkeypatch):
    with pytest.raises(Exception):
        _reload_config(monkeypatch, anthropic=None, openai=None)
