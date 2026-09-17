from .models import Fact, Requirement
from .skills import normalize_skill

ALLOWED = {
    "saved": {"ready", "archived"},
    "ready": {"applied", "archived"},
    "applied": {"interview", "rejected"},
    "interview": {"offer", "rejected"},
}


def transition(current: str, new: str) -> str:
    if new not in ALLOWED.get(current, set()):
        raise ValueError(f"Cannot move an application from {current} to {new}")
    return new


def coverage(reqs: list[Requirement], facts: list[Fact]) -> tuple[float, list[str]]:
    have = {normalize_skill(s) for f in facts for s in f.skills}
    must = [r for r in reqs if r.kind == "must_have"]
    gaps = [r.text for r in must if r.skills and not {normalize_skill(s) for s in r.skills} & have]
    return 1 - len(gaps) / max(len(must), 1), gaps


def gap_report(reqs: list[Requirement], facts: list[Fact]) -> list[str]:
    _, gaps = coverage(reqs, facts)
    return [f"{text}: no evidence in profile" for text in gaps]
