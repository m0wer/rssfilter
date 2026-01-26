"""add user is_frozen and frozen_at fields

Revision ID: a1b2c3d4e5f6
Revises: 3d4e9bb15501
Create Date: 2025-01-26 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "3d4e9bb15501"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("is_frozen", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user",
        sa.Column("frozen_at", sa.DateTime(), nullable=True),
    )
    op.create_index(op.f("ix_user_is_frozen"), "user", ["is_frozen"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_is_frozen"), table_name="user")
    op.drop_column("user", "frozen_at")
    op.drop_column("user", "is_frozen")
