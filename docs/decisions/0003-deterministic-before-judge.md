# 0003: Deterministic checks run before the LLM judge

## Context

`verify_bullet` (`src/jobpilot/graph/nodes.py`) needs to catch three kinds of
fabrication: an unknown fact id, a number or skill absent from the cited
evidence, and a claim that's technically evidenced but inflated in scope or
outcome. All three could go straight to an LLM judge.

## Decision

`deterministic_checks` (regex/set-based, `src/jobpilot/verify/checks.py`) runs
first. `judge_support` (`src/jobpilot/verify/judge.py`) only runs on a bullet
that already passed the deterministic pass.

## Consequences

Unknown-id, number, and skill fabrications - the bulk of expected failures in
`evals/datasets/verifier_pairs.jsonl` - are caught for free, with no LLM call,
no latency, and no chance of the judge being talked into excusing an obviously
invented number. The judge model's cost and non-determinism are spent only on
the harder case (inflated scope, invented outcomes) that regexes can't catch.
