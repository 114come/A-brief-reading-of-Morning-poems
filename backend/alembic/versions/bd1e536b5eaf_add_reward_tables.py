"""add reward tables

Revision ID: bd1e536b5eaf
Revises: d0e1f2a3b4c5
Create Date: 2026-08-13 22:21:32.483871

晨光奖励系统：新增积分余额 / 积分流水 / 已解锁奖励 / 奖励设置 4 张表。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bd1e536b5eaf'
down_revision: Union[str, Sequence[str], None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ── 积分余额（每人一条）────────────────────────────────────────
    op.create_table(
        "reward_user_points",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False),
        sa.Column("total_earned", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_reward_user_points_user"),
    )
    op.create_index("ix_reward_user_points_user_id", "reward_user_points", ["user_id"])

    # ── 积分流水 ───────────────────────────────────────────────────
    op.create_table(
        "reward_point_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=30), nullable=False),
        sa.Column("ref_date", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "reason", "ref_date", name="uq_reward_logs_uid_reason_date"),
    )
    op.create_index("ix_reward_point_logs_user_id", "reward_point_logs", ["user_id"])

    # ── 已解锁奖励 ─────────────────────────────────────────────────
    op.create_table(
        "reward_unlocks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_key", sa.String(length=50), nullable=False),
        sa.Column("unlock_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "item_key", name="uq_reward_unlocks_uid_item"),
    )
    op.create_index("ix_reward_unlocks_user_id", "reward_unlocks", ["user_id"])

    # ── 奖励设置 ───────────────────────────────────────────────────
    op.create_table(
        "reward_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("equipped_title", sa.String(length=50), nullable=True),
        sa.Column("equipped_decor", sa.String(length=50), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_reward_settings_user"),
    )
    op.create_index("ix_reward_settings_user_id", "reward_settings", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_reward_settings_user_id", table_name="reward_settings")
    op.drop_table("reward_settings")
    op.drop_index("ix_reward_unlocks_user_id", table_name="reward_unlocks")
    op.drop_table("reward_unlocks")
    op.drop_index("ix_reward_point_logs_user_id", table_name="reward_point_logs")
    op.drop_table("reward_point_logs")
    op.drop_index("ix_reward_user_points_user_id", table_name="reward_user_points")
    op.drop_table("reward_user_points")
