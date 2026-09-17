from pathlib import Path

from evals import run as run_module


class _FakeResult:
    def __init__(self, passed: bool):
        self.passed = passed


async def test_score_pairs_computes_recall_and_false_block_rate(monkeypatch):
    pairs = [
        {"label": "supported", "facts": [], "evidence_ids": ["F001"], "claim": "a"},
        {"label": "supported", "facts": [], "evidence_ids": ["F001"], "claim": "b"},
        {"label": "unsupported", "facts": [], "evidence_ids": ["F001"], "claim": "c"},
        {"label": "unsupported", "facts": [], "evidence_ids": ["F001"], "claim": "d"},
    ]
    # a: correctly passed. b: wrongly blocked (false block). c: correctly caught. d: missed.
    passed_by_claim = {"a": True, "b": False, "c": False, "d": True}

    async def fake_verify_bullet(bullet, facts):
        return _FakeResult(passed=passed_by_claim[bullet.text])

    monkeypatch.setattr(run_module, "verify_bullet", fake_verify_bullet)

    metrics = await run_module.score_pairs(pairs)
    assert metrics["verifier_recall"] == 0.5
    assert metrics["false_block_rate"] == 0.5
    assert metrics["trials"] == 4


def test_regenerate_readme_table_replaces_only_marked_section(monkeypatch, tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Title\n\n## Results\n\n<!-- eval-results:start -->\n"
        "old\n<!-- eval-results:end -->\n\n## Next\n"
    )
    monkeypatch.setattr(run_module, "README_PATH", readme)

    run_module.regenerate_readme_table(
        {
            "verifier_recall": 0.9,
            "false_block_rate": 0.05,
            "model": "gemini-2.5-flash",
            "trials": 20,
            "date": "2026-09-18",
        }
    )

    text = readme.read_text()
    assert "old" not in text
    assert "0.9" in text
    assert "## Next" in text


def test_verifier_pairs_dataset_has_expected_split():
    lines = Path("evals/datasets/verifier_pairs.jsonl").read_text().splitlines()
    assert len(lines) == 120
