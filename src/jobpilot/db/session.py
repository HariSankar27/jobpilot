from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..settings import settings

# connect_timeout: without it, `make dev` hangs forever at "Waiting for
# application startup" when Postgres isn't up, with no error to diagnose.
engine = create_async_engine(
    settings.database_url, connect_args={"connect_timeout": settings.db_connect_timeout_s}
)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with async_session() as session:
        yield session
