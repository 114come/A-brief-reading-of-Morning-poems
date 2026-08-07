"""每日一读服务

每日推送 1 篇适配用户词汇水平的短文（LLM 实时生成、按 (date, level, topic) 缓存落库）。
核心闭环：每日一读 → 抓取生词 → SRS 间隔重复 → 生词专项测试 → AI 当日阅读分析。
"""
import json
import logging
import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.services.ai.service import PROVIDER_ADAPTERS, AIService
from app.services.english.models import EnglishReadingArticle, EnglishWord, EnglishWordBook, UserDailyReading
from app.services.english.repository import EnglishRepository
from app.services.english.schemas import (
    ArticleOut,
    DailyReadingRecordOut,
    DailyReadingTodayOut,
    ReadingArchiveItemOut,
)
from app.services.tenant.models import User

logger = logging.getLogger(__name__)

# 难度档位
LEVELS = ("basic", "cet4", "advanced")
LEVEL_LABEL = {"basic": "基础", "cet4": "四级", "advanced": "高阶"}
LEVEL_ORDER = {lv: i for i, lv in enumerate(LEVELS)}

# 题材每日轮换
TOPICS = ("fun_science", "life_story", "film", "motto", "exam")
TOPIC_LABEL = {
    "fun_science": "趣味科普",
    "life_story": "生活故事",
    "film": "影视文摘",
    "motto": "短句美文",
    "exam": "应试短文",
}

# 出题：4-6 题，题型轮换（a英译中/b中译英/c听音选义/d单词填空）
QUIZ_TYPES = ("a", "b", "d", "c")

# 艾宾浩斯间隔（与前端 srsEngine.SUCCESSOR 一致）：复习答对升级
SUCCESSOR = {1: 2, 2: 4, 4: 7, 7: 15}

ARTICLE_SYSTEM = (
    "你是英语学习内容的资深编辑。请根据要求输出一篇面向中国学生的英语短文，"
    "输出严格 JSON，不要输出其他内容。JSON 格式："
    '{"title":"英文标题","content":"英文正文（120-280词）","content_cn":"全文中译","keywords":[{"word":"重点单词","definition":"中文释义","example":"正文中包含该词的英文原句"}]}'
    "其中 keywords 提供 5-8 个与难度匹配的重点单词及其释义。"
)


class DailyReadingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EnglishRepository(db)

    # ── 今日任务 ──────────────────────────────────────────────────
    async def get_today(self, user: User) -> DailyReadingTodayOut:
        tenant = _tenant_of(user, self.db)
        today = date.today()
        settings_row = self.repo.get_settings(user.id)
        level_mode = settings_row.reading_level_mode if settings_row else "auto"
        manual_level = settings_row.reading_manual_level if settings_row else None

        record = self.repo.get_daily_reading(user.id, today)
        manual_override = level_mode == "manual" and manual_level in LEVELS
        desired_level = manual_level if manual_override else (record.level if record else self._adapt_level(user))

        if record:
            article_now = self.repo.get_article(record.article_id)
            # 重派条件：手动切换难度 或 记录与文章难度不一致（含脏数据兜底）
            needs_repick = (
                (manual_override and record.level != manual_level)
                or (not article_now)
                or (article_now and article_now.level != record.level)
            )
            if needs_repick:
                topic = self._topic_of_day()
                article = self.repo.get_article_by_daily(tenant.id, today, desired_level, topic)
                if not article:
                    article = await self._generate_article(tenant.id, desired_level, topic)
                self.repo.update_daily_reading(
                    record, article_id=article.id, level=desired_level,
                    status="pending", correct_count=0, total_questions=0,
                    wrong_word_ids=[], new_word_ids=[], duration_sec=0,
                )
        else:
            level = desired_level
            topic = self._topic_of_day()
            article = self.repo.get_article_by_daily(tenant.id, today, level, topic)
            if not article:
                article = await self._generate_article(tenant.id, level, topic)
            record = self.repo.create_daily_reading(user.id, today, article.id, level)

        article = self.repo.get_article(record.article_id)
        if not article:
            raise NotFoundException("文章不存在")

        fav_set = self._favorite_set(user, "reading")
        note = self.repo.get_note_by_article(user.id, article.id) if user else None
        article_out = ArticleOut(
            id=article.id, title=article.title, level=article.level,
            word_count=article.word_count, content=article.content,
            content_cn=article.content_cn, topic=article.topic,
            publish_date=article.publish_date, keywords=article.keywords,
            is_favorite=article.id in fav_set,
            note_id=note.id if note else None,
            note_updated_at=note.updated_at if note else None,
        )

        return DailyReadingTodayOut(
            record=self._record_out(record),
            article=article_out,
            level_mode=level_mode,
            manual_level=manual_level,
            topics=TOPIC_LABEL.get(article.topic or "") and [article.topic or ""] or [],
            estimated_min=max(1, round(article.word_count / 200)),
            word_task_done=self._word_task_done(user),
        )

    # ── 难度适配 ──────────────────────────────────────────────────
    def _adapt_level(self, user: User) -> str:
        settings_row = self.repo.get_settings(user.id)
        if settings_row and settings_row.reading_level_mode == "manual" and settings_row.reading_manual_level in LEVELS:
            return settings_row.reading_manual_level

        # 基础分档：按背诵目标
        target = (settings_row.target if settings_row else "cet4") or "cet4"
        if target in ("primary_school", "high_school", "daily"):
            base = "basic"
        elif target == "cet4":
            base = "cet4"
        else:  # cet6/kaoyan/toefl/ielts/gre
            base = "advanced"

        # 按最近 3 次已打卡答题正确率微调
        recent = [r for r in self.repo.list_daily_reading_recent(user.id, 10) if r.status == "done"][:3]
        if recent:
            accs = [
                round(r.correct_count * 100 / r.total_questions) if r.total_questions else 50
                for r in recent
            ]
            avg = sum(accs) / len(accs)
            idx = LEVEL_ORDER[base]
            if avg < 55:
                idx = max(0, idx - 1)
            elif avg > 85:
                idx = min(len(LEVELS) - 1, idx + 1)
            base = LEVELS[idx]
        return base

    def set_level_mode(self, user: User, mode: str, level: str | None) -> dict:
        if mode == "manual" and level not in LEVELS:
            raise ValidationException("手动难度必须是 basic/cet4/advanced")
        kwargs: dict = {"reading_level_mode": mode, "reading_manual_level": level if mode == "manual" else None}
        existing = self.repo.get_settings(user.id)
        if existing is None:
            kwargs["book_id"] = self._active_book_id(user)  # 无设置行时先补主词书
        self.repo.upsert_settings(user.id, **kwargs)
        return {"saved": True, "mode": mode, "level": level}

    # ── LLM 生成文章 ──────────────────────────────────────────────
    async def _generate_article(self, tenant_id: int, level: str, topic: str) -> EnglishReadingArticle:
        prompt = (
            f"难度：{LEVEL_LABEL[level]}（请按以下词汇范围选词："
            f"{'基础=小学至初中高频词' if level=='basic' else '四级=大学英语四级词汇' if level=='cet4' else '高阶=六级及以上词汇'}）。"
            f"题材：{TOPIC_LABEL[topic]}。请写一篇 120-280 词的英语短文，并提供全文中译与重点单词。"
        )
        messages = [{"role": "system", "content": ARTICLE_SYSTEM}, {"role": "user", "content": prompt}]

        last_err: Exception | None = None
        for attempt in range(2):
            try:
                content = await self._chat_llm(messages)
                data = self._parse_json(content)
                title = str(data.get("title", "")).strip()
                body = str(data.get("content", "")).strip()
                cn = str(data.get("content_cn", "")).strip()
                keywords = data.get("keywords") or []
                if not title or not body or not cn:
                    raise ValueError("文章字段缺失")
                word_count = len(body.split())
                if not (120 <= word_count <= 280):
                    raise ValueError(f"词数 {word_count} 不在 120-280")
                clean_kw = [
                    {"word": str(k.get("word", "")).strip(), "definition": str(k.get("definition", "")).strip(), "example": str(k.get("example", "")).strip()}
                    for k in keywords if isinstance(k, dict) and k.get("word") and k.get("definition")
                ]
                if len(clean_kw) < 4:
                    raise ValueError("关键词不足 4 个")
                today = date.today()
                return self.repo.create_article(
                    tenant_id, title, body, cn, level, topic, today, clean_kw,
                )
            except Exception as e:
                logger.warning("文章生成第 %s 次失败: %s", attempt + 1, e)
                last_err = e

        # LLM 失败降级：复用该难度最近一篇
        fallback = self.repo.get_latest_article_by_level(tenant_id, level)
        if fallback:
            logger.warning("LLM 生成失败，降级复用最近文章 id=%s", fallback.id)
            return fallback
        raise ValidationException("今日文章生成失败，请稍后重试") from last_err

    async def _chat_llm(self, messages: list[dict]) -> str:
        try:
            from app.services.english.service import get_english_tenant

            tenant = get_english_tenant(self.db)
            result = await AIService(self.db).chat_completion(
                tenant_id=tenant.id, model=settings.LLM_MODEL,
                messages=messages, temperature=0.8, max_tokens=1600,
            )
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning("AIService 生成失败，尝试 env 直连: %s", e)
        if settings.LLM_API_KEY:
            adapter_cls = PROVIDER_ADAPTERS.get(settings.LLM_PROVIDER_TYPE)
            if adapter_cls:
                adapter = adapter_cls(api_key=settings.LLM_API_KEY, api_base=settings.LLM_BASE_URL or None)
                result = await adapter.chat_completion(
                    model=settings.LLM_MODEL, messages=messages, temperature=0.8, max_tokens=1600,
                )
                return result["choices"][0]["message"]["content"]
        raise ValidationException("LLM 服务不可用")

    @staticmethod
    def _parse_json(content: str) -> dict:
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1] if len(content.split("```")) > 1 else content
            content = content.strip()
            if content.startswith("json"):
                content = content[4:].strip()
        start, end = content.find("{"), content.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("LLM 返回非 JSON")
        return json.loads(content[start : end + 1])

    # ── 小测 ──────────────────────────────────────────────────────
    def get_quiz(self, user: User, article_id: int) -> dict:
        article = self.repo.get_article(article_id)
        if not article:
            raise NotFoundException("文章不存在")
        keywords = [k for k in (article.keywords or []) if isinstance(k, dict) and k.get("word")]
        if len(keywords) < 4:
            raise ValidationException("文章暂无足够可出题词汇")
        random.shuffle(keywords)
        pick = keywords[: min(6, len(keywords))]
        # 保证 ≥2 单选 + ≥1 填空
        if len(pick) < 6:
            while sum(1 for _ in range(len(pick))) and len(pick) < 4:
                pick.append(keywords[len(pick) % len(keywords)])

        questions = []
        for i, kw in enumerate(pick):
            qtype = QUIZ_TYPES[i % len(QUIZ_TYPES)]
            q = self._build_keyword_question(kw, qtype, pick)
            if q:
                questions.append(q)
        # 题型去重兜底：若单选不足 2 或填空不足 1，重排
        if sum(1 for q in questions if q["type"] in ("a", "b", "c")) < 2 or sum(1 for q in questions if q["type"] in ("d", "e")) < 1:
            questions = []
            for i, kw in enumerate(pick):
                q = self._build_keyword_question(kw, QUIZ_TYPES[i % len(QUIZ_TYPES)], pick)
                if q:
                    questions.append(q)
        return {"questions": questions, "total": len(questions)}

    def _build_keyword_question(self, kw: dict, qtype: str, all_kws: list[dict]) -> dict | None:
        word = str(kw["word"]).strip().lower()
        definition = str(kw["definition"]).strip()
        example = str(kw.get("example", "")).strip()
        # 从 english_words 补音标（可选）
        phonetic = None
        ew = self.db.query(EnglishWord).filter(EnglishWord.word == word).limit(1).first()
        if ew:
            phonetic = ew.phonetic
        base = {"word_id": 0, "word": word, "phonetic": phonetic, "definition": definition, "pos": None}

        others = [k for k in all_kws if str(k.get("word", "")).strip().lower() != word]
        def_pool = [str(k["definition"]).strip() for k in others if k.get("definition")]
        word_pool = [str(k["word"]).strip().lower() for k in others if k.get("word")]

        if qtype in ("a", "c"):
            distractors = [d for d in def_pool if d != definition][:3]
            if len(distractors) < 3:
                return None
            options = [definition] + distractors[:3]
            random.shuffle(options)
            return {**base, "type": qtype, "show": "word" if qtype == "a" else "audio", "options": options, "answer": definition}
        if qtype == "b":
            distractors = [w for w in word_pool if w != word][:3]
            if len(distractors) < 3:
                return None
            options = [word] + distractors[:3]
            random.shuffle(options)
            return {**base, "type": "b", "show": "definition", "options": options, "answer": word}
        if qtype == "d":
            if not example:
                return None
            return {**base, "type": "d", "mask": self._mask_word(word), "example_en": example, "example_cn": definition, "answer": word}
        return None

    @staticmethod
    def _mask_word(word: str) -> str:
        n = len(word)
        if n <= 3:
            return "_" * n
        if n <= 6:
            start = (n - 2) // 2
            end = start + 2
        else:
            start = (n - 3) // 2
            end = start + 3
        return word[:start] + "_" * (end - start) + word[end:]

    # ── 提交答案 ──────────────────────────────────────────────────
    def submit_quiz(self, user: User, article_id: int, answers: list[dict]) -> dict:
        record = self._today_record_for_article(user, article_id)
        correct = 0
        wrong_ids: list[int] = []
        for ans in answers:
            is_correct = bool(ans.get("correct"))
            word = str(ans.get("word", "")).strip()
            if is_correct:
                correct += 1
            self._apply_srs_effect(user, word, is_correct, record, definition=str(ans.get("definition", "")).strip() or None)
            if not is_correct:
                wid = self._resolve_word_id(user, word)
                if wid and wid not in wrong_ids:
                    wrong_ids.append(wid)
        total = record.total_questions + len(answers)
        new_wrong = list(dict.fromkeys(list(record.wrong_word_ids or []) + wrong_ids))
        self.repo.update_daily_reading(
            record,
            total_questions=total,
            correct_count=record.correct_count + correct,
            wrong_word_ids=new_wrong,
        )
        return {"saved": True, "correct": correct, "total": len(answers)}

    def _apply_srs_effect(self, user: User, word: str, is_correct: bool, record: UserDailyReading, definition: str | None = None) -> None:
        """SRS 联动：学习中词答对升级间隔/答错重置；未学词答错自动收集为新词"""
        if not word:
            return
        book_id = self._active_book_id(user)
        word_row = self.repo.get_word_in_book(word, book_id) or self.repo.get_word_by_text(word, _tenant_of(user, self.db).id)
        if not word_row:
            if is_correct:
                return  # 未学词答对：不预埋
            # 词典外的阅读生词：建词后收集
            self._collect_text(user, word, record, definition)
            return
        wid = word_row.id
        if self.repo.get_blacklist(user.id, wid):
            return
        mem = self.repo.get_memory(user.id, wid, book_id)
        if mem and mem.status == 2:
            return  # 已掌握，跳过
        if is_correct:
            if mem and mem.status == 1:
                # 阅读中再遇旧词且答对 → 升级间隔（SUCCESSOR）
                interval = SUCCESSOR.get(mem.current_interval, mem.current_interval or 1)
                self.repo.upsert_memory_row(
                    user.id, wid, book_id,
                    {"status": 1, "next_review_date": date.today() + timedelta(days=interval), "interval": interval, "wrong_count": 0},
                )
        else:
            if mem and mem.status == 1:
                self.repo.upsert_memory_row(
                    user.id, wid, book_id,
                    {"status": 1, "next_review_date": date.today(), "interval": mem.current_interval, "wrong_count": mem.wrong_count + 1},
                )
            else:
                # 自动收集为新词
                self._collect_text(user, word, record, definition)

    # ── 生词收集 ──────────────────────────────────────────────────
    def collect_word(self, user: User, article_id: int, word: str, source: str, definition: str | None = None) -> dict:
        record = self._today_record_for_article(user, article_id)
        if not word.strip():
            raise ValidationException("单词不能为空")
        return self._collect_text(user, word.strip(), record, definition)

    def _collect_text(self, user: User, word: str, record: UserDailyReading, definition: str | None = None, example: str | None = None) -> dict:
        """收集生词：确保词存在于用户主词书 → memory status=0 → 生词本 → 记入当日 new_word_ids"""
        book_id = self._active_book_id(user)
        word_row = self.repo.get_word_in_book(word, book_id) or self.repo.get_word_by_text(word, _tenant_of(user, self.db).id)
        if word_row:
            target_id = word_row.id
            # 词不在主词书 → 补入主词书（幂等）
            if word_row.book_id != book_id:
                target_id = self.repo.create_word_copy(
                    _tenant_of(user, self.db).id, book_id, word_row.word, word_row.definition,
                    word_row.phonetic, word_row.pos, word_row.example, word_row.example_cn,
                ).id
        else:
            # 词典外的阅读生词：用 LLM 关键词释义建词
            target_id = self.repo.create_word_copy(
                _tenant_of(user, self.db).id, book_id, word,
                definition or "（阅读生词）", example=example,
            ).id
        if self.repo.get_blacklist(user.id, target_id):
            return {"status": "skipped", "reason": "blacklisted"}
        mem = self.repo.get_memory(user.id, target_id, book_id)
        if mem and mem.status == 2:
            return {"status": "skipped", "reason": "mastered"}
        self.repo.upsert_memory_row(user.id, target_id, book_id, {"status": 0, "next_review_date": None, "interval": 0, "wrong_count": 0})
        self.repo.add_to_wordbook(user.id, target_id, book_id)
        ids = list(dict.fromkeys(list(record.new_word_ids or []) + [target_id]))
        self.repo.update_daily_reading(record, new_word_ids=ids)
        return {"status": "collected", "word_id": target_id}

    # ── 黑名单 ────────────────────────────────────────────────────
    def set_blacklist(self, user: User, word: str, blacklisted: bool) -> dict:
        wid = self._resolve_word_id(user, word.strip())
        if not wid:
            raise NotFoundException("词典中未找到该词")
        existing = self.repo.get_blacklist(user.id, wid)
        if blacklisted and not existing:
            self.repo.add_blacklist(user.id, wid)
        elif not blacklisted and existing:
            self.repo.remove_blacklist(existing)
        return {"saved": True, "blacklisted": blacklisted}

    # ── 打卡 ──────────────────────────────────────────────────────
    def complete(self, user: User, article_id: int, duration_sec: int) -> dict:
        record = self._today_record_for_article(user, article_id)
        if record.status == "done":
            return {"saved": True, "status": "done"}
        self.repo.update_daily_reading(
            record,
            status="done",
            duration_sec=max(record.duration_sec, int(duration_sec)),
        )
        # 埋点：阅读篇数 + 时长（幂等篇数、累加时长）
        self.repo.upsert_activity(user.id, record.reading_date, reading_article_id=article_id)
        if duration_sec > 0:
            self.repo.upsert_activity(user.id, record.reading_date, reading_duration_sec=int(duration_sec))
        return {"saved": True, "status": "done"}

    # ── 历史存档 ──────────────────────────────────────────────────
    def archive(self, user: User) -> list[ReadingArchiveItemOut]:
        records = self.repo.list_daily_reading(user.id)
        articles = {a.id: a for a in self.repo.list_articles_in([r.article_id for r in records])}
        fav_set = self._favorite_set(user, "reading")
        notes = {n.article_id: n for n in self.repo.list_notes(user.id)}
        out = []
        for r in records:
            a = articles.get(r.article_id)
            if not a:
                continue
            out.append(ReadingArchiveItemOut(
                id=r.id, reading_date=r.reading_date, article_id=a.id, title=a.title,
                level=r.level, level_label=LEVEL_LABEL.get(r.level, r.level),
                topic=a.topic, topic_label=TOPIC_LABEL.get(a.topic or "", ""),
                status=r.status,
                correct_count=r.correct_count, total_questions=r.total_questions,
                accuracy=round(r.correct_count * 100 / r.total_questions) if r.total_questions else 0,
                new_word_count=len(r.new_word_ids or []),
                is_favorite=a.id in fav_set,
                note_id=notes.get(a.id).id if a.id in notes else None,
            ))
        return out

    # ── 辅助 ──────────────────────────────────────────────────────
    def _today_record_for_article(self, user: User, article_id: int) -> UserDailyReading:
        record = self.repo.get_daily_reading(user.id, date.today())
        if not record or record.article_id != article_id:
            raise NotFoundException("今日任务不存在，请先进入每日一读")
        return record

    def _active_book_id(self, user: User) -> int:
        """用户主词书（未 onboarding 默认 cet4）"""
        s = self.repo.get_settings(user.id)
        if s and s.book_id:
            return s.book_id
        book = self.db.query(EnglishWordBook).filter(EnglishWordBook.code == "cet4").first()
        return book.id if book else 0

    def _resolve_word_id(self, user: User, word: str) -> int | None:
        row = self.repo.get_word_by_text(word, _tenant_of(user, self.db).id)
        return row.id if row else None

    def _favorite_set(self, user: User, item_type: str) -> set[int]:
        return {c.item_id for c in self.repo.list_collections(user.id, item_type)}

    def _word_task_done(self, user: User) -> bool:
        today = date.today()
        return (
            self.repo.get_checkin(user.id, today) is not None
            or self.repo.sum_daily_stats(user.id, today) != (0, 0, 0)
        )

    @staticmethod
    def _topic_of_day() -> str:
        return TOPICS[(date.today().toordinal()) % len(TOPICS)]

    @staticmethod
    def _record_out(r: UserDailyReading) -> DailyReadingRecordOut:
        return DailyReadingRecordOut(
            status=r.status, level=r.level, level_label=LEVEL_LABEL.get(r.level, r.level),
            correct_count=r.correct_count, total_questions=r.total_questions,
            accuracy=round(r.correct_count * 100 / r.total_questions) if r.total_questions else 0,
            new_word_count=len(r.new_word_ids or []),
        )


def _tenant_of(user: User | None, db: Session):
    """用户所属 english 租户"""
    from app.services.english.service import get_english_tenant
    return get_english_tenant(db)
