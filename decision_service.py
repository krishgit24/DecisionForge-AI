"""Application logic that ties validation, AI, scoring and sample data together.

The analysis is a plain ``dict`` (easy to store in session state and SQLite).
All numbers shown to the user come from ``scoring_engine`` via these helpers.
"""
from __future__ import annotations

import math
import re
import uuid

import pandas as pd
from pydantic import ValidationError

import config
import scoring_engine as se
from ai_service import AIServiceError, DecisionAnalyzer
from models import AnalysisPayload, Constraints, CriterionInput, DecisionRequest
from sample_data import SAMPLES

FIXED_COLUMNS = {"Rank", "Alternative", "Final Score", "Key Advantage", "Main Disadvantage"}


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate_request(
    *, title: str, description: str, alternatives: list[str], use_ai_alternatives: bool,
    ai_alternative_count: int, criteria: list[dict], use_ai_criteria: bool, ai_criteria_count: int,
    budget: str = "", time_limit: str = "", team: str = "", other_constraints: str = "",
    priorities_note: str = "",
) -> tuple[DecisionRequest | None, list[str]]:
    """Return ``(request, [])`` or ``(None, friendly_error_messages)``."""
    errors: list[str] = []
    title, description = (title or "").strip(), (description or "").strip()

    if not title:
        errors.append("Please enter a decision title.")
    elif len(title) > 150:
        errors.append("The decision title must be 150 characters or fewer.")
    if not description:
        errors.append("Please describe the decision you need to make.")
    elif len(description) < 20:
        errors.append("The description is very short. Add a sentence or two about your goals and context.")
    elif len(description) > 3000:
        errors.append("The description must be 3000 characters or fewer.")
    elif not re.search(r"[^\W\d_]", description):
        errors.append("The description must contain readable text.")

    for label, value, limit in (("Budget", budget, 500), ("Time", time_limit, 500), ("Team", team, 500),
                                ("Other constraints", other_constraints, 1000), ("Priorities note", priorities_note, 500)):
        if len((value or "").strip()) > limit:
            errors.append(f"{label} must be {limit} characters or fewer.")

    alts: list[str] = []
    if use_ai_alternatives:
        if not config.MIN_ALTERNATIVES <= ai_alternative_count <= config.MAX_ALTERNATIVES:
            errors.append(f"Ask the AI for {config.MIN_ALTERNATIVES}-{config.MAX_ALTERNATIVES} alternatives.")
    else:
        alts = [a.strip() for a in alternatives if a and a.strip()]
        if len({a.casefold() for a in alts}) != len(alts):
            errors.append("Alternative names must be unique.")
        if not config.MIN_ALTERNATIVES <= len(alts) <= config.MAX_ALTERNATIVES:
            errors.append(f"Enter {config.MIN_ALTERNATIVES}-{config.MAX_ALTERNATIVES} alternatives (one per line), "
                          "or let the AI suggest them.")
        if any(len(a) > 100 for a in alts):
            errors.append("Each alternative name must be 100 characters or fewer.")

    crits: list[CriterionInput] = []
    if use_ai_criteria:
        if not config.MIN_CRITERIA <= ai_criteria_count <= config.MAX_CRITERIA:
            errors.append(f"Ask the AI for {config.MIN_CRITERIA}-{config.MAX_CRITERIA} criteria.")
    else:
        rows = [c for c in criteria if str(c.get("name") or "").strip()]
        names = [str(c["name"]).strip() for c in rows]
        if len({n.casefold() for n in names}) != len(names):
            errors.append("Criterion names must be unique.")
        if not config.MIN_CRITERIA <= len(rows) <= config.MAX_CRITERIA:
            errors.append(f"Select {config.MIN_CRITERIA}-{config.MAX_CRITERIA} criteria, or let the AI suggest them.")
        parsed_weights = []
        for row in rows:
            name = str(row["name"]).strip()
            direction = row.get("direction") or "benefit"
            try:
                weight = 5.0 if row.get("weight") is None else float(row["weight"])
                if not math.isfinite(weight) or not config.WEIGHT_MIN <= weight <= config.WEIGHT_MAX:
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"The weight for '{name}' must be a number from 0 to 10.")
                continue
            if direction not in ("benefit", "cost"):
                errors.append(f"The type for '{name}' must be Benefit or Cost.")
                continue
            if len(name) > 60:
                errors.append(f"The criterion name '{name[:20]}…' is longer than 60 characters.")
                continue
            parsed_weights.append(weight)
            crits.append(CriterionInput(name=name, direction=direction, weight=weight))
        if parsed_weights and sum(parsed_weights) <= 0:
            errors.append("At least one criterion weight must be greater than zero.")

    if errors:
        return None, errors
    try:
        request = DecisionRequest(
            title=title, description=description,
            constraints=Constraints(budget=budget or "", time=time_limit or "", team=team or "", other=other_constraints or ""),
            priorities_note=priorities_note or "", alternatives=alts, criteria=crits,
            suggest_alternative_count=ai_alternative_count if use_ai_alternatives else config.MIN_ALTERNATIVES,
            suggest_criteria_count=ai_criteria_count if use_ai_criteria else config.MIN_CRITERIA,
        )
    except ValidationError:
        return None, ["Some inputs are invalid. Please review the form."]
    return request, []


