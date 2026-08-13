"""英语学习 API 路由

认证说明：
- 注册/刷新为公开接口；
- /srs/books、/words、/reading 等内容接口游客可读（OptionalUserDep）；
- 其余接口均需 Bearer Token（UserDep）；
- 登录复用 /api/v1/tenant/auth/login_with_tenant?tenant_code=english
- 统一响应包裹：{code, data, message}
"""
from typing import Any

from fastapi import APIRouter

from app.core.dependencies import DbDep, OptionalUserDep, UserDep
from app.core.response import UnifiedResponse
from app.services.english.schemas import (
    ActivityIn,
    ArticleListItemOut,
    ArticleOut,
    CategoryOut,
    CheckinStatsOut,
    CollectOut,
    CollectionCreate,
    CollectionItemOut,
    CompleteIn,
    CompleteOut,
    DailyReadingRecordOut,
    DailyReadingTodayOut,
    DailySummaryOut,
    EquipIn,
    NoteCreate,
    NoteOut,
    NoteUpdate,
    OnboardingIn,
    ProfileOut,
    ProfileUpdate,
    RedeemIn,
    ReadingArchiveItemOut,
    ReadingBlacklistIn,
    ReadingCompleteIn,
    ReadingLevelIn,
    ReadingQuizSubmitIn,
    ReadingWordCollectIn,
    RefreshRequest,

    RegisterRequest,
    ResetIn,
    RewardOverviewOut,
    SetTagIn,
    ShopItemOut,
    SrsSettingsOut,
    SrsStateIn,
    SrsStateOut,
    StudyStatsOut,
    SyncIn,
    SyncOut,
    TestQuestionsOut,
    TodayActivityOut,
    TokenPair,
    WordBookOut,
    WordOut,
    WordbookAddIn,
    WordbookItemOut,
)
from app.services.english.service import EnglishService
from app.services.english.srs_service import SrsService
from app.services.english.test_service import TestService
from app.services.english.daily_summary_service import DailySummaryService
from app.services.english.daily_reading_service import DailyReadingService
from app.services.english.reward_service import RewardService

router = APIRouter(prefix="/english", tags=["英语学习"])


def _service(db: DbDep) -> EnglishService:
    return EnglishService(db)


def _srs(db: DbDep) -> SrsService:
    return SrsService(db)


def _reading(db: DbDep) -> DailyReadingService:
    return DailyReadingService(db)


# ── 认证 ─────────────────────────────────────────────────────────────


@router.post("/auth/register", response_model=UnifiedResponse[Any])
def register(data: RegisterRequest, db: DbDep) -> UnifiedResponse[Any]:
    service = _service(db)
    user, access, refresh = service.register(data.username, data.email, data.password)
    return UnifiedResponse.success(
        data={
            "user": ProfileOut.model_validate(user).model_dump(),
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
        },
        message="注册成功",
    )


@router.post("/auth/refresh", response_model=UnifiedResponse[TokenPair])
def refresh(data: RefreshRequest, db: DbDep) -> UnifiedResponse[TokenPair]:
    access, refresh_token = _service(db).refresh(data.refresh_token)
    return UnifiedResponse.success(data=TokenPair(access_token=access, refresh_token=refresh_token))


@router.get("/auth/profile", response_model=UnifiedResponse[ProfileOut])
def get_profile(user: UserDep, db: DbDep) -> UnifiedResponse[ProfileOut]:
    return UnifiedResponse.success(data=_service(db).get_profile(user))


@router.put("/auth/profile", response_model=UnifiedResponse[ProfileOut])
def update_profile(data: ProfileUpdate, user: UserDep, db: DbDep) -> UnifiedResponse[ProfileOut]:
    return UnifiedResponse.success(data=_service(db).update_profile(user, data.nickname, data.avatar))


# ── 单词 / 词书 ──────────────────────────────────────────────────────


