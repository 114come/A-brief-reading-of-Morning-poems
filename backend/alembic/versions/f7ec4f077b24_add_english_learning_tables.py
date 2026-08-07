"""add english learning tables

Revision ID: f7ec4f077b24
Revises: c0d1e2f3a4b5
Create Date: 2026-08-01 12:05:10.878343

只新增英语学习相关表 + users.nickname/avatar 两列，不改动既有表结构。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'f7ec4f077b24'
down_revision: Union[str, Sequence[str], None] = 'c0d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('english_listening_materials',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('tenant_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('audio_url', sa.String(length=500), nullable=True),
    sa.Column('transcript', sa.Text(), nullable=False),
    sa.Column('level', sa.String(length=20), nullable=True),
    sa.Column('duration_seconds', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_english_listening_materials_tenant_id'), 'english_listening_materials', ['tenant_id'], unique=False)
    op.create_table('english_reading_articles',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('tenant_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('content', sa.Text().with_variant(mysql.MEDIUMTEXT(), 'mysql'), nullable=False),
    sa.Column('level', sa.String(length=20), nullable=True),
    sa.Column('word_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_english_reading_articles_tenant_id'), 'english_reading_articles', ['tenant_id'], unique=False)
    op.create_table('english_words',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('tenant_id', sa.Integer(), nullable=False),
    sa.Column('word', sa.String(length=100), nullable=False),
    sa.Column('phonetic', sa.String(length=100), nullable=True),
    sa.Column('definition', sa.Text(), nullable=False),
    sa.Column('example', sa.Text(), nullable=True),
    sa.Column('level', sa.String(length=20), nullable=True),
    sa.Column('tags', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'word', name='uq_english_words_tenant_word')
    )
    op.create_index(op.f('ix_english_words_tenant_id'), 'english_words', ['tenant_id'], unique=False)
    op.create_table('checkin_records',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('checkin_date', sa.Date(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'checkin_date', name='uq_checkin_records_user_date')
    )
    op.create_index(op.f('ix_checkin_records_user_id'), 'checkin_records', ['user_id'], unique=False)
    op.create_table('reading_notes',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('article_id', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['article_id'], ['english_reading_articles.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reading_notes_article_id'), 'reading_notes', ['article_id'], unique=False)
    op.create_index(op.f('ix_reading_notes_user_id'), 'reading_notes', ['user_id'], unique=False)
    op.create_table('user_collections',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('item_type', sa.String(length=20), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'item_type', 'item_id', name='uq_user_collections_user_type_item')
    )
    op.create_index(op.f('ix_user_collections_user_id'), 'user_collections', ['user_id'], unique=False)
    op.create_table('user_wordbook',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('word_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['word_id'], ['english_words.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'word_id', name='uq_user_wordbook_user_word')
    )
    op.create_index(op.f('ix_user_wordbook_user_id'), 'user_wordbook', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_wordbook_word_id'), 'user_wordbook', ['word_id'], unique=False)
    op.add_column('users', sa.Column('nickname', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('avatar', sa.String(length=255), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'avatar')
    op.drop_column('users', 'nickname')
    op.drop_index(op.f('ix_user_wordbook_word_id'), table_name='user_wordbook')
    op.drop_index(op.f('ix_user_wordbook_user_id'), table_name='user_wordbook')
    op.drop_table('user_wordbook')
    op.drop_index(op.f('ix_user_collections_user_id'), table_name='user_collections')
    op.drop_table('user_collections')
    op.drop_index(op.f('ix_reading_notes_user_id'), table_name='reading_notes')
    op.drop_index(op.f('ix_reading_notes_article_id'), table_name='reading_notes')
    op.drop_table('reading_notes')
    op.drop_index(op.f('ix_checkin_records_user_id'), table_name='checkin_records')
    op.drop_table('checkin_records')
    op.drop_index(op.f('ix_english_words_tenant_id'), table_name='english_words')
    op.drop_table('english_words')
    op.drop_index(op.f('ix_english_reading_articles_tenant_id'), table_name='english_reading_articles')
    op.drop_table('english_reading_articles')
    op.drop_index(op.f('ix_english_listening_materials_tenant_id'), table_name='english_listening_materials')
    op.drop_table('english_listening_materials')
    # ### end Alembic commands ###
