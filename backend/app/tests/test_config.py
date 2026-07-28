import os

from app.core.config import Settings


def test_settings_loads_from_env() -> None:
    os.environ["MASTER_DB_HOST"] = "testhost"
    os.environ["SECRET_KEY"] = "a" * 32
    settings = Settings()
    assert settings.MASTER_DB_HOST == "testhost"
    assert settings.SECRET_KEY == "a" * 32
