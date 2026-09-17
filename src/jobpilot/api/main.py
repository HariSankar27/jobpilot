from fastapi import FastAPI
from sqlalchemy import text

from ..db.session import engine

app = FastAPI(title="jobpilot")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"db": "ok"}
