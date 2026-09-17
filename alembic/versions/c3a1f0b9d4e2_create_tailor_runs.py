"""create tailor_runs

Revision ID: c3a1f0b9d4e2
Revises: 8b75f34ff92e
Create Date: 2026-09-18

"""

import sqlalchemy as sa

from alembic import op

revision = "c3a1f0b9d4e2"
down_revision = "8b75f34ff92e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tailor_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("trace_id", sa.String(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("tailor_runs")
