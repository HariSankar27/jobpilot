import hashlib

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..db.repo import replace_requirements, upsert_job
from ..db.session import async_session
from ..db.tables import JobRow, RequirementRow
from ..domain.models import JobPosting, Requirement
from ..graph.nodes import parse_job
from ..ingest.greenhouse import fetch_greenhouse
from ..ingest.lever import fetch_lever

router = APIRouter()


class CreateJobRequest(BaseModel):
    text: str | None = None
    greenhouse_board: str | None = None
    lever_site: str | None = None


async def _postings_for(payload: CreateJobRequest) -> list[JobPosting]:
    if payload.text:
        return [
            JobPosting(
                source="paste",
                company="unknown",
                title="Pasted posting",
                description_text=payload.text,
                content_hash=hashlib.sha256(payload.text.encode()).hexdigest(),
            )
        ]
    if payload.greenhouse_board:
        return await fetch_greenhouse(payload.greenhouse_board)
    if payload.lever_site:
        return await fetch_lever(payload.lever_site)
    raise HTTPException(422, "Provide text, greenhouse_board, or lever_site")


@router.post("/jobs")
async def create_jobs(payload: CreateJobRequest) -> list[dict]:
    postings = await _postings_for(payload)
    results = []
    async with async_session() as session:
        for posting in postings:
            job = await upsert_job(session, posting)
            parsed = await parse_job({"job_text": job.description_text})
            requirements = [Requirement(**r) for r in parsed["requirements"]]
            await replace_requirements(session, job.id, requirements)
            results.append({"id": job.id, "company": job.company, "title": job.title})
        await session.commit()
    return results


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    async with async_session() as session:
        job = await session.get(JobRow, job_id)
        if job is None:
            raise HTTPException(404, "Job not found")
        requirements = (
            (await session.execute(select(RequirementRow).where(RequirementRow.job_id == job_id)))
            .scalars()
            .all()
        )
    return {
        "id": job.id,
        "company": job.company,
        "title": job.title,
        "url": job.url,
        "requirements": [
            {"id": r.id, "kind": r.kind, "text": r.text, "source_quote": r.source_quote}
            for r in requirements
        ],
    }
