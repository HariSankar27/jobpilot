import pytest
from sqlalchemy import select

from jobpilot.db.repo import import_facts
from jobpilot.db.session import async_session
from jobpilot.db.tables import FactRow
from jobpilot.domain.profile import load_facts

pytestmark = pytest.mark.integration

PROFILE = "profile/profile.example.yaml"


async def test_importing_twice_leaves_identical_rows() -> None:
    facts = load_facts(PROFILE)
    async with async_session() as session:
        await import_facts(session, facts)
        await import_facts(session, facts)
        await session.commit()
        rows = (await session.execute(select(FactRow))).scalars().all()
    assert sorted(r.id for r in rows) == sorted(f.id for f in facts)
