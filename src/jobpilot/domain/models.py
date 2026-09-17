from typing import Literal

from pydantic import BaseModel, Field


class Fact(BaseModel):
    id: str
    kind: Literal["achievement", "responsibility", "skill", "education", "certification"]
    org: str | None = None
    role: str | None = None
    text: str
    skills: list[str] = []
    metrics: list[str] = []


class JobPosting(BaseModel):
    source: Literal["paste", "greenhouse", "lever"]
    external_id: str | None = None
    company: str
    title: str
    location: str | None = None
    url: str | None = None
    description_text: str
    content_hash: str


class Requirement(BaseModel):
    id: str
    kind: Literal["must_have", "nice_to_have"]
    text: str
    skills: list[str] = []
    source_quote: str = Field(description="Exact words copied from the posting")


class Bullet(BaseModel):
    id: str
    text: str = Field(max_length=220)
    evidence_ids: list[str] = Field(min_length=1)
    requirement_ids: list[str] = []


class CheckFailure(BaseModel):
    check: Literal["unknown_fact_id", "unsupported_number", "unsupported_skill", "not_supported"]
    detail: str


class VerificationResult(BaseModel):
    bullet_id: str
    passed: bool
    failures: list[CheckFailure] = []


class ReviewDecision(BaseModel):
    bullet_id: str
    action: Literal["accept", "edit", "reject"]
    edited_text: str | None = None
