import math

import pytest

import scoring_engine as se

ALTS = ["A", "B", "C"]
CRITERIA = {"Cost": "cost", "Quality": "benefit"}
# normalised (cost inverted as 11 - raw):  A -> 9, 6 | B -> 3, 9 | C -> 6, 5
RATINGS = {
    "A": {"Cost": 2, "Quality": 6},
    "B": {"Cost": 8, "Quality": 9},
    "C": {"Cost": 5, "Quality": 5},
}


def run(weights, ratings=RATINGS, criteria=CRITERIA, alts=ALTS):
    return se.calculate_scores(alts, criteria, ratings, weights)


def by_name(results):
    return {r.alternative: r for r in results}


def test_weighted_average_matches_hand_calculation():
    res = by_name(run({"Cost": 1, "Quality": 3}))
    assert res["A"].score == pytest.approx((1 * 9 + 3 * 6) / 4)  # 6.75
    assert res["B"].score == pytest.approx((1 * 3 + 3 * 9) / 4)  # 7.5
    assert res["C"].score == pytest.approx((1 * 6 + 3 * 5) / 4)  # 5.25


def test_ranking_is_sorted_with_sequential_ranks():
    res = run({"Cost": 1, "Quality": 3})
    assert [r.alternative for r in res] == ["B", "A", "C"]
    assert [r.rank for r in res] == [1, 2, 3]
    scores = [r.score for r in res]
    assert scores == sorted(scores, reverse=True)


def test_cost_criterion_is_inverted_and_benefit_is_not():
    only_cost = by_name(run({"Cost": 1, "Quality": 0}))
    assert only_cost["A"].score == pytest.approx(9)  # raw 2 (cheap) -> 9
    assert only_cost["B"].score == pytest.approx(3)  # raw 8 (expensive) -> 3
    only_quality = by_name(run({"Cost": 0, "Quality": 1}))
    assert only_quality["B"].score == pytest.approx(9)
    assert se.normalize_rating(1, "cost") == 10 and se.normalize_rating(10, "cost") == 1
    assert se.normalize_rating(7, "benefit") == 7


def test_higher_cost_rating_never_improves_ranking():
    cheap = {**RATINGS, "B": {"Cost": 2, "Quality": 9}}
    assert by_name(run({"Cost": 1, "Quality": 1}, cheap))["B"].score > by_name(run({"Cost": 1, "Quality": 1}))["B"].score


def test_zero_weight_criterion_is_ignored():
    res = run({"Cost": 0, "Quality": 5})
    assert [r.alternative for r in res] == ["B", "A", "C"]
    assert by_name(res)["A"].score == pytest.approx(6)


def test_all_zero_weights_rejected():
    with pytest.raises(se.ScoringError):
        run({"Cost": 0, "Quality": 0})


def test_negative_weight_rejected():
    with pytest.raises(se.ScoringError):
        run({"Cost": -1, "Quality": 3})


@pytest.mark.parametrize("bad", [0, 0.5, 10.5, 11, -3, float("nan"), float("inf"), "7", None, True])
def test_invalid_ratings_rejected(bad):
    ratings = {**RATINGS, "A": {"Cost": bad, "Quality": 6}}
    with pytest.raises(se.ScoringError):
        run({"Cost": 1, "Quality": 1}, ratings)


def test_missing_rating_and_weight_mismatch_rejected():
    with pytest.raises(se.ScoringError):
        run({"Cost": 1, "Quality": 1}, {**RATINGS, "A": {"Cost": 2}})
    with pytest.raises(se.ScoringError):
        run({"Cost": 1})


def test_non_numeric_weight_rejected():
    with pytest.raises(se.ScoringError):
        run({"Cost": "high", "Quality": 1})


