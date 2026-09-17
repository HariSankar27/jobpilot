"""Scores the verifier against evals/datasets/verifier_pairs.jsonl.

Reports verifier recall (share of seeded fabrications correctly blocked) and
the false-block rate (share of truthful claims wrongly blocked), with the
model and run date, then regenerates the README results table. `--suite smoke`
runs a fast subset for pull requests; `--suite full` runs everything before a
release. `--fail-under-baseline` compares against evals/baseline.json and
exits non-zero on a regression larger than the given margin.
"""

import argparse
import asyncio
import json
import re
import time
from datetime import date
from pathlib import Path

from jobpilot.domain.models import Bullet, Fact
from jobpilot.graph.nodes import verify_bullet
from jobpilot.settings import settings

RESULTS_DIR = Path("evals/results")
BASELINE_PATH = Path("evals/baseline.json")
VERIFIER_PAIRS_PATH = Path("evals/datasets/verifier_pairs.jsonl")
README_PATH = Path("README.md")
README_MARKERS = ("<!-- eval-results:start -->", "<!-- eval-results:end -->")


def load_pairs(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


async def score_pairs(pairs: list[dict]) -> dict:
    unsupported = [p for p in pairs if p["label"] == "unsupported"]
    supported = [p for p in pairs if p["label"] == "supported"]

    async def check(pair: dict) -> bool:
        facts = {f["id"]: Fact(**f) for f in pair["facts"]}
        bullet = Bullet(id="eval", text=pair["claim"], evidence_ids=pair["evidence_ids"])
        result = await verify_bullet(bullet, facts)
        return result.passed

    caught = 0
    for pair in unsupported:
        if not await check(pair):
            caught += 1

    false_blocks = 0
    for pair in supported:
        if not await check(pair):
            false_blocks += 1

    return {
        "verifier_recall": caught / len(unsupported) if unsupported else None,
        "false_block_rate": false_blocks / len(supported) if supported else None,
        "trials": len(pairs),
    }


def regenerate_readme_table(metrics: dict) -> None:
    start, end = README_MARKERS
    text = README_PATH.read_text()
    header = (
        "| Metric | Value | Model | Dataset | Trials | Date |\n"
        "|--------|-------|-------|---------|--------|------|"
    )
    dataset = f"verifier_pairs.jsonl ({metrics['trials']})"
    row_fmt = "| {name} | {value} | {model} | {dataset} | {trials} | {date} |"
    rows = "\n".join(
        row_fmt.format(
            name=name,
            value=metrics[name],
            model=metrics["model"],
            dataset=dataset,
            trials=metrics["trials"],
            date=metrics["date"],
        )
        for name in ("verifier_recall", "false_block_rate")
    )
    table = f"{start}\n{header}\n{rows}\n{end}"
    new_text = re.sub(f"{re.escape(start)}.*?{re.escape(end)}", table, text, flags=re.DOTALL)
    README_PATH.write_text(new_text)


def check_baseline(metrics: dict, margin: float) -> None:
    if not BASELINE_PATH.exists():
        return
    baseline = json.loads(BASELINE_PATH.read_text())
    for key in ("verifier_recall",):
        current, accepted = metrics.get(key), baseline.get(key)
        if current is not None and accepted is not None and current < accepted - margin:
            raise SystemExit(f"{key} regressed: {current} < baseline {accepted} - {margin}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--fail-under-baseline", type=float, default=None)
    args = parser.parse_args()

    pairs = load_pairs(VERIFIER_PAIRS_PATH)
    if args.suite == "smoke":
        pairs = pairs[:20]

    start = time.monotonic()
    metrics = asyncio.run(score_pairs(pairs))
    metrics["latency_s"] = round(time.monotonic() - start, 2)
    metrics["model"] = settings.llm_model
    metrics["date"] = date.today().isoformat()
    metrics["suite"] = args.suite

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / f"{metrics['date']}.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))

    if args.fail_under_baseline is not None:
        check_baseline(metrics, args.fail_under_baseline)

    regenerate_readme_table(metrics)


if __name__ == "__main__":
    main()
