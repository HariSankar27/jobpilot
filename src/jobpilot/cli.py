import asyncio

import typer

from .db.repo import import_facts
from .db.session import async_session
from .domain.profile import load_facts

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


if __name__ == "__main__":
    app()
