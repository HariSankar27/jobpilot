import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from jobpilot.api.main import app
from jobpilot.db.repo import create_resume_version, upsert_job
from jobpilot.db.session import async_session
from jobpilot.db.tables import TailorRunRow
from jobpilot.domain.models import JobPosting

pytestmark = pytest.mark.integration


async def _seed_application() -> str:
    # Unique per call: these tests share one database, so fixed ids collide
    # between tests and across re-runs.
    suffix = uuid.uuid4().hex[:8]
    run_id = f"run-apps-{suffix}"

    async with async_session() as session:
        job, _ = await upsert_job(
            session,
            JobPosting(
                source="paste",
                company="Acme",
                title="Eng",
                description_text="text",
                content_hash=f"hash-apps-{suffix}",
            ),
        )
        session.add(TailorRunRow(id=run_id, job_id=job.id, status="completed", trace_id="t"))
        # resume_versions.run_id references tailor_runs, so the run has to exist
        # before the dependent row is inserted.
        await session.flush()
        version = await create_resume_version(session, run_id, "var/resumes/x.pdf")
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/applications", json={"job_id": job.id, "resume_version_id": version.id}
        )
        return resp.json()["id"]


async def test_valid_transition_succeeds():
    app_id = await _seed_application()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(f"/applications/{app_id}", json={"status": "ready"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


async def test_invalid_transition_returns_409():
    app_id = await _seed_application()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(f"/applications/{app_id}", json={"status": "interview"})
        assert resp.status_code == 409
