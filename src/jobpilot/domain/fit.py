from typing import Literal

from pydantic import BaseModel

from ..llm import chat_model

RUBRIC_PROMPT = """Rate how well this candidate's experience fits the job posting on a scale of
1 (no fit) to 5 (excellent fit). Base the score only on the facts given, not assumptions.
<posting>{posting}</posting>
<facts>{facts}</facts>"""


class RubricVerdict(BaseModel):
    score: Literal[1, 2, 3, 4, 5]
    reason: str


async def rubric_score(job_text: str, facts_text: str) -> RubricVerdict:
    llm = chat_model(temperature=0).with_structured_output(RubricVerdict)
    return await llm.ainvoke(RUBRIC_PROMPT.format(posting=job_text, facts=facts_text))


def fit_score(coverage_score: float, rubric: int) -> float:
    return 0.7 * coverage_score + 0.3 * (rubric / 5)
