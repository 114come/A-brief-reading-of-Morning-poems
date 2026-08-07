"""add example cn translation columns

Revision ID: d8e9f0a1b2c3
Revises: d7e8f9a0b1c2
Create Date: 2026-08-02 10:00:00

english_words 增加例句中文翻译列，供题型E例句填空使用。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd8e9f0a1b2c3'
down_revision: Union[str, Sequence[str], None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("english_words", sa.Column("example_cn", sa.Text(), nullable=True))
    op.add_column("english_words", sa.Column("example2_cn", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("english_words", "example2_cn")
    op.drop_column("english_words", "example_cn")
