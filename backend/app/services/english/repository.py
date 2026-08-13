"""英语学习数据访问层"""
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.services.english.models import (
    CheckinRecord,
    EnglishReadingArticle,
    EnglishWord,
    EnglishWordBook,
    ReadingNote,
    ReadingWordBlacklist,
    RewardPointLog,
    RewardSettings,
    RewardUnlock,
    RewardUserPoints,
    UserCollection,
    UserDailyActivity,
    UserDailyReading,
    UserDailySession,
    UserDailyStats,
    UserDailySummary,
    UserWordbook,
    UserWordMemory,
    UserWordSettings,
)


class EnglishRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── 词书 ──────────────────────────────────────────────────────
    def list_books(self, tenant_id: int) -> list[EnglishWordBook]:
        return (
            self.db.query(EnglishWordBook)
            .filter(EnglishWordBook.tenant_id == tenant_id)
            .order_by(EnglishWordBook.sort_order)
            .all()
        )

    def get_book(self, book_id: int) -> EnglishWordBook | None:
        return self.db.query(EnglishWordBook).filter(EnglishWordBook.id == book_id).first()

    def count_words_in_book(self, book_id: int) -> int:
        return self.db.query(EnglishWord).filter(EnglishWord.book_id == book_id).count()

    # ── 单词 ──────────────────────────────────────────────────────
    def list_words(
        self,
        tenant_id: int,
        book_id: int | None = None,
        level: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EnglishWord]:
        query = self.db.query(EnglishWord).filter(EnglishWord.tenant_id == tenant_id)
        if book_id:
            query = query.filter(EnglishWord.book_id == book_id)
        if level:
            query = query.filter(EnglishWord.level == level)
        return query.order_by(EnglishWord.id).offset(skip).limit(limit).all()

    def list_book_word_ids(self, book_id: int) -> list[int]:
        rows = self.db.query(EnglishWord.id).filter(EnglishWord.book_id == book_id).all()
        return [r[0] for r in rows]

    def get_word(self, word_id: int) -> EnglishWord | None:
        return self.db.query(EnglishWord).filter(EnglishWord.id == word_id).first()

    def get_word_by_text(self, word: str, tenant_id: int) -> EnglishWord | None:
        return (
            self.db.query(EnglishWord)
            .filter(EnglishWord.tenant_id == tenant_id, EnglishWord.word == word)
            .first()
        )

    def get_word_in_book(self, word: str, book_id: int) -> EnglishWord | None:
        return (
            self.db.query(EnglishWord)
            .filter(EnglishWord.book_id == book_id, EnglishWord.word == word)
            .first()
        )

    def list_words_in(self, ids: list[int]) -> list[EnglishWord]:
        if not ids:
            return []
        return self.db.query(EnglishWord).filter(EnglishWord.id.in_(ids)).all()

    def create_word_copy(
        self,
        tenant_id: int,
        book_id: int,
        word: str,
        definition: str,
        phonetic: str | None = None,
        pos: str | None = None,
        example: str | None = None,
        example_cn: str | None = None,
    ) -> EnglishWord:
        """把阅读生词补进指定词书（幂等：unique(book_id, word)，已存在则复用）"""
        existing = self.get_word_in_book(word, book_id)
        if existing:
            return existing
        item = EnglishWord(
            tenant_id=tenant_id, book_id=book_id, word=word,
            definition=definition or "（暂无释义）",
            phonetic=phonetic, pos=pos, example=example, example_cn=example_cn,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def count_words(self, tenant_id: int) -> int:
        return self.db.query(EnglishWord).filter(EnglishWord.tenant_id == tenant_id).count()

    # ── SRS 记忆 ──────────────────────────────────────────────────
    def list_memory(self, user_id: int, book_id: int) -> list[UserWordMemory]:
        return (
            self.db.query(UserWordMemory)
            .filter(UserWordMemory.user_id == user_id, UserWordMemory.book_id == book_id)
            .all()
        )

    def get_memory(self, user_id: int, word_id: int, book_id: int) -> UserWordMemory | None:
        return (
            self.db.query(UserWordMemory)
            .filter(
                UserWordMemory.user_id == user_id,
                UserWordMemory.word_id == word_id,
                UserWordMemory.book_id == book_id,
            )
            .first()
        )

    def bulk_init_memory(self, user_id: int, book_id: int, word_ids: list[int]) -> None:
        """批量初始化记忆行 status=0（仅当该 (user, book) 尚无任何行时）"""
        existing_count = (
            self.db.query(UserWordMemory)
            .filter(UserWordMemory.user_id == user_id, UserWordMemory.book_id == book_id)
            .count()
        )
        if existing_count > 0:
            return
        for word_id in word_ids:
            self.db.add(
                UserWordMemory(
                    user_id=user_id, word_id=word_id, book_id=book_id,
                    status=0, next_review_date=None, current_interval=0, wrong_count=0,
                )
            )
        self.db.commit()

    def upsert_memory_row(self, user_id: int, word_id: int, book_id: int, data: dict) -> UserWordMemory:
        row = self.get_memory(user_id, word_id, book_id)
        if row is None:
            row = UserWordMemory(user_id=user_id, word_id=word_id, book_id=book_id)
            self.db.add(row)
        row.status = int(data.get("status", 0))
        row.next_review_date = data.get("next_review_date")
        row.current_interval = int(data.get("interval", 0))
        row.wrong_count = int(data.get("wrong_count", 0))
        row.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_memory_for_book(self, user_id: int, book_id: int) -> None:
        self.db.query(UserWordMemory).filter(
            UserWordMemory.user_id == user_id, UserWordMemory.book_id == book_id
        ).delete()
        self.db.commit()

    # ── 设置 ──────────────────────────────────────────────────────
    def get_settings(self, user_id: int) -> UserWordSettings | None:
        return self.db.query(UserWordSettings).filter(UserWordSettings.user_id == user_id).first()

    def upsert_settings(self, user_id: int, **kwargs) -> UserWordSettings:
        settings = self.get_settings(user_id)
        if settings is None:
            settings = UserWordSettings(user_id=user_id)
            self.db.add(settings)
        for k, v in kwargs.items():
            setattr(settings, k, v)
        settings.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(settings)
        return settings

    # ── 日会话 ────────────────────────────────────────────────────
    def get_session(self, user_id: int, book_id: int, session_date: date) -> UserDailySession | None:
        return (
            self.db.query(UserDailySession)
            .filter(
                UserDailySession.user_id == user_id,
                UserDailySession.book_id == book_id,
                UserDailySession.session_date == session_date,
            )
            .first()
        )

    def upsert_session(self, user_id: int, book_id: int, session_date: date, state: dict) -> UserDailySession:
        """原子 upsert（并发安全）：先查，无则插；存在则更新"""
        from sqlalchemy import text

        row = self.get_session(user_id, book_id, session_date)
        if row is None:
            try:
                row = UserDailySession(user_id=user_id, book_id=book_id, session_date=session_date)
                self.db.add(row)
                self.db.flush()
            except Exception:
                self.db.rollback()
                row = self.get_session(user_id, book_id, session_date)
        if row is None:
            raise RuntimeError("session upsert failed")
        row.state = state
        row.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_session_for_book(self, user_id: int, book_id: int) -> None:
        self.db.query(UserDailySession).filter(
            UserDailySession.user_id == user_id, UserDailySession.book_id == book_id
        ).delete()
        self.db.commit()

    # ── 日统计 ────────────────────────────────────────────────────
    def get_daily_stats(self, user_id: int, book_id: int, study_date: date) -> UserDailyStats | None:
        return (
            self.db.query(UserDailyStats)
            .filter(
                UserDailyStats.user_id == user_id,
                UserDailyStats.book_id == book_id,
                UserDailyStats.study_date == study_date,
            )
            .first()
        )

    def upsert_daily_stats(self, user_id: int, book_id: int, study_date: date, review_count: int, new_count: int, wrong_count: int) -> UserDailyStats:
        row = self.get_daily_stats(user_id, book_id, study_date)
        if row is None:
            row = UserDailyStats(
                user_id=user_id, book_id=book_id, study_date=study_date,
                review_count=review_count, new_count=new_count, wrong_count=wrong_count,
            )
            self.db.add(row)
        else:
            # 多轮学习累加，而非覆盖
            row.review_count += review_count
            row.new_count += new_count
            row.wrong_count += wrong_count
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_daily_stats_for_user(self, user_id: int) -> None:
        self.db.query(UserDailyStats).filter(UserDailyStats.user_id == user_id).delete()
        self.db.commit()

    def delete_checkins_for_user(self, user_id: int) -> None:
        self.db.query(CheckinRecord).filter(CheckinRecord.user_id == user_id).delete()
        self.db.commit()

    # ── 生词本（纯列表） ──────────────────────────────────────────
    def list_wordbook(self, user_id: int, book_id: int | None = None) -> list[UserWordbook]:
        query = self.db.query(UserWordbook).filter(UserWordbook.user_id == user_id)
        if book_id:
            query = query.filter(UserWordbook.book_id == book_id)
        return query.order_by(UserWordbook.updated_at.desc()).all()

    def get_wordbook(self, user_id: int, word_id: int, book_id: int) -> UserWordbook | None:
        return (
            self.db.query(UserWordbook)
            .filter(
                UserWordbook.user_id == user_id,
                UserWordbook.word_id == word_id,
                UserWordbook.book_id == book_id,
            )
            .first()
        )

    def get_wordbook_by_id(self, user_id: int, wb_id: int) -> UserWordbook | None:
        return (
            self.db.query(UserWordbook)
            .filter(UserWordbook.id == wb_id, UserWordbook.user_id == user_id)
            .first()
        )

    def add_to_wordbook(self, user_id: int, word_id: int, book_id: int) -> UserWordbook | None:
        existing = self.get_wordbook(user_id, word_id, book_id)
        if existing:
            existing.updated_at = datetime.now()
            self.db.commit()
            return existing
        item = UserWordbook(user_id=user_id, word_id=word_id, book_id=book_id)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def touch_wordbook(self, item: UserWordbook) -> UserWordbook:
        item.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(item)
        return item

    def remove_from_wordbook(self, item: UserWordbook) -> None:
        self.db.delete(item)
        self.db.commit()

    def clear_wordbook(self, user_id: int, book_id: int) -> None:
        self.db.query(UserWordbook).filter(
            UserWordbook.user_id == user_id, UserWordbook.book_id == book_id
        ).delete()
        self.db.commit()

    def count_wordbook(self, user_id: int, book_id: int | None = None) -> int:
        query = self.db.query(UserWordbook).filter(UserWordbook.user_id == user_id)
        if book_id:
            query = query.filter(UserWordbook.book_id == book_id)
        return query.count()

    def list_wordbook_word_ids(self, user_id: int, book_id: int) -> list[int]:
        rows = (
            self.db.query(UserWordbook.word_id)
            .filter(UserWordbook.user_id == user_id, UserWordbook.book_id == book_id)
            .all()
        )
        return [r[0] for r in rows]

    # ── 单词分类 ─────────────────────────────────────────────────
    def get_word_tag(self, user_id: int, word_id: int, book_id: int) -> str | None:
        from app.services.english.models import UserWordTag

        row = (
            self.db.query(UserWordTag)
            .filter(
                UserWordTag.user_id == user_id,
                UserWordTag.word_id == word_id,
                UserWordTag.book_id == book_id,
            )
            .first()
        )
        return row.tag if row else None

    def list_word_tags(self, user_id: int, book_id: int, word_ids: list[int] | None = None) -> dict[int, str]:
        """返回 {word_id: tag}"""
        from app.services.english.models import UserWordTag

        query = self.db.query(UserWordTag).filter(
            UserWordTag.user_id == user_id, UserWordTag.book_id == book_id
        )
        if word_ids:
            query = query.filter(UserWordTag.word_id.in_(word_ids))
        rows = query.all()
        return {r.word_id: r.tag for r in rows}

    def set_word_tag(self, user_id: int, word_id: int, book_id: int, tag: str | None) -> None:
        """设置/清除单词分类。tag 为空则删除记录。"""
        from app.services.english.models import UserWordTag

        existing = (
            self.db.query(UserWordTag)
            .filter(
                UserWordTag.user_id == user_id,
                UserWordTag.word_id == word_id,
                UserWordTag.book_id == book_id,
            )
            .first()
        )
        if not tag:
            if existing:
                self.db.delete(existing)
                self.db.commit()
            return
        if existing:
            existing.tag = tag
            existing.updated_at = datetime.now()
        else:
            self.db.add(UserWordTag(user_id=user_id, word_id=word_id, book_id=book_id, tag=tag))
        self.db.commit()

    def count_words_by_tag(self, user_id: int, book_id: int, tag: str) -> int:
        from app.services.english.models import UserWordTag

        return (
            self.db.query(UserWordTag)
            .filter(
                UserWordTag.user_id == user_id,
                UserWordTag.book_id == book_id,
                UserWordTag.tag == tag,
            )
            .count()
        )

    # ── 每日活动 / AI 总结 ───────────────────────────────────────
    def get_activity(self, user_id: int, activity_date: date) -> UserDailyActivity | None:
        return (
            self.db.query(UserDailyActivity)
            .filter(
                UserDailyActivity.user_id == user_id,
                UserDailyActivity.activity_date == activity_date,
            )
            .first()
        )

    def upsert_activity(self, user_id: int, activity_date: date, **fields) -> UserDailyActivity:
        """累加埋点；reading_article_id 去重 append 到 JSON 数组"""
        from app.services.english.models import UserDailyActivity

        row = self.get_activity(user_id, activity_date)
        if row is None:
            row = UserDailyActivity(user_id=user_id, activity_date=activity_date)
            self.db.add(row)
        for key, val in fields.items():
            if key == "reading_article_id":
                if val is None:
                    continue
                arr = list(getattr(row, "reading_article_ids") or [])
                if val not in arr:
                    arr.append(val)
                    setattr(row, "reading_article_ids", arr)
            elif key in ("word_study_sec", "reading_duration_sec", "word_lookups",
                         "test_choice_questions", "test_choice_correct",
                         "test_fill_questions", "test_fill_correct"):
                if val and val > 0:
                    setattr(row, key, int(getattr(row, key) or 0) + int(val))
        row.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(row)
        return row

    def has_activity_today(self, user_id: int, today: date) -> bool:
        from app.services.english.models import UserDailyActivity

        return (
            self.db.query(UserDailyActivity.id)
            .filter(UserDailyActivity.user_id == user_id, UserDailyActivity.activity_date == today)
            .first()
            is not None
        )

    def get_summary(self, user_id: int, summary_date: date) -> UserDailySummary | None:
        from app.services.english.models import UserDailySummary

        return (
            self.db.query(UserDailySummary)
            .filter(
                UserDailySummary.user_id == user_id,
                UserDailySummary.summary_date == summary_date,
            )
            .first()
        )

    def create_summary(self, user_id: int, summary_date: date, table: list, overview: str, advice: str, source: str) -> UserDailySummary:
        from app.services.english.models import UserDailySummary

        row = UserDailySummary(
            user_id=user_id, summary_date=summary_date,
            table_json=table, ai_overview=overview, ai_advice=advice,
            source=source, generated_at=datetime.now(),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def sum_daily_stats(self, user_id: int, study_date: date) -> tuple[int, int, int]:
        """SUM user_daily_stats（跨 book）当日复习/新词/错词"""
        rows = (
            self.db.query(UserDailyStats)
            .filter(UserDailyStats.user_id == user_id, UserDailyStats.study_date == study_date)
            .all()
        )
        review = sum(r.review_count for r in rows)
        new = sum(r.new_count for r in rows)
        wrong = sum(r.wrong_count for r in rows)
        return review, new, wrong

    def count_wordbook_added_today(self, user_id: int, today: date) -> int:
        from sqlalchemy import func

        return (
            self.db.query(func.count(UserWordbook.id))
            .filter(
                UserWordbook.user_id == user_id,
                func.date(UserWordbook.created_at) == today,
            )
            .scalar()
            or 0
        )

    def count_notes_added_today(self, user_id: int, today: date) -> int:
        from sqlalchemy import func

        return (
            self.db.query(func.count(ReadingNote.id))
            .filter(
                ReadingNote.user_id == user_id,
                func.date(ReadingNote.created_at) == today,
            )
            .scalar()
            or 0
        )


    # ── 文章 ──────────────────────────────────────────────────────
    def list_articles(self, tenant_id: int, skip: int = 0, limit: int = 100) -> list[EnglishReadingArticle]:
        return (
            self.db.query(EnglishReadingArticle)
            .filter(EnglishReadingArticle.tenant_id == tenant_id)
            .order_by(EnglishReadingArticle.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_article(self, article_id: int) -> EnglishReadingArticle | None:
        return self.db.query(EnglishReadingArticle).filter(EnglishReadingArticle.id == article_id).first()

    def list_articles_in(self, ids: list[int]) -> list[EnglishReadingArticle]:
        if not ids:
            return []
        return self.db.query(EnglishReadingArticle).filter(EnglishReadingArticle.id.in_(ids)).all()

    def get_article_by_daily(self, tenant_id: int, publish_date: date, level: str, topic: str) -> EnglishReadingArticle | None:
        return (
            self.db.query(EnglishReadingArticle)
            .filter(
                EnglishReadingArticle.tenant_id == tenant_id,
                EnglishReadingArticle.publish_date == publish_date,
                EnglishReadingArticle.level == level,
                EnglishReadingArticle.topic == topic,
            )
            .first()
        )

    def get_latest_article_by_level(self, tenant_id: int, level: str) -> EnglishReadingArticle | None:
        return (
            self.db.query(EnglishReadingArticle)
            .filter(
                EnglishReadingArticle.tenant_id == tenant_id,
                EnglishReadingArticle.level == level,
                EnglishReadingArticle.publish_date.isnot(None),
            )
            .order_by(EnglishReadingArticle.publish_date.desc(), EnglishReadingArticle.id.desc())
            .first()
        )

    def create_article(
        self,
        tenant_id: int,
        title: str,
        content: str,
        content_cn: str,
        level: str,
        topic: str,
        publish_date: date,
        keywords: list,
    ) -> EnglishReadingArticle:
        item = EnglishReadingArticle(
            tenant_id=tenant_id, title=title, content=content, content_cn=content_cn,
            level=level, topic=topic, publish_date=publish_date,
            keywords=keywords, word_count=len(content.split()),
        )
        self.db.add(item)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            # 并发重复生成：复用已有
            existing = self.get_article_by_daily(tenant_id, publish_date, level, topic)
            if existing:
                return existing
            raise
        self.db.refresh(item)
        return item

    # ── 阅读笔记 ──────────────────────────────────────────────────
    def list_notes(self, user_id: int) -> list[ReadingNote]:
        return (
            self.db.query(ReadingNote)
            .filter(ReadingNote.user_id == user_id)
            .order_by(ReadingNote.updated_at.desc())
            .all()
        )

    def get_note(self, user_id: int, note_id: int) -> ReadingNote | None:
        return (
            self.db.query(ReadingNote)
            .filter(ReadingNote.id == note_id, ReadingNote.user_id == user_id)
            .first()
        )

    def get_note_by_article(self, user_id: int, article_id: int) -> ReadingNote | None:
        return (
            self.db.query(ReadingNote)
            .filter(ReadingNote.user_id == user_id, ReadingNote.article_id == article_id)
            .first()
        )

    def create_note(self, user_id: int, article_id: int, content: str) -> ReadingNote:
        note = ReadingNote(user_id=user_id, article_id=article_id, content=content)
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def update_note(self, note: ReadingNote, content: str) -> ReadingNote:
        note.content = content
        note.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(note)
        return note

    def delete_note(self, note: ReadingNote) -> None:
        self.db.delete(note)
        self.db.commit()

    def count_notes(self, user_id: int) -> int:
        return self.db.query(ReadingNote).filter(ReadingNote.user_id == user_id).count()

    # ── 收藏 ──────────────────────────────────────────────────────
    def list_collections(self, user_id: int, item_type: str | None = None) -> list[UserCollection]:
        query = self.db.query(UserCollection).filter(UserCollection.user_id == user_id)
        if item_type:
            query = query.filter(UserCollection.item_type == item_type)
        return query.order_by(UserCollection.created_at.desc()).all()

    def get_collection(self, user_id: int, item_type: str, item_id: int) -> UserCollection | None:
        return (
            self.db.query(UserCollection)
            .filter(
                UserCollection.user_id == user_id,
                UserCollection.item_type == item_type,
                UserCollection.item_id == item_id,
            )
            .first()
        )

    def add_collection(self, user_id: int, item_type: str, item_id: int) -> UserCollection:
        item = UserCollection(user_id=user_id, item_type=item_type, item_id=item_id)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def remove_collection(self, item: UserCollection) -> None:
        self.db.delete(item)
        self.db.commit()

    def count_collections(self, user_id: int) -> int:
        return self.db.query(UserCollection).filter(UserCollection.user_id == user_id).count()

    # ── 打卡 ──────────────────────────────────────────────────────
    def get_checkin(self, user_id: int, checkin_date: date) -> CheckinRecord | None:
        return (
            self.db.query(CheckinRecord)
            .filter(CheckinRecord.user_id == user_id, CheckinRecord.checkin_date == checkin_date)
            .first()
        )

    def create_checkin(self, user_id: int, checkin_date: date) -> CheckinRecord:
        item = CheckinRecord(user_id=user_id, checkin_date=checkin_date)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_checkin_dates(self, user_id: int) -> list[date]:
        rows = (
            self.db.query(CheckinRecord.checkin_date)
            .filter(CheckinRecord.user_id == user_id)
            .order_by(CheckinRecord.checkin_date.desc())
            .all()
        )
        return [r[0] for r in rows]

    def count_checkins(self, user_id: int) -> int:
        return self.db.query(CheckinRecord).filter(CheckinRecord.user_id == user_id).count()

    # ── 每日一读 ──────────────────────────────────────────────────
    def get_daily_reading(self, user_id: int, reading_date: date) -> UserDailyReading | None:
        return (
            self.db.query(UserDailyReading)
            .filter(UserDailyReading.user_id == user_id, UserDailyReading.reading_date == reading_date)
            .first()
        )

    def create_daily_reading(self, user_id: int, reading_date: date, article_id: int, level: str) -> UserDailyReading:
        item = UserDailyReading(
            user_id=user_id, reading_date=reading_date, article_id=article_id,
            level=level, status="pending",
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_daily_reading(self, record: UserDailyReading, **fields) -> UserDailyReading:
        for k, v in fields.items():
            setattr(record, k, v)
        record.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_daily_reading(self, user_id: int) -> list[UserDailyReading]:
        return (
            self.db.query(UserDailyReading)
            .filter(UserDailyReading.user_id == user_id)
            .order_by(UserDailyReading.reading_date.desc())
            .all()
        )

    def list_daily_reading_recent(self, user_id: int, limit: int = 10) -> list[UserDailyReading]:
        """最近 N 条记录（按日期倒序，用于专项测试生词并集与难度适配）"""
        return (
            self.db.query(UserDailyReading)
            .filter(UserDailyReading.user_id == user_id)
            .order_by(UserDailyReading.reading_date.desc())
            .limit(limit)
            .all()
        )

    # ── 阅读生词黑名单 ────────────────────────────────────────────
    def get_blacklist(self, user_id: int, word_id: int) -> ReadingWordBlacklist | None:
        return (
            self.db.query(ReadingWordBlacklist)
            .filter(ReadingWordBlacklist.user_id == user_id, ReadingWordBlacklist.word_id == word_id)
            .first()
        )

    def add_blacklist(self, user_id: int, word_id: int) -> ReadingWordBlacklist:
        item = ReadingWordBlacklist(user_id=user_id, word_id=word_id)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def remove_blacklist(self, item: ReadingWordBlacklist) -> None:
        self.db.delete(item)
        self.db.commit()

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

    def has_point_log(self, user_id: int, reason: str) -> bool:
        """该 reason 是否历史任何一天已发放过（里程碑跨天幂等）"""
        return (
            self.db.query(RewardPointLog)
            .filter(RewardPointLog.user_id == user_id, RewardPointLog.reason == reason)
            .first()
            is not None
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
