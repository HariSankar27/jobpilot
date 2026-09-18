from pathlib import Path

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from jobpilot.domain.models import Bullet, Requirement
from jobpilot.graph import nodes as nodes_module
from jobpilot.graph.build import build_graph
from jobpilot.render import pdf as pdf_module
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


def _fake_render(candidate, bullets, out_path):
    Path(out_path).write_text("\n".join(bullets))
    return out_path


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
    monkeypatch.setattr(pdf_module, "render_resume", _fake_render)
    monkeypatch.chdir(tmp_path)


async def _run_to_first_interrupt():
    graph = build_graph(MemorySaver())
    config = {"configurable": {"thread_id": "t1"}}
    await graph.ainvoke(
        {"job_id": "job-1", "job_text": JOB_TEXT, "facts": FACTS, "attempts": 0}, config=config
    )
    snapshot = await graph.aget_state(config)
    return graph, config, snapshot


async def test_human_review_interrupts_with_bullets_and_verification():
    _, _, snapshot = await _run_to_first_interrupt()
    assert snapshot.interrupts
    payload = snapshot.interrupts[0].value
    assert {b["id"] for b in payload["bullets"]} == {"B1", "B2"}
    verification_by_id = {v["bullet_id"]: v["passed"] for v in payload["verification"]}
    assert verification_by_id == {"B1": True, "B2": False}


async def test_accept_and_reject_render_only_accepted_bullet():
    graph, config, _ = await _run_to_first_interrupt()
    decisions = [
        {"bullet_id": "B1", "action": "accept", "edited_text": None},
        {"bullet_id": "B2", "action": "reject", "edited_text": None},
    ]
    result = await graph.ainvoke(Command(resume=decisions), config=config)
    snapshot = await graph.aget_state(config)
    assert not snapshot.interrupts
    rendered = Path(result["pdf_path"]).read_text()
    assert "Led a team of 3 engineers" in rendered
    assert "kubernetes" not in rendered


async def test_edit_that_still_fails_loops_back_to_review():
    graph, config, _ = await _run_to_first_interrupt()
    decisions = [
        {"bullet_id": "B1", "action": "accept", "edited_text": None},
        {
            "bullet_id": "B2",
            "action": "edit",
            "edited_text": "Deployed services with kubernetes and azure openai",
        },
    ]
    await graph.ainvoke(Command(resume=decisions), config=config)
    snapshot = await graph.aget_state(config)
    assert snapshot.interrupts
    payload = snapshot.interrupts[0].value
    verification_by_id = {v["bullet_id"]: v for v in payload["verification"]}
    assert verification_by_id["B2"]["passed"] is False
    assert any(f["detail"] == "azure-openai" for f in verification_by_id["B2"]["failures"])


async def test_edit_that_now_passes_proceeds_to_render():
    graph, config, _ = await _run_to_first_interrupt()
    decisions = [
        {"bullet_id": "B1", "action": "accept", "edited_text": None},
        {"bullet_id": "B2", "action": "edit", "edited_text": "Led a team of 3 engineers well"},
    ]
    result = await graph.ainvoke(Command(resume=decisions), config=config)
    snapshot = await graph.aget_state(config)
    assert not snapshot.interrupts
    rendered = Path(result["pdf_path"]).read_text()
    assert "Led a team of 3 engineers well" in rendered


async def test_review_decision_for_an_unknown_bullet_is_ignored_not_fatal():
    graph, config, _ = await _run_to_first_interrupt()
    decisions = [
        {"bullet_id": "B1", "action": "accept", "edited_text": None},
        {"bullet_id": "B2", "action": "reject", "edited_text": None},
        {"bullet_id": "GHOST", "action": "edit", "edited_text": "never existed"},
    ]
    result = await graph.ainvoke(Command(resume=decisions), config=config)
    snapshot = await graph.aget_state(config)
    assert not snapshot.interrupts
    assert "Led a team of 3 engineers" in Path(result["pdf_path"]).read_text()