def test_ties_are_broken_by_heaviest_weighted_criterion_then_name():
    ratings = {"X": {"Cost": 5, "Quality": 8}, "Y": {"Cost": 5, "Quality": 8},
               "P": {"Cost": 2, "Quality": 5}, "Q": {"Cost": 8, "Quality": 8}}
    # X and Y are identical -> tie broken alphabetically
    res = se.calculate_scores(["Y", "X"], CRITERIA, ratings, {"Cost": 1, "Quality": 1})
    assert [r.alternative for r in res] == ["X", "Y"]
    assert res[0].tied_with == ("Y",)
    # P: 9,5 (avg 7)  Q: 3,8 (avg 5.5)  -> use a real tie with different profiles
    tie = {"P": {"Cost": 2, "Quality": 5}, "Q": {"Cost": 5, "Quality": 8}}  # P: 9,5 ; Q: 6,8 -> both 7 equal weights
    equal = se.calculate_scores(["Q", "P"], CRITERIA, tie, {"Cost": 1, "Quality": 1})
    assert equal[0].score == pytest.approx(equal[1].score)
    assert [r.alternative for r in equal] == ["P", "Q"]  # tie -> higher Cost score (9) wins when weights equal (name order of criteria)
    # heavier weight on Quality flips the tie-break only through the score itself
    heavy_q = se.calculate_scores(["Q", "P"], CRITERIA, tie, {"Cost": 1, "Quality": 2})
    assert heavy_q[0].alternative == "Q"


def test_tie_order_is_deterministic_regardless_of_input_order():
    ratings = {"X": {"Cost": 5, "Quality": 8}, "Y": {"Cost": 5, "Quality": 8}}
    a = se.calculate_scores(["X", "Y"], CRITERIA, ratings, {"Cost": 1, "Quality": 1})
    b = se.calculate_scores(["Y", "X"], CRITERIA, ratings, {"Cost": 1, "Quality": 1})
    assert [r.alternative for r in a] == [r.alternative for r in b]


def test_recalculation_after_weight_change_can_change_leader():
    before = run({"Cost": 10, "Quality": 1})
    after = run({"Cost": 1, "Quality": 10})
    assert before[0].alternative == "A" and after[0].alternative == "B"
    cmp = se.compare_rankings(before, after)
    assert cmp.leader_changed and cmp.old_leader == "A" and cmp.new_leader == "B"
    text = se.summarize_weight_change({"Cost": 10, "Quality": 1}, {"Cost": 1, "Quality": 10}, before, after)
    assert "changed" in text and "B" in text


def test_summary_says_leader_unchanged_when_it_is():
    before = run({"Cost": 1, "Quality": 3})
    after = run({"Cost": 1, "Quality": 5})
    text = se.summarize_weight_change({"Cost": 1, "Quality": 3}, {"Cost": 1, "Quality": 5}, before, after)
    assert "did not change" in text


def test_identical_weights_report_no_change():
    r = run({"Cost": 1, "Quality": 3})
    assert "identical" in se.summarize_weight_change({"Cost": 1, "Quality": 3}, {"Cost": 1, "Quality": 3}, r, r)


def test_scores_stay_within_bounds():
    extremes = {"H": {"Cost": 1, "Quality": 10}, "L": {"Cost": 10, "Quality": 1}}
    for w in ({"Cost": 1, "Quality": 1}, {"Cost": 0.1, "Quality": 999}, {"Cost": 3.3, "Quality": 0.0001}):
        for r in se.calculate_scores(["H", "L"], CRITERIA, extremes, w):
            assert 1 <= r.score <= 10
    top = se.calculate_scores(["H"], CRITERIA, extremes, {"Cost": 1, "Quality": 1})[0]
    assert top.score == pytest.approx(10)


def test_normalize_weights_sum_to_one():
    shares = se.normalize_weights({"Cost": 1, "Quality": 3})
    assert math.isclose(sum(shares.values()), 1) and shares["Quality"] == pytest.approx(0.75)


def test_duplicate_alternatives_rejected():
    with pytest.raises(se.ScoringError):
        se.calculate_scores(["A", "A"], CRITERIA, RATINGS, {"Cost": 1, "Quality": 1})


def test_displayed_score_equals_backend_score():
    for r in run({"Cost": 1, "Quality": 3}):
        assert se.round_score(r.score) == round(r.score, 2)
