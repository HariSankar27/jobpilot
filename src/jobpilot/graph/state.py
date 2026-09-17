from typing import TypedDict


class TailorState(TypedDict, total=False):  # JSON-friendly values only, so checkpoints serialize
    job_id: str
    job_text: str
    requirements: list[dict]
    facts: list[dict]
    bullets: list[dict]
    verification: list[dict]
    attempts: int
    review: list[dict]
    pdf_path: str
