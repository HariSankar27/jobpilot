import json
from pathlib import Path

from pydantic import BaseModel

from ..domain.models import Bullet, CheckFailure, Fact, Requirement, VerificationResult
from ..domain.skills import normalize_skill
from ..llm import chat_model
from ..verify.checks import deterministic_checks
from ..verify.judge import judge_support
from .prompts import PARSE_PROMPT, WRITE_BULLETS_PROMPT
from .state import TailorState


class ParsedJob(BaseModel):
    requirements: list[Requirement]


class DraftBullets(BaseModel):
    bullets: list[Bullet]


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def filter_verified_requirements(
    requirements: list[Requirement], job_text: str
) -> list[Requirement]:
    haystack = _norm(job_text)
    return [r for r in requirements if _norm(r.source_quote) in haystack]


async def parse_job(state: TailorState) -> dict:
    llm = chat_model().with_structured_output(ParsedJob)
    parsed = await llm.ainvoke(PARSE_PROMPT.format(posting=state["job_text"]))
    kept = filter_verified_requirements(parsed.requirements, state["job_text"])
    return {"requirements": [r.model_dump() for r in kept]}


def _skill_overlap(fact: Fact, req_skills: set[str]) -> int:
    return len({normalize_skill(s) for s in fact.skills} & req_skills)


def select_facts(state: TailorState) -> dict:
    req_skills = {normalize_skill(s) for r in state["requirements"] for s in r.get("skills", [])}
    facts = [Fact(**f) for f in state["facts"]]
    ranked = sorted(facts, key=lambda f: _skill_overlap(f, req_skills), reverse=True)
    return {"facts": [f.model_dump() for f in ranked[:12]]}


async def write_bullets(state: TailorState) -> dict:
    retry_note = ""
    failed = [v for v in state.get("verification", []) if not v["passed"]]
    if failed:
        retry_note = f"The previous attempt failed these checks, fix them: {json.dumps(failed)}\n"
    llm = chat_model().with_structured_output(DraftBullets)
    prompt = WRITE_BULLETS_PROMPT.format(
        retry_note=retry_note,
        requirements=json.dumps(state["requirements"]),
        facts=json.dumps(state["facts"]),
    )
    draft = await llm.ainvoke(prompt)
    return {"bullets": [b.model_dump() for b in draft.bullets]}


async def verify_claims(state: TailorState) -> dict:
    facts = {f["id"]: Fact(**f) for f in state["facts"]}
    results = []
    for raw in state["bullets"]:
        bullet = Bullet(**raw)
        failures = deterministic_checks(bullet, facts)
        if not failures:
            verdict = await judge_support(bullet.text, [facts[i].text for i in bullet.evidence_ids])
            if verdict.verdict != "supported":
                failures.append(CheckFailure(check="not_supported", detail=verdict.reason))
        results.append(
            VerificationResult(
                bullet_id=bullet.id, passed=not failures, failures=failures
            ).model_dump()
        )
    return {"verification": results, "attempts": state.get("attempts", 0) + 1}


def route_after_verify(state: TailorState) -> str:
    failed = any(not r["passed"] for r in state["verification"])
    return "write_bullets" if failed and state["attempts"] < 2 else "human_review"


def human_review(state: TailorState) -> dict:
    # ponytail: auto-accepts every passing bullet until M4 wires a real interrupt()-based review.
    decisions = [
        {"bullet_id": v["bullet_id"], "action": "accept" if v["passed"] else "reject"}
        for v in state["verification"]
    ]
    return {"review": decisions}


def render_pdf(state: TailorState) -> dict:
    # ponytail: writes Markdown, not a PDF, until M4 adds the WeasyPrint renderer.
    accepted = {d["bullet_id"] for d in state["review"] if d["action"] == "accept"}
    bullets = [b["text"] for b in state["bullets"] if b["id"] in accepted]
    out_path = Path("var/resumes") / f"{state['job_id']}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(f"- {b}" for b in bullets))
    return {"pdf_path": str(out_path)}
