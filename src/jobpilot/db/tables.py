import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class FactRow(Base):
    __tablename__ = "facts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    org: Mapped[str | None] = mapped_column(String)
    role: Mapped[str | None] = mapped_column(String)
    text: Mapped[str] = mapped_column(String, nullable=False)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    metrics: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)


class JobRow(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String)
    company: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)
    description_text: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    requirements: Mapped[list["RequirementRow"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class RequirementRow(Base):
    __tablename__ = "requirements"

    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    source_quote: Mapped[str] = mapped_column(String, nullable=False)

    job: Mapped[JobRow] = relationship(back_populates="requirements")


class TailorRunRow(Base):
    __tablename__ = "tailor_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # == LangGraph thread_id
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    trace_id: Mapped[str] = mapped_column(String, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class ResumeVersionRow(Base):
    __tablename__ = "resume_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("tailor_runs.id"), nullable=False)
    pdf_path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApplicationRow(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    resume_version_id: Mapped[str] = mapped_column(ForeignKey("resume_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="saved")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