# --------------------------------------------------------------------------- #
# Building analyses
# --------------------------------------------------------------------------- #
def build_analysis(request: DecisionRequest, payload: AnalysisPayload, *, mode: str,
                   model: str | None = None, scenario_key: str | None = None) -> dict:
    ratings: dict = {a.name: {} for a in payload.alternatives}
    rationales: dict = {a.name: {} for a in payload.alternatives}
    for r in payload.ratings:
        ratings[r.alternative][r.criterion] = float(r.rating)
        rationales[r.alternative][r.criterion] = r.rationale
    weights = {c.name: float(c.suggested_weight) for c in payload.criteria}
    constraints = request.constraints.model_dump()
    constraints["priorities_note"] = request.priorities_note
    rec = payload.initial_recommendation
    return {
        "uid": uuid.uuid4().hex[:12], "id": None,
        "title": request.title, "description": request.description,
        "mode": mode, "model": model, "scenario_key": scenario_key,
        "constraints": constraints,
        "summary": payload.summary.model_dump(),
        "alternatives": [a.model_dump() for a in payload.alternatives],
        "criteria": [c.model_dump(exclude={"suggested_weight"}) for c in payload.criteria],
        "ratings": ratings, "rationales": rationales,
        "original_weights": dict(weights), "weights": dict(weights),
        "risks": [r.model_dump() for r in payload.risks],
        "tradeoffs": [t.model_dump() for t in payload.tradeoffs],
        "assumptions": list(payload.assumptions), "limitations": list(payload.limitations),
        "verify_before_deciding": list(payload.verify_before_deciding),
        "initial_recommendation": rec.model_dump() if rec else None,
        "recommendation": None, "ratings_edited": False,
    }


def run_live_analysis(request: DecisionRequest, analyzer: DecisionAnalyzer) -> dict:
    payload = analyzer.analyze(request)
    return build_analysis(request, payload, mode="live", model=analyzer.provider.model)


def load_sample(key: str) -> dict:
    sample = SAMPLES[key]
    payload = AnalysisPayload.model_validate(sample["payload"])
    request = DecisionRequest(
        title=sample["title"], description=sample["description"],
        constraints=Constraints(**sample["constraints"]),
        alternatives=[a.name for a in payload.alternatives],
        criteria=[CriterionInput(name=c.name, direction=c.direction, weight=c.suggested_weight) for c in payload.criteria],
    )
    analysis = build_analysis(request, payload, mode="sample", scenario_key=key)
    analysis["recommendation"] = {**sample["recommendation"], "source": "sample"}
    return analysis


# --------------------------------------------------------------------------- #
# Scoring helpers (thin wrappers over the engine)
# --------------------------------------------------------------------------- #
def criteria_directions(analysis: dict) -> dict[str, str]:
    return {c["name"]: c["direction"] for c in analysis["criteria"]}


def compute_results(analysis: dict, weights: dict | None = None) -> list[se.ScoreResult]:
    return se.calculate_scores(
        [a["name"] for a in analysis["alternatives"]], criteria_directions(analysis),
        analysis["ratings"], weights if weights is not None else analysis["weights"])


