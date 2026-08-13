"""英语学习数据模型

内容表（单词/文章/词书）带 tenant_id 列，与平台其他业务表约定一致；
用户私有表（记忆/设置/日会话/生词本/收藏/笔记/打卡）只带 user_id，
因为所有英语用户都归属于专用的 english 租户。
"""
from datetime import datetime, date

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EnglishWordBook(Base):
    """词书（学习词库）"""

    __tablename__ = "word_books"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_word_books_tenant_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)  # primary_school/high_school/cet4/cet6/kaoyan/daily
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class EnglishWord(Base):
    __tablename__ = "english_words"
    __table_args__ = (
        UniqueConstraint("tenant_id", "book_id", "word", name="uq_english_words_tenant_book_word"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("word_books.id"), nullable=False, index=True
    )
    word: Mapped[str] = mapped_column(String(100), nullable=False)
    phonetic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    pos: Mapped[str | None] = mapped_column(String(100), nullable=True)
    example: Mapped[str | None] = mapped_column(Text, nullable=True)
    example2: Mapped[str | None] = mapped_column(Text, nullable=True)
    example_cn: Mapped[str | None] = mapped_column(Text, nullable=True)
    example2_cn: Mapped[str | None] = mapped_column(Text, nullable=True)
    phrase: Mapped[str | None] = mapped_column(String(200), nullable=True)
    level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class EnglishReadingArticle(Base):
    """阅读文章（每日一读：LLM 按 (date, level, topic) 生成缓存；历史文章 publish_date 为空）"""

    __tablename__ = "english_reading_articles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "publish_date", "level", "topic", name="uq_english_articles_tenant_date_level_topic"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text().with_variant(MEDIUMTEXT, "mysql"), nullable=False)
    content_cn: Mapped[str | None] = mapped_column(Text().with_variant(MEDIUMTEXT, "mysql"), nullable=True)
    level: Mapped[str | None] = mapped_column(String(20), nullable=True)  # basic/cet4/advanced
    topic: Mapped[str | None] = mapped_column(String(20), nullable=True)  # fun_science/life_story/film/motto/exam
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{word, definition, example}]
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class UserWordMemory(Base):
    """用户单词记忆表（SRS 状态）

    status: 0=未学习, 1=学习中(有复习计划), 2=已掌握
    current_interval: 当前等待复习天数（1/2/4/7/15，0=未初始化）
    wrong_count: 当日答错次数（跨天由客户端引擎重置）
    """

    __tablename__ = "user_word_memory"
    __table_args__ = (
        UniqueConstraint("user_id", "word_id", "book_id", name="uq_user_word_memory_uid_word_book"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("english_words.id"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("word_books.id"), nullable=False, index=True
    )
    status: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_interval: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class UserWordSettings(Base):
    """用户背诵参数设置（词书引导时初始化）"""

    __tablename__ = "user_word_settings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("word_books.id"), nullable=False
    )
    target: Mapped[str] = mapped_column(String(40), default="cet4", nullable=False)
    daily_new_words: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    pronunciation: Mapped[str] = mapped_column(String(10), default="us", nullable=False)
    autoplay: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    onboarding_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 每日一读难度设置
    reading_level_mode: Mapped[str] = mapped_column(String(10), default="auto", nullable=False)  # auto/manual
    reading_manual_level: Mapped[str | None] = mapped_column(String(20), nullable=True)  # basic/cet4/advanced
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class UserDailySession(Base):
    """每日学习会话（客户端 SRS 引擎状态，跨刷新续期）"""

    __tablename__ = "user_daily_session"
    __table_args__ = (
        UniqueConstraint("user_id", "book_id", "session_date", name="uq_user_daily_session_uid_book_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("word_books.id"), nullable=False, index=True
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    state: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class UserDailyStats(Base):
    """每日学习统计数据"""

    __tablename__ = "user_daily_stats"
    __table_args__ = (
        UniqueConstraint("user_id", "book_id", "study_date", name="uq_user_daily_stats_uid_book_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("word_books.id"), nullable=False, index=True
    )
    study_date: Mapped[date] = mapped_column(Date, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )


class UserWordbook(Base):
    """用户生词本（纯列表，无复习状态；认识→移除，不认识→保留）"""

    __tablename__ = "user_wordbook"
    __table_args__ = (
        UniqueConstraint("user_id", "word_id", "book_id", name="uq_user_wordbook_uid_word_book"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("english_words.id"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("word_books.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class UserWordTag(Base):
    """用户对单词的简单分类（核心/常用/拓展；每词一个标签，可清空）"""

    __tablename__ = "user_word_tags"
    __table_args__ = (
        UniqueConstraint("user_id", "word_id", "book_id", name="uq_user_word_tags_uid_word_book"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("english_words.id"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("word_books.id"), nullable=False, index=True
    )
    tag: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class UserCollection(Base):
    """统一收藏（word/reading 两种类型共用）"""

    __tablename__ = "user_collections"
    __table_args__ = (
        UniqueConstraint("user_id", "item_type", "item_id", name="uq_user_collections_user_type_item"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)  # word/reading
    item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )


class ReadingNote(Base):
    __tablename__ = "reading_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("english_reading_articles.id"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class CheckinRecord(Base):
    """每日打卡记录"""

    __tablename__ = "checkin_records"
    __table_args__ = (
        UniqueConstraint("user_id", "checkin_date", name="uq_checkin_records_user_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    checkin_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )


class UserDailyActivity(Base):
    """用户每日学习活动埋点（阅读/划词/测试，单词数据从 user_daily_stats 推导）"""

    __tablename__ = "user_daily_activity"
    __table_args__ = (
        UniqueConstraint("user_id", "activity_date", name="uq_user_daily_activity_uid_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    word_study_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reading_article_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    reading_duration_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    word_lookups: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    test_choice_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    test_choice_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    test_fill_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    test_fill_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class UserDailyReading(Base):
    """每日一读任务记录（每人每天一条：文章/难度/答题/新增生词/打卡状态）"""

    __tablename__ = "user_daily_reading"
    __table_args__ = (
        UniqueConstraint("user_id", "reading_date", name="uq_user_daily_reading_uid_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    reading_date: Mapped[date] = mapped_column(Date, nullable=False)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("english_reading_articles.id"), nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # basic/cet4/advanced
    status: Mapped[str] = mapped_column(String(10), default="pending", nullable=False)  # pending/done
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wrong_word_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    new_word_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class ReadingWordBlacklist(Base):
    """用户标记的熟词黑名单：阅读中遇到不再收录为生词"""

    __tablename__ = "reading_word_blacklist"
    __table_args__ = (
        UniqueConstraint("user_id", "word_id", name="uq_reading_blacklist_uid_word"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("english_words.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )


class UserDailySummary(Base):
    """AI 每日学习总结缓存（每日 1 条，同时承担每日 1 次生成限制）"""

    __tablename__ = "user_daily_summary"
    __table_args__ = (
        UniqueConstraint("user_id", "summary_date", name="uq_user_daily_summary_uid_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    summary_date: Mapped[date] = mapped_column(Date, nullable=False)
    table_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    ai_overview: Mapped[str] = mapped_column(Text, nullable=False)
    ai_advice: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="llm", nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


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
