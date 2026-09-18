import pytest

from jobpilot.domain.models import Fact, Requirement
from jobpilot.domain.tracker import coverage, gap_report, transition

FACTS = [Fact(id="F001", kind="skill", text="Comfortable with Python", skills=["python"])]


def test_valid_transition():
    assert transition("saved", "ready") == "ready"


def test_invalid_transition_raises():
    with pytest.raises(ValueError):
        transition("saved", "interview")


def test_terminal_status_has_no_transitions():
    with pytest.raises(ValueError):
        transition("offer", "saved")


def test_coverage_is_full_when_all_must_haves_are_matched():
    reqs = [
        Requirement(id="R1", kind="must_have", text="Python", skills=["python"], source_quote="")
    ]
    score, gaps = coverage(reqs, FACTS)
    assert score == 1.0
    assert gaps == []


def test_coverage_drops_for_unmatched_must_have():
    reqs = [
        Requirement(id="R1", kind="must_have", text="Python", skills=["python"], source_quote=""),
        Requirement(
            id="R2", kind="must_have", text="Kubernetes", skills=["kubernetes"], source_quote=""
        ),
    ]
    score, gaps = coverage(reqs, FACTS)
    assert score == 0.5
    assert gaps == ["Kubernetes"]


def test_nice_to_have_does_not_affect_coverage():
    reqs = [
        Requirement(id="R1", kind="nice_to_have", text="Rust", skills=["rust"], source_quote="")
    ]
    score, gaps = coverage(reqs, FACTS)
    assert score == 1.0  # no must-haves at all -> full coverage by definition
    assert gaps == []


def test_gap_report_formats_uncovered_must_haves():
    reqs = [
        Requirement(
            id="R1", kind="must_have", text="Kubernetes", skills=["kubernetes"], source_quote=""
        )
    ]
    assert gap_report(reqs, FACTS) == ["Kubernetes: no evidence in profile"]


def test_untagged_must_have_counts_as_a_gap():
    # Prose requirements often parse with no skill tags; treating them as
    # covered scored an unmet posting at 100%.
    reqs = [Requirement(id="R1", kind="must_have", text="Active TS/SCI clearance", source_quote="")]
    score, gaps = coverage(reqs, FACTS)
    assert score == 0.0
    assert gaps == ["Active TS/SCI clearance"]
