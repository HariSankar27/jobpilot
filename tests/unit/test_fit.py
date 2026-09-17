from jobpilot.domain.fit import fit_score


def test_fit_score_weights_coverage_over_rubric():
    assert fit_score(coverage_score=1.0, rubric=1) == 0.7 + 0.3 * (1 / 5)


def test_fit_score_zero_coverage_caps_at_rubric_share():
    assert fit_score(coverage_score=0.0, rubric=5) == 0.3


def test_fit_score_perfect_on_both():
    assert fit_score(coverage_score=1.0, rubric=5) == 1.0
