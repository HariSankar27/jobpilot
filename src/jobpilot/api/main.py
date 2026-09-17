from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy import text

from ..db.session import engine
from ..graph.build import build_graph
from ..settings import settings
from .routes_jobs import router as jobs_router
from .routes_tailor import router as tailor_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # the checkpointer takes a plain postgresql:// URL, not SQLAlchemy's postgresql+psycopg://
    conn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
    async with AsyncPostgresSaver.from_conn_string(conn) as checkpointer:
        await checkpointer.setup()
        app.state.graph = build_graph(checkpointer)
        yield


app = FastAPI(title="jobpilot", lifespan=lifespan)
app.include_router(jobs_router)
app.include_router(tailor_router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"db": "ok"}
