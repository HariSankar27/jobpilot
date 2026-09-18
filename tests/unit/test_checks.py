from jobpilot.domain.models import Bullet, Fact
from jobpilot.verify.checks import deterministic_checks, mentioned_skills

FACT = Fact(
    id="F001",
    kind="achievement",
    org="Acme",
    text="Cut latency from 300ms to 50ms using gcp and langgraph",
    skills=["gcp", "langgraph"],
    metrics=["300ms", "50ms"],
)


def _bullet(text: str, evidence_ids: list[str] = ("F001",)) -> Bullet:
    return Bullet(id="B1", text=text, evidence_ids=list(evidence_ids))


def test_no_failures_for_fully_supported_bullet():
    bullet = _bullet("Cut latency from 300ms to 50ms with GCP")
    assert deterministic_checks(bullet, {"F001": FACT}) == []


def test_unknown_fact_id_is_rejected():
    bullet = _bullet("Did something", evidence_ids=["F999"])
    failures = deterministic_checks(bullet, {"F001": FACT})
    assert [f.check for f in failures] == ["unknown_fact_id"]


def test_invented_number_is_caught():
    bullet = _bullet("Cut latency from 300ms to 10ms with GCP")
    failures = deterministic_checks(bullet, {"F001": FACT})
    assert any(f.check == "unsupported_number" and f.detail == "10" for f in failures)


def test_number_present_in_metrics_passes():
    bullet = _bullet("Reduced latency to 50ms")
    assert deterministic_checks(bullet, {"F001": FACT}) == []


def test_alias_skill_is_accepted():
    # the fact records "gcp"; the bullet spells it "Google Cloud" - same canonical skill
    bullet = _bullet("Shipped it on Google Cloud")
    assert deterministic_checks(bullet, {"F001": FACT}) == []


def test_unsupported_skill_is_rejected():
    bullet = _bullet("Built it with kubernetes")
    failures = deterministic_checks(bullet, {"F001": FACT})
    assert any(f.check == "unsupported_skill" and f.detail == "kubernetes" for f in failures)


def test_evidence_from_multiple_facts_is_combined():
    other = Fact(id="F002", kind="skill", text="Comfortable with kubernetes", skills=["kubernetes"])
    bullet = _bullet("Ran it on kubernetes and gcp", evidence_ids=["F001", "F002"])
    assert deterministic_checks(bullet, {"F001": FACT, "F002": other}) == []


def test_percentage_number_is_checked():
    fact = Fact(id="F003", kind="achievement", text="Improved accuracy by 20%", skills=[])
    bullet = _bullet("Improved accuracy by 90%", evidence_ids=["F003"])
    failures = deterministic_checks(bullet, {"F003": fact})
    assert any(f.detail == "90%" for f in failures)


def test_both_number_and_skill_failures_are_reported():
    bullet = _bullet("Cut latency to 77ms with kubernetes")
    failures = deterministic_checks(bullet, {"F001": FACT})
    checks = {f.check for f in failures}
    assert checks == {"unsupported_number", "unsupported_skill"}


def test_mentioned_skills_respects_word_boundaries():
    assert "python" not in mentioned_skills("pythonic code")
    assert "python" in mentioned_skills("wrote it in python")


def test_unknown_fact_id_short_circuits_other_checks():
    bullet = _bullet("Cut latency to 1ms with kubernetes", evidence_ids=["F404"])
    failures = deterministic_checks(bullet, {"F001": FACT})
    assert len(failures) == 1
    assert failures[0].check == "unknown_fact_id"


def test_understated_number_is_caught_not_matched_as_substring():
    # "5" is a substring of "50" - a substring test would let this through.
    fact = Fact(id="F9", kind="achievement", text="Led a team of 50 engineers", metrics=["50"])
    bullet = _bullet("Led a team of 5 engineers", evidence_ids=["F9"])
    failures = deterministic_checks(bullet, {"F9": fact})
    assert [f.detail for f in failures if f.check == "unsupported_number"] == ["5"]
