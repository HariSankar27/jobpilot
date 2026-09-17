import json
from pathlib import Path

from langgraph.types import interrupt
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


async def verify_bullet(bullet: Bullet, facts: dict[str, Fact]) -> VerificationResult:
    failures = deterministic_checks(bullet, facts)
    if not failures:
        verdict = await judge_support(bullet.text, [facts[i].text for i in bullet.evidence_ids])
        if verdict.verdict != "supported":
            failures.append(CheckFailure(check="not_supported", detail=verdict.reason))
    return VerificationResult(bullet_id=bullet.id, passed=not failures, failures=failures)


async def verify_claims(state: TailorState) -> dict:
    facts = {f["id"]: Fact(**f) for f in state["facts"]}
    results = [await verify_bullet(Bullet(**raw), facts) for raw in state["bullets"]]
    return {
        "verification": [r.model_dump() for r in results],
        "attempts": state.get("attempts", 0) + 1,
    }


def route_after_verify(state: TailorState) -> str:
    failed = any(not r["passed"] for r in state["verification"])
    return "write_bullets" if failed and state["attempts"] < 2 else "human_review"


def human_review(state: TailorState) -> dict:
    decisions = interrupt({"bullets": state["bullets"], "verification": state["verification"]})
    return {"review": decisions}


async def apply_review(state: TailorState) -> dict:
    # ponytail: re-verification runs here, not inside human_review, so a failing edit
    # loops back through a conditional edge instead of retrying inside the node.
    facts = {f["id"]: Fact(**f) for f in state["facts"]}
    bullets_by_id = {b["id"]: dict(b) for b in state["bullets"]}
    verification_by_id = {v["bullet_id"]: v for v in state["verification"]}

    for decision in state["review"]:
        if decision["action"] != "edit":
            continue
        bullet_id = decision["bullet_id"]
        edited = Bullet(**{**bullets_by_id[bullet_id], "text": decision["edited_text"]})
        bullets_by_id[bullet_id] = edited.model_dump()
        verification_by_id[bullet_id] = (await verify_bullet(edited, facts)).model_dump()

    return {
        "bullets": list(bullets_by_id.values()),
        "verification": list(verification_by_id.values()),
    }


def route_after_review(state: TailorState) -> str:
    verification_by_id = {v["bullet_id"]: v for v in state["verification"]}
    edited_ids = [d["bullet_id"] for d in state["review"] if d["action"] == "edit"]
    still_failing = any(not verification_by_id[i]["passed"] for i in edited_ids)
    return "human_review" if still_failing else "render_pdf"


def render_pdf(state: TailorState) -> dict:
    from ..render.pdf import render_resume  # lazy: WeasyPrint needs system Pango libraries

    verification_by_id = {v["bullet_id"]: v for v in state["verification"]}
    accepted_ids = {
        d["bullet_id"]
        for d in state["review"]
        if d["action"] == "accept"
        or (d["action"] == "edit" and verification_by_id.get(d["bullet_id"], {}).get("passed"))
    }
    bullets_by_id = {b["id"]: b for b in state["bullets"]}
    bullets = [bullets_by_id[i]["text"] for i in bullets_by_id if i in accepted_ids]

    out_path = Path("var/resumes") / f"{state['job_id']}.pdf"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    render_resume({"name": "Candidate"}, bullets, str(out_path))
    return {"pdf_path": str(out_path)}
