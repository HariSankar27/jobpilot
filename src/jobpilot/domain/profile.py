from pathlib import Path

import yaml

from .models import Fact


class DuplicateFactIdError(ValueError):
    pass


def load_facts(path: str | Path) -> list[Fact]:
    data = yaml.safe_load(Path(path).read_text())
    facts = [Fact(**raw) for raw in data.get("facts", [])]
    seen: set[str] = set()
    for fact in facts:
        if fact.id in seen:
            raise DuplicateFactIdError(f"Duplicate fact id: {fact.id}")
        seen.add(fact.id)
    return facts
