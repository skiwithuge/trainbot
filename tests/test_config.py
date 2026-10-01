import pytest
from trainbot.config import Config


def test_config_user_whitelist_parsing(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_token_123")
    monkeypatch.setenv("SNCF_API_KEY", "sncf_secret_key")
    monkeypatch.setenv("ALLOWED_USER_IDS", "12345, 67890, invalid, -100999")
    monkeypatch.setenv("TIMEZONE", "Europe/Paris")

    cfg = Config.from_env()
    assert cfg.telegram_bot_token == "fake_token_123"
    assert cfg.sncf_api_key == "sncf_secret_key"
    assert 12345 in cfg.allowed_user_ids
    assert 67890 in cfg.allowed_user_ids
    assert -100999 in cfg.allowed_user_ids
    assert len(cfg.allowed_user_ids) == 3


def test_is_user_allowed(monkeypatch):
    monkeypatch.setenv("ALLOWED_USER_IDS", "111,222")
    cfg = Config.from_env()

    assert cfg.is_user_allowed(111) is True
    assert cfg.is_user_allowed(222) is True
    assert cfg.is_user_allowed(333) is False
    assert cfg.is_user_allowed(None) is False


def test_empty_whitelist_denies_all(monkeypatch):
    monkeypatch.setenv("ALLOWED_USER_IDS", "")
    cfg = Config.from_env()

    assert cfg.is_user_allowed(111) is False


def test_config_default_reminder_times(monkeypatch):
    monkeypatch.delenv("MORNING_TIME", raising=False)
    monkeypatch.delenv("EVENING_TIME", raising=False)
    cfg = Config.from_env()

    assert cfg.morning_time == "07:15"
    assert cfg.evening_time == "16:15"

