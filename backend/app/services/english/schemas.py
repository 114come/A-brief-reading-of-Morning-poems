"""英语学习 Pydantic Schemas"""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ─── 认证 ────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ProfileUpdate(BaseModel):
    nickname: str | None = Field(default=None, max_length=50)
    avatar: str | None = Field(default=None, max_length=255)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    nickname: str | None = None
    avatar: str | None = None


# ─── 词书 / 单词 ─────────────────────────────────────────────────────


class WordBookOut(BaseModel):
    id: int
    code: str
    name: str
    sort_order: int
    word_count: int = 0


class WordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    word: str
    phonetic: str | None = None
    definition: str
    pos: str | None = None
    example: str | None = None
    example2: str | None = None
    phrase: str | None = None
    level: str | None = None
    tags: str | None = None
    in_wordbook: bool = False
    is_favorite: bool = False
    tag: str | None = None  # 用户自定义分类（核心/常用/拓展）


class SetTagIn(BaseModel):
    book_id: int
    word_id: int
    tag: str | None = Field(default=None, max_length=20)


class CategoryOut(BaseModel):
    tag: str
    name: str
    count: int


class WordbookItemOut(BaseModel):
    id: int
    book_id: int
    created_at: datetime
    word: "WordOut"


class WordbookAddIn(BaseModel):
    word_id: int
    book_id: int


# ─── 单词测试 ────────────────────────────────────────────────────────


class TestQuestionOut(BaseModel):
    word_id: int
    word: str
    phonetic: str | None = None
    definition: str
    pos: str | None = None
    type: str  # a/b/c/d/e
    show: str = ""  # word/definition/audio
    options: list[str] = []  # 单选选项
    answer: str = ""  # 标准答案
    mask: str = ""  # 单词填空遮蔽
    example_en: str | None = None  # 例句填空原文
    example_cn: str | None = None  # 例句填空中文


class TestQuestionsOut(BaseModel):
    questions: list[TestQuestionOut]
    mode: str
    module: str
    question_type: str
    total: int


# ─── SRS 记忆 / 会话 ────────────────────────────────────────────────


class MemoryRow(BaseModel):
    word_id: int
    status: int = 0
    next_review_date: date | None = None
    interval: int = 0
    wrong_count: int = 0


class SrsSessionState(BaseModel):
    date: str | None = None
    phase: str = "new"  # review / new / done
    review_queue: list[int] = []
    new_queue: list[int] = []
    review_done: int = 0
    new_done: int = 0
    wrong_total: int = 0
    round: int = 0  # 当日第几轮（继续学习轮次）


class SrsSettingsOut(BaseModel):
    book_id: int
    target: str
    daily_new_words: int
    pronunciation: str
    autoplay: bool
    onboarding_done: bool


class OnboardingIn(BaseModel):
    target: str
    book_id: int
    daily_new_words: int = Field(default=20, ge=1, le=100)
    pronunciation: str = Field(default="us", pattern="^(us|uk)$")
    autoplay: bool = False


class SrsStateIn(BaseModel):
    book_id: int
    memory: list[MemoryRow] = []
    session: SrsSessionState | None = None


class SrsStateOut(BaseModel):
    settings: SrsSettingsOut | None = None
    memory: list[MemoryRow] = []
    session: SrsSessionState | None = None


class CompleteIn(BaseModel):
    book_id: int
    study_date: date
    review_count: int = 0
    new_count: int = 0
    wrong_count: int = 0


class CompleteOut(BaseModel):
    checkin: dict
    summary: dict


class SyncIn(BaseModel):
    book_id: int
    memory: list[MemoryRow] = []
    wordbook: list[int] = []


class SyncOut(BaseModel):
    memory_merged: int
    wordbook_merged: int


class BookStats(BaseModel):
    book_id: int
    total_words: int
    unlearned: int
    learning: int
    mastered: int
    wordbook_count: int


class SrsStatsOut(BaseModel):
    total_studied: int
    wordbook_count: int
    mastered_count: int
    streak_days: int
    total_days: int
    today_done: bool
    per_book: list[BookStats]


class ResetIn(BaseModel):
    book_id: int


# ─── 每日活动 / AI 总结 ──────────────────────────────────────────────


