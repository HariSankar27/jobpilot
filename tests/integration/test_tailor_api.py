from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pypdf import PdfReader

from jobpilot.api.routes_jobs import router as jobs_router
from jobpilot.api.routes_tailor import router as tailor_router
from jobpilot.db.repo import upsert_job
from jobpilot.db.session import async_session
from jobpilot.db.tables import TailorRunRow
from jobpilot.domain.models import Bullet, JobPosting
from jobpilot.graph import nodes as nodes_module
from jobpilot.graph.build import build_graph
from jobpilot.settings import settings
from jobpilot.verify import judge as judge_module

pytestmark = pytest.mark.integration


class _FakeStructured:
    def __init__(self, result):
        self._result = result

    async def ainvoke(self, prompt: str):
        return self._result


class _FakeChatModel:
    def __init__(self, responses: dict):
        self._responses = responses

    def with_structured_output(self, schema):
        return _FakeStructured(self._responses[schema])


def _make_app() -> FastAPI:
    conn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with AsyncPostgresSaver.from_conn_string(conn) as checkpointer:
            await checkpointer.setup()
            app.state.graph = build_graph(checkpointer)
            yield

    app = FastAPI(lifespan=lifespan)
    app.include_router(jobs_router)
    app.include_router(tailor_router)
    return app


@pytest.fixture(autouse=True)
def fake_llms(monkeypatch):
    parsed = nodes_module.ParsedJob(requirements=[])
    drafted = nodes_module.DraftBullets(
        bullets=[Bullet(id="B1", text="Led a team of 3 engineers", evidence_ids=["F001"])]
    )
    monkeypatch.setattr(
        nodes_module,
        "chat_model",
        lambda *a, **k: _FakeChatModel(
            {nodes_module.ParsedJob: parsed, nodes_module.DraftBullets: drafted}
        ),
    )
    monkeypatch.setattr(
        judge_module,
        "chat_model",
        lambda *a, **k: _FakeChatModel(
            {
                judge_module.SupportVerdict: judge_module.SupportVerdict(
                    verdict="supported", reason="ok"
                )
            }
        ),
    )


async def test_run_survives_restart_and_resumes_with_ordered_pdf(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    posting = JobPosting(
        source="paste",
        company="Acme",
        title="Eng",
        description_text="Need a backend engineer with 3 years of experience.",
        content_hash="hash-restart-test",
    )
    async with async_session() as session:
        job = await upsert_job(session, posting)
        job_id = job.id
        await session.commit()

    app1 = _make_app()
    async with app1.router.lifespan_context(app1):
        transport = ASGITransport(app=app1)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start = await client.post(f"/jobs/{job_id}/tailor")
            assert start.status_code == 202
            run_id = start.json()["run_id"]

            status = await client.get(f"/runs/{run_id}")
            assert status.json()["status"] == "needs_review"

    # A brand-new app + graph instance against the same Postgres simulates an API restart.
    app2 = _make_app()
    async with app2.router.lifespan_context(app2):
        transport = ASGITransport(app=app2)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            decisions = [{"bullet_id": "B1", "action": "accept", "edited_text": None}]
            review = await client.post(f"/runs/{run_id}/review", json=decisions)
            body = review.json()
            assert body["needs_review"] is False

            reader = PdfReader(body["pdf_path"])
            text = "\n".join(page.extract_text() for page in reader.pages)
            assert "Led a team of 3 engineers" in text

    async with async_session() as session:
        run = await session.get(TailorRunRow, run_id)
        assert run.status == "completed"
