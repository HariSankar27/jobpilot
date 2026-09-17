import pytest
from httpx import ASGITransport, AsyncClient

from jobpilot.api.main import app
from jobpilot.domain.models import Requirement
from jobpilot.graph import nodes as nodes_module

pytestmark = pytest.mark.integration

JOB_TEXT = "We need a backend engineer who knows Python and FastAPI."


class _FakeStructuredLLM:
    def __init__(self, result):
        self._result = result

    async def ainvoke(self, prompt: str):
        return self._result


class _FakeChatModel:
    def __init__(self, result):
        self._result = result

    def with_structured_output(self, schema):
        return _FakeStructuredLLM(self._result)


@pytest.fixture(autouse=True)
def fake_chat_model(monkeypatch):
    parsed = nodes_module.ParsedJob(
        requirements=[
            Requirement(id="R1", kind="must_have", text="Python", source_quote="knows Python")
        ]
    )
    monkeypatch.setattr(nodes_module, "chat_model", lambda: _FakeChatModel(parsed))


async def test_create_job_is_idempotent_and_stores_requirements():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/jobs", json={"text": JOB_TEXT})
        second = await client.post("/jobs", json={"text": JOB_TEXT})
        assert first.status_code == 200
        job_id = first.json()[0]["id"]
        assert second.json()[0]["id"] == job_id

        detail = await client.get(f"/jobs/{job_id}")
        assert detail.status_code == 200
        assert [r["source_quote"] for r in detail.json()["requirements"]] == ["knows Python"]
