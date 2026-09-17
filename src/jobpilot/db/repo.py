from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.models import Fact
from .tables import FactRow


async def import_facts(session: AsyncSession, facts: list[Fact]) -> None:
    for fact in facts:
        await session.merge(FactRow(**fact.model_dump()))
