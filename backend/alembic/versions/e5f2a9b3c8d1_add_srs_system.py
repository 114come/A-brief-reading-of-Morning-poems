"""add srs word learning system

Revision ID: e5f2a9b3c8d1
Revises: f7ec4f077b24
Create Date: 2026-08-01 14:40:00

新增 SRS 背单词系统：词书表、单词归属词书、用户记忆表、设置表、日会话表、
日统计表；生词本改造为纯列表（加 book_id、去 status）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5f2a9b3c8d1'
down_revision: Union[str, Sequence[str], None] = 'f7ec4f077b24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BOOKS = [
    ("primary_school", "中小学", 1),
    ("high_school", "高中", 2),
    ("cet4", "四级", 3),
    ("cet6", "六级", 4),
    ("kaoyan", "考研", 5),
    ("daily", "日常口语", 6),
]


def upgrade() -> None:
    # 1) word_books 表 + 6 本词书
    op.create_table(
        "word_books",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_word_books_tenant_code"),
    )
    op.create_index(op.f("ix_word_books_tenant_id"), "word_books", ["tenant_id"], unique=False)
    # 为已存在的 english 租户（code='english'）插入词书
    conn = op.get_bind()
    tenant_rows = conn.execute(sa.text("SELECT id FROM tenants WHERE code = 'english'")).fetchall()
    for (tid,) in tenant_rows:
        for code, name, sort_order in _BOOKS:
            conn.execute(
                sa.text(
                    "INSERT INTO word_books (tenant_id, code, name, sort_order, created_at, updated_at) "
                    "VALUES (:tid, :code, :name, :sort_order, NOW(), NOW()) "
                    "ON DUPLICATE KEY UPDATE name = VALUES(name), sort_order = VALUES(sort_order)"
                ),
                {"tid": tid, "code": code, "name": name, "sort_order": sort_order},
            )

    # 2) english_words 加列 + 回填 book_id + NOT NULL
    op.add_column("english_words", sa.Column("book_id", sa.Integer(), nullable=True))
    op.add_column("english_words", sa.Column("example2", sa.Text(), nullable=True))
    op.add_column("english_words", sa.Column("phrase", sa.String(length=200), nullable=True))
    conn.execute(
        sa.text(
            "UPDATE english_words w "
            "JOIN word_books b ON b.code = (CASE WHEN w.level = 'CET6' THEN 'cet6' ELSE 'cet4' END) "
            "AND b.tenant_id = w.tenant_id "
            "SET w.book_id = b.id"
        )
    )
    op.alter_column("english_words", "book_id", existing_type=sa.Integer(), nullable=False)
    op.create_index(op.f("ix_english_words_book_id"), "english_words", ["book_id"], unique=False)
    op.create_foreign_key(None, "english_words", "word_books", ["book_id"], ["id"])

    # 3) 用户记忆 / 设置 / 日会话 / 日统计
    op.create_table(
        "user_word_memory",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("word_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.SmallInteger(), nullable=False),
        sa.Column("next_review_date", sa.Date(), nullable=True),
        sa.Column("current_interval", sa.Integer(), nullable=False),
        sa.Column("wrong_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["word_books.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["word_id"], ["english_words.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "word_id", "book_id", name="uq_user_word_memory_uid_word_book"),
    )
    op.create_index(op.f("ix_user_word_memory_user_id"), "user_word_memory", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_word_memory_book_id"), "user_word_memory", ["book_id"], unique=False)
    op.create_index(op.f("ix_user_word_memory_word_id"), "user_word_memory", ["word_id"], unique=False)

    op.create_table(
        "user_word_settings",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("target", sa.String(length=40), nullable=False),
        sa.Column("daily_new_words", sa.Integer(), nullable=False),
        sa.Column("pronunciation", sa.String(length=10), nullable=False),
        sa.Column("autoplay", sa.Boolean(), nullable=False),
        sa.Column("onboarding_done", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["word_books.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "user_daily_session",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["word_books.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "book_id", "session_date", name="uq_user_daily_session_uid_book_date"),
    )
    op.create_index(op.f("ix_user_daily_session_user_id"), "user_daily_session", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_daily_session_book_id"), "user_daily_session", ["book_id"], unique=False)

    op.create_table(
        "user_daily_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("study_date", sa.Date(), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False),
        sa.Column("new_count", sa.Integer(), nullable=False),
        sa.Column("wrong_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["word_books.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "book_id", "study_date", name="uq_user_daily_stats_uid_book_date"),
    )
    op.create_index(op.f("ix_user_daily_stats_user_id"), "user_daily_stats", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_daily_stats_book_id"), "user_daily_stats", ["book_id"], unique=False)

    # 4) 生词本改造：加 book_id、删 status、改唯一约束
    op.add_column("user_wordbook", sa.Column("book_id", sa.Integer(), nullable=True))
    conn.execute(
        sa.text(
            "UPDATE user_wordbook uw JOIN english_words w ON uw.word_id = w.id SET uw.book_id = w.book_id"
        )
    )
    op.drop_constraint("uq_user_wordbook_user_word", "user_wordbook", type_="unique")
    op.drop_column("user_wordbook", "status")
    op.alter_column("user_wordbook", "book_id", existing_type=sa.Integer(), nullable=False)
    op.create_index(op.f("ix_user_wordbook_book_id"), "user_wordbook", ["book_id"], unique=False)
    op.create_foreign_key(None, "user_wordbook", "word_books", ["book_id"], ["id"])
    op.create_unique_constraint("uq_user_wordbook_uid_word_book", "user_wordbook", ["user_id", "word_id", "book_id"])


def downgrade() -> None:
    op.drop_constraint("uq_user_wordbook_uid_word_book", "user_wordbook", type_="unique")
    op.drop_constraint(None, "user_wordbook", type_="foreignkey")
    op.drop_index(op.f("ix_user_wordbook_book_id"), table_name="user_wordbook")
    op.add_column("user_wordbook", sa.Column("status", sa.String(length=20), nullable=False, server_default="new"))
    op.create_unique_constraint("uq_user_wordbook_user_word", "user_wordbook", ["user_id", "word_id"])
    op.drop_column("user_wordbook", "book_id")

    op.drop_index(op.f("ix_user_daily_stats_book_id"), table_name="user_daily_stats")
    op.drop_index(op.f("ix_user_daily_stats_user_id"), table_name="user_daily_stats")
    op.drop_table("user_daily_stats")
    op.drop_index(op.f("ix_user_daily_session_book_id"), table_name="user_daily_session")
    op.drop_index(op.f("ix_user_daily_session_user_id"), table_name="user_daily_session")
    op.drop_table("user_daily_session")
    op.drop_table("user_word_settings")
    op.drop_index(op.f("ix_user_word_memory_word_id"), table_name="user_word_memory")
    op.drop_index(op.f("ix_user_word_memory_book_id"), table_name="user_word_memory")
    op.drop_index(op.f("ix_user_word_memory_user_id"), table_name="user_word_memory")
    op.drop_table("user_word_memory")

    op.drop_constraint(None, "english_words", type_="foreignkey")
    op.drop_index(op.f("ix_english_words_book_id"), table_name="english_words")
    op.alter_column("english_words", "book_id", existing_type=sa.Integer(), nullable=True)
    op.drop_column("english_words", "phrase")
    op.drop_column("english_words", "example2")
    op.drop_column("english_words", "book_id")

    op.drop_index(op.f("ix_word_books_tenant_id"), table_name="word_books")
    op.drop_table("word_books")
