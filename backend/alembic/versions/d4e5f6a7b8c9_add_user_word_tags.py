"""add user word tags

Revision ID: d4e5f6a7b8c9
Revises: e5f2a9b3c8d1
Create Date: 2026-08-01 16:40:00

用户对单词的简单分类（查看词库 + 按类型背诵）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'e5f2a9b3c8d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_word_tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("word_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["word_books.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["word_id"], ["english_words.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "word_id", "book_id", name="uq_user_word_tags_uid_word_book"),
    )
    op.create_index(op.f("ix_user_word_tags_user_id"), "user_word_tags", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_word_tags_word_id"), "user_word_tags", ["word_id"], unique=False)
    op.create_index(op.f("ix_user_word_tags_book_id"), "user_word_tags", ["book_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_word_tags_book_id"), table_name="user_word_tags")
    op.drop_index(op.f("ix_user_word_tags_word_id"), table_name="user_word_tags")
    op.drop_index(op.f("ix_user_word_tags_user_id"), table_name="user_word_tags")
    op.drop_table("user_word_tags")
