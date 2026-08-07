"""英语学习业务服务层"""
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from app.core.security import create_access_token, decode_token
from app.services.english.models import (
    EnglishReadingArticle,
    EnglishWord,
    ReadingNote,
    UserCollection,
)
from app.services.english.repository import EnglishRepository
from app.services.english.schemas import (
    ArticleListItemOut,
    ArticleOut,
    CheckinStatsOut,
    CollectionItemOut,
    NoteOut,
    ProfileOut,
    StudyStatsOut,
    WordOut,
)
from app.services.tenant.models import Tenant, User
from app.services.tenant.repository import TenantRepository, UserRepository
from app.services.tenant.service import TenantService

TENANT_CODE = "english"

# 单词简单分类选项（每词一个标签）
WORD_CATEGORIES = [
    {"tag": "core", "name": "核心"},
    {"tag": "common", "name": "常用"},
    {"tag": "advanced", "name": "拓展"},
]


def get_english_tenant(db: Session) -> Tenant:
    """获取（必要时创建）英语学习专用租户"""
    tenant = TenantRepository(db).get_by_code(TENANT_CODE)
    if tenant:
        return tenant
    tenant = TenantRepository(db).create(
        name="英语学习",
        code=TENANT_CODE,
        db_name="tenant_english",
        db_host="localhost",
        db_port=3306,
        db_user="root",
        db_password_encrypted="",
    )
    TenantService(db).create_user(
        username="english_admin",
        email="admin@english.local",
        password=settings.SECRET_KEY or "english-admin",
        tenant_id=tenant.id,
        is_superuser=True,
    )
    return tenant


