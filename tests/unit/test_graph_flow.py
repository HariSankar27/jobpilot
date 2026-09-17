from pathlib import Path

import pytest
from langgraph.checkpoint.memory import MemorySaver

from jobpilot.domain.models import Bullet, Requirement
from jobpilot.graph import nodes as nodes_module
from jobpilot.graph.build import build_graph
from jobpilot.verify import judge as judge_module

JOB_TEXT = "We need a backend engineer who knows kubernetes and has led a team of 3 engineers."

FACTS = [
    {
        "id": "F001",
        "kind": "achievement",
        "org": "Acme",
        "role": "Eng",
        "text": "Led a team of 3 engineers",
        "skills": ["python"],
        "metrics": ["3 engineers"],
    }
]


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


@pytest.fixture(autouse=True)
def fake_llms(monkeypatch, tmp_path):
    parsed = nodes_module.ParsedJob(
        requirements=[
            Requirement(
                id="R1", kind="must_have", text="kubernetes", source_quote="knows kubernetes"
            )
        ]
    )
    drafted = nodes_module.DraftBullets(
        bullets=[
            Bullet(id="B1", text="Led a team of 3 engineers", evidence_ids=["F001"]),
            Bullet(id="B2", text="Deployed services with kubernetes", evidence_ids=["F001"]),
        ]
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
    monkeypatch.chdir(tmp_path)


async def test_bullet_claiming_missing_skill_is_excluded_from_final_render():
    graph = build_graph(MemorySaver())
    result = await graph.ainvoke(
        {"job_id": "job-1", "job_text": JOB_TEXT, "facts": FACTS, "attempts": 0},
        config={"configurable": {"thread_id": "t1"}},
    )

    accepted = {d["bullet_id"] for d in result["review"] if d["action"] == "accept"}
    assert accepted == {"B1"}

    rendered = Path(result["pdf_path"]).read_text()
    assert "kubernetes" not in rendered
    assert "Led a team of 3 engineers" in rendered
