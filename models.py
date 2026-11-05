"""Pydantic schemas.

* ``DecisionRequest`` - validated user input.
* ``AnalysisPayload`` - the structured JSON the LLM must return. The LLM supplies
  *qualitative content and raw 1-10 ratings*; it never supplies final scores.
* ``RecommendationExplanation`` - the LLM's explanation of the calculated ranking.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

import config


class _Base(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


# --------------------------------------------------------------------------- #
# User input
# --------------------------------------------------------------------------- #
class Constraints(_Base):
    budget: str = Field(default="", max_length=500)
    time: str = Field(default="", max_length=500)
    team: str = Field(default="", max_length=500)
    other: str = Field(default="", max_length=1000)


class CriterionInput(_Base):
    name: str = Field(min_length=1, max_length=60)
    direction: Literal["benefit", "cost"] = "benefit"
    weight: float = Field(default=5.0, ge=config.WEIGHT_MIN, le=config.WEIGHT_MAX)


class DecisionRequest(_Base):
    title: str = Field(min_length=1, max_length=150)
    description: str = Field(min_length=1, max_length=3000)
    constraints: Constraints = Field(default_factory=Constraints)
    priorities_note: str = Field(default="", max_length=500)
    alternatives: list[str] = Field(default_factory=list)  # empty => AI suggests
    suggest_alternative_count: int = Field(default=4, ge=config.MIN_ALTERNATIVES, le=config.MAX_ALTERNATIVES)
    criteria: list[CriterionInput] = Field(default_factory=list)  # empty => AI suggests
    suggest_criteria_count: int = Field(default=5, ge=config.MIN_CRITERIA, le=config.MAX_CRITERIA)

    @property
    def needs_alternatives(self) -> bool:
        return not self.alternatives

    @property
    def needs_criteria(self) -> bool:
        return not self.criteria


# --------------------------------------------------------------------------- #
# LLM output
# --------------------------------------------------------------------------- #
class DecisionSummary(_Base):
    restated_decision: str = ""
    key_considerations: list[str] = Field(default_factory=list)


class AlternativeInfo(_Base):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    strengths: list[str] = Field(min_length=1)
    weaknesses: list[str] = Field(min_length=1)
    suitable_use_cases: list[str] = Field(default_factory=list)
    key_advantage: str = ""
    main_disadvantage: str = ""


class CriterionSpec(_Base):
    name: str = Field(min_length=1, max_length=60)
    description: str = ""
    direction: Literal["benefit", "cost"]
    suggested_weight: float = Field(default=5.0, ge=config.WEIGHT_MIN, le=config.WEIGHT_MAX)

    @field_validator("direction", mode="before")
    @classmethod
    def _norm_direction(cls, v):
        return str(v).strip().lower()


class RatingItem(_Base):
    alternative: str = Field(min_length=1)
    criterion: str = Field(min_length=1)
    rating: float = Field(ge=config.RATING_MIN, le=config.RATING_MAX)
    rationale: str = ""


class RiskItem(_Base):
    alternative: str = "General"
    description: str = Field(min_length=1)
    impact: str = ""
    likelihood: Literal["Low", "Medium", "High"] = "Medium"
    mitigation: str = ""

    @field_validator("likelihood", mode="before")
    @classmethod
    def _norm_likelihood(cls, v):
        return str(v).strip().capitalize()


class TradeOffItem(_Base):
    alternative: str = Field(min_length=1)
    gains: str = ""
    sacrifices: str = ""


class InitialRecommendation(_Base):
    alternative: str = Field(min_length=1)
    reasoning: str = ""


class AnalysisPayload(_Base):
    supported: bool = True
    unsupported_reason: str = ""
    summary: DecisionSummary = Field(default_factory=DecisionSummary)
    alternatives: list[AlternativeInfo] = Field(default_factory=list)
    criteria: list[CriterionSpec] = Field(default_factory=list)
    ratings: list[RatingItem] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)
    tradeoffs: list[TradeOffItem] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    verify_before_deciding: list[str] = Field(default_factory=list)
    initial_recommendation: Optional[InitialRecommendation] = None


class RecommendationExplanation(_Base):
    explanation: str = Field(min_length=1)
    main_caveat: str = ""