class EnglishService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EnglishRepository(db)

    # ── 认证 ──────────────────────────────────────────────────────
    def register(self, username: str, email: str, password: str) -> tuple[User, str, str]:
        tenant = get_english_tenant(self.db)
        user_repo = UserRepository(self.db)
        if user_repo.get_by_username(username, tenant.id):
            raise ValidationException("用户名已被注册")
        user = TenantService(self.db).create_user(
            username=username,
            email=email,
            password=password,
            tenant_id=tenant.id,
        )
        return user, *self._issue_tokens(user, tenant)

    def refresh(self, refresh_token: str) -> tuple[str, str]:
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise UnauthorizedException("刷新令牌无效或已过期")
        if payload.get("type") != "refresh":
            raise UnauthorizedException("不是有效的刷新令牌")
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        if not user_id or not tenant_id:
            raise UnauthorizedException("令牌信息不完整")
        user = UserRepository(self.db).get_by_id(int(user_id))
        tenant = TenantRepository(self.db).get_by_id(int(tenant_id))
        if not user or not tenant or user.tenant_id != tenant.id:
            raise UnauthorizedException("用户或租户不存在")
        return self._issue_tokens(user, tenant)

    def get_profile(self, user: User) -> ProfileOut:
        return ProfileOut.model_validate(user)

    def update_profile(self, user: User, nickname: str | None, avatar: str | None) -> ProfileOut:
        if nickname is not None:
            user.nickname = nickname
        if avatar is not None:
            user.avatar = avatar
        self.db.commit()
        self.db.refresh(user)
        return ProfileOut.model_validate(user)

    @staticmethod
    def _issue_tokens(user: User, tenant: Tenant) -> tuple[str, str]:
        access_token = create_access_token(
            data={"sub": str(user.id), "tenant_id": str(tenant.id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = create_access_token(
            data={"sub": str(user.id), "tenant_id": str(tenant.id), "type": "refresh"},
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        return access_token, refresh_token

    # ── 单词 ──────────────────────────────────────────────────────
    def list_words(
        self,
        user: User | None,
        book_id: int | None = None,
        level: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[WordOut]:
        words = self.repo.list_words(self._tenant_of(user), book_id, level, skip, limit)
        fav_set = self._collection_id_set(user.id, "word") if user else set()
        tag_map = {}
        if user and book_id:
            tag_map = self.repo.list_word_tags(user.id, book_id, [w.id for w in words])
        out: list[WordOut] = []
        for w in words:
            out.append(
                WordOut(
                    **self._word_attrs(w),
                    in_wordbook=False,
                    is_favorite=w.id in fav_set,
                    tag=tag_map.get(w.id),
                )
            )
        return out

    def lookup_word(self, user: User | None, word: str) -> dict:
        """划词快速查询：返回单词释义/音标/词性（每日一读用）"""
        row = self.repo.get_word_by_text(word.strip().lower(), self._tenant_of(user))
        if not row:
            raise NotFoundException("词典中未找到该词")
        return {
            "word": row.word,
            "phonetic": row.phonetic,
            "definition": row.definition,
            "pos": row.pos,
        }

    def set_word_tag(self, user: User, book_id: int, word_id: int, tag: str | None) -> dict:
        word = self.repo.get_word(word_id)
        if not word:
            raise NotFoundException("单词不存在")
        self.repo.set_word_tag(user.id, word_id, book_id, tag or None)
        return {"word_id": word_id, "tag": tag or None}

    def get_categories(self, user: User, book_id: int) -> list:
        from app.services.english.schemas import CategoryOut

        return [
            CategoryOut(tag=c["tag"], name=c["name"], count=self.repo.count_words_by_tag(user.id, book_id, c["tag"]))
            for c in WORD_CATEGORIES
        ]

    # ── 阅读 ──────────────────────────────────────────────────────
    def list_articles(
        self, user: User | None, skip: int = 0, limit: int = 100
    ) -> list[ArticleListItemOut]:
        articles = self.repo.list_articles(self._tenant_of(user), skip, limit)
        fav_set = self._collection_id_set(user.id, "reading") if user else set()
        note_map = self._note_map(user.id, [a.id for a in articles]) if user else {}
        return [
            ArticleListItemOut(
                id=a.id,
                title=a.title,
                level=a.level,
                word_count=a.word_count,
                is_favorite=a.id in fav_set,
                note_id=note_map.get(a.id, (None, None))[0],
                note_updated_at=note_map.get(a.id, (None, None))[1],
            )
            for a in articles
        ]

    def get_article(self, user: User | None, article_id: int) -> ArticleOut:
        article = self.repo.get_article(article_id)
        if not article:
            raise NotFoundException("文章不存在")
        fav_set = self._collection_id_set(user.id, "reading") if user else set()
        note = self.repo.get_note_by_article(user.id, article_id) if user else None
        return ArticleOut(
            id=article.id,
            title=article.title,
            level=article.level,
            word_count=article.word_count,
            content=article.content,
            content_cn=article.content_cn,
            topic=article.topic,
            publish_date=article.publish_date,
            keywords=article.keywords,
            is_favorite=article.id in fav_set,
            note_id=note.id if note else None,
            note_updated_at=note.updated_at if note else None,
        )

    def list_notes(self, user: User) -> list[NoteOut]:
        notes = self.repo.list_notes(user.id)
        article_map = {a.id: a for a in self.repo.list_articles_in([n.article_id for n in notes])}
        return [
            NoteOut(
                **self._note_attrs(n),
                article_title=article_map[n.article_id].title if n.article_id in article_map else None,
            )
            for n in notes
        ]

    def create_note(self, user: User, article_id: int, content: str) -> NoteOut:
        article = self.repo.get_article(article_id)
        if not article:
            raise NotFoundException("文章不存在")
        existing = self.repo.get_note_by_article(user.id, article_id)
        if existing:
            raise ValidationException("该文章已有笔记，请使用更新")
        note = self.repo.create_note(user.id, article_id, content)
        return NoteOut(**self._note_attrs(note), article_title=article.title)

    def update_note(self, user: User, note_id: int, content: str) -> NoteOut:
        note = self.repo.get_note(user.id, note_id)
        if not note:
            raise NotFoundException("笔记不存在")
        note = self.repo.update_note(note, content)
        return NoteOut(**self._note_attrs(note))

    def delete_note(self, user: User, note_id: int) -> None:
        note = self.repo.get_note(user.id, note_id)
        if not note:
            raise NotFoundException("笔记不存在")
        self.repo.delete_note(note)

    # ── 收藏 ──────────────────────────────────────────────────────
    def add_collection(self, user: User, item_type: str, item_id: int) -> CollectionItemOut:
        if item_type == "word":
            obj = self.repo.get_word(item_id)
        elif item_type == "reading":
            obj = self.repo.get_article(item_id)
        else:
            raise ValidationException("不支持的收藏类型")
        if not obj:
            raise NotFoundException("收藏对象不存在")
        existing = self.repo.get_collection(user.id, item_type, item_id)
        if existing:
            raise ValidationException("已在收藏列表中")
        item = self.repo.add_collection(user.id, item_type, item_id)
        return self._collection_item_out(item)

    def list_collections(self, user: User, item_type: str | None = None) -> list[CollectionItemOut]:
        items = self.repo.list_collections(user.id, item_type)
        out: list[CollectionItemOut] = []
        for i in items:
            item = self._collection_item_out(i)
            if i.item_type == "word":
                word = self.repo.get_word(i.item_id)
                if word:
                    item.title = word.word
                    item.subtitle = word.definition
            elif i.item_type == "reading":
                a = self.repo.get_article(i.item_id)
                if a:
                    item.title = a.title
                    item.subtitle = a.level or ""
            out.append(item)
        return out

    def remove_collection(self, user: User, collection_id: int) -> None:
        item = self.db.query(UserCollection).filter(
            UserCollection.id == collection_id, UserCollection.user_id == user.id
        ).first()
        if not item:
            raise NotFoundException("收藏记录不存在")
        self.repo.remove_collection(item)

    # ── 打卡 ──────────────────────────────────────────────────────
    def checkin(self, user: User) -> CheckinStatsOut:
        today = date.today()
        if not self.repo.get_checkin(user.id, today):
            self.repo.create_checkin(user.id, today)
        return self.checkin_stats(user)

    def checkin_stats(self, user: User) -> CheckinStatsOut:
        dates = self.repo.list_checkin_dates(user.id)
        date_set = set(dates)
        streak = 0
        d = date.today()
        if d not in date_set:
            d -= timedelta(days=1)
        while d in date_set:
            streak += 1
            d -= timedelta(days=1)
        return CheckinStatsOut(
            streak_days=streak,
            total_days=len(dates),
            today_done=date.today() in date_set,
            recent_dates=sorted(dates, reverse=True)[:30],
        )

    # ── 学习统计 ──────────────────────────────────────────────────
    def study_stats(self, user: User) -> StudyStatsOut:
        from app.services.english.models import UserWordMemory

        stats = self.checkin_stats(user)
        mastered_count = (
            self.db.query(UserWordMemory)
            .filter(UserWordMemory.user_id == user.id, UserWordMemory.status == 2)
            .count()
        )
        return StudyStatsOut(
            total_words=self.repo.count_words(user.tenant_id),
            wordbook_count=self.repo.count_wordbook(user.id),
            mastered_count=mastered_count,
            favorite_count=self.repo.count_collections(user.id),
            note_count=self.repo.count_notes(user.id),
            checkin_total=stats.total_days,
            checkin_streak=stats.streak_days,
            today_checkin=stats.today_done,
        )

    # ── 辅助 ──────────────────────────────────────────────────────
    def _tenant_of(self, user: User | None) -> int:
        """游客访问内容时回退到 english 租户"""
        if user:
            return user.tenant_id
        return get_english_tenant(self.db).id

    def _collection_id_set(self, user_id: int, item_type: str) -> set[int]:
        rows = (
            self.db.query(UserCollection.item_id)
            .filter(UserCollection.user_id == user_id, UserCollection.item_type == item_type)
            .all()
        )
        return {r[0] for r in rows}

    def _note_map(self, user_id: int, article_ids: list[int]) -> dict[int, tuple[int | None, datetime | None]]:
        if not article_ids:
            return {}
        notes = (
            self.db.query(ReadingNote)
            .filter(ReadingNote.user_id == user_id, ReadingNote.article_id.in_(article_ids))
            .all()
        )
        return {n.article_id: (n.id, n.updated_at) for n in notes}

    @staticmethod
    def _word_attrs(word: EnglishWord) -> dict:
        return {
            "id": word.id,
            "book_id": word.book_id,
            "word": word.word,
            "phonetic": word.phonetic,
            "definition": word.definition,
            "pos": word.pos,
            "example": word.example,
            "example2": word.example2,
            "phrase": word.phrase,
            "level": word.level,
            "tags": word.tags,
        }

    @staticmethod
    def _article_attrs(a: EnglishReadingArticle) -> dict:
        return {
            "id": a.id,
            "title": a.title,
            "level": a.level,
            "word_count": a.word_count,
        }

    @staticmethod
    def _note_attrs(n: ReadingNote) -> dict:
        return {
            "id": n.id,
            "article_id": n.article_id,
            "content": n.content,
            "created_at": n.created_at,
            "updated_at": n.updated_at,
        }

    @staticmethod
    def _collection_item_out(item: UserCollection) -> CollectionItemOut:
        return CollectionItemOut(
            id=item.id,
            item_type=item.item_type,
            item_id=item.item_id,
            created_at=item.created_at,
        )
