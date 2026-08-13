# 晨光奖励系统 · 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为「朝词浅阅」实现积分 + 兑换站 + 情绪价值的每日奖励系统（每日任务结算、里程碑奖励、玄幻称号兑换、晨语与庆祝动效）。

**Architecture:** 完整后端方案。新增 4 张表（积分余额/流水/解锁/设置）+ RewardService 结算逻辑 + 5 个 API；前端在「归处」页新增「奖励」Tab（积分卡 + 任务进度 + 兑换站），打卡/背词/阅读完成后调用 `collect()` 结算并弹反馈。数据源复用现有表（`checkin_records` / `user_daily_stats` / `user_daily_reading`），无需重复埋点。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + PyMySQL（后端）；Vue 3 + Pinia + TypeScript（前端）。

## Global Constraints

- 后端统一响应包裹 `UnifiedResponse{code, data, message}`，业务成功 `code=0`
- 路由挂载 `/english` 前缀、Bearer 认证（`UserDep`）
- 表唯一约束命名 `uq_<table>_<cols>`；索引命名 `ix_<table>_<col>`
- **技术修正**：spec 提到"含 tenant_id"，但现有打卡表 `checkin_records` 实际只含 `user_id`；奖励表遵循 `CheckinRecord` 模式（只 `user_id`），保证一致性
- 里程碑是否已发放由 `reward_point_logs` 对应 reason 流水存在性判断（唯一约束防重），不另落库
- 前端遵循晨光森林设计 token（`--primary/--sun/--brand-gradient` 等）
- 测试用 sqlite in-memory + `Base.metadata.create_all`（参照 `test_daily_reading.py` fixtures）
- 前端命令：`cd english-learning && npm run build`；后端命令：`cd backend && python -m pytest app/tests/<file> -v`

---

### Task 1: 数据模型（4 张表）

**Files:**
- Modify: `backend/app/services/english/models.py`（文件末尾追加 4 个模型类）
- Test: `backend/app/tests/test_reward_models.py`（新建）

**Interfaces:**
- Produces: `RewardUserPoints` / `RewardPointLog` / `RewardUnlock` / `RewardSettings` —— 供 Task 3 的 Repository 使用

- [ ] **Step 1: 写失败测试（模型可创建）**

```python
"""奖励系统数据模型测试"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.services.english.models import RewardPointLog, RewardUnlock, RewardUserPoints

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
    with pytest.raises(Exception):
        db.commit()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest app/tests/test_reward_models.py -v`
Expected: FAIL（`RewardUserPoints` ImportError 或表不存在）

- [ ] **Step 3: 在 models.py 末尾追加模型**

```python
# ── 奖励系统 ──────────────────────────────────────────────────────


class RewardUserPoints(Base):
    """用户积分余额（每人一条）"""

    __tablename__ = "reward_user_points"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_reward_user_points_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class RewardPointLog(Base):
    """积分流水（到账为正、兑换为负；唯一约束防重复发放）"""

    __tablename__ = "reward_point_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "reason", "ref_date", name="uq_reward_logs_uid_reason_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    ref_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )


class RewardUnlock(Base):
    """已解锁奖励（称号/装饰/彩蛋）"""

    __tablename__ = "reward_unlocks"
    __table_args__ = (
        UniqueConstraint("user_id", "item_key", name="uq_reward_unlocks_uid_item"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    item_key: Mapped[str] = mapped_column(String(50), nullable=False)
    unlock_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)


class RewardSettings(Base):
    """用户奖励设置（佩戴称号/装饰）"""

    __tablename__ = "reward_settings"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_reward_settings_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    equipped_title: Mapped[str | None] = mapped_column(String(50), nullable=True)
    equipped_decor: Mapped[str | None] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest app/tests/test_reward_models.py -v`
