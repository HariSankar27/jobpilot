import respx
from httpx import Response

from jobpilot.ingest.lever import fetch_lever

POSTINGS_RESPONSE = [
    {
        "id": "abc-123",
        "text": "GenAI Engineer",
        "categories": {"location": "Remote"},
        "hostedUrl": "https://jobs.lever.co/acme/abc-123",
        "descriptionPlain": "We build agentic systems.",
        "lists": [{"text": "Requirements", "content": "&lt;li&gt;Python&lt;/li&gt;"}],
    }
]


@respx.mock
async def test_fetch_lever_parses_description_and_lists():
    respx.get("https://api.lever.co/v0/postings/acme").mock(
        return_value=Response(200, json=POSTINGS_RESPONSE)
    )
    postings = await fetch_lever("acme")
    assert len(postings) == 1
    posting = postings[0]
    assert posting.external_id == "abc-123"
    assert posting.title == "GenAI Engineer"
    assert posting.location == "Remote"
    assert "agentic systems" in posting.description_text
    assert "Python" in posting.description_text
