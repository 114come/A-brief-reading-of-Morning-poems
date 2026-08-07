"""remove listening feature

Revision ID: da0e1f2a3b4c5
Revises: d9e0f1a2b3c4
Create Date: 2026-08-02 13:00:00

删除听力功能：english_listening_materials 表 + user_daily_activity 的听力/听写列。
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'da0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'd9e0f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("english_listening_materials")
    op.drop_column("user_daily_activity", "listening_duration_sec")
    op.drop_column("user_daily_activity", "listening_item_ids")
    op.drop_column("user_daily_activity", "dictation_sentences")
    op.drop_column("user_daily_activity", "dictation_wrong_words")


def downgrade() -> None:
    """Downgrade schema."""
    import sqlalchemy as sa

    op.add_column("user_daily_activity", sa.Column("dictation_wrong_words", sa.Integer(), nullable=False))
    op.add_column("user_daily_activity", sa.Column("dictation_sentences", sa.Integer(), nullable=False))
    op.add_column("user_daily_activity", sa.Column("listening_item_ids", sa.JSON(), nullable=False))
    op.add_column("user_daily_activity", sa.Column("listening_duration_sec", sa.Integer(), nullable=False))
    op.create_table(
        "english_listening_materials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("audio_url", sa.String(length=500), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
