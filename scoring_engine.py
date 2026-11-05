"""Deterministic weighted multi-criteria scoring engine.

This module is intentionally independent of Streamlit, the database and any
LLM provider. Given ratings and weights it always produces the same ranking.

Method
------
* Every alternative i receives a raw rating on every criterion j, in [1, 10].
* Criteria are either ``benefit`` (a higher raw rating is better) or ``cost``
  (a higher raw rating means more cost / effort / time, which is worse).
* Normalised rating:   r(i,j) = raw            for benefit criteria
                       r(i,j) = 11 - raw       for cost criteria
  so a better outcome always receives a higher score on the same 1-10 scale.
* Weighted score:      S(i) = SUM_j( w(j) * r(i,j) ) / SUM_j( w(j) )
  which is a weighted average and therefore always lies between 1 and 10.
* Ranking: descending S(i). Ties (equal to 9 decimals) are broken by the
  normalised rating on the most heavily weighted criterion, then the next one,
  and finally alphabetically, so the order is always reproducible.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

RATING_MIN = 1.0
RATING_MAX = 10.0
BENEFIT = "benefit"
COST = "cost"
VALID_DIRECTIONS = (BENEFIT, COST)
DISPLAY_DECIMALS = 2
CLOSE_MARGIN = 0.25  # score gap below which a lead is described as narrow
_TIE_DECIMALS = 9


class ScoringError(ValueError):
    """Raised when scoring inputs are invalid."""


# --------------------------------------------------------------------------- #
# Validation helpers
# --------------------------------------------------------------------------- #
def _is_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def round_score(value: float) -> float:
    """The single rounding rule used everywhere scores are displayed."""
    return round(float(value), DISPLAY_DECIMALS)


def validate_weights(weights: Mapping[str, float]) -> dict[str, float]:
    """Return a clean copy of ``weights`` or raise :class:`ScoringError`."""
    if not weights:
        raise ScoringError("At least one criterion weight is required.")
    clean: dict[str, float] = {}
    for name, weight in weights.items():
        if not _is_number(weight):
            raise ScoringError(f"The weight for '{name}' must be a finite number.")
        if weight < 0:
            raise ScoringError(f"The weight for '{name}' cannot be negative.")
        clean[name] = float(weight)
    if sum(clean.values()) <= 0:
        raise ScoringError("At least one criterion weight must be greater than zero.")
    return clean


def validate_rating(rating: object, label: str = "rating") -> float:
    if not _is_number(rating):
        raise ScoringError(f"The {label} must be a finite number.")
    if not RATING_MIN <= rating <= RATING_MAX:
        raise ScoringError(
            f"The {label} ({rating}) must be between {RATING_MIN:g} and {RATING_MAX:g}."
        )
    return float(rating)


def normalize_rating(rating: float, direction: str, label: str = "rating") -> float:
    """Convert a raw rating into a benefit-oriented score (higher is better)."""
    if direction not in VALID_DIRECTIONS:
        raise ScoringError(f"Criterion direction must be 'benefit' or 'cost', got '{direction}'.")
    value = validate_rating(rating, label)
    if direction == BENEFIT:
        return value
    return RATING_MIN + RATING_MAX - value


def normalize_weights(weights: Mapping[str, float]) -> dict[str, float]:
    """Weights expressed as fractions that sum to 1 (their share of importance)."""
    clean = validate_weights(weights)
    total = math.fsum(clean.values())
    return {name: w / total for name, w in clean.items()}


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ScoreResult:
    alternative: str
    rank: int
    score: float  # full precision; use round_score() for display
    criterion_scores: dict  # normalised, benefit-oriented scores per criterion
    raw_ratings: dict  # the ratings as entered / generated
    tied_with: tuple = ()


def calculate_scores(
    alternatives: Sequence[str],
    criteria: Mapping[str, str],
    ratings: Mapping[str, Mapping[str, float]],
    weights: Mapping[str, float],
) -> list[ScoreResult]:
    """Score and rank alternatives.

    Parameters
    ----------
    alternatives: ordered alternative names (must be unique and non-empty)
    criteria:     criterion name -> "benefit" | "cost"
    ratings:      alternative -> criterion -> raw rating in [1, 10]
    weights:      criterion -> non-negative weight (not all zero)
    """
    if not alternatives:
        raise ScoringError("At least one alternative is required.")
    if len(set(alternatives)) != len(alternatives):
        raise ScoringError("Alternative names must be unique.")
    if not criteria:
        raise ScoringError("At least one criterion is required.")

    clean_weights = validate_weights(weights)
    if set(clean_weights) != set(criteria):
        raise ScoringError("Weights must be provided for exactly the defined criteria.")
    for name, direction in criteria.items():
        if direction not in VALID_DIRECTIONS:
            raise ScoringError(f"Criterion '{name}' must be 'benefit' or 'cost'.")

    total_weight = math.fsum(clean_weights.values())
    priority_order = sorted(criteria, key=lambda c: (-clean_weights[c], c.casefold()))

    staged = []
    for alt in alternatives:
        if alt not in ratings:
            raise ScoringError(f"No ratings were provided for '{alt}'.")
        normalized: dict[str, float] = {}
        raw: dict[str, float] = {}
        for crit, direction in criteria.items():
            if crit not in ratings[alt]:
                raise ScoringError(f"Missing rating for '{alt}' on '{crit}'.")
            label = f"rating for '{alt}' on '{crit}'"
            raw[crit] = validate_rating(ratings[alt][crit], label)
            normalized[crit] = normalize_rating(raw[crit], direction, label)
        weighted = math.fsum(clean_weights[c] * normalized[c] for c in criteria) / total_weight
        weighted = min(RATING_MAX, max(RATING_MIN, weighted))  # guard float drift
        staged.append((alt, weighted, normalized, raw))

    def sort_key(item):
        alt, score, normalized, _ = item
        return (
            -round(score, _TIE_DECIMALS),
            *[-round(normalized[c], _TIE_DECIMALS) for c in priority_order],
            alt.casefold(),
        )

    staged.sort(key=sort_key)

    results = []
    for position, (alt, score, normalized, raw) in enumerate(staged, start=1):
        tied = tuple(
            other
            for other, other_score, _, _ in staged
            if other != alt and round(other_score, _TIE_DECIMALS) == round(score, _TIE_DECIMALS)
        )
        results.append(
            ScoreResult(
                alternative=alt,
                rank=position,
                score=score,
                criterion_scores=normalized,
                raw_ratings=raw,
                tied_with=tied,
            )
        )
    return results


# --------------------------------------------------------------------------- #
# Comparing rankings after a weight change
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RankingComparison:
    old_leader: str
    new_leader: str
    leader_changed: bool
    order_changed: bool
    movements: tuple  # (alternative, old_rank, new_rank, old_score, new_score)
    new_margin: float  # score gap between first and second place


def compare_rankings(old: Sequence[ScoreResult], new: Sequence[ScoreResult]) -> RankingComparison:
    if not old or not new:
        raise ScoringError("Both rankings must contain at least one alternative.")
    old_by_name = {r.alternative: r for r in old}
    movements = []
    for r in new:
        if r.alternative not in old_by_name:
            raise ScoringError("Rankings must contain the same alternatives.")
        o = old_by_name[r.alternative]
        movements.append((r.alternative, o.rank, r.rank, o.score, r.score))
    margin = new[0].score - new[1].score if len(new) > 1 else 0.0
    return RankingComparison(
        old_leader=old[0].alternative,
        new_leader=new[0].alternative,
        leader_changed=old[0].alternative != new[0].alternative,
        order_changed=any(m[1] != m[2] for m in movements),
        movements=tuple(movements),
        new_margin=margin,
    )


def summarize_weight_change(
    old_weights: Mapping[str, float],
    new_weights: Mapping[str, float],
    old: Sequence[ScoreResult],
    new: Sequence[ScoreResult],
) -> str:
    """Plain-language (Markdown) explanation built only from actual numbers."""
    changes = []
    for name in new_weights:
        before, after = old_weights.get(name, 0.0), new_weights[name]
        if abs(before - after) > 1e-9:
            arrow = "↑" if after > before else "↓"
            changes.append(f"{name} {before:g} → {after:g} {arrow}")
    if not changes:
        return "The weights are identical to the original weights, so the ranking is unchanged."

    cmp = compare_rankings(old, new)
    old_top, new_top = old[0], new[0]
    parts = ["**Weight changes:** " + "; ".join(changes) + "."]
    if cmp.leader_changed:
        old_leader_new_score = next(m[4] for m in cmp.movements if m[0] == cmp.old_leader)
        parts.append(
            f"**The leading alternative changed.** *{cmp.old_leader}* led with "
            f"{round_score(old_top.score):.2f}; under the revised weights it scores "
            f"{round_score(old_leader_new_score):.2f} and *{cmp.new_leader}* now leads with "
            f"{round_score(new_top.score):.2f}."
        )
    else:
        parts.append(
            f"**The leading alternative did not change.** *{cmp.new_leader}* remains first "
            f"({round_score(old_top.score):.2f} → {round_score(new_top.score):.2f}) "
            "under the revised priorities."
        )
    moved = [m for m in cmp.movements if m[1] != m[2]]
    if moved:
        parts.append(
            "Rank movements: "
            + "; ".join(f"{m[0]} #{m[1]} → #{m[2]}" for m in moved)
            + "."
        )
    else:
        parts.append("The full ranking order is unchanged.")
    if len(new) > 1 and cmp.new_margin < CLOSE_MARGIN:
        parts.append(
            f"The gap between first and second place is only {round_score(cmp.new_margin):.2f} "
            "points, so this result is sensitive to the ratings and weights."
        )
    return "\n\n".join(parts)
