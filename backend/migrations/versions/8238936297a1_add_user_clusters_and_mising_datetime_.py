"""add user.clusters and mising datetime fields

Revision ID: 8238936297a1
Revises: 66db43bbbd2b
Create Date: 2024-03-25 22:10:34.961850

"""

from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "8238936297a1"
down_revision: Union[str, None] = "66db43bbbd2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "feed",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=datetime.now(tz=timezone.utc).isoformat(),
        ),
    )
    op.add_column(
        "feed",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=datetime.now(tz=timezone.utc).isoformat(),
        ),
    )
    op.drop_column("feed", "updated")
    op.add_column(
        "user",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=datetime.now(tz=timezone.utc).isoformat(),
        ),
    )
    op.add_column(
        "user",
        sa.Column("clusters", sqlmodel.sql.sqltypes.AutoString(), nullable=True),  # type: ignore[attr-defined]
    )
    op.add_column(
        "user", sa.Column("clusters_updated_at", sa.DateTime(), nullable=True)
    )
    op.drop_column("user", "first_request")
    op.add_column(
        "userarticlelink",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=datetime.now(tz=timezone.utc).isoformat(),
        ),
    )
    op.add_column(
        "userfeedlink",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=datetime.now(tz=timezone.utc).isoformat(),
        ),
    )


def downgrade() -> None:
    op.drop_column("userfeedlink", "created_at")
    op.drop_column("userarticlelink", "created_at")
    op.add_column(
        "user",
        sa.Column(
            "first_request",
            sa.DATETIME(),
            nullable=False,
            server_default=datetime.now(tz=timezone.utc).isoformat(),
        ),
    )
    op.drop_column("user", "clusters_updated_at")
    op.drop_column("user", "clusters")
    op.drop_column("user", "created_at")
    op.add_column(
        "feed",
        sa.Column(
            "updated",
            sa.DATETIME(),
            nullable=False,
            server_default=datetime.now(tz=timezone.utc).isoformat(),
        ),
    )
    op.drop_column("feed", "updated_at")
    op.drop_column("feed", "created_at")
