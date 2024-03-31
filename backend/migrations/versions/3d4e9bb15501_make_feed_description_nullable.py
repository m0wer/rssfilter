"""make feed.description nullable

Revision ID: 3d4e9bb15501
Revises: 8238936297a1
Create Date: 2024-03-31 19:40:25.956478

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3d4e9bb15501"
down_revision: Union[str, None] = "8238936297a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # add new column to store the values of feed.description where it's nullable
    # then remove the old column and then rename the new one to description
    # because sqlite doesn't support directly changing the column's constrains
    op.add_column("feed", sa.Column("description_new", sa.VARCHAR(), nullable=True))
    op.execute("UPDATE feed SET description_new = description")
    op.drop_column("feed", "description")
    op.add_column("feed", sa.Column("description", sa.VARCHAR(), nullable=True))
    op.execute("UPDATE feed SET description = description_new")
    op.drop_column("feed", "description_new")


def downgrade() -> None:
    op.add_column("feed", sa.Column("description_new", sa.VARCHAR(), nullable=True))
    op.execute("UPDATE feed SET description_new = description")
    op.drop_column("feed", "description")
    op.add_column("feed", sa.Column("description", sa.VARCHAR(), nullable=False))
    # set the feed description to its title if the description was null
    op.execute("UPDATE feed SET description = title WHERE description IS NULL")
    op.execute("UPDATE feed SET description = description_new")
    op.drop_column("feed", "description_new")
