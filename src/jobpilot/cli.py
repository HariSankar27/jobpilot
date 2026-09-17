import asyncio
import uuid

import typer
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import select

from .cost import cost_usd
from .db.repo import import_facts
from .db.session import async_session
from .db.tables import FactRow, JobRow, TailorRunRow
from .domain.models import Fact
from .domain.profile import load_facts
from .graph.build import build_graph

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
        result = await graph.ainvoke(
            {
                "job_id": job_id,
                "job_text": job.description_text,
                "facts": [f.model_dump() for f in facts],
                "attempts": 0,
            },
            config={"configurable": {"thread_id": thread_id}, "callbacks": [callback]},
        )

        async with async_session() as session:
            session.add(
                TailorRunRow(
                    id=thread_id,
                    job_id=job_id,
                    status="completed",
                    trace_id=thread_id,  # ponytail: real Langfuse tracing lands with M4
                    cost_usd=cost_usd(callback.usage_metadata),
                )
            )
            await session.commit()

        verification_by_id = {v["bullet_id"]: v for v in result["verification"]}
        for bullet in result["bullets"]:
            verification = verification_by_id.get(bullet["id"])
            passed = bool(verification and verification["passed"])
            typer.echo(f"[{'PASS' if passed else 'FAIL'}] {bullet['text']}")
            if verification and not passed:
                for failure in verification["failures"]:
                    typer.echo(f"    - {failure['check']}: {failure['detail']}")

    asyncio.run(_run())


if __name__ == "__main__":
    app()
