"""Regenerates evals/datasets/verifier_pairs.jsonl from the fictional eval profiles.

40 supported claims (facts restated verbatim or lightly paraphrased) and 80
seeded fabrications split evenly across four categories: a changed number, an
added tool the fact doesn't mention, inflated scope, and an invented outcome.
Deterministic and reproducible - no LLM calls, so re-running it never drifts.
"""

import json
from pathlib import Path

import yaml

PROFILES = ["junior", "mid", "senior"]
OUT_PATH = Path("evals/datasets/verifier_pairs.jsonl")

FABRICATED_NUMBERS = ["999", "500%", "1000ms", "42"]
FABRICATED_TOOLS = ["rust", "haskell", "cobol", "assembly"]
SCOPE_PHRASES = [
    ", single-handedly and without any help from the team",
    ", across the entire company",
    ", as the sole architect of the whole platform",
    ", entirely on their own initiative",
]
OUTCOME_PHRASES = [
    ", winning an internal engineering award",
    ", resulting in a company-wide policy change",
    ", which was featured in a national tech conference keynote",
    ", earning a spot-bonus and a promotion the same week",
]


def load_facts(profile_name: str) -> list[dict]:
    data = yaml.safe_load(Path(f"evals/datasets/profiles/{profile_name}.yaml").read_text())
    return data["facts"]


def supported_pair(fact: dict, claim: str) -> dict:
    return {
        "claim": claim,
        "facts": [fact],
        "evidence_ids": [fact["id"]],
        "label": "supported",
        "category": None,
    }


def fabricate(fact: dict, category: str, variant: str) -> dict:
    text = fact["text"]
    if category == "changed_number":
        claim = text
        for metric in fact.get("metrics", []):
            claim = claim.replace(metric, variant)
        if claim == text:
            claim = f"{text}, improving results by {variant}"
    elif category == "added_tool":
        claim = f"{text}, using {variant}"
    else:  # inflated_scope, invented_outcome - both append a suffix phrase
        claim = text + variant
    return {
        "claim": claim,
        "facts": [fact],
        "evidence_ids": [fact["id"]],
        "label": "unsupported",
        "category": category,
    }


def main() -> None:
    all_facts = [f for profile in PROFILES for f in load_facts(profile)]

    supported = [supported_pair(f, f["text"]) for f in all_facts]
    i = 0
    while len(supported) < 40:
        fact = all_facts[i % len(all_facts)]
        paraphrase = f"Successfully {fact['text'][0].lower()}{fact['text'][1:]}"
        supported.append(supported_pair(fact, paraphrase))
        i += 1
    supported = supported[:40]

    fabricated = []
    for category, variants in [
        ("changed_number", FABRICATED_NUMBERS),
        ("added_tool", FABRICATED_TOOLS),
        ("inflated_scope", SCOPE_PHRASES),
        ("invented_outcome", OUTCOME_PHRASES),
    ]:
        for i in range(20):
            fact = all_facts[i % len(all_facts)]
            variant = variants[i % len(variants)]
            fabricated.append(fabricate(fact, category, variant))

    pairs = supported + fabricated
    with OUT_PATH.open("w", encoding="utf-8") as handle:
        for pair in pairs:
            handle.write(json.dumps(pair) + "\n")
    print(f"wrote {len(pairs)} pairs ({len(supported)} supported, {len(fabricated)} fabricated)")


if __name__ == "__main__":
    main()
