import importlib
import pytest


def _reload_config(monkeypatch, anthropic, openai):
    # Set absent keys to "" (not delenv): a real env var — even empty — takes
    # precedence over the on-disk .env file in pydantic-settings, so this isolates
    # the test from backend/.env (which carries a real ANTHROPIC_API_KEY).
    monkeypatch.setenv("ANTHROPIC_API_KEY", anthropic if anthropic is not None else "")
    monkeypatch.setenv("OPENAI_API_KEY", openai if openai is not None else "")
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


def test_demo_fast_forward_defaults_false(monkeypatch):
    monkeypatch.delenv("DEMO_FAST_FORWARD", raising=False)
    cfg = _reload_config(monkeypatch, anthropic="sk-ant-x", openai=None)
    assert cfg.settings.demo_fast_forward is False
