from unittest.mock import MagicMock, patch

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.core import database
from app.core.config import settings


class TestDatabase:
    def test_master_engine_is_created(self) -> None:
        assert isinstance(database.master_engine, Engine)
        assert database.master_engine.url.render_as_string(hide_password=False) == settings.MASTER_DATABASE_URL

    def test_base_is_declarative(self) -> None:
        assert hasattr(database.Base, "metadata")

    def test_get_master_db_yields_session(self) -> None:
        mock_session = MagicMock(spec=Session)
        with patch.object(database, "MasterSessionLocal", return_value=mock_session):
            gen = database.get_master_db()
            session = next(gen)
            assert session is mock_session
            # generator should close the session when done
            try:
                next(gen)
            except StopIteration:
                pass
            mock_session.close.assert_called_once()

    def test_settings_database_url_format(self) -> None:
        url = settings.MASTER_DATABASE_URL
        assert url.startswith("mysql+pymysql://")
        assert settings.MASTER_DB_HOST in url
        assert str(settings.MASTER_DB_PORT) in url
        assert settings.MASTER_DB_NAME in url
