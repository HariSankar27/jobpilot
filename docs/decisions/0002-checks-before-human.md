# 0002: Verify claims before the human reviews them

## Context

The tailoring graph could show every drafted bullet to the human immediately,
or run `verify_claims` first and only then interrupt for review.

## Decision

`verify_claims` always runs before `human_review`, with up to two automatic
retries through `write_bullets` when checks fail. The human sees bullets
alongside their pass/fail verdicts and failure reasons, not a blank slate.

## Consequences

Most fabrications never reach the human at all - the retry loop fixes or
drops them first. What the human does see is triaged: passing bullets need a
quick skim, failing ones come with a specific reason to fix or reject. The
cost is up to two extra LLM calls per run before a human ever looks at it,
which the retry cap (`attempts < 2`) bounds.
