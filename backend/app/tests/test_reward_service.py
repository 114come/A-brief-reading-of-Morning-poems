"""奖励系统服务与仓库测试"""
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.core.security import get_password_hash
from app.services.english.models import CheckinRecord, UserDailyReading, UserDailyStats
from app.services.english.repository import EnglishRepository
from app.services.english.reward_service import RewardService
from app.services.english.service import get_english_tenant
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


@pytest.fixture
def user(db: Session) -> User:
    tenant = get_english_tenant(db)
    u = User(
        tenant_id=tenant.id, username="tester", email="t@t.com",
        password_hash=get_password_hash("secret"), is_superuser=False,
    )
    db.add(u)
    db.commit()
    return u


def _checkin(db: Session, user_id: int, days_ago: int = 0) -> None:
    d = date.today() - timedelta(days=days_ago)
    db.add(CheckinRecord(user_id=user_id, checkin_date=d))
    db.commit()


def test_collect_single_day(db: Session, user: User) -> None:
    _checkin(db, user.id, 0)
    db.add(UserDailyStats(user_id=user.id, book_id=1, study_date=date.today(), review_count=20, new_count=5))
    db.commit()

    svc = RewardService(db)
    out = svc.collect(user)
    assert out.earned_total == 20  # 打卡10 + 背词10
    assert {t.key for t in out.tasks if t.earned} == {"checkin", "srs_study"}

    out2 = svc.collect(user)
    assert out2.earned_total == 0  # 幂等
    assert svc.overview(user).balance == 20


def test_collect_milestone(db: Session, user: User) -> None:
    for i in range(6, -1, -1):  # 连续 7 天
        _checkin(db, user.id, i)
    svc = RewardService(db)
    out = svc.collect(user)
    assert "milestone_7" in out.milestones
    assert svc.overview(user).balance == 10 + 50  # 打卡10 + 里程碑50

    svc.collect(user)  # 里程碑只发一次
    assert svc.overview(user).balance == 60


def test_redeem_and_equip(db: Session, user: User) -> None:
    svc = RewardService(db)
    svc._grant(user, 100, "checkin", date.today())
    item = svc.redeem(user, "title_juling")
    assert item.is_unlocked is True
    try:
        svc.redeem(user, "title_juling")  # 重复兑换被拒
        assert False, "should raise"
    except Exception:
        pass

    svc.equip(user, "title_juling")
    assert svc.overview(user).equipped_title == "title_juling"
    svc.equip(user, None)
    assert svc.overview(user).equipped_title is None
