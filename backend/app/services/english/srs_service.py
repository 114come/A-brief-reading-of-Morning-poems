"""SRS 背单词持久化 + 聚合服务

SRS 状态机逻辑完全由前端纯 TS 引擎（srsEngine.ts）计算，本服务只做：
持久化记忆行/日会话、开卡批量初始化、打卡+日统计、游客→云端合并、
清空、统计聚合。绝不做 SRS 间隔决策。
"""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.services.english.models import UserWordbook
from app.services.english.repository import EnglishRepository
from app.services.english.schemas import (
    BookStats,
    CompleteOut,
    MemoryRow,
    SrsSessionState,
    SrsSettingsOut,
    SrsStateOut,
    SyncOut,
    WordBookOut,
    WordbookItemOut,
)
from app.services.tenant.models import User


class SrsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EnglishRepository(db)

    # ── 词书 ──────────────────────────────────────────────────────
    def get_books(self, tenant_id: int) -> list[WordBookOut]:
        books = self.repo.list_books(tenant_id)
        return [
            WordBookOut(
                id=b.id,
                code=b.code,
                name=b.name,
                sort_order=b.sort_order,
                word_count=self.repo.count_words_in_book(b.id),
            )
            for b in books
        ]

    # ── 状态读写 ──────────────────────────────────────────────────
    def get_state(self, user: User, book_id: int | None) -> SrsStateOut:
        settings = self.repo.get_settings(user.id)
        if book_id is None:
            book_id = settings.book_id if settings else None
        if book_id is None:
            return SrsStateOut(settings=None, memory=[], session=None)
        settings_out = None
        if settings:
            settings_out = SrsSettingsOut(
                book_id=settings.book_id,
                target=settings.target,
                daily_new_words=settings.daily_new_words,
                pronunciation=settings.pronunciation,
                autoplay=settings.autoplay,
                onboarding_done=settings.onboarding_done,
            )
        memory = [
            MemoryRow(
                word_id=m.word_id,
                status=m.status,
                next_review_date=m.next_review_date,
                interval=m.current_interval,
                wrong_count=m.wrong_count,
            )
            for m in self.repo.list_memory(user.id, book_id)
        ]
        session = self.repo.get_session(user.id, book_id, date.today())
        return SrsStateOut(
            settings=settings_out,
            memory=memory,
            session=SrsSessionState(**session.state) if session else None,
        )

    def save_state(self, user: User, book_id: int, memory: list[MemoryRow], session: SrsSessionState | None) -> dict:
        for row in memory:
            self.repo.upsert_memory_row(
                user.id,
                row.word_id,
                book_id,
                {
                    "status": row.status,
                    "next_review_date": row.next_review_date,
                    "interval": row.interval,
                    "wrong_count": row.wrong_count,
                },
            )
        if session and session.date:
            try:
                session_date = date.fromisoformat(session.date)
            except ValueError:
                raise ValidationException("会话日期格式错误")
            self.repo.upsert_session(user.id, book_id, session_date, session.model_dump())
        return {"saved": True}

    # ── 引导 ──────────────────────────────────────────────────────
    def save_onboarding(self, user: User, target: str, book_id: int, daily_new_words: int, pronunciation: str, autoplay: bool) -> SrsSettingsOut:
        book = self.repo.get_book(book_id)
        if not book:
            raise NotFoundException("词书不存在")
        word_ids = self.repo.list_book_word_ids(book_id)
        # 批量初始化该词书全部单词 status=0（仅当该词书尚无任何记忆行时）
        self.repo.bulk_init_memory(user.id, book_id, word_ids)
        settings = self.repo.upsert_settings(
            user.id,
            book_id=book_id,
            target=target,
            daily_new_words=daily_new_words,
            pronunciation=pronunciation,
            autoplay=autoplay,
            onboarding_done=True,
        )
        return SrsSettingsOut(
            book_id=settings.book_id,
            target=settings.target,
            daily_new_words=settings.daily_new_words,
            pronunciation=settings.pronunciation,
            autoplay=settings.autoplay,
            onboarding_done=settings.onboarding_done,
        )

    # ── 完成每日 ──────────────────────────────────────────────────
    def complete_day(self, user: User, book_id: int, study_date: date, review_count: int, new_count: int, wrong_count: int) -> CompleteOut:
        # 钳制异常时钟：study_date 须在服务器当天 ±1 天内
        today = date.today()
        if abs((study_date - today).days) > 1:
            raise ValidationException("学习日期异常")
        if not self.repo.get_checkin(user.id, study_date):
            self.repo.create_checkin(user.id, study_date)
        self.repo.upsert_daily_stats(user.id, book_id, study_date, review_count, new_count, wrong_count)
        checkin = self._checkin_stats(user)
        summary = {
            "total_studied": self._count_studied(user.id),
            "wordbook_count": self.repo.count_wordbook(user.id),
            "mastered_count": self._count_mastered(user.id),
            "streak_days": checkin["streak_days"],
        }
        return CompleteOut(checkin=checkin, summary=summary)

    # ── 游客同步 ──────────────────────────────────────────────────
    def sync_guest(self, user: User, book_id: int, memory: list[MemoryRow], wordbook: list[int]) -> SyncOut:
        """合并游客本地数据到云端：
        - 云端无行 → 整批导入；
        - 云端有行 → 保留 status 更高者；同值取 next_review_date 更晚者；绝不删云端行。
        """
        memory_merged = 0
        for row in memory:
            existing = self.repo.get_memory(user.id, row.word_id, book_id)
            if existing is None:
                self.repo.upsert_memory_row(
                    user.id, row.word_id, book_id,
                    {
                        "status": row.status,
                        "next_review_date": row.next_review_date,
                        "interval": row.interval,
                        "wrong_count": row.wrong_count,
                    },
                )
                memory_merged += 1
                continue
            # 合并规则：status 高者胜；同 status 取 next_review_date 更晚者
            if row.status > existing.status:
                self.repo.upsert_memory_row(
                    user.id, row.word_id, book_id,
                    {
                        "status": row.status,
                        "next_review_date": row.next_review_date,
                        "interval": row.interval,
                        "wrong_count": row.wrong_count,
                    },
                )
                memory_merged += 1
            elif row.status == existing.status:
                guest_date = row.next_review_date
                cloud_date = existing.next_review_date
                if guest_date and (cloud_date is None or guest_date > cloud_date):
                    self.repo.upsert_memory_row(
                        user.id, row.word_id, book_id,
                        {
                            "status": row.status,
                            "next_review_date": row.next_review_date,
                            "interval": row.interval,
                            "wrong_count": row.wrong_count,
                        },
                    )
                    memory_merged += 1
        wordbook_merged = 0
        for word_id in wordbook:
            item = self.repo.add_to_wordbook(user.id, word_id, book_id)
            if item:
                wordbook_merged += 1
        return SyncOut(memory_merged=memory_merged, wordbook_merged=wordbook_merged)

    # ── 清空 ──────────────────────────────────────────────────────
    def reset_book(self, user: User, book_id: int) -> dict:
        self.repo.delete_memory_for_book(user.id, book_id)
        self.repo.delete_session_for_book(user.id, book_id)
        self.repo.clear_wordbook(user.id, book_id)
        self.repo.delete_daily_stats_for_user(user.id)
        self.repo.delete_checkins_for_user(user.id)
        # 设置保留（词书可再引导），但标记未完成引导以回到全新状态
        settings = self.repo.get_settings(user.id)
        if settings:
            settings.onboarding_done = False
            self.db.commit()
        return {"reset": True}

    # ── 统计 ──────────────────────────────────────────────────────
    def srs_stats(self, user: User) -> dict:
        per_book: list[BookStats] = []
        for book in self.repo.list_books(user.tenant_id):
            total = self.repo.count_words_in_book(book.id)
            learning = self._count_status(user.id, book.id, 1)
            mastered = self._count_status(user.id, book.id, 2)
            per_book.append(
                BookStats(
                    book_id=book.id,
                    total_words=total,
                    unlearned=total - learning - mastered,
                    learning=learning,
                    mastered=mastered,
                    wordbook_count=self.repo.count_wordbook(user.id, book.id),
                )
            )
        checkin = self._checkin_stats(user)
        return {
            "total_studied": self._count_studied(user.id),
            "wordbook_count": self.repo.count_wordbook(user.id),
            "mastered_count": self._count_mastered(user.id),
            "streak_days": checkin["streak_days"],
            "total_days": checkin["total_days"],
            "today_done": checkin["today_done"],
            "per_book": per_book,
        }

    # ── 生词本 ────────────────────────────────────────────────────
    def list_wordbook(self, user: User, book_id: int | None) -> list[WordbookItemOut]:
        items = self.repo.list_wordbook(user.id, book_id)
        out: list[WordbookItemOut] = []
        for item in items:
            word = self.repo.get_word(item.word_id)
            if not word:
                continue
            out.append(
                WordbookItemOut(
                    id=item.id,
                    book_id=item.book_id,
                    created_at=item.created_at,
                    word=self._word_out(word),
                )
            )
        return out

    def add_wordbook(self, user: User, word_id: int, book_id: int) -> WordbookItemOut:
        word = self.repo.get_word(word_id)
        if not word:
            raise NotFoundException("单词不存在")
        item = self.repo.add_to_wordbook(user.id, word_id, book_id)
        if item is None:
            raise ValidationException("已在生词本中")
        return WordbookItemOut(
            id=item.id,
            book_id=item.book_id,
            created_at=item.created_at,
            word=self._word_out(word),
        )

    def touch_wordbook(self, user: User, wb_id: int) -> None:
        """认识→移除；不认识→保留并提升优先级（touch 后 next 复习优先）"""
        item = self.repo.get_wordbook_by_id(user.id, wb_id)
        if not item:
            raise NotFoundException("生词本记录不存在")
        self.repo.remove_from_wordbook(item)

    def keep_wordbook(self, user: User, wb_id: int) -> None:
        item = self.repo.get_wordbook_by_id(user.id, wb_id)
        if not item:
            raise NotFoundException("生词本记录不存在")
        self.repo.touch_wordbook(item)

    def remove_wordbook(self, user: User, wb_id: int) -> None:
        item = self.repo.get_wordbook_by_id(user.id, wb_id)
        if not item:
            raise NotFoundException("生词本记录不存在")
        self.repo.remove_from_wordbook(item)

    def clear_wordbook(self, user: User, book_id: int) -> None:
        self.repo.clear_wordbook(user.id, book_id)

    # ── 辅助 ──────────────────────────────────────────────────────
    @staticmethod
    def _word_out(word) -> dict:
        from app.services.english.schemas import WordOut

        return WordOut(
            id=word.id,
            book_id=word.book_id,
            word=word.word,
            phonetic=word.phonetic,
            definition=word.definition,
            pos=word.pos,
            example=word.example,
            example2=word.example2,
            phrase=word.phrase,
            level=word.level,
            tags=word.tags,
            in_wordbook=False,
            is_favorite=False,
        ).model_dump()

    def _count_studied(self, user_id: int) -> int:
        from app.services.english.models import UserWordMemory

        return (
            self.db.query(UserWordMemory)
            .filter(UserWordMemory.user_id == user_id, UserWordMemory.status >= 1)
            .count()
        )

    def _count_mastered(self, user_id: int) -> int:
        from app.services.english.models import UserWordMemory

        return (
            self.db.query(UserWordMemory)
            .filter(UserWordMemory.user_id == user_id, UserWordMemory.status == 2)
            .count()
        )

    def _count_status(self, user_id: int, book_id: int, status: int) -> int:
        from app.services.english.models import UserWordMemory

        return (
            self.db.query(UserWordMemory)
            .filter(
                UserWordMemory.user_id == user_id,
                UserWordMemory.book_id == book_id,
                UserWordMemory.status == status,
            )
            .count()
        )

    def _checkin_stats(self, user: User) -> dict:
        dates = self.repo.list_checkin_dates(user.id)
        date_set = set(dates)
        streak = 0
        d = date.today()
        if d not in date_set:
            d -= timedelta(days=1)
        while d in date_set:
            streak += 1
            d -= timedelta(days=1)
        return {
            "streak_days": streak,
            "total_days": len(dates),
            "today_done": date.today() in date_set,
        }
