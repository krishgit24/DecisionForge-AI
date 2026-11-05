import pytest

import decision_service as ds
import scoring_engine as se
from ai_service import reconcile_payload
from models import AnalysisPayload
from sample_data import SAMPLES


def valid_kwargs(**over):
    base = dict(title="Pick a stack", description="We must choose a stack for a four week project.",
                alternatives=["A", "B"], use_ai_alternatives=False, ai_alternative_count=4,
                criteria=[{"name": n, "direction": d, "weight": 5} for n, d in
                          (("Cost", "cost"), ("Speed", "cost"), ("Quality", "benefit"))],
                use_ai_criteria=False, ai_criteria_count=5)
    base.update(over)
    return base


def test_valid_request_passes():
    req, errors = ds.validate_request(**valid_kwargs())
    assert not errors and req.title == "Pick a stack" and len(req.criteria) == 3


def test_ai_suggestion_request_needs_no_manual_lists():
    req, errors = ds.validate_request(**valid_kwargs(alternatives=[], use_ai_alternatives=True, criteria=[], use_ai_criteria=True))
    assert not errors and req.needs_alternatives and req.needs_criteria


@pytest.mark.parametrize("over,fragment", [
    ({"title": ""}, "title"),
    ({"description": "short"}, "short"),
    ({"description": "12345 67890 12345 67890"}, "readable"),
    ({"alternatives": ["only one"]}, "alternatives"),
    ({"alternatives": ["A", "a"]}, "unique"),
    ({"alternatives": [f"x{i}" for i in range(7)]}, "alternatives"),
    ({"criteria": [{"name": "Cost", "direction": "cost", "weight": 5}]}, "criteria"),
    ({"criteria": [{"name": n, "direction": "cost", "weight": 0} for n in "abc"]}, "greater than zero"),
    ({"criteria": [{"name": n, "direction": "cost", "weight": 11} for n in "abc"]}, "0 to 10"),
    ({"criteria": [{"name": n, "direction": "cost", "weight": "x"} for n in "abc"]}, "0 to 10"),
])
def test_invalid_requests_give_friendly_errors(over, fragment):
    req, errors = ds.validate_request(**valid_kwargs(**over))
    assert req is None and any(fragment in e.lower() for e in errors)


@pytest.mark.parametrize("key", list(SAMPLES))
def test_samples_are_valid_and_consistent(key):
    analysis = ds.load_sample(key)
    assert analysis["mode"] == "sample"
    results = ds.compute_results(analysis)
    assert 3 <= len(analysis["criteria"]) <= 7 and 2 <= len(results) <= 6
    assert all(1 <= r.score <= 10 for r in results)
    # the sample payload also passes the same reconciliation used for live AI output
    sample = SAMPLES[key]
    payload = AnalysisPayload.model_validate(sample["payload"])
    request, _ = ds.validate_request(
        title=sample["title"], description=sample["description"], alternatives=[a.name for a in payload.alternatives],
        use_ai_alternatives=False, ai_alternative_count=4,
        criteria=[{"name": c.name, "direction": c.direction, "weight": c.suggested_weight} for c in payload.criteria],
        use_ai_criteria=False, ai_criteria_count=5)
    reconcile_payload(payload, request)


def test_tech_stack_sample_leader_changes_with_weights():
    a = ds.load_sample("tech_stack")
    assert ds.compute_results(a)[0].alternative == "Python + Streamlit"
    revised = SAMPLES["tech_stack"]["suggested_revised_weights"]
    assert ds.compute_results(a, revised)[0].alternative == "Django + Bootstrap"
    assert "leading alternative changed" in ds.weight_change_summary(a, revised)
    assert ds.weight_change_summary(a, a["original_weights"]) is None


def test_pm_sample_demonstrates_disagreement_note():
    a = ds.load_sample("pm_tools")
    kind, text = ds.initial_recommendation_note(a, ds.compute_results(a))
    assert kind == "disagree" and "has not been altered" in text


def test_results_dataframe_matches_engine():
    a = ds.load_sample("tech_stack")
    results = ds.compute_results(a)
    df = ds.results_dataframe(a, results)
    assert list(df["Alternative"]) == [r.alternative for r in results]
    assert list(df["Final Score"]) == [se.round_score(r.score) for r in results]


def test_deterministic_recommendation_mentions_top_alternative():
    a = ds.load_sample("tech_stack")
    a["mode"] = "live"
    a["recommendation"] = None
    ds.attach_recommendation(a, analyzer=None)
    assert "Python + Streamlit" in a["recommendation"]["explanation"]
