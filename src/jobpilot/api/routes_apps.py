import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..db.repo import create_application
from ..db.session import async_session
from ..db.tables import ApplicationRow, FactRow, JobRow, RequirementRow
from ..domain.fit import fit_score, rubric_score
from ..domain.models import Fact, Requirement
from ..domain.tracker import coverage, gap_report, transition

router = APIRouter()


class CreateApplicationRequest(BaseModel):
    job_id: str
    resume_version_id: str


class UpdateStatusRequest(BaseModel):
    status: str


@router.post("/applications", status_code=201)
async def create_application_route(payload: CreateApplicationRequest) -> dict:
    async with async_session() as session:
        row = await create_application(session, payload.job_id, payload.resume_version_id)
        await session.commit()
        return {"id": row.id, "job_id": row.job_id, "status": row.status}


@router.patch("/applications/{application_id}")
async def update_application_status(application_id: str, payload: UpdateStatusRequest) -> dict:
    async with async_session() as session:
        app_row = await session.get(ApplicationRow, application_id)
        if app_row is None:
            raise HTTPException(404, "Application not found")
        try:
            app_row.status = transition(app_row.status, payload.status)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        await session.commit()
        return {"id": app_row.id, "status": app_row.status}


@router.get("/jobs/{job_id}/fit")
async def get_job_fit(job_id: str) -> dict:
    async with async_session() as session:
        job = await session.get(JobRow, job_id)
        if job is None:
            raise HTTPException(404, "Job not found")
        req_rows = (
            (await session.execute(select(RequirementRow).where(RequirementRow.job_id == job_id)))
            .scalars()
            .all()
        )
        fact_rows = (await session.execute(select(FactRow))).scalars().all()

    requirements = [
        Requirement(id=r.id, kind=r.kind, text=r.text, skills=r.skills, source_quote=r.source_quote)
        for r in req_rows
    ]
    facts = [
        Fact(
            id=f.id,
            kind=f.kind,
            org=f.org,
            role=f.role,
            text=f.text,
            skills=f.skills,
            metrics=f.metrics,
        )
        for f in fact_rows
    ]

    coverage_score, _ = coverage(requirements, facts)
    verdict = await rubric_score(job.description_text, json.dumps([f.model_dump() for f in facts]))

    return {
        "coverage": coverage_score,
        "rubric": verdict.score,
        "rubric_reason": verdict.reason,
        "fit_score": fit_score(coverage_score, verdict.score),
        "gaps": gap_report(requirements, facts),
    }
