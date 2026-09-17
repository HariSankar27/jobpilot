import respx
from httpx import Response

from jobpilot.ingest.greenhouse import fetch_greenhouse

BOARD_RESPONSE = {
    "jobs": [
        {
            "id": 123,
            "title": "GenAI Engineer",
            "location": {"name": "Remote"},
            "absolute_url": "https://job-boards.greenhouse.io/acme/jobs/123",
            "content": "&lt;p&gt;Must know &lt;b&gt;Python&lt;/b&gt;.&lt;/p&gt;",
        }
    ]
}


@respx.mock
async def test_fetch_greenhouse_parses_and_cleans_html():
    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(
        return_value=Response(200, json=BOARD_RESPONSE)
    )
    postings = await fetch_greenhouse("acme")
    assert len(postings) == 1
    posting = postings[0]
    assert posting.external_id == "123"
    assert posting.company == "acme"
    assert posting.location == "Remote"
    assert "Must know Python ." in posting.description_text
    assert "&lt;" not in posting.description_text
