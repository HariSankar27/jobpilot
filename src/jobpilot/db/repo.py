from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.models import Fact, JobPosting, Requirement
from .tables import ApplicationRow, FactRow, JobRow, RequirementRow, ResumeVersionRow


async def import_facts(session: AsyncSession, facts: list[Fact]) -> None:
    for fact in facts:
        await session.merge(FactRow(**fact.model_dump()))


async def upsert_job(session: AsyncSession, posting: JobPosting) -> tuple[JobRow, bool]:
    existing = (
        await session.execute(select(JobRow).where(JobRow.content_hash == posting.content_hash))
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False
    row = JobRow(**posting.model_dump())
    session.add(row)
    await session.flush()
    return row, True


async def replace_requirements(
    session: AsyncSession, job_id: str, requirements: list[Requirement]
) -> None:
    await session.execute(delete(RequirementRow).where(RequirementRow.job_id == job_id))
    for req in requirements:
        session.add(RequirementRow(job_id=job_id, **req.model_dump()))


async def create_resume_version(
    session: AsyncSession, run_id: str, pdf_path: str
) -> ResumeVersionRow:
    row = ResumeVersionRow(run_id=run_id, pdf_path=pdf_path)
    session.add(row)
    await session.flush()
    return row


async def create_application(
    session: AsyncSession, job_id: str, resume_version_id: str
) -> ApplicationRow:
    row = ApplicationRow(job_id=job_id, resume_version_id=resume_version_id, status="saved")
    session.add(row)
    await session.flush()
    return row
