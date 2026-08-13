"""奖励系统服务与仓库测试"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.services.english.repository import EnglishRepository
from app.services.tenant.models import Tenant, User  # noqa: F401

TEST_ENGINE = create_engine("sqlite:///:memory:")
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture
def db() -> Session:
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


def test_points_repository(db: Session) -> None:
    repo = EnglishRepository(db)
    assert repo.get_points(1) is None
    repo.create_points(1, balance=0)
    points = repo.get_points(1)
    assert points is not None and points.balance == 0


def test_point_log_unique(db: Session) -> None:
    repo = EnglishRepository(db)
    repo.create_point_log(1, 10, "checkin", date.today())
    # 唯一约束拦截：sqlite 对重复 (user, reason, ref_date) 抛 IntegrityError
    with pytest.raises(Exception):
        repo.create_point_log(1, 10, "checkin", date.today())
    db.rollback()
    logs = repo.list_point_logs(1)
    assert len(logs) == 1
