"""奖励系统业务服务

积分 · 每日任务 · 里程碑 · 兑换站 · 晨语与温暖话语
"""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException
from app.services.english.repository import EnglishRepository
from app.services.english.schemas import (
    CollectOut,
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
        self.db.flush()
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
            # 里程碑一次性发放：历史任何一天发过就不再发（跨天幂等）
            if streak >= days and not self.repo.has_point_log(user.id, reason):
                if self._grant(user, bonus, reason, today, f"连续打卡 {days} 天"):
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
        self.db.flush()
        self.repo.create_point_log(user.id, -item["price"], f"redeem_{item_key}", date.today(), item["name"])
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
