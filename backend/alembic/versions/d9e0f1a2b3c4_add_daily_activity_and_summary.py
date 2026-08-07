"""add daily activity and summary tables

Revision ID: d9e0f1a2b3c4
Revises: d8e9f0a1b2c3
Create Date: 2026-08-02 11:30:00

AI 每日学习总结：用户每日学习活动埋点表 + AI 总结缓存表。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd9e0f1a2b3c4'
down_revision: Union[str, Sequence[str], None] = 'd8e9f0a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_daily_activity",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("word_study_sec", sa.Integer(), nullable=False),
        sa.Column("listening_duration_sec", sa.Integer(), nullable=False),
        sa.Column("listening_item_ids", sa.JSON(), nullable=False),
        sa.Column("dictation_sentences", sa.Integer(), nullable=False),
        sa.Column("dictation_wrong_words", sa.Integer(), nullable=False),
        sa.Column("reading_article_ids", sa.JSON(), nullable=False),
        sa.Column("reading_duration_sec", sa.Integer(), nullable=False),
        sa.Column("word_lookups", sa.Integer(), nullable=False),
        sa.Column("test_choice_questions", sa.Integer(), nullable=False),
        sa.Column("test_choice_correct", sa.Integer(), nullable=False),
        sa.Column("test_fill_questions", sa.Integer(), nullable=False),
        sa.Column("test_fill_correct", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "activity_date", name="uq_user_daily_activity_uid_date"),
    )
    op.create_index(op.f("ix_user_daily_activity_user_id"), "user_daily_activity", ["user_id"], unique=False)

    op.create_table(
        "user_daily_summary",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("summary_date", sa.Date(), nullable=False),
        sa.Column("table_json", sa.JSON(), nullable=False),
        sa.Column("ai_overview", sa.Text(), nullable=False),
        sa.Column("ai_advice", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "summary_date", name="uq_user_daily_summary_uid_date"),
    )
    op.create_index(op.f("ix_user_daily_summary_user_id"), "user_daily_summary", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_daily_summary_user_id"), table_name="user_daily_summary")
    op.drop_table("user_daily_summary")
    op.drop_index(op.f("ix_user_daily_activity_user_id"), table_name="user_daily_activity")
    op.drop_table("user_daily_activity")
