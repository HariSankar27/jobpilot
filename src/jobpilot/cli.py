import asyncio
import uuid
from pathlib import Path

import typer
import yaml
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from sqlalchemy import select

from .cost import cost_usd
from .db.repo import import_facts, upsert_job
from .db.session import async_session
from .db.tables import FactRow, JobRow, TailorRunRow
from .domain.models import Fact, Requirement
from .domain.profile import load_facts
from .domain.tracker import coverage
from .graph.build import build_graph
from .graph.nodes import parse_job
from .ingest.greenhouse import fetch_greenhouse
from .ingest.lever import fetch_lever

app = typer.Typer()
profile_app = typer.Typer()
app.add_typer(profile_app, name="profile")


@profile_app.command("import")
def import_profile(path: str) -> None:
    facts = load_facts(path)

    async def _run() -> None:
        async with async_session() as session:
            await import_facts(session, facts)
            await session.commit()

    asyncio.run(_run())
    typer.echo(f"Imported {len(facts)} facts")


@app.command()
def tailor(job_id: str) -> None:
    async def _run() -> None:
        async with async_session() as session:
            job = await session.get(JobRow, job_id)
            if job is None:
                typer.echo(f"No such job: {job_id}", err=True)
                raise typer.Exit(1)
            rows = (await session.execute(select(FactRow))).scalars().all()
            facts = [
                Fact(
                    id=r.id,
                    kind=r.kind,
                    org=r.org,
                    role=r.role,
                    text=r.text,
                    skills=r.skills,
                    metrics=r.metrics,
                )
                for r in rows
            ]

        graph = build_graph(MemorySaver())
        thread_id = str(uuid.uuid4())
        callback = UsageMetadataCallbackHandler()
        config = {"configurable": {"thread_id": thread_id}, "callbacks": [callback]}

        result = await graph.ainvoke(
            {
                "job_id": job_id,
                "job_text": job.description_text,
                "facts": [f.model_dump() for f in facts],
                "attempts": 0,
            },
            config=config,
        )

        snapshot = await graph.aget_state(config)
        while snapshot.interrupts:
            payload = snapshot.interrupts[0].value
            verification_by_id = {v["bullet_id"]: v for v in payload["verification"]}
            decisions = []
            for bullet in payload["bullets"]:
                verification = verification_by_id.get(bullet["id"], {})
                passed = bool(verification.get("passed"))
                typer.echo(f"[{'PASS' if passed else 'FAIL'}] {bullet['id']}: {bullet['text']}")
                for failure in verification.get("failures", []):
                    typer.echo(f"    - {failure['check']}: {failure['detail']}")
                action = typer.prompt(
                    "accept/edit/reject", default="accept" if passed else "reject"
                )
                edited_text = typer.prompt("New text") if action == "edit" else None
                decisions.append(
                    {"bullet_id": bullet["id"], "action": action, "edited_text": edited_text}
                )
            result = await graph.ainvoke(Command(resume=decisions), config=config)
            snapshot = await graph.aget_state(config)

        async with async_session() as session:
            session.add(
                TailorRunRow(
                    id=thread_id,
                    job_id=job_id,
                    status="completed",
                    trace_id=thread_id,  # ponytail: real Langfuse tracing is future polish
                    cost_usd=cost_usd(callback.usage_metadata),
                )
            )
            await session.commit()

        typer.echo(f"Resume written to {result['pdf_path']}")

    asyncio.run(_run())


@app.command()
def watch(boards_path: str = "profile/boards.yaml", min_coverage: float = 0.5) -> None:
    async def _run() -> None:
        config = yaml.safe_load(Path(boards_path).read_text()) or {}

        async with async_session() as session:
            fact_rows = (await session.execute(select(FactRow))).scalars().all()
        facts = [
            Fact(
                id=r.id,
                kind=r.kind,
                org=r.org,
                role=r.role,
                text=r.text,
                skills=r.skills,
                metrics=r.metrics,
            )
            for r in fact_rows
        ]

        postings = []
        for board in config.get("greenhouse", []):
            postings += await fetch_greenhouse(board)
        for site in config.get("lever", []):
            postings += await fetch_lever(site)

        new_jobs = []
        async with async_session() as session:
            for posting in postings:
                job, created = await upsert_job(session, posting)
                if created:
                    new_jobs.append(job)
            await session.commit()

        if not new_jobs:
            typer.echo("No new postings.")
            return

        # ponytail: coverage only, no rubric LLM call - keeps a routine sweep free
        for job in new_jobs:
            parsed = await parse_job({"job_text": job.description_text})
            requirements = [Requirement(**r) for r in parsed["requirements"]]
            score, _ = coverage(requirements, facts)
            if score >= min_coverage:
                typer.echo(f"[{score:.0%}] {job.company} — {job.title}: {job.url}")

    asyncio.run(_run())


if __name__ == "__main__":
    app()
