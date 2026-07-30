"""add agent_memories table and memory_config to agents

Revision ID: b0c1d2e3f4a5
Revises: a8b9c0d1e2f3
Create Date: 2026-07-30 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b0c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = 'a8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add memory_config column to agents table
    op.add_column('agents',
        sa.Column('memory_config', sa.Text(), nullable=False, server_default='{}',
                  comment='JSON: {"enabled": true, "short_term_interval": 5, "long_term_enabled": true}')
    )

    # Create agent_memories table
    op.create_table('agent_memories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=True),
        sa.Column('memory_type', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata_', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_memories_tenant_id'), 'agent_memories', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_agent_memories_agent_id'), 'agent_memories', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_memories_conversation_id'), 'agent_memories', ['conversation_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_agent_memories_conversation_id'), table_name='agent_memories')
    op.drop_index(op.f('ix_agent_memories_agent_id'), table_name='agent_memories')
    op.drop_index(op.f('ix_agent_memories_tenant_id'), table_name='agent_memories')
    op.drop_table('agent_memories')
    op.drop_column('agents', 'memory_config')
