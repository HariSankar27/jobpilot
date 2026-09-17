import pytest

from jobpilot.domain.skills import normalize_skill


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("GCP", "google-cloud"),
        ("Google Cloud", "google-cloud"),
        ("k8s", "kubernetes"),
        ("Azure OpenAI", "azure-openai"),
        ("LLMs", "llm"),
        ("python", "python"),
        ("Multi Agent", "multi-agent"),
    ],
)
def test_normalize_skill(raw: str, expected: str) -> None:
    assert normalize_skill(raw) == expected
