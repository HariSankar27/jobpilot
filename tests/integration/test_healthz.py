import pytest
from httpx import ASGITransport, AsyncClient

from jobpilot.api.main import app

pytestmark = pytest.mark.integration


async def test_healthz_reports_db_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"db": "ok"}
