from typing import Literal

from pydantic import BaseModel

from ..llm import chat_model

JUDGE_PROMPT = """Decide whether the claim is fully supported by the evidence.
Inflated scope, invented outcomes, or implied ownership make it unsupported.
<evidence>{evidence}</evidence>
<claim>{claim}</claim>"""


class SupportVerdict(BaseModel):
    verdict: Literal["supported", "partially_supported", "unsupported"]
    reason: str


async def judge_support(claim: str, evidence: list[str]) -> SupportVerdict:
    llm = chat_model(temperature=0).with_structured_output(SupportVerdict)
    return await llm.ainvoke(JUDGE_PROMPT.format(evidence="\n".join(evidence), claim=claim))
