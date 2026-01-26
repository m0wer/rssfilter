"""add performance indexes

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-26 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f("ix_article_updated"), "article", ["updated"], unique=False)
    op.create_index(op.f("ix_article_pub_date"), "article", ["pub_date"], unique=False)
    op.create_index(
        op.f("ix_user_last_request"), "user", ["last_request"], unique=False
    )
    op.create_index(op.f("ix_feed_updated_at"), "feed", ["updated_at"], unique=False)
    op.create_index(
        op.f("ix_userarticlelink_article_id"),
        "userarticlelink",
        ["article_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_userfeedlink_feed_id"), "userfeedlink", ["feed_id"], unique=False
    )
    op.create_index(
        op.f("ix_userfeedlink_user_id"), "userfeedlink", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_userfeedlink_user_id"), table_name="userfeedlink")
    op.drop_index(op.f("ix_userfeedlink_feed_id"), table_name="userfeedlink")
    op.drop_index(op.f("ix_userarticlelink_article_id"), table_name="userarticlelink")
    op.drop_index(op.f("ix_feed_updated_at"), table_name="feed")
    op.drop_index(op.f("ix_user_last_request"), table_name="user")
    op.drop_index(op.f("ix_article_pub_date"), table_name="article")
    op.drop_index(op.f("ix_article_updated"), table_name="article")
