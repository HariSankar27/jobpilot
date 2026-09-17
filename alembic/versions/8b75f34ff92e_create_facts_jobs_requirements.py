"""create facts, jobs, requirements

Revision ID: 8b75f34ff92e
Revises:
Create Date: 2026-09-18

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

from alembic import op

revision = "8b75f34ff92e"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "facts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("org", sa.String()),
        sa.Column("role", sa.String()),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("skills", ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("metrics", ARRAY(sa.String()), nullable=False, server_default="{}"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("external_id", sa.String()),
        sa.Column("company", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("location", sa.String()),
        sa.Column("url", sa.String()),
        sa.Column("description_text", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False, unique=True),
    )
    op.create_table(
        "requirements",
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), primary_key=True),
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("skills", ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("source_quote", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("requirements")
    op.drop_table("jobs")
    op.drop_table("facts")
