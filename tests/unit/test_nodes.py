from jobpilot.domain.models import Requirement
from jobpilot.graph.nodes import filter_verified_requirements

JOB_TEXT = "We need someone who knows Python and has led a team of 3 engineers."


def test_keeps_requirement_with_verbatim_quote():
    reqs = [Requirement(id="R1", kind="must_have", text="Python", source_quote="knows Python")]
    assert filter_verified_requirements(reqs, JOB_TEXT) == reqs


def test_drops_requirement_with_hallucinated_quote():
    reqs = [
        Requirement(
            id="R1",
            kind="must_have",
            text="Rust",
            source_quote="expert in Rust and Go",
        )
    ]
    assert filter_verified_requirements(reqs, JOB_TEXT) == []


def test_quote_match_is_case_and_whitespace_insensitive():
    reqs = [
        Requirement(id="R1", kind="nice_to_have", text="Team lead", source_quote="LED a   team")
    ]
    assert filter_verified_requirements(reqs, JOB_TEXT) == reqs
