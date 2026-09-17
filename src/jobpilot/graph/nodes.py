from pydantic import BaseModel

from ..domain.models import Requirement
from ..llm import chat_model
from .prompts import PARSE_PROMPT
from .state import TailorState


class ParsedJob(BaseModel):
    requirements: list[Requirement]


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
