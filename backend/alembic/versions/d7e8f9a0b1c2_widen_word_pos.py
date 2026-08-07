"""widen word pos column

Revision ID: d7e8f9a0b1c2
Revises: d6e7f8a9b0c1
Create Date: 2026-08-01 18:40:00

pos 列从 30 加宽到 100，容纳词典 API 返回的多词性字符串（如 "verb/noun/adjective"）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, Sequence[str], None] = 'd6e7f8a9b0c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("english_words", "pos", existing_type=sa.String(length=30), type_=sa.String(length=100))


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("english_words", "pos", existing_type=sa.String(length=100), type_=sa.String(length=30))
