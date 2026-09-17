from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.models import Fact, JobPosting, Requirement
from .tables import FactRow, JobRow, RequirementRow


async def import_facts(session: AsyncSession, facts: list[Fact]) -> None:
    for fact in facts:
        await session.merge(FactRow(**fact.model_dump()))


async def upsert_job(session: AsyncSession, posting: JobPosting) -> JobRow:
    existing = (
        await session.execute(select(JobRow).where(JobRow.content_hash == posting.content_hash))
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    row = JobRow(**posting.model_dump())
    session.add(row)
    await session.flush()
    return row


async def replace_requirements(
    session: AsyncSession, job_id: str, requirements: list[Requirement]
) -> None:
    await session.execute(delete(RequirementRow).where(RequirementRow.job_id == job_id))
    for req in requirements:
        session.add(RequirementRow(job_id=job_id, **req.model_dump()))
