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
async def fetch_lever(site: str) -> list[JobPosting]:
    url = f"https://api.lever.co/v0/postings/{site}"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url, params={"mode": "json"})
        resp.raise_for_status()
    postings = []
    for job in resp.json():
        lists_text = "\n".join(
            f"{item.get('text', '')}\n{html_to_text(item.get('content', ''))}"
            for item in job.get("lists", [])
        )
        text = "\n".join(filter(None, [job.get("descriptionPlain", ""), lists_text]))
        postings.append(
            JobPosting(
                source="lever",
                external_id=job.get("id"),
                company=site,
                title=job["text"],
                location=(job.get("categories") or {}).get("location"),
                url=job.get("hostedUrl"),
                description_text=text,
                content_hash=hashlib.sha256(text.encode()).hexdigest(),
            )
        )
    return postings
