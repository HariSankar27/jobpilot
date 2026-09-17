import hashlib

import httpx
import tenacity

from ..domain.models import JobPosting
from .clean import html_to_text

_retry = tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
    retry=tenacity.retry_if_exception_type(httpx.HTTPError),
)


@_retry
async def fetch_greenhouse(board: str) -> list[JobPosting]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url, params={"content": "true"})
        resp.raise_for_status()
    postings = []
    for job in resp.json()["jobs"]:
        text = html_to_text(job.get("content", ""))
        postings.append(
            JobPosting(
                source="greenhouse",
                external_id=str(job["id"]),
                company=board,
                title=job["title"],
                location=(job.get("location") or {}).get("name"),
                url=job["absolute_url"],
                description_text=text,
                content_hash=hashlib.sha256(text.encode()).hexdigest(),
            )
        )
    return postings
