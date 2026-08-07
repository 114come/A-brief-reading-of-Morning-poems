"""add daily reading

Revision ID: d0e1f2a3b4c5
Revises: da0e1f2a3b4c5
Create Date: 2026-08-06 09:00:00

每日一读：阅读文章加 题材/中文翻译/关键词/发布日期；新增 user_daily_reading 任务表、
reading_word_blacklist 黑名单表；旧阅读数据整体替换（删除旧文章/笔记/收藏）。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'da0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ── 阅读文章加列 ──────────────────────────────────────────────
    op.add_column("english_reading_articles", sa.Column("content_cn", sa.Text(), nullable=True))
    op.add_column("english_reading_articles", sa.Column("topic", sa.String(length=20), nullable=True))
    op.add_column("english_reading_articles", sa.Column("publish_date", sa.Date(), nullable=True))
    op.add_column("english_reading_articles", sa.Column("keywords", sa.JSON(), nullable=True))
    op.create_unique_constraint(
        "uq_english_articles_tenant_date_level_topic",
        "english_reading_articles",
        ["tenant_id", "publish_date", "level", "topic"],
    )

    # ── 旧阅读数据整体替换 ────────────────────────────────────────
    op.execute("DELETE FROM reading_notes")
    op.execute("DELETE FROM user_collections WHERE item_type = 'reading'")
    op.execute("DELETE FROM english_reading_articles")

    # ── 每日一读任务表 ────────────────────────────────────────────
    op.create_table(
        "user_daily_reading",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reading_date", sa.Date(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("wrong_word_ids", sa.JSON(), nullable=False),
        sa.Column("new_word_ids", sa.JSON(), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["english_reading_articles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "reading_date", name="uq_user_daily_reading_uid_date"),
    )
    op.create_index("ix_user_daily_reading_user_id", "user_daily_reading", ["user_id"])
    op.create_index("ix_user_daily_reading_article_id", "user_daily_reading", ["article_id"])

    # ── 阅读生词黑名单 ────────────────────────────────────────────
    op.create_table(
        "reading_word_blacklist",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("word_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["word_id"], ["english_words.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "word_id", name="uq_reading_blacklist_uid_word"),
    )
    op.create_index("ix_reading_word_blacklist_user_id", "reading_word_blacklist", ["user_id"])
    op.create_index("ix_reading_word_blacklist_word_id", "reading_word_blacklist", ["word_id"])

    # ── 难度设置 ──────────────────────────────────────────────────
    op.add_column("user_word_settings", sa.Column("reading_level_mode", sa.String(length=10), server_default="auto", nullable=False))
    op.add_column("user_word_settings", sa.Column("reading_manual_level", sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_word_settings", "reading_manual_level")
    op.drop_column("user_word_settings", "reading_level_mode")
    op.drop_index("ix_reading_word_blacklist_word_id", table_name="reading_word_blacklist")
    op.drop_index("ix_reading_word_blacklist_user_id", table_name="reading_word_blacklist")
    op.drop_table("reading_word_blacklist")
    op.drop_index("ix_user_daily_reading_article_id", table_name="user_daily_reading")
    op.drop_index("ix_user_daily_reading_user_id", table_name="user_daily_reading")
    op.drop_table("user_daily_reading")
    op.drop_constraint("uq_english_articles_tenant_date_level_topic", "english_reading_articles", type_="unique")
    op.drop_column("english_reading_articles", "keywords")
    op.drop_column("english_reading_articles", "publish_date")
    op.drop_column("english_reading_articles", "topic")
    op.drop_column("english_reading_articles", "content_cn")
