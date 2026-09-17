# Architecture

FastAPI owns all state. The tailoring graph pauses at human review using a
Postgres checkpoint, so a review can wait for days and resume exactly where
it stopped.

```mermaid
flowchart LR
  UI[HTMX review UI] --> API[FastAPI]
  API --> ING[Job ingestion]
  ING --> GH[Greenhouse API]
  ING --> LV[Lever API]
  API --> G[LangGraph tailoring graph]
  G --> LLM[Chat model]
  G --> V[Claim verifier]
  G --> CP[(Postgres checkpoints)]
  API --> DB[(Postgres app data)]
  API --> PDF[WeasyPrint renderer]
```

## Tailoring graph

```mermaid
flowchart TD
  A[parse_job] --> B[select_facts]
  B --> C[write_bullets]
  C --> D[verify_claims]
  D -->|failures and attempts < 2| C
  D -->|all pass or out of retries| E[human_review]
  E --> F[render_pdf]
```

Mental model: the verifier is a newspaper fact-checker. The writer may phrase
a claim any way it likes, but every claim needs a source on file.