Expected: PASS（2 passed）

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/english/models.py backend/app/tests/test_reward_models.py
git commit -m "feat: add reward system data models"
```

---

### Task 2: Alembic 迁移

**Files:**
- Create: `backend/alembic/versions/<new>_add_reward_tables.py`（用 `python -m alembic revision --autogenerate -m "add reward tables"` 生成，或手写）

**Interfaces:**
- Consumes: Task 1 的模型
- Produces: 数据库 4 张新表

- [ ] **Step 1: 生成迁移**

Run:
```bash
cd backend && python -m alembic revision --autogenerate -m "add reward tables"
```

- [ ] **Step 2: 检查生成的迁移文件，确认包含 4 张表的 create_table**

确认 `op.create_table("reward_user_points"...)`、`reward_point_logs`、`reward_unlocks`、`reward_settings` 都存在，且唯一约束/索引命名正确（`uq_*` / `ix_*`）。若 autogenerate 缺失，按 Task 1 模型手动补齐。

- [ ] **Step 3: 执行迁移**

Run: `cd backend && python -m alembic upgrade head`
Expected: 成功升级到 head，无报错

- [ ] **Step 4: 提交**

```bash
git add backend/alembic/versions/
git commit -m "feat: add reward tables migration"
```

---

### Task 3: Repository 方法

**Files:**
- Modify: `backend/app/services/english/repository.py`（末尾追加「奖励系统」区块）

**Interfaces:**
- Consumes: Task 1 的模型
- Produces: 以下方法供 Task 5 使用：
  - `get_points(user_id) -> RewardUserPoints | None`
  - `create_points(user_id, balance=0) -> RewardUserPoints`
  - `get_point_log(user_id, reason, ref_date) -> RewardPointLog | None`
  - `create_point_log(user_id, amount, reason, ref_date, note="") -> RewardPointLog`
  - `list_point_logs(user_id, limit=50) -> list[RewardPointLog]`
  - `get_unlock(user_id, item_key) -> RewardUnlock | None`
  - `list_unlocks(user_id) -> list[RewardUnlock]`
  - `create_unlock(user_id, item_key) -> RewardUnlock`
  - `get_reward_settings(user_id) -> RewardSettings | None`
  - `create_reward_settings(user_id) -> RewardSettings`
  - `sum_daily_words(user_id, study_date) -> int`（今日背词数 = review+new，供任务结算）

- [ ] **Step 1: 写失败测试**

在 `backend/app/tests/test_reward_service.py` 中先写（本任务只测 repository 方法；Task 7 扩展同文件）：

```python
"""奖励系统服务与仓库测试"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.services.english.repository import EnglishRepository

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
    points = repo.get_points(1)
    assert points is None
    repo.create_points(1, balance=0)
    points = repo.get_points(1)
    assert points is not None and points.balance == 0


def test_point_log_unique(db: Session) -> None:
    repo = EnglishRepository(db)
    repo.create_point_log(1, 10, "checkin", date.today())
    repo.create_point_log(1, 10, "checkin", date.today())  # 唯一约束应拦截
    logs = repo.list_point_logs(1)
    assert len(logs) == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest app/tests/test_reward_service.py -v`
Expected: FAIL（`get_points` 不存在）

- [ ] **Step 3: 在 repository.py 末尾追加**

```python
    # ── 奖励系统 ─────────────────────────────────────────────────
    def get_points(self, user_id: int) -> RewardUserPoints | None:
        return (
            self.db.query(RewardUserPoints)
            .filter(RewardUserPoints.user_id == user_id)
            .first()
        )

    def create_points(self, user_id: int, balance: int = 0) -> RewardUserPoints:
        item = RewardUserPoints(user_id=user_id, balance=balance, total_earned=balance)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_point_log(self, user_id: int, reason: str, ref_date: date) -> RewardPointLog | None:
        return (
            self.db.query(RewardPointLog)
            .filter(
                RewardPointLog.user_id == user_id,
                RewardPointLog.reason == reason,
                RewardPointLog.ref_date == ref_date,
            )
            .first()
        )

    def create_point_log(self, user_id: int, amount: int, reason: str, ref_date: date, note: str = "") -> RewardPointLog:
        item = RewardPointLog(
            user_id=user_id, amount=amount, reason=reason, ref_date=ref_date, note=note
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_point_logs(self, user_id: int, limit: int = 50) -> list[RewardPointLog]:
        return (
            self.db.query(RewardPointLog)
            .filter(RewardPointLog.user_id == user_id)
            .order_by(RewardPointLog.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_unlock(self, user_id: int, item_key: str) -> RewardUnlock | None:
        return (
            self.db.query(RewardUnlock)
            .filter(RewardUnlock.user_id == user_id, RewardUnlock.item_key == item_key)
            .first()
        )

    def list_unlocks(self, user_id: int) -> list[RewardUnlock]:
        return (
            self.db.query(RewardUnlock)
            .filter(RewardUnlock.user_id == user_id)
            .order_by(RewardUnlock.unlock_date.desc())
            .all()
        )

    def create_unlock(self, user_id: int, item_key: str) -> RewardUnlock:
        item = RewardUnlock(user_id=user_id, item_key=item_key)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_reward_settings(self, user_id: int) -> RewardSettings | None:
        return (
            self.db.query(RewardSettings)
            .filter(RewardSettings.user_id == user_id)
            .first()
        )

    def create_reward_settings(self, user_id: int) -> RewardSettings:
        item = RewardSettings(user_id=user_id)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def sum_daily_words(self, user_id: int, study_date: date) -> int:
        """今日背词数 = review_count + new_count 合计"""
        rows = (
            self.db.query(UserDailyStats)
            .filter(UserDailyStats.user_id == user_id, UserDailyStats.study_date == study_date)
            .all()
        )
        return sum((r.review_count or 0) + (r.new_count or 0) for r in rows)
```

> 记得在 repository.py 顶部 import 中追加：`RewardPointLog, RewardUnlock, RewardUserPoints, RewardSettings`（`UserDailyStats` 应已在 import 中，若没有则一并加入）。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest app/tests/test_reward_service.py -v`
Expected: PASS（2 passed）

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/english/repository.py backend/app/tests/test_reward_service.py
git commit -m "feat: add reward repository methods"
```

---

### Task 4: Pydantic Schemas

**Files:**
- Modify: `backend/app/services/english/schemas.py`（末尾追加奖励系统 Schemas）

**Interfaces:**
- Produces:
  - `RewardTaskOut{key, name, desc, earned, done, points}`
  - `RewardOverviewOut{balance, total_earned, streak_days, today_earned, tasks: list[RewardTaskOut], unlocked_keys: list[str], equipped_title, equipped_decor, quote, quote_source}`
  - `ShopItemOut{item_key, name, desc, type, price, is_unlocked}`
  - `RedeemIn{item_key}`
  - `EquipIn{item_key: str | None}`
  - `CollectOut{earned_total, tasks: list[RewardTaskOut], milestones: list[str], message, quote}`

- [ ] **Step 1: 在 schemas.py 末尾追加**

```python
# ─── 奖励系统 ───────────────────────────────────────────────────────


class RewardTaskOut(BaseModel):
    key: str
    name: str
    desc: str
    points: int
    done: bool = False
    earned: bool = False  # 今日是否已结算该任务积分


class RewardOverviewOut(BaseModel):
    balance: int
    total_earned: int
    streak_days: int
    today_earned: int
    tasks: list[RewardTaskOut]
    unlocked_keys: list[str]
    equipped_title: str | None = None
    equipped_decor: str | None = None
    quote: str
    quote_source: str


class ShopItemOut(BaseModel):
    item_key: str
    name: str
    desc: str
    type: str  # title / decor / egg
    price: int
    is_unlocked: bool = False


class RedeemIn(BaseModel):
    item_key: str


class EquipIn(BaseModel):
    item_key: str | None = None  # None 表示卸下


class CollectOut(BaseModel):
    earned_total: int
    tasks: list[RewardTaskOut]
    milestones: list[str] = []
    message: str
    quote: str
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/english/schemas.py
git commit -m "feat: add reward schemas"
```

---

### Task 5: RewardService 核心逻辑

**Files:**
- Create: `backend/app/services/english/reward_service.py`

**Interfaces:**
- Consumes: Task 3 repo 方法、Task 4 Schemas、现有 `EnglishRepository` 的 `list_checkin_dates / get_daily_reading / get_checkin / sum_daily_words`
- Produces:
  - `RewardService(db)` 类，方法：`overview(user) -> RewardOverviewOut` / `shop(user) -> list[ShopItemOut]` / `redeem(user, item_key) -> ShopItemOut` / `equip(user, item_key: str | None) -> dict` / `collect(user) -> CollectOut` / `_streak_days(user) -> int`

- [ ] **Step 1: 写失败测试（结算幂等 / 里程碑 / 兑换幂等）**

在 `backend/app/tests/test_reward_service.py` 追加（复用该文件已有 fixtures）：

```python
from app.services.english.models import (
    CheckinRecord,
    UserDailyReading,
    UserDailyStats,
)
from app.services.english.reward_service import RewardService
from app.services.english.service import get_english_tenant
from app.services.tenant.models import User
from app.core.security import get_password_hash


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
    d = date.today() - __import__("datetime").timedelta(days=days_ago)
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

    # 幂等：再次 collect 不重复加分
    out2 = svc.collect(user)
    assert out2.earned_total == 0
    assert svc.overview(user).balance == 20


def test_collect_milestone(db: Session, user: User) -> None:
    for i in range(6, -1, -1):  # 连续 7 天
        _checkin(db, user.id, i)
    out = svc.collect(user)
    assert "milestone_7" in {t.key for t in out.tasks} or out.milestones
    assert svc.overview(user).balance == 10 + 50  # 打卡10 + 里程碑50

    # 里程碑只发一次
    svc.collect(user)
    assert svc.overview(user).balance == 60


def test_redeem_and_equip(db: Session, user: User) -> None:
    svc = RewardService(db)
    # 给 100 分
    svc._grant(user, 100, "checkin", date.today())
    item = svc.redeem(user, "title_juling")
    assert item.is_unlocked is True
    with pytest.raises(Exception):
        svc.redeem(user, "title_juling")  # 重复兑换被拒

    equipped = svc.equip(user, "title_juling")
    assert equipped.equipped_title == "title_juling"
    svc.equip(user, None)
    assert svc.overview(user).equipped_title is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest app/tests/test_reward_service.py -v`
Expected: FAIL（`RewardService` ImportError）

- [ ] **Step 3: 创建 reward_service.py**

写完整文件（以下为最终实现）：

```python
"""奖励系统业务服务

