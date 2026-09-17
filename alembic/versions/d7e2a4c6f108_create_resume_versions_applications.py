"""create resume_versions, applications

Revision ID: d7e2a4c6f108
Revises: c3a1f0b9d4e2
Create Date: 2026-09-18

"""

import sqlalchemy as sa

from alembic import op

revision = "d7e2a4c6f108"
down_revision = "c3a1f0b9d4e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_versions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("tailor_runs.id"), nullable=False),
        sa.Column("pdf_path", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "applications",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column(
            "resume_version_id", sa.String(), sa.ForeignKey("resume_versions.id"), nullable=False
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="saved"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("applications")
    op.drop_table("resume_versions")
