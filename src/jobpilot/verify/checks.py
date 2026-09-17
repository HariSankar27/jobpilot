import re

from ..domain.models import Bullet, CheckFailure, Fact
from ..domain.skills import SKILL_VOCAB, normalize_skill

NUMBER = re.compile(r"\d+(?:[.,]\d+)?%?")


def mentioned_skills(text: str) -> set[str]:
    low = text.lower()
    return {
        normalize_skill(s) for s in SKILL_VOCAB if re.search(rf"(?<!\w){re.escape(s)}(?!\w)", low)
    }


def deterministic_checks(bullet: Bullet, facts: dict[str, Fact]) -> list[CheckFailure]:
    unknown = [i for i in bullet.evidence_ids if i not in facts]
    if unknown:
        return [CheckFailure(check="unknown_fact_id", detail=str(unknown))]
    evidence = [facts[i] for i in bullet.evidence_ids]
    evidence_text = " ".join(f.text + " " + " ".join(f.metrics) for f in evidence).lower()
    failures = [
        CheckFailure(check="unsupported_number", detail=n)
        for n in NUMBER.findall(bullet.text)
        if n not in evidence_text
    ]
    evidence_skills = {normalize_skill(s) for f in evidence for s in f.skills}
    failures += [
        CheckFailure(check="unsupported_skill", detail=s)
        for s in mentioned_skills(bullet.text) - evidence_skills
    ]
    return failures
