from pathlib import Path

import pytest
import yaml

from jobpilot.domain.profile import DuplicateFactIdError, load_facts


def _write_profile(tmp_path: Path, facts: list[dict]) -> Path:
    path = tmp_path / "profile.yaml"
    path.write_text(yaml.safe_dump({"candidate": {"name": "Test"}, "facts": facts}))
    return path


def test_load_facts_returns_parsed_facts(tmp_path: Path) -> None:
    path = _write_profile(
        tmp_path,
        [{"id": "F001", "kind": "achievement", "text": "Did a thing", "skills": ["python"]}],
    )
    facts = load_facts(path)
    assert len(facts) == 1
    assert facts[0].id == "F001"
    assert facts[0].skills == ["python"]


def test_load_facts_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = _write_profile(
        tmp_path,
        [
            {"id": "F001", "kind": "achievement", "text": "Did a thing"},
            {"id": "F001", "kind": "skill", "text": "Same id again"},
        ],
    )
    with pytest.raises(DuplicateFactIdError):
        load_facts(path)
