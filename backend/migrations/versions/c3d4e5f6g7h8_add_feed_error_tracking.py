"""add feed error tracking fields

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-02-03 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "feed",
        sa.Column(
            "consecutive_failures", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "feed",
        sa.Column("last_error", sa.String(), nullable=True),
    )
    op.add_column(
        "feed",
        sa.Column("is_disabled", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "feed",
        sa.Column("original_url", sa.String(), nullable=True),
    )
    op.create_index(op.f("ix_feed_is_disabled"), "feed", ["is_disabled"], unique=False)
    op.create_index(
        op.f("ix_feed_original_url"), "feed", ["original_url"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_feed_original_url"), table_name="feed")
    op.drop_index(op.f("ix_feed_is_disabled"), table_name="feed")
    op.drop_column("feed", "original_url")
    op.drop_column("feed", "is_disabled")
    op.drop_column("feed", "last_error")
    op.drop_column("feed", "consecutive_failures")
