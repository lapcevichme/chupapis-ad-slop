"""Recoverable chat deletion."""

import sqlalchemy as sa

from alembic import op

revision = "91bc28e7a102"
down_revision = "0727e0138c95"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("chat_sessions") as batch:
        batch.add_column(sa.Column("archived_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("archived_campaign_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("chat_sessions") as batch:
        batch.drop_column("archived_campaign_id")
        batch.drop_column("archived_at")