def results_dataframe(analysis: dict, results: list[se.ScoreResult]) -> pd.DataFrame:
    info = {a["name"]: a for a in analysis["alternatives"]}
    rows = []
    for r in results:
        row = {"Rank": r.rank, "Alternative": r.alternative}
        for crit, value in r.criterion_scores.items():
            col = f"{crit} (criterion)" if crit in FIXED_COLUMNS else crit
            row[col] = se.round_score(value)
        row["Final Score"] = se.round_score(r.score)
        row["Key Advantage"] = info[r.alternative].get("key_advantage", "")
        row["Main Disadvantage"] = info[r.alternative].get("main_disadvantage", "")
        rows.append(row)
    return pd.DataFrame(rows)


def weight_change_summary(analysis: dict, new_weights: dict) -> str | None:
    """Markdown explanation of the effect of the current weights, or ``None`` if unchanged."""
    original = analysis["original_weights"]
    if all(abs(original[k] - new_weights[k]) < 1e-9 for k in original):
        return None
    return se.summarize_weight_change(original, new_weights, compute_results(analysis, original),
                                      compute_results(analysis, new_weights))


def why_ranked_first(analysis: dict, results: list[se.ScoreResult], weights: dict) -> str:
    top = results[0]
    others = results[1:]
    leads = [c for c in sorted(weights, key=lambda c: -weights[c])
             if weights[c] > 0 and all(top.criterion_scores[c] >= o.criterion_scores[c] for o in others)]
    weakest = min(top.criterion_scores, key=lambda c: (top.criterion_scores[c], c))
    text = f"**{top.alternative}** has the highest weighted score under the current weights."
    if leads:
        text += " It scores best (or equal best) on: " + ", ".join(leads[:3]) + "."
    text += f" Its weakest normalised criterion is {weakest} ({se.round_score(top.criterion_scores[weakest]):.2f}/10)."
    return text


def main_caveat(analysis: dict, results: list[se.ScoreResult]) -> str:
    top = results[0].alternative
    info = next(a for a in analysis["alternatives"] if a["name"] == top)
    parts = []
    if info.get("main_disadvantage"):
        parts.append(info["main_disadvantage"])
    risks = [r for r in analysis.get("risks", []) if r.get("alternative") == top]
    if risks:
        parts.append("Risk: " + risks[0]["description"])
    return " ".join(parts) or "Verify the AI-estimated ratings before relying on this ranking."


def initial_recommendation_note(analysis: dict, results: list[se.ScoreResult]) -> tuple[str, str] | None:
    init = analysis.get("initial_recommendation")
    if not init:
        return None
    top = results[0].alternative
    if init["alternative"] == top:
        return "agree", f"The AI's initial qualitative recommendation (**{top}**) matches the calculated top-ranked alternative."
    return "disagree", (
        f"The AI's initial qualitative recommendation was **{init['alternative']}**, but the calculated ranking "
        f"places **{top}** first. The ranking has not been altered. The AI may have weighed factors outside the "
        "listed criteria, or its implied priorities differ from the weights. Please review the ratings, weights "
        "and assumptions before deciding.")


def deterministic_recommendation(analysis: dict, results: list[se.ScoreResult]) -> dict:
    top = results[0]
    text = (f"Under the selected priorities, **{top.alternative}** ranks first with a weighted score of "
            f"{se.round_score(top.score):.2f}/10.")
    if len(results) > 1:
        text += f" The runner-up is {results[1].alternative} ({se.round_score(results[1].score):.2f}/10)."
    text += " " + why_ranked_first(analysis, results, analysis["weights"]).split("\n")[0]
    return {"explanation": text, "main_caveat": main_caveat(analysis, results),
            "source": "deterministic", "weights": dict(analysis["weights"])}


def attach_recommendation(analysis: dict, analyzer: DecisionAnalyzer | None = None) -> dict:
    """Create the recommendation text (live: LLM explanation; otherwise deterministic)."""
    results = compute_results(analysis)
    if analysis.get("mode") == "sample" and analysis.get("recommendation"):
        return analysis
    if analyzer is None:
        analysis["recommendation"] = deterministic_recommendation(analysis, results)
        return analysis
    try:
        expl = analyzer.explain(analysis, results)
        analysis["recommendation"] = {"explanation": expl.explanation, "main_caveat": expl.main_caveat,
                                      "source": "ai", "weights": dict(analysis["weights"])}
    except AIServiceError as exc:
        rec = deterministic_recommendation(analysis, results)
        rec["warning"] = f"The AI explanation was unavailable ({exc.message}). A calculated summary is shown instead."
        analysis["recommendation"] = rec
    return analysis
