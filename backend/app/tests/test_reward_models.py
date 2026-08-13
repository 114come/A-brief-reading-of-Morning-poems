"""奖励系统数据模型测试"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.services.english.models import RewardPointLog, RewardUnlock, RewardUserPoints
from app.services.tenant.models import Tenant, User  # noqa: F401  # 注册 users/tenants 表到 metadata

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


def test_reward_tables_create(db: Session) -> None:
    points = RewardUserPoints(user_id=1, balance=100, total_earned=100)
    db.add(points)
    log = RewardPointLog(user_id=1, amount=10, reason="checkin", ref_date=date.today())
    db.add(log)
    unlock = RewardUnlock(user_id=1, item_key="title_juling")
    db.add(unlock)
    db.commit()

    assert points.balance == 100
    assert log.reason == "checkin"
    assert unlock.item_key == "title_juling"


def test_unique_user_points(db: Session) -> None:
    db.add(RewardUserPoints(user_id=1, balance=10, total_earned=10))
    db.commit()
    db.add(RewardUserPoints(user_id=1, balance=20, total_earned=20))
    with pytest.raises(IntegrityError):
        db.commit()
