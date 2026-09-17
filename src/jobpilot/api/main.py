from fastapi import FastAPI
from sqlalchemy import text

from ..db.session import engine
from .routes_jobs import router as jobs_router

app = FastAPI(title="jobpilot")
app.include_router(jobs_router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"db": "ok"}