class ActivityIn(BaseModel):
    activity_date: date | None = None
    word_study_sec: int = 0
    reading_article_id: int | None = None
    reading_duration_sec: int = 0
    word_lookups: int = 0
    test_choice_questions: int = 0
    test_choice_correct: int = 0
    test_fill_questions: int = 0
    test_fill_correct: int = 0


class TodayActivityOut(BaseModel):
    has_activity: bool = False


class SummaryItem(BaseModel):
    label: str
    value: str


class SummaryCategory(BaseModel):
    category: str
    items: list[SummaryItem]


class DailySummaryOut(BaseModel):
    date: date
    table: list[SummaryCategory] | None = None
    ai_overview: str | None = None
    ai_advice: str | None = None
    source: str | None = None
    generated_at: datetime | None = None


# ─── 阅读 ────────────────────────────────────────────────────────────


class ArticleListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    level: str | None = None
    word_count: int
    is_favorite: bool = False
    note_id: int | None = None
    note_updated_at: datetime | None = None


class ArticleOut(ArticleListItemOut):
    content: str
    content_cn: str | None = None
    topic: str | None = None
    publish_date: date | None = None
    keywords: list | None = None


class NoteCreate(BaseModel):
    article_id: int
    content: str = Field(min_length=1)


class NoteUpdate(BaseModel):
    content: str = Field(min_length=1)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    article_id: int
    article_title: str | None = None
    content: str
    created_at: datetime
    updated_at: datetime


# ─── 每日一读 ─────────────────────────────────────────────────────────


class ReadingKeyword(BaseModel):
    word: str
    definition: str
    example: str = ""


class ReadingQuizQuestion(TestQuestionOut):
    """阅读小测题目（结构复用 TestQuestionOut，word_id 可为 0=仅关键词）"""
    pass


class DailyReadingRecordOut(BaseModel):
    status: str  # pending/done
    level: str
    level_label: str = ""
    correct_count: int = 0
    total_questions: int = 0
    accuracy: int = 0  # 百分比 0-100
    new_word_count: int = 0


class DailyReadingTodayOut(BaseModel):
    record: DailyReadingRecordOut
    article: "ArticleOut"
    level_mode: str = "auto"  # auto/manual
    manual_level: str | None = None
    topics: list[str] = []  # 题材标签（code）
    estimated_min: int = 0
    word_task_done: bool = False  # 今日背单词打卡状态


class ReadingLevelIn(BaseModel):
    mode: str = Field(pattern="^(auto|manual)$")
    level: str | None = Field(default=None, pattern="^(basic|cet4|advanced)$")


class ReadingQuizSubmitIn(BaseModel):
    article_id: int
    answers: list[dict] = []  # [{word, type, correct}]


class ReadingWordCollectIn(BaseModel):
    article_id: int
    word: str
    source: str = "lookup"  # lookup/favorite/wrong
    definition: str | None = None  # LLM 关键词释义（词典外生词建词用）


class ReadingBlacklistIn(BaseModel):
    word: str
    blacklisted: bool = True


class ReadingCompleteIn(BaseModel):
    article_id: int
    duration_sec: int = 0


class ReadingArchiveItemOut(BaseModel):
    id: int
    reading_date: date
    article_id: int
    title: str
    level: str
    level_label: str = ""
    topic: str | None = None
    topic_label: str = ""
    status: str
    correct_count: int = 0
    total_questions: int = 0
    accuracy: int = 0
    new_word_count: int = 0
    is_favorite: bool = False
    note_id: int | None = None


# ─── 收藏 ────────────────────────────────────────────────────────────


class CollectionCreate(BaseModel):
    item_type: str = Field(pattern="^(word|reading)$")
    item_id: int


class CollectionItemOut(BaseModel):
    id: int
    item_type: str
    item_id: int
    created_at: datetime
    # 冗余字段，便于前端直接展示
    title: str | None = None
    subtitle: str | None = None


# ─── 打卡 ────────────────────────────────────────────────────────────


class CheckinOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    checkin_date: date
    streak_days: int = 0
    total_days: int = 0


class CheckinStatsOut(BaseModel):
    streak_days: int
    total_days: int
    today_done: bool
    recent_dates: list[date]


# ─── 学习统计 ─────────────────────────────────────────────────────────


class StudyStatsOut(BaseModel):
    total_words: int
    wordbook_count: int
    mastered_count: int
    favorite_count: int
    note_count: int
    checkin_total: int
    checkin_streak: int
    today_checkin: bool


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
