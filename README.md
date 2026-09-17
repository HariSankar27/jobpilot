# jobpilot

Paste a job; get a tailored resume where every bullet traces back to your real experience.

![CI](https://github.com/HariSankar27/jobpilot/actions/workflows/ci.yml/badge.svg)

## Why this exists

Resume tailoring tools either rewrite freely (and invent claims) or require
tedious manual editing. jobpilot tailors bullets to a job posting, then blocks
any bullet whose claim it cannot trace to a fact in your profile.

## Architecture

See [docs/architecture.md](docs/architecture.md).

## Quickstart

    cp .env.example .env      # add one API key
    docker compose up -d
    uv run alembic upgrade head
    make dev

## Results

| Metric | Value | Model | Dataset | Trials | Date |
|--------|-------|-------|---------|--------|------|

## Design decisions and tradeoffs

See `docs/decisions/`.

## Safety and limitations

The claim verifier blocks unsupported numbers, tools, and claims before you
see them, but it cannot catch a fabrication that happens to match your
profile's vocabulary. Submitting applications stays manual.

## Roadmap

M0–M3 (MVP): ingestion, tailoring graph, claim verifier, CLI.
M4–M6: human review UI, PDF export, fit scoring, published evals.

## License

MIT
