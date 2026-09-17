import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.templating import Jinja2Templates
from langgraph.types import Command
from sqlalchemy import select

from ..db.session import async_session
from ..db.tables import FactRow, JobRow, TailorRunRow
from ..domain.models import Fact, ReviewDecision

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "web" / "templates")
)


async def _load_facts(session) -> list[dict]:
    rows = (await session.execute(select(FactRow))).scalars().all()
    return [
        Fact(
            id=r.id,
            kind=r.kind,
            org=r.org,
            role=r.role,
            text=r.text,
            skills=r.skills,
            metrics=r.metrics,
        ).model_dump()
        for r in rows
    ]


async def _run_tailor(graph, thread_id: str, job_id: str, job_text: str, facts: list[dict]) -> None:
    await graph.ainvoke(
        {"job_id": job_id, "job_text": job_text, "facts": facts, "attempts": 0},
        config={"configurable": {"thread_id": thread_id}},
    )


@router.post("/jobs/{job_id}/tailor", status_code=202)
async def start_tailor(job_id: str, background_tasks: BackgroundTasks, request: Request) -> dict:
    async with async_session() as session:
        job = await session.get(JobRow, job_id)
        if job is None:
            raise HTTPException(404, "Job not found")
        facts = await _load_facts(session)
        thread_id = str(uuid.uuid4())
        session.add(
            TailorRunRow(
                id=thread_id, job_id=job_id, status="running", trace_id=thread_id, cost_usd=0.0
            )
        )
        await session.commit()

    background_tasks.add_task(
        _run_tailor, request.app.state.graph, thread_id, job_id, job.description_text, facts
    )
    return {"run_id": thread_id}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, request: Request) -> dict:
    graph = request.app.state.graph
    snapshot = await graph.aget_state({"configurable": {"thread_id": run_id}})
    if not snapshot.values:
        raise HTTPException(404, "Run not found")
    if snapshot.interrupts:
        return {"status": "needs_review", "review": snapshot.interrupts[0].value}
    if snapshot.next:
        return {"status": "running"}
    return {"status": "completed", "pdf_path": snapshot.values.get("pdf_path")}


@router.get("/runs/{run_id}/page")
async def run_page(run_id: str, request: Request):
    graph = request.app.state.graph
    snapshot = await graph.aget_state({"configurable": {"thread_id": run_id}})
    if not snapshot.values:
        raise HTTPException(404, "Run not found")
    if snapshot.interrupts:
        status = "needs_review"
    elif not snapshot.next:
        status = "completed"
    else:
        status = "running"
    return templates.TemplateResponse(
        request,
        "review.html",
        {
            "run_id": run_id,
            "status": status,
            "review": snapshot.interrupts[0].value if snapshot.interrupts else None,
            "pdf_path": snapshot.values.get("pdf_path"),
        },
    )


@router.post("/runs/{run_id}/review")
async def submit_review(run_id: str, decisions: list[ReviewDecision], request: Request) -> dict:
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": run_id}}
    result = await graph.ainvoke(Command(resume=[d.model_dump() for d in decisions]), config)
    snapshot = await graph.aget_state(config)

    if not snapshot.next:
        async with async_session() as session:
            run = await session.get(TailorRunRow, run_id)
            if run is not None:
                run.status = "completed"
                await session.commit()

    return {"needs_review": bool(snapshot.interrupts), "pdf_path": result.get("pdf_path")}
