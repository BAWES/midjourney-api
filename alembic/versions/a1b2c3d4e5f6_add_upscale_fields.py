"""add upscale fields

Revision ID: a1b2c3d4e5f6
Revises: e6de2c77be7c
Create Date: 2026-02-22 17:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e6de2c77be7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add UPSCALING enum value, image_urls and upscale_count columns."""
    # Add UPSCALING to taskstatus enum
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'UPSCALING' AFTER 'PROCESSING'")

    # Add image_urls JSON column
    op.add_column("tasks", sa.Column("image_urls", sa.JSON(), nullable=True))

    # Add upscale_count integer column with default 1
    op.add_column(
        "tasks",
        sa.Column("upscale_count", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    """Remove upscale fields (enum value removal requires recreation)."""
    op.drop_column("tasks", "upscale_count")
    op.drop_column("tasks", "image_urls")
    # Note: PostgreSQL does not support removing enum values directly.
    # To fully downgrade, you would need to recreate the enum type.
