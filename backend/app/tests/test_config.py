import pytest

from app.core.config import Settings, _reset_settings_for_test, get_settings


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MASTER_DB_HOST", "testhost")
    monkeypatch.setenv("SECRET_KEY", "a" * 32)
    settings = Settings()
    assert settings.MASTER_DB_HOST == "testhost"
    assert settings.SECRET_KEY == "a" * 32


def test_settings_singleton_can_be_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MASTER_DB_HOST", "reset-host")
    _reset_settings_for_test()
    settings = get_settings()
    assert settings.MASTER_DB_HOST == "reset-host"