@router.get("/words", response_model=UnifiedResponse[list[WordOut]])
def list_words(
    user: OptionalUserDep,
    db: DbDep,
    book_id: int | None = None,
    level: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> UnifiedResponse[list[WordOut]]:
    return UnifiedResponse.success(data=_service(db).list_words(user, book_id, level, skip, limit))


@router.get("/words/lookup", response_model=UnifiedResponse[dict])
def word_lookup(word: str, user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    return UnifiedResponse.success(data=_service(db).lookup_word(user, word))


# ── SRS 背单词 ───────────────────────────────────────────────────────


@router.get("/srs/books", response_model=UnifiedResponse[list[WordBookOut]])
def srs_books(user: OptionalUserDep, db: DbDep) -> UnifiedResponse[list[WordBookOut]]:
    if user:
        tenant_id = user.tenant_id
    else:
        from app.services.english.service import get_english_tenant

        tenant_id = get_english_tenant(db).id  # 游客回退到 english 租户
    return UnifiedResponse.success(data=_srs(db).get_books(tenant_id))


@router.get("/srs/state", response_model=UnifiedResponse[SrsStateOut])
def srs_state(user: UserDep, db: DbDep, book_id: int | None = None) -> UnifiedResponse[SrsStateOut]:
    return UnifiedResponse.success(data=_srs(db).get_state(user, book_id))


@router.post("/srs/onboarding", response_model=UnifiedResponse[SrsSettingsOut])
def srs_onboarding(data: OnboardingIn, user: UserDep, db: DbDep) -> UnifiedResponse[SrsSettingsOut]:
    result = _srs(db).save_onboarding(
        user, data.target, data.book_id, data.daily_new_words, data.pronunciation, data.autoplay
    )
    return UnifiedResponse.success(data=result, message="设置已保存")


@router.post("/srs/state", response_model=UnifiedResponse[dict])
def srs_save_state(data: SrsStateIn, user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    return UnifiedResponse.success(data=_srs(db).save_state(user, data.book_id, data.memory, data.session))


@router.post("/srs/complete", response_model=UnifiedResponse[CompleteOut])
def srs_complete(data: CompleteIn, user: UserDep, db: DbDep) -> UnifiedResponse[CompleteOut]:
    result = _srs(db).complete_day(
        user, data.book_id, data.study_date, data.review_count, data.new_count, data.wrong_count
    )
    return UnifiedResponse.success(data=result, message="打卡成功")


@router.post("/srs/sync", response_model=UnifiedResponse[SyncOut])
def srs_sync(data: SyncIn, user: UserDep, db: DbDep) -> UnifiedResponse[SyncOut]:
    return UnifiedResponse.success(data=_srs(db).sync_guest(user, data.book_id, data.memory, data.wordbook))


@router.post("/srs/reset", response_model=UnifiedResponse[dict])
def srs_reset(data: ResetIn, user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    return UnifiedResponse.success(data=_srs(db).reset_book(user, data.book_id), message="已清除学习数据")


@router.get("/srs/stats", response_model=UnifiedResponse[dict])
def srs_stats(user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    return UnifiedResponse.success(data=_srs(db).srs_stats(user))


# ── 单词分类（查看词库 + 按类型背诵） ───────────────────────────────


@router.put("/srs/tag", response_model=UnifiedResponse[dict])
def srs_set_tag(data: SetTagIn, user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    return UnifiedResponse.success(data=_service(db).set_word_tag(user, data.book_id, data.word_id, data.tag))


@router.get("/srs/categories", response_model=UnifiedResponse[list[CategoryOut]])
def srs_categories(user: UserDep, db: DbDep, book_id: int) -> UnifiedResponse[list[CategoryOut]]:
    return UnifiedResponse.success(data=_service(db).get_categories(user, book_id))


# ── 单词测试 ─────────────────────────────────────────────────────────


@router.get("/test/questions", response_model=UnifiedResponse[TestQuestionsOut])
def test_questions(
    user: UserDep,
    db: DbDep,
    book_id: int,
    module: str = "choice",
    question_type: str = "a",
    mode: str = "book",
    count: int = 20,
) -> UnifiedResponse[TestQuestionsOut]:
    result = TestService(db).generate(user, book_id, module, question_type, mode, count)
    return UnifiedResponse.success(data=TestQuestionsOut(**result))


# ── 每日活动埋点 / AI 学习总结 ───────────────────────────────────────


@router.post("/activity", response_model=UnifiedResponse[dict])
def report_activity(data: ActivityIn, user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    from datetime import date, timedelta

    today = date.today()
    d = data.activity_date or today
    if abs((d - today).days) > 1:
        d = today  # 钳制异常时钟
    svc = DailySummaryService(db)
    svc.repo.upsert_activity(user.id, d, **data.model_dump(exclude={"activity_date"}))
    return UnifiedResponse.success(data={"saved": True})


@router.get("/activity/today", response_model=UnifiedResponse[TodayActivityOut])
def activity_today(user: UserDep, db: DbDep) -> UnifiedResponse[TodayActivityOut]:
    return UnifiedResponse.success(data=TodayActivityOut(has_activity=DailySummaryService(db).has_activity_today(user)))


@router.get("/daily-summary", response_model=UnifiedResponse[DailySummaryOut])
def daily_summary(user: UserDep, db: DbDep) -> UnifiedResponse[DailySummaryOut]:
    return UnifiedResponse.success(data=DailySummaryService(db).get_summary(user))


@router.post("/daily-summary/generate", response_model=UnifiedResponse[DailySummaryOut])
async def daily_summary_generate(user: UserDep, db: DbDep) -> UnifiedResponse[DailySummaryOut]:
    result = await DailySummaryService(db).generate(user)
    return UnifiedResponse.success(data=result, message="日报已生成")


# ── 生词本（纯列表） ─────────────────────────────────────────────────


@router.get("/wordbook", response_model=UnifiedResponse[list[WordbookItemOut]])
def list_wordbook(
    user: UserDep, db: DbDep, book_id: int | None = None
) -> UnifiedResponse[list[WordbookItemOut]]:
    return UnifiedResponse.success(data=_srs(db).list_wordbook(user, book_id))


@router.post("/wordbook", response_model=UnifiedResponse[WordbookItemOut])
def add_wordbook(data: WordbookAddIn, user: UserDep, db: DbDep) -> UnifiedResponse[WordbookItemOut]:
    return UnifiedResponse.success(data=_srs(db).add_wordbook(user, data.word_id, data.book_id), message="已加入生词本")


@router.delete("/wordbook", response_model=UnifiedResponse[dict])
def clear_wordbook(user: UserDep, db: DbDep, book_id: int) -> UnifiedResponse[dict]:
    _srs(db).clear_wordbook(user, book_id)
    return UnifiedResponse.success(data={"deleted": True}, message="生词本已清空")


@router.delete("/wordbook/{wb_id}", response_model=UnifiedResponse[dict])
def remove_wordbook(wb_id: int, user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    _srs(db).remove_wordbook(user, wb_id)
    return UnifiedResponse.success(data={"deleted": True}, message="已从生词本移除")


# ── 每日一读 ─────────────────────────────────────────────────────────


@router.get("/daily-reading/today", response_model=UnifiedResponse[DailyReadingTodayOut])
async def daily_reading_today(user: UserDep, db: DbDep) -> UnifiedResponse[DailyReadingTodayOut]:
    return UnifiedResponse.success(data=await _reading(db).get_today(user))


@router.put("/daily-reading/level", response_model=UnifiedResponse[dict])
def daily_reading_level(data: ReadingLevelIn, user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    return UnifiedResponse.success(data=_reading(db).set_level_mode(user, data.mode, data.level))


@router.get("/daily-reading/quiz", response_model=UnifiedResponse[dict])
def daily_reading_quiz(user: UserDep, db: DbDep, article_id: int) -> UnifiedResponse[dict]:
    return UnifiedResponse.success(data=_reading(db).get_quiz(user, article_id))


@router.post("/daily-reading/quiz", response_model=UnifiedResponse[dict])
def daily_reading_quiz_submit(data: ReadingQuizSubmitIn, user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    return UnifiedResponse.success(data=_reading(db).submit_quiz(user, data.article_id, data.answers))


@router.post("/daily-reading/words", response_model=UnifiedResponse[dict])
def daily_reading_collect(data: ReadingWordCollectIn, user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    return UnifiedResponse.success(data=_reading(db).collect_word(user, data.article_id, data.word, data.source, data.definition))


@router.put("/daily-reading/words/blacklist", response_model=UnifiedResponse[dict])
def daily_reading_blacklist(data: ReadingBlacklistIn, user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    return UnifiedResponse.success(data=_reading(db).set_blacklist(user, data.word, data.blacklisted))


@router.post("/daily-reading/complete", response_model=UnifiedResponse[dict])
def daily_reading_complete(data: ReadingCompleteIn, user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    return UnifiedResponse.success(data=_reading(db).complete(user, data.article_id, data.duration_sec), message="今日一读打卡成功")


@router.get("/daily-reading/archive", response_model=UnifiedResponse[list[ReadingArchiveItemOut]])
def daily_reading_archive(user: UserDep, db: DbDep) -> UnifiedResponse[list[ReadingArchiveItemOut]]:
    return UnifiedResponse.success(data=_reading(db).archive(user))


# ── 阅读 ─────────────────────────────────────────────────────────────


@router.get("/reading/articles", response_model=UnifiedResponse[list[ArticleListItemOut]])
def list_articles(
    user: OptionalUserDep, db: DbDep, skip: int = 0, limit: int = 100
) -> UnifiedResponse[list[ArticleListItemOut]]:
    return UnifiedResponse.success(data=_service(db).list_articles(user, skip, limit))


@router.get("/reading/articles/{article_id}", response_model=UnifiedResponse[ArticleOut])
def get_article(article_id: int, user: OptionalUserDep, db: DbDep) -> UnifiedResponse[ArticleOut]:
    return UnifiedResponse.success(data=_service(db).get_article(user, article_id))


@router.get("/reading/notes", response_model=UnifiedResponse[list[NoteOut]])
def list_notes(user: UserDep, db: DbDep) -> UnifiedResponse[list[NoteOut]]:
    return UnifiedResponse.success(data=_service(db).list_notes(user))


@router.post("/reading/notes", response_model=UnifiedResponse[NoteOut])
def create_note(data: NoteCreate, user: UserDep, db: DbDep) -> UnifiedResponse[NoteOut]:
    return UnifiedResponse.success(data=_service(db).create_note(user, data.article_id, data.content), message="笔记已保存")


@router.put("/reading/notes/{note_id}", response_model=UnifiedResponse[NoteOut])
def update_note(note_id: int, data: NoteUpdate, user: UserDep, db: DbDep) -> UnifiedResponse[NoteOut]:
    return UnifiedResponse.success(data=_service(db).update_note(user, note_id, data.content), message="笔记已更新")


@router.delete("/reading/notes/{note_id}", response_model=UnifiedResponse[dict])
def delete_note(note_id: int, user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    _service(db).delete_note(user, note_id)
    return UnifiedResponse.success(data={"deleted": True}, message="笔记已删除")


# ── 收藏 ─────────────────────────────────────────────────────────────


@router.get("/collections", response_model=UnifiedResponse[list[CollectionItemOut]])
def list_collections(
    user: UserDep, db: DbDep, item_type: str | None = None
) -> UnifiedResponse[list[CollectionItemOut]]:
    return UnifiedResponse.success(data=_service(db).list_collections(user, item_type))


@router.post("/collections", response_model=UnifiedResponse[CollectionItemOut])
def add_collection(data: CollectionCreate, user: UserDep, db: DbDep) -> UnifiedResponse[CollectionItemOut]:
    return UnifiedResponse.success(data=_service(db).add_collection(user, data.item_type, data.item_id), message="已收藏")


@router.delete("/collections/{collection_id}", response_model=UnifiedResponse[dict])
def remove_collection(collection_id: int, user: UserDep, db: DbDep) -> UnifiedResponse[dict]:
    _service(db).remove_collection(user, collection_id)
    return UnifiedResponse.success(data={"deleted": True}, message="已取消收藏")


# ── 打卡 / 统计 ──────────────────────────────────────────────────────


@router.post("/checkin", response_model=UnifiedResponse[CheckinStatsOut])
def checkin(user: UserDep, db: DbDep) -> UnifiedResponse[CheckinStatsOut]:
    return UnifiedResponse.success(data=_service(db).checkin(user), message="打卡成功")


@router.get("/checkin/stats", response_model=UnifiedResponse[CheckinStatsOut])
def checkin_stats(user: UserDep, db: DbDep) -> UnifiedResponse[CheckinStatsOut]:
    return UnifiedResponse.success(data=_service(db).checkin_stats(user))


@router.get("/study/stats", response_model=UnifiedResponse[StudyStatsOut])
def study_stats(user: UserDep, db: DbDep) -> UnifiedResponse[StudyStatsOut]:
    return UnifiedResponse.success(data=_service(db).study_stats(user))


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
