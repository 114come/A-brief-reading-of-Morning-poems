from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.services.tenant.models import Permission
from app.services.tenant.seed import DEFAULT_PERMISSIONS, seed_permissions

TEST_ENGINE = create_engine("sqlite:///:memory:", echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


def test_seed_permissions_creates_all(db: Session) -> None:
    seed_permissions(db)
    permissions = db.query(Permission).all()
    codes = {p.code for p in permissions}
    assert len(permissions) == len(DEFAULT_PERMISSIONS)
    for perm_data in DEFAULT_PERMISSIONS:
        assert perm_data["code"] in codes


def test_seed_permissions_is_idempotent(db: Session) -> None:
    seed_permissions(db)
    seed_permissions(db)
    permissions = db.query(Permission).all()
    assert len(permissions) == len(DEFAULT_PERMISSIONS)
