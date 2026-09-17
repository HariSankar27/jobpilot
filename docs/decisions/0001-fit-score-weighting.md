# 0001: Fit score weighting

## Context

A posting needs one fit number to sort applications by. Two signals are
available: deterministic requirement coverage (`domain.tracker.coverage`) and
an LLM rubric score (1-5) that judges overall experience fit.

## Decision

`fit_score = 0.7 * coverage + 0.3 * (rubric / 5)`. Coverage dominates because
it is auditable and reproducible; the rubric adds judgment coverage can't
capture (seniority, domain fit) without letting an LLM's opinion outweigh a
requirement the profile plainly doesn't meet.

## Consequences

A posting can never score above `0.3` on rubric alone if coverage is zero,
which is intentional: a missing must-have skill should cap the score even if
the LLM likes the candidate's overall trajectory.
