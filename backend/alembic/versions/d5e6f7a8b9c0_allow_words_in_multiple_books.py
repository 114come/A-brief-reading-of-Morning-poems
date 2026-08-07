"""allow words in multiple books

Revision ID: d5e6f7a8b9c0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-01 17:30:00

每本词书保存完整的本级大纲词表，同一单词可出现在多本书。
唯一约束由 (tenant_id, word) 改为 (tenant_id, book_id, word)。
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("uq_english_words_tenant_word", "english_words", type_="unique")
    op.create_unique_constraint(
        "uq_english_words_tenant_book_word", "english_words", ["tenant_id", "book_id", "word"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_english_words_tenant_book_word", "english_words", type_="unique")
    op.create_unique_constraint("uq_english_words_tenant_word", "english_words", ["tenant_id", "word"])
