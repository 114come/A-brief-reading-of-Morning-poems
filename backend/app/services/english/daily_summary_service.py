"""AI 每日学习总结服务

聚合当日学习数据 → DeepSeek 生成两段文案（客观概括 + 个性化建议）→ 缓存落库。
每日 1 次限制（user_daily_summary 唯一约束）；LLM 失败降级为规则模板（仍落库）。
"""
import asyncio
import json
import logging
from datetime import date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.services.ai.service import PROVIDER_ADAPTERS, AIService
from app.services.english.repository import EnglishRepository
from app.services.english.schemas import (
    DailySummaryOut,
    SummaryCategory,
    SummaryItem,
)
from app.services.tenant.models import User

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM = (
    "你是一位专业的英语学习数据分析助手。根据用户今天的学习数据，"
    "输出严格 JSON {\"overview\":\"客观数据概括，2-3句\",\"advice\":\"个性化点评与次日学习建议，3-4句\"}，不要输出其他内容。"
)


class DailySummaryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EnglishRepository(db)

    # ── 读取缓存 ──────────────────────────────────────────────────
    def get_summary(self, user: User) -> DailySummaryOut:
        today = date.today()
        row = self.repo.get_summary(user.id, today)
        if not row:
            return DailySummaryOut(date=today)
        return DailySummaryOut(
            date=today,
            table=row.table_json or [],
            ai_overview=row.ai_overview,
            ai_advice=row.ai_advice,
            source=row.source,
            generated_at=row.generated_at,
        )

    def has_activity_today(self, user: User) -> bool:
        today = date.today()
        dr = self.repo.get_daily_reading(user.id, today)
        return (
            self.repo.has_activity_today(user.id, today)
            or self.repo.get_checkin(user.id, today) is not None
            or self.repo.sum_daily_stats(user.id, today) != (0, 0, 0)
            or (dr is not None and dr.status == "done")
        )

    # ── 聚合当日数据 ──────────────────────────────────────────────
    def _aggregate_today(self, user: User) -> list[SummaryCategory]:
        today = date.today()
        review, new, wrong = self.repo.sum_daily_stats(user.id, today)
        checkin = self._checkin_stats(user)
        activity = self.repo.get_activity(user.id, today)

        test_choice_q = activity.test_choice_questions if activity else 0
        test_choice_c = activity.test_choice_correct if activity else 0
        test_fill_q = activity.test_fill_questions if activity else 0
        test_fill_c = activity.test_fill_correct if activity else 0
        test_total = test_choice_q + test_fill_q
        test_correct = test_choice_c + test_fill_c

        read_sec = activity.reading_duration_sec if activity else 0
        read_items = len(activity.reading_article_ids or []) if activity else 0
        lookups = activity.word_lookups if activity else 0

        wordbook_added = self.repo.count_wordbook_added_today(user.id, today)
        notes_added = self.repo.count_notes_added_today(user.id, today)
        total_sec = (activity.word_study_sec if activity else 0) + read_sec

        # 每日一读数据
        daily_reading = self.repo.get_daily_reading(user.id, today)
        dr_done = daily_reading.status == "done" if daily_reading else False
        dr_level = self._level_label(daily_reading.level) if daily_reading else "-"
        dr_total = daily_reading.total_questions if daily_reading else 0
        dr_correct = daily_reading.correct_count if daily_reading else 0
        dr_new = len(daily_reading.new_word_ids or []) if daily_reading else 0
        dr_wrong = self._wrong_words_text(user, daily_reading) if daily_reading else "-"

        pct = lambda c, q: f"{round(c * 100 / q)}%" if q > 0 else "0%"

        return [
            SummaryCategory(category="单词", items=[
                SummaryItem(label="今日复习旧词数", value=f"{review} 个"),
                SummaryItem(label="今日新词数", value=f"{new} 个"),
                SummaryItem(label="测试总题数", value=f"{test_total} 题"),
                SummaryItem(label="测试正确率", value=pct(test_correct, test_total)),
                SummaryItem(label="单选正确率", value=pct(test_choice_c, test_choice_q)),
                SummaryItem(label="填空正确率", value=pct(test_fill_c, test_fill_q)),
                SummaryItem(label="今日新增生词", value=f"{wordbook_added} 个"),
                SummaryItem(label="标记不认识数", value=f"{wrong} 个"),
                SummaryItem(label="连续打卡天数", value=f"{checkin['streak_days']} 天"),
            ]),
            SummaryCategory(category="每日一读", items=[
                SummaryItem(label="是否完成今日一读", value="已完成" if dr_done else "未打卡"),
                SummaryItem(label="文章难度", value=dr_level),
                SummaryItem(label="答题正确率", value=pct(dr_correct, dr_total)),
                SummaryItem(label="本次新增生词数量", value=f"{dr_new} 个"),
                SummaryItem(label="高频易错单词", value=dr_wrong),
            ]),
            SummaryCategory(category="阅读", items=[
                SummaryItem(label="阅读文章", value=f"{read_items} 篇"),
                SummaryItem(label="阅读时长", value=f"{round(read_sec / 60)} 分钟"),
                SummaryItem(label="划词查询", value=f"{lookups} 次"),
                SummaryItem(label="新增笔记", value=f"{notes_added} 条"),
            ]),
            SummaryCategory(category="综合", items=[
                SummaryItem(label="全站学习时长", value=f"{round(total_sec / 60)} 分钟"),
                SummaryItem(label="完成单词基础任务", value="是" if checkin["today_done"] else "否"),
                SummaryItem(label="完成单词测试", value="是" if test_total > 0 else "否"),
                SummaryItem(label="完成每日一读", value="是" if dr_done else "否"),
            ]),
        ]

    @staticmethod
    def _level_label(level: str | None) -> str:
        return {"basic": "基础", "cet4": "四级", "advanced": "高阶"}.get(level or "", level or "-")

    def _wrong_words_text(self, user, daily_reading) -> str:
        """高频易错单词：错词前 3 个 → 词+释义"""
        ids = list(daily_reading.wrong_word_ids or [])[:3]
        if not ids:
            return "无"
        words = self.repo.list_words_in(ids)
        return "；".join(f"{w.word}({w.definition[:20]})" for w in words if w)

    # ── LLM 调用 ──────────────────────────────────────────────────
    async def _chat_llm(self, user: User, messages: list[dict]) -> str:
        """优先 AIService（DB provider），无则 env 直连（DeepSeek）"""
        try:
            result = await AIService(self.db).chat_completion(
                tenant_id=user.tenant_id, model=settings.LLM_MODEL,
                messages=messages, temperature=0.4, max_tokens=800,
            )
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning("AIService LLM 调用失败，尝试 env 直连: %s", e)
        if settings.LLM_API_KEY:
            adapter_cls = PROVIDER_ADAPTERS.get(settings.LLM_PROVIDER_TYPE)
            if adapter_cls:
                adapter = adapter_cls(api_key=settings.LLM_API_KEY, api_base=settings.LLM_BASE_URL or None)
                result = await adapter.chat_completion(
                    model=settings.LLM_MODEL, messages=messages, temperature=0.4, max_tokens=800,
                )
                return result["choices"][0]["message"]["content"]
        raise ValidationException("LLM 服务不可用")

    @staticmethod
    def _parse_llm(content: str) -> dict:
        """解析 LLM 返回的 JSON（容忍 markdown 围栏）"""
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

    # ── 生成总结 ──────────────────────────────────────────────────
    async def generate(self, user: User) -> DailySummaryOut:
        today = date.today()
        # 每日 1 次限制
        existing = self.repo.get_summary(user.id, today)
        if existing:
            raise ValidationException("今日日报已生成，明日 0 点后可重新生成")

        table = self._aggregate_today(user)
        table_plain = json.dumps([c.model_dump() for c in table], ensure_ascii=False)
        prompt = (
            f"今天的学习数据如下（JSON）：{table_plain}。"
            "请按此输出：overview=客观数据概括（提炼关键数据，2-3句）；"
            "advice=个性化点评与次日学习建议（分析薄弱项，如单词拼写/阅读，给出具体建议，3-4句）。"
        )
        messages = [{"role": "system", "content": SUMMARY_SYSTEM}, {"role": "user", "content": prompt}]

        overview = advice = ""
        source = "llm"
        try:
            content = await self._chat_llm(user, messages)
            parsed = self._parse_llm(content)
            overview = str(parsed.get("overview", "")).strip()
            advice = str(parsed.get("advice", "")).strip()
            if not overview or not advice:
                raise ValueError("LLM 输出缺字段")
        except Exception as e:
            logger.warning("LLM 生成失败，走降级模板: %s", e)
            source = "fallback"
            overview, advice = self._fallback_text(table)

        try:
            row = self.repo.create_summary(
                user.id, today, [c.model_dump() for c in table], overview, advice, source,
            )
        except IntegrityError:
            self.db.rollback()
            row = self.repo.get_summary(user.id, today)
            if not row:
                raise
        return DailySummaryOut(
            date=today,
            table=[SummaryCategory(**c) for c in row.table_json or []],
            ai_overview=row.ai_overview,
            ai_advice=row.ai_advice,
            source=row.source,
            generated_at=row.generated_at,
        )

    # ── 降级模板 ──────────────────────────────────────────────────
    @staticmethod
    def _fallback_text(table: list[SummaryCategory]) -> tuple[str, str]:
        def get(cat: str, label: str) -> str:
            for c in table:
                if c.category == cat:
                    for item in c.items:
                        if item.label == label:
                            return item.value
            return "0"

        def num(s: str) -> int:
            import re

            m = re.search(r"\d+", s)
            return int(m.group()) if m else 0

        review = get("单词", "今日复习旧词数")
        new = get("单词", "今日新词数")
        acc = get("单词", "测试正确率")
        read = get("阅读", "阅读文章")
        lookup = get("阅读", "划词查询")
        total_min = get("综合", "全站学习时长")
        streak = get("单词", "连续打卡天数")

        overview = f"你今日共学习 {total_min}，复习旧词 {num(review)} 个、新学 {num(new)} 个，完成测试正确率 {acc}；阅读 {read} 篇文章，累计查词 {num(lookup)} 次，已连续打卡 {streak}。"

        # 分类建议
        fill_acc = get("单词", "填空正确率")
        if num(fill_acc) < 60:
            advice = "你的填空拼写正确率偏低，明日优先用「单词填空」模式专项训练拼写，反复巩固今日新增生词，减少拼写错误。"
        elif num(lookup) >= 10:
            advice = "阅读时查词次数较多，建议先背完对应词库单词再阅读，降低生词阻力，提升阅读流畅度。"
        elif num(acc) >= 70:
            advice = "各项数据均衡、正确率高，保持当前学习节奏，可适当增加每日新词量加速积累。"
        else:
            advice = "今日学习时长较温和，建议拆分碎片时间完成每日基础单词任务，保持打卡连贯性。"

        return overview, advice

    # ── 辅助 ──────────────────────────────────────────────────────
    def _checkin_stats(self, user: User) -> dict:
        from datetime import timedelta

        dates = self.repo.list_checkin_dates(user.id)
        date_set = set(dates)
        streak = 0
        d = date.today()
        if d not in date_set:
            d -= timedelta(days=1)
        while d in date_set:
            streak += 1
            d -= timedelta(days=1)
        return {"streak_days": streak, "total_days": len(dates), "today_done": date.today() in date_set}