积分 · 每日任务 · 里程碑 · 兑换站 · 晨语与温暖话语
"""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException
from app.services.english.models import RewardPointLog
from app.services.english.repository import EnglishRepository
from app.services.english.schemas import (
    CollectOut,
    EquipIn,
    RewardOverviewOut,
    RewardTaskOut,
    ShopItemOut,
)
from app.services.tenant.models import User

# ── 每日任务配置 ──────────────────────────────────────────────────
TASKS = [
    {"key": "checkin", "name": "每日打卡", "desc": "完成今日打卡", "points": 10},
    {"key": "srs_study", "name": "词海拾贝", "desc": "今日背词 ≥ 20 词", "points": 10},
    {"key": "reading", "name": "浅读一页", "desc": "今日读完 1 篇文章", "points": 15},
    {"key": "quiz", "name": "小试牛刀", "desc": "今日阅读小测及格", "points": 5},
]

# ── 里程碑配置（连续天数 → 额外积分）────────────────────────────
MILESTONES = {7: 50, 30: 200, 100: 800}

# ── 兑换站配置 ────────────────────────────────────────────────────
SHOP_ITEMS = [
    {"item_key": "title_juling", "name": "聚灵", "desc": "聚气于晨，始成灵识", "type": "title", "price": 30},
    {"item_key": "title_qiming", "name": "启明", "desc": "晨星初启，灵台渐明", "type": "title", "price": 60},
    {"item_key": "title_yunfeng", "name": "蕴锋", "desc": "灵气蕴于笔锋", "type": "title", "price": 100},
    {"item_key": "title_chengguang", "name": "承光", "desc": "承晨光以砺道", "type": "title", "price": 150},
    {"item_key": "title_yufeng", "name": "御风", "desc": "驭词而行，御风千里", "type": "title", "price": 220},
    {"item_key": "title_guanxing", "name": "观星", "desc": "观星照词海，问道于朝", "type": "title", "price": 350},
    {"item_key": "decor_pine_border", "name": "松风边框", "desc": "卡片换松风主题边框", "type": "decor", "price": 80},
    {"item_key": "decor_sunrise", "name": "晨光氛围", "desc": "归处页顶部晨光渐变氛围条", "type": "decor", "price": 150},
    {"item_key": "egg_hidden_words", "name": "冷门好词集", "desc": "解锁冷门好词隐藏内容", "type": "egg", "price": 120},
    {"item_key": "egg_idiom_cards", "name": "英语习语趣味卡", "desc": "解锁习语趣味卡内容", "type": "egg", "price": 200},
]

# ── 晨语库（随日期轮换） ──────────────────────────────────────────
QUOTES = [
    ("晨光熹微，宜读书。", "朝词浅阅"),
    ("把今天的第一页翻开。", "朝词浅阅"),
    ("词汇是清晨的露水，积多了便是江河。", "朝词浅阅"),
    ("读一页，世界便亮一分。", "朝词浅阅"),
    ("坚持是最朴素的天赋。", "朝词浅阅"),
]

# ── 温暖话语（随连续天数递进）───────────────────────────────────
WARM_WORDS = [
    (1, "开始就是最好的进步"),
    (3, "微光正聚"),
    (7, "习惯正在发芽"),
    (15, "渐入佳境"),
    (30, "你已走出一条路"),
    (100, "朝闻道，夕可诵"),
]


class RewardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EnglishRepository(db)

    # ── 工具 ─────────────────────────────────────────────────────
    def _streak_days(self, user_id: int) -> int:
        dates = self.repo.list_checkin_dates(user_id)
        date_set = set(dates)
        streak = 0
        d = date.today()
        if d not in date_set:
            d -= timedelta(days=1)
        while d in date_set:
            streak += 1
            d -= timedelta(days=1)
        return streak

    def _task_done(self, user_id: int, key: str) -> bool:
        today = date.today()
        if key == "checkin":
            return self.repo.get_checkin(user_id, today) is not None
        if key == "srs_study":
            return self.repo.sum_daily_words(user_id, today) >= 20
        if key == "reading":
            rec = self.repo.get_daily_reading(user_id, today)
            return rec is not None and rec.status == "done"
        if key == "quiz":
            rec = self.repo.get_daily_reading(user_id, today)
            return (
                rec is not None
                and rec.total_questions > 0
                and rec.correct_count >= rec.total_questions / 2
            )
        return False

    def _grant(self, user: User, amount: int, reason: str, ref_date: date, note: str = "") -> bool:
        """发放积分并写流水；重复发放返回 False"""
        if self.repo.get_point_log(user.id, reason, ref_date):
            return False
        points = self.repo.get_points(user.id) or self.repo.create_points(user.id)
        points.balance += amount
        points.total_earned += amount
        self.db.commit()
        self.repo.create_point_log(user.id, amount, reason, ref_date, note)
        return True

    # ── 每日任务结算 ─────────────────────────────────────────────
    def collect(self, user: User) -> CollectOut:
        today = date.today()
        self.repo.get_points(user.id) or self.repo.create_points(user.id)
        earned_total = 0
        task_results: list[RewardTaskOut] = []
        for t in TASKS:
            done = self._task_done(user.id, t["key"])
            already = self.repo.get_point_log(user.id, t["key"], today) is not None
            if done and not already:
                if self._grant(user, t["points"], t["key"], today, t["name"]):
                    earned_total += t["points"]
            task_results.append(
                RewardTaskOut(
                    key=t["key"], name=t["name"], desc=t["desc"],
                    points=t["points"], done=done, earned=already or (done and not already),
                )
            )

        # 里程碑
        streak = self._streak_days(user.id)
        milestones: list[str] = []
        for days, bonus in MILESTONES.items():
            reason = f"milestone_{days}"
            if streak >= days and self._grant(user, bonus, reason, today, f"连续打卡 {days} 天"):
                earned_total += bonus
                milestones.append(reason)

        points = self.repo.get_points(user.id) or self.repo.create_points(user.id)
        message = self._warm_word(streak)
        quote, source = self._daily_quote()
        return CollectOut(
            earned_total=earned_total,
            tasks=task_results,
            milestones=milestones,
            message=message,
            quote=quote,
        )

    def _warm_word(self, streak: int) -> str:
        word = "继续坚持，进步正在积累"
        for days, text in WARM_WORDS:
            if streak >= days:
                word = text
        return word

    def _daily_quote(self) -> tuple[str, str]:
        idx = date.today().toordinal() % len(QUOTES)
        return QUOTES[idx]

    # ── 概览 / 兑换站 ────────────────────────────────────────────
    def overview(self, user: User) -> RewardOverviewOut:
        points = self.repo.get_points(user.id) or self.repo.create_points(user.id)
        settings = self.repo.get_reward_settings(user.id) or self.repo.create_reward_settings(user.id)
        unlocks = {u.item_key for u in self.repo.list_unlocks(user.id)}
        tasks: list[RewardTaskOut] = []
        today = date.today()
        today_earned = 0
        for t in TASKS:
            done = self._task_done(user.id, t["key"])
            earned = self.repo.get_point_log(user.id, t["key"], today) is not None
            if earned:
                today_earned += t["points"]
            tasks.append(
                RewardTaskOut(
                    key=t["key"], name=t["name"], desc=t["desc"],
                    points=t["points"], done=done, earned=earned,
                )
            )
        quote, source = self._daily_quote()
        return RewardOverviewOut(
            balance=points.balance,
            total_earned=points.total_earned,
            streak_days=self._streak_days(user.id),
            today_earned=today_earned,
            tasks=tasks,
            unlocked_keys=sorted(unlocks),
            equipped_title=settings.equipped_title,
            equipped_decor=settings.equipped_decor,
            quote=quote,
            quote_source=source,
        )

    def shop(self, user: User) -> list[ShopItemOut]:
        unlocks = {u.item_key for u in self.repo.list_unlocks(user.id)}
        return [
            ShopItemOut(
                item_key=i["item_key"], name=i["name"], desc=i["desc"],
                type=i["type"], price=i["price"],
                is_unlocked=i["item_key"] in unlocks,
            )
            for i in SHOP_ITEMS
        ]

    def redeem(self, user: User, item_key: str) -> ShopItemOut:
        item = next((i for i in SHOP_ITEMS if i["item_key"] == item_key), None)
        if not item:
            raise ValidationException("奖励不存在")
        if self.repo.get_unlock(user.id, item_key):
            raise ValidationException("该奖励已解锁")
        points = self.repo.get_points(user.id) or self.repo.create_points(user.id)
        if points.balance < item["price"]:
            raise ValidationException("积分不足，继续学习攒积分吧")
        points.balance -= item["price"]
        self.db.commit()
        self.repo.create_point_log(user.id, -item["price"], "redeem", date.today(), item["name"])
        self.repo.create_unlock(user.id, item_key)
        return ShopItemOut(
            item_key=item_key, name=item["name"], desc=item["desc"],
            type=item["type"], price=item["price"], is_unlocked=True,
        )

    def equip(self, user: User, item_key: str | None) -> dict:
        settings = self.repo.get_reward_settings(user.id) or self.repo.create_reward_settings(user.id)
        if item_key is None:
            settings.equipped_title = None
        else:
            item = next((i for i in SHOP_ITEMS if i["item_key"] == item_key), None)
            if not item or item["type"] != "title":
                raise ValidationException("只能佩戴称号")
            if not self.repo.get_unlock(user.id, item_key):
                raise ValidationException("尚未解锁该称号")
            settings.equipped_title = item_key
        self.db.commit()
        return {"equipped_title": settings.equipped_title, "equipped_decor": settings.equipped_decor}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest app/tests/test_reward_service.py -v`
Expected: PASS（test_points_repository / test_point_log_unique / test_collect_single_day / test_collect_milestone / test_redeem_and_equip 全部通过）

> 若 `test_point_log_unique` 因 sqlite 不强制唯一约束而失败，改为断言 `list_point_logs` 逻辑正确（去掉重复写入一行），并在提交信息注明。

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/english/reward_service.py backend/app/tests/test_reward_service.py
git commit -m "feat: add reward service with daily tasks, milestones, shop"
```

---

### Task 6: API 路由

**Files:**
- Modify: `backend/app/api/v1/english.py`（末尾追加奖励路由；顶部 import 补 RewardService 与 Schemas）

**Interfaces:**
- Consumes: Task 5 RewardService
- Produces: 5 个接口

- [ ] **Step 1: 追加 import 与路由**

在 `english.py` 顶部 import 区追加：

```python
from app.services.english.reward_service import RewardService
from app.services.english.schemas import (
    ...
    CollectOut,
    EquipIn,
    RedeemIn,
    RewardOverviewOut,
    ShopItemOut,
)
```

文件末尾追加：

```python
# ── 奖励系统 ──────────────────────────────────────────────────────


@router.get("/rewards/overview", response_model=UnifiedResponse[RewardOverviewOut])
def rewards_overview(user: UserDep, db: DbDep) -> UnifiedResponse[RewardOverviewOut]:
    return UnifiedResponse.success(data=RewardService(db).overview(user))


@router.get("/rewards/shop", response_model=UnifiedResponse[list[ShopItemOut]])
def rewards_shop(user: UserDep, db: DbDep) -> UnifiedResponse[list[ShopItemOut]]:
    return UnifiedResponse.success(data=RewardService(db).shop(user))


@router.post("/rewards/collect", response_model=UnifiedResponse[CollectOut])
def rewards_collect(user: UserDep, db: DbDep) -> UnifiedResponse[CollectOut]:
    return UnifiedResponse.success(data=RewardService(db).collect(user), message="奖励结算完成")


@router.post("/rewards/redeem", response_model=UnifiedResponse[ShopItemOut])
def rewards_redeem(data: RedeemIn, user: UserDep, db: DbDep) -> UnifiedResponse[ShopItemOut]:
    return UnifiedResponse.success(data=RewardService(db).redeem(user, data.item_key), message="兑换成功")


@router.post("/rewards/equip", response_model=UnifiedResponse[dict])
def rewards_equip(data: EquipIn, user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    return UnifiedResponse.success(data=RewardService(db).equip(user, data.item_key))
```

- [ ] **Step 2: 冒烟验证（路由可导入）**

Run: `cd backend && python -c "from app.api.v1.english import router; print(len(router.routes), 'routes')"`
Expected: 打印路由数，无 ImportError

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/v1/english.py
git commit -m "feat: add reward API routes"
```

---

### Task 7: API 集成测试（可选但推荐）

**Files:**
- Modify: `backend/app/tests/test_reward_service.py`（追加）

- [ ] **Step 1: 追加 API 层测试**

在 `test_reward_service.py` 追加（复用 user fixture；用 `app.main.app` + TestClient，参照 `test_api.py` 登录方式）：

```python
def test_reward_api_flow(db: Session, user: User) -> None:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.english.service import EnglishService

    # 直接用 service 发 token
    access, _ = EnglishService(db)._issue_tokens(user, get_english_tenant(db))
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {access}"}

    r = client.get("/api/v1/english/rewards/overview", headers=headers)
    assert r.status_code == 200 and r.json()["code"] == 0
    assert "tasks" in r.json()["data"]

    r = client.get("/api/v1/english/rewards/shop", headers=headers)
    assert r.json()["code"] == 0 and len(r.json()["data"]) == 10
```

> 注意：`TestClient(app)` 需要真实 DB（MySQL），若测试环境无 DB 则此任务改为手动 curl 验证，见 Step 2。

- [ ] **Step 2: 运行测试**

Run: `cd backend && python -m pytest app/tests/test_reward_service.py -v`
Expected: PASS；若 API 测试因 DB 依赖失败，用 Step 3 手动验证替代并注明

- [ ] **Step 3: （替代）手动冒烟验证**

后端已在 8001 运行，用已登录 token 验证：

```bash
curl -s -H "Authorization: Bearer <token>" http://localhost:8001/api/v1/english/rewards/overview
curl -s -H "Authorization: Bearer <token>" http://localhost:8001/api/v1/english/rewards/shop
```

Expected: 返回 `{"code":0,"data":{...}}`

- [ ] **Step 4: 提交**

```bash
git add backend/app/tests/test_reward_service.py
git commit -m "test: add reward API integration test"
```

---

### Task 8: 前端 API 封装 + 类型 + Pinia store

**Files:**
- Modify: `english-learning/src/types/index.ts`（追加奖励类型）
- Modify: `english-learning/src/api/english.ts`（追加 5 个 API）
- Create: `english-learning/src/stores/rewards.ts`

**Interfaces:**
- Produces: `useRewardsStore`（`overview / loadOverview / collect / redeem / equip / quoteText`）

- [ ] **Step 1: types/index.ts 追加**

```typescript
// ── 奖励系统 ─────────────────────────────────────────────────────
export interface RewardTask {
  key: string
  name: string
  desc: string
  points: number
  done: boolean
  earned: boolean
}

export interface RewardOverview {
  balance: number
  total_earned: number
  streak_days: number
  today_earned: number
  tasks: RewardTask[]
  unlocked_keys: string[]
  equipped_title: string | null
  equipped_decor: string | null
  quote: string
  quote_source: string
}

export interface ShopItem {
  item_key: string
  name: string
  desc: string
  type: 'title' | 'decor' | 'egg'
  price: number
  is_unlocked: boolean
}

export interface CollectResult {
  earned_total: number
  tasks: RewardTask[]
  milestones: string[]
  message: string
  quote: string
}
```

- [ ] **Step 2: api/english.ts 追加**

```typescript
// ── 奖励系统 ─────────────────────────────────────────────────────
export function getRewardsOverview(): Promise<RewardOverview> {
  return request('/rewards/overview')
}
export function getRewardsShop(): Promise<ShopItem[]> {
  return request('/rewards/shop')
}
export function collectRewards(): Promise<CollectResult> {
  return request('/rewards/collect', { method: 'POST' })
}
export function redeemReward(itemKey: string): Promise<ShopItem> {
  return request('/rewards/redeem', { method: 'POST', body: { item_key: itemKey } })
}
export function equipReward(itemKey: string | null): Promise<{ equipped_title: string | null; equipped_decor: string | null }> {
  return request('/rewards/equip', { method: 'POST', body: { item_key: itemKey } })
}
```

（顶部 import 追加 `CollectResult, RewardOverview, ShopItem`）

- [ ] **Step 3: 创建 stores/rewards.ts**

```typescript
import { ref } from 'vue'
import { defineStore } from 'pinia'
import {
  collectRewards,
  equipReward,
  getRewardsOverview,
  getRewardsShop,
  redeemReward,
} from '@/api/english'
import type { CollectResult, RewardOverview, ShopItem } from '@/types'

export const useRewardsStore = defineStore('rewards', () => {
  const overview = ref<RewardOverview | null>(null)
  const shop = ref<ShopItem[]>([])
  const loading = ref(false)

  async function loadOverview() {
    overview.value = await getRewardsOverview()
  }

  async function loadShop() {
    shop.value = await getRewardsShop()
  }

  async function collect(): Promise<CollectResult> {
    const result = await collectRewards()
    await loadOverview()
    return result
  }

  async function redeem(itemKey: string) {
    await redeemReward(itemKey)
    await Promise.all([loadOverview(), loadShop()])
  }

  async function equip(itemKey: string | null) {
    await equipReward(itemKey)
    await loadOverview()
  }

  return { overview, shop, loading, loadOverview, loadShop, collect, redeem, equip }
})
```

- [ ] **Step 4: 构建验证**

Run: `cd english-learning && npm run build`
Expected: `✓ built`（无 TS 错误）

- [ ] **Step 5: 提交**

```bash
git add english-learning/src/types/index.ts english-learning/src/api/english.ts english-learning/src/stores/rewards.ts
git commit -m "feat: add reward API client and pinia store"
```

---

### Task 9: 前端组件（RewardsPane / 庆祝弹窗 / 到账反馈 / 晨语）

**Files:**
- Create: `english-learning/src/components/DailyQuote.vue`
- Create: `english-learning/src/components/PointToast.vue`
- Create: `english-learning/src/components/RewardCelebrationModal.vue`
- Create: `english-learning/src/components/RewardsPane.vue`

**Interfaces:**
- Consumes: Task 8 store
- Produces: 4 个组件供 Task 10 集成

- [ ] **Step 1: 创建 DailyQuote.vue**

```vue
<script setup lang="ts">
defineProps<{ quote: string; source: string }>()
</script>

<template>
  <div class="daily-quote">
    <span class="dq-mark">「</span>
    <p class="dq-text">{{ quote }}</p>
    <span class="dq-source">—— {{ source }}</span>
  </div>
</template>

<style scoped>
.daily-quote {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 14px 20px;
  border-radius: var(--radius-lg);
  background: linear-gradient(120deg, var(--sun-soft), var(--primary-soft));
  color: var(--text-2);
  font-size: var(--fs-base);
}
.dq-mark {
  color: var(--sun);
  font-size: 18px;
  line-height: 1;
}
.dq-text {
  flex: 1;
  font-family: var(--font-display);
}
.dq-source {
  font-size: var(--fs-xs);
  color: var(--text-3);
  white-space: nowrap;
}
</style>
```

- [ ] **Step 2: 创建 PointToast.vue**

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { Sparkles } from 'lucide-vue-next'

const visible = ref(false)
const amount = ref(0)
const message = ref('')
let timer: ReturnType<typeof setTimeout> | null = null

function show(earned: number, msg: string): void {
  amount.value = earned
  message.value = msg
  visible.value = true
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => (visible.value = false), 2600)
}

defineExpose({ show })
</script>

<template>
  <transition name="float">
    <div v-if="visible" class="point-toast">
      <Sparkles :size="16" :stroke-width="1.8" />
      <span class="pt-amount">+{{ amount }}</span>
      <span class="pt-msg">{{ message }}</span>
    </div>
  </transition>
</template>

<style scoped>
.point-toast {
  position: fixed;
  left: 50%;
  bottom: 120px;
  transform: translateX(-50%);
  z-index: 1100;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 999px;
  background: var(--text);
  color: var(--bg);
  font-size: 14px;
  box-shadow: var(--shadow-lg);
}
.pt-amount {
  color: var(--sun);
  font-weight: 700;
}
.float-enter-active,
.float-leave-active {
  transition: all 0.3s var(--ease);
}
.float-enter-from,
.float-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(12px);
}
</style>
```

- [ ] **Step 3: 创建 RewardCelebrationModal.vue**

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { PartyPopper, X } from 'lucide-vue-next'

const visible = ref(false)
const title = ref('')
const desc = ref('')

function show(t: string, d: string): void {
  title.value = t
  desc.value = d
  visible.value = true
}

function close(): void {
  visible.value = false
}

defineExpose({ show })
</script>

<template>
  <transition name="modal">
    <div v-if="visible" class="modal-mask" @click.self="close">
      <div class="celebration">
        <button class="close" type="button" aria-label="关闭" @click="close">
          <X :size="18" :stroke-width="1.8" />
        </button>
        <div class="cel-icon">
          <PartyPopper :size="30" :stroke-width="1.6" />
        </div>
        <h2 class="cel-title">{{ title }}</h2>
        <p class="cel-desc">{{ desc }}</p>
        <button class="btn btn-primary" type="button" @click="close">收下这份鼓励</button>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.celebration {
  position: relative;
  width: 360px;
  max-width: calc(100vw - 40px);
  padding: 40px 32px 32px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  text-align: center;
  animation: pop 0.4s var(--ease);
  overflow: hidden;
}
.celebration::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--sunrise-glow);
  pointer-events: none;
}
@keyframes pop {
  from {
    transform: scale(0.86) translateY(16px);
    opacity: 0;
  }
  to {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
}
.close {
  position: absolute;
  top: 14px;
  right: 14px;
  border: none;
  background: transparent;
  color: var(--text-3);
}
.cel-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--brand-gradient);
  color: #fff;
  box-shadow: 0 8px 24px var(--sun-soft);
}
.cel-title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 8px;
}
.cel-desc {
  color: var(--text-2);
  margin-bottom: 24px;
}
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
```

> 依赖全局 `.modal-mask`（main.css 已有）。

- [ ] **Step 4: 创建 RewardsPane.vue**

```vue
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Coins, Gift, Medal, Sparkles, Trophy } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useRewardsStore } from '@/stores/rewards'
import DailyQuote from './DailyQuote.vue'
import type { ShopItem } from '@/types'

const auth = useAuthStore()
const store = useRewardsStore()
const activeTab = ref<'tasks' | 'shop'>('tasks')
const shopType = ref<'title' | 'decor' | 'egg'>('title')

const TITLE_META: Record<string, { key: string; name: string }> = {
  title_juling: { key: 'title_juling', name: '聚灵' },
  title_qiming: { key: 'title_qiming', name: '启明' },
  title_yunfeng: { key: 'title_yunfeng', name: '蕴锋' },
  title_chengguang: { key: 'title_chengguang', name: '承光' },
  title_yufeng: { key: 'title_yufeng', name: '御风' },
  title_guanxing: { key: 'title_guanxing', name: '观星' },
}

const shopItems = computed(() => store.shop.filter((i) => i.type === shopType.value))

async function onEquip(item: ShopItem): Promise<void> {
  const current = store.overview?.equipped_title
  await store.equip(current === item.item_key ? null : item.item_key)
}

onMounted(() => {
  store.loadOverview()
  store.loadShop()
})
</script>

<template>
  <div v-if="store.overview" class="rewards">
    <!-- 积分卡 -->
    <div class="points-card">
      <div class="pc-left">
        <div class="pc-icon"><Coins :size="20" :stroke-width="1.8" /></div>
        <div>
          <div class="pc-label">当前积分</div>
          <div class="pc-balance">{{ store.overview.balance }}</div>
        </div>
      </div>
      <div class="pc-right">
        <div class="pc-stat">
          <span class="pc-num">{{ store.overview.streak_days }}</span>
          <span class="pc-cap">连续天数</span>
        </div>
        <div class="pc-stat">
          <span class="pc-num">{{ store.overview.today_earned }}</span>
          <span class="pc-cap">今日已得</span>
        </div>
        <div class="pc-stat">
          <span class="pc-num">{{ store.overview.total_earned }}</span>
          <span class="pc-cap">累计获得</span>
        </div>
      </div>
    </div>

    <DailyQuote :quote="store.overview.quote" :source="store.overview.quote_source" />

    <!-- Tab 切换 -->
    <div class="tabs reward-tabs">
      <button class="tab-item" :class="{ active: activeTab === 'tasks' }" type="button" @click="activeTab = 'tasks'">每日任务</button>
      <button class="tab-item" :class="{ active: activeTab === 'shop' }" type="button" @click="activeTab = 'shop'">兑换站</button>
    </div>

    <!-- 每日任务 -->
    <section v-if="activeTab === 'tasks'" class="task-list">
      <div v-for="t in store.overview.tasks" :key="t.key" class="card task-item" :class="{ done: t.done }">
        <span class="task-icon"><Medal :size="18" :stroke-width="1.8" /></span>
        <div class="task-main">
          <div class="task-name">{{ t.name }}</div>
          <div class="task-desc">{{ t.desc }}</div>
        </div>
        <div class="task-side">
          <span class="task-points">+{{ t.points }}</span>
          <span v-if="t.earned" class="tag tag-success">已领</span>
          <span v-else-if="t.done" class="tag">待领取</span>
        </div>
      </div>
      <p class="task-hint">完成任务后积分自动到账 · 每天 0 点重置</p>
    </section>

    <!-- 兑换站 -->
    <section v-else class="shop">
      <div class="tabs shop-tabs">
        <button class="tab-item" :class="{ active: shopType === 'title' }" type="button" @click="shopType = 'title'">称号</button>
        <button class="tab-item" :class="{ active: shopType === 'decor' }" type="button" @click="shopType = 'decor'">装饰</button>
        <button class="tab-item" :class="{ active: shopType === 'egg' }" type="button" @click="shopType = 'egg'">彩蛋</button>
      </div>
      <div class="shop-grid">
        <div v-for="item in shopItems" :key="item.item_key" class="card shop-item">
          <div class="si-name">{{ item.name }}</div>
          <div class="si-desc">{{ item.desc }}</div>
          <div class="si-foot">
            <span class="si-price"><Gift :size="13" /> {{ item.price }} 分</span>
            <template v-if="item.type === 'title'">
              <button
                v-if="item.is_unlocked"
                class="btn btn-soft btn-sm"
                type="button"
                @click="onEquip(item)"
              >
                {{ store.overview.equipped_title === item.item_key ? '佩戴中' : '佩戴' }}
              </button>
              <span v-else class="tag tag-primary">已拥有</span>
            </template>
            <span v-else-if="item.is_unlocked" class="tag tag-success">已解锁</span>
            <button v-else class="btn btn-primary btn-sm" type="button" @click="store.redeem(item.item_key)">兑换</button>
          </div>
        </div>
      </div>
      <p class="task-hint">称号可佩戴显示在用户名旁 · 装饰与彩蛋解锁后生效</p>
    </section>
  </div>
</template>

<style scoped>
.rewards {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 积分卡 */
.points-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 24px 28px;
  border-radius: var(--radius-xl);
  background: var(--brand-gradient);
  color: #fff;
  box-shadow: 0 12px 32px var(--sun-soft);
}
.pc-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.pc-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.18);
}
.pc-label {
  font-size: 12px;
  opacity: 0.85;
}
.pc-balance {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  line-height: 1.15;
}
.pc-right {
  display: flex;
  gap: 24px;
}
.pc-stat {
  text-align: center;
}
.pc-num {
  display: block;
  font-size: 20px;
  font-weight: 700;
}
.pc-cap {
  font-size: 11px;
  opacity: 0.85;
}

/* 任务 */
.task-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.task-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
}
.task-item.done .task-icon {
  background: var(--success-soft);
  color: var(--success);
}
.task-icon {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: var(--primary-soft);
  color: var(--primary);
}
.task-main {
  flex: 1;
}
.task-name {
  font-weight: 600;
}
.task-desc {
  font-size: var(--fs-sm);
  color: var(--text-2);
}
.task-side {
  display: flex;
  align-items: center;
  gap: 10px;
}
.task-points {
  font-weight: 700;
  color: var(--sun);
}
.task-hint {
  font-size: var(--fs-xs);
  color: var(--text-3);
  text-align: center;
}

/* 兑换站 */
.shop-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}
.shop-item {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.si-name {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
}
.si-desc {
  font-size: var(--fs-sm);
  color: var(--text-2);
  flex: 1;
}
.si-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
}
.si-price {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--sun);
}
.reward-tabs {
  margin-bottom: 0;
}

@media (max-width: 768px) {
  .points-card {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
```

- [ ] **Step 5: 构建验证**

Run: `cd english-learning && npm run build`
Expected: `✓ built`

- [ ] **Step 6: 提交**

```bash
git add english-learning/src/components/DailyQuote.vue english-learning/src/components/PointToast.vue english-learning/src/components/RewardCelebrationModal.vue english-learning/src/components/RewardsPane.vue
git commit -m "feat: add rewards pane, celebration modal, point toast, daily quote"
```

---

### Task 10: 集成（归处 Tab + 打卡结算 + 称号显示）

**Files:**
- Modify: `english-learning/src/views/StudyCenterView.vue`（新增「奖励」Tab）
- Modify: `english-learning/src/components/CheckinPane.vue`（打卡后 collect + 反馈）
- Modify: `english-learning/src/components/UserArea.vue`（称号显示）
- Modify: `english-learning/src/App.vue`（挂载 PointToast + RewardCelebrationModal）

**Interfaces:**
- Consumes: Task 8 store、Task 9 组件

- [ ] **Step 1: StudyCenterView.vue 新增 Tab**

查看该文件 `PageTabs` 用法后，在 tabs 数组追加第 4 项 `{ key: 'rewards', label: '奖励' }`，并在 `v-if` 分支追加：

```vue
<section v-else-if="activeTab === 'rewards'">
  <RewardsPane />
</section>
```

顶部 import：`import RewardsPane from '@/components/RewardsPane.vue'`

- [ ] **Step 2: CheckinPane.vue 打卡后结算**

在打卡成功逻辑处追加（checkin 成功后触发 collect 并展示反馈）：

```typescript
import { useRewardsStore } from '@/stores/rewards'
import { useUiStore } from '@/stores/ui'

const rewards = useRewardsStore()
const ui = useUiStore()

// 打卡成功后：
async function afterCheckin(): Promise<void> {
  try {
    const result = await rewards.collect()
    if (result.earned_total > 0) {
      ui.showToast(`奖励到账 +${result.earned_total} 分 · ${result.message}`)
    }
  } catch {
    /* 奖励结算失败不阻塞打卡 */
  }
}
```

> 在打卡按钮的 click handler 中于 `checkin()` 成功后调用 `afterCheckin()`。

- [ ] **Step 3: App.vue 挂载反馈组件**

在模板中追加（用 ref 暴露 `show` 方法，供 RewardsPane 等调用）：

```vue
<PointToast ref="pointToast" />
<RewardCelebrationModal ref="celebrationModal" />
```

> 需要时可把 toast/modal 实例通过 provide/inject 或简单全局 ref 暴露；本迭代在 RewardsPane 内直接引用各自实例即可（RewardsPane 内 `const toast = ref<InstanceType<typeof PointToast>>()` 并 `toast.value?.show(...)`）。

- [ ] **Step 4: UserArea.vue 称号显示**

在用户名旁追加称号标签（读 rewards store 的 `overview.equipped_title`，映射到中文名，可用 Task 9 的 `TITLE_META`）：

```vue
<span v-if="titleName" class="user-title">{{ titleName }}</span>
```

样式：`font-size: 11px; color: var(--sun); border: 1px solid var(--sun-soft); border-radius: 999px; padding: 1px 8px; background: var(--sun-soft);`

> UserArea 挂载时需 `rewards.loadOverview()`（仅登录用户）。若 UserArea 结构不便，可移到 AppHeader 登录区展示。

- [ ] **Step 5: 构建验证**

Run: `cd english-learning && npm run build`
Expected: `✓ built`

- [ ] **Step 6: 浏览器冒烟（可选）**

本地服务运行中打开 http://localhost:5174/study-center?tab=rewards，登录后确认「奖励」Tab 渲染、打卡后积分到账。

- [ ] **Step 7: 提交**

```bash
git add english-learning/src/views/StudyCenterView.vue english-learning/src/components/CheckinPane.vue english-learning/src/components/UserArea.vue english-learning/src/App.vue
git commit -m "feat: integrate rewards into study center, checkin collect, title display"
```

---

### Task 11: 全量回归 + 提交

**Files:** 无新增

- [ ] **Step 1: 后端全量测试**

Run: `cd backend && python -m pytest app/tests/ -q`
Expected: 全部通过（含新奖励测试）

- [ ] **Step 2: 前端全量构建 + 单元测试**

Run:
```bash
cd english-learning && npm run build
npm test
```
Expected: `✓ built`；vitest 全部通过

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "chore: reward system regression pass"
```

> 若 `docs/` 被 .gitignore 忽略，不要 `git add -A` 带上（除非设计文档已用 -f 提交）。提交前用 `git status` 确认。
