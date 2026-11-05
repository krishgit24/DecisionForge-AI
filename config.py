"""Central configuration for DecisionForge AI.

Provider credentials come from environment variables (optionally loaded from
a local ``.env`` file). They are read lazily and never logged or stored.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

APP_NAME = "DecisionForge AI"
APP_TAGLINE = "An Explainable Generative AI System for Multi-Criteria Decision Analysis"

# --- Limits used by validation, the scoring engine and the AI prompts -------
MIN_ALTERNATIVES = 2
MAX_ALTERNATIVES = 6
MIN_CRITERIA = 3
MAX_CRITERIA = 7
WEIGHT_MIN = 0.0
WEIGHT_MAX = 10.0
RATING_MIN = 1.0
RATING_MAX = 10.0

# --- AI settings -------------------------------------------------------------
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "").strip() or "gemini-3.1-flash-lite"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "").strip() or "gpt-4o-mini"
AI_PROVIDER = os.getenv("AI_PROVIDER", "").strip().lower()
# Number of *repair* attempts after the first call when the model returns
# malformed JSON. Total calls per step are therefore 1 + MAX_AI_REPAIRS.
MAX_AI_REPAIRS = 1

_PLACEHOLDER_KEYS = {
    "", "your_openai_api_key_here", "your_gemini_api_key_here",
    "sk-your-key-here", "changeme",
}


def _float_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, "") or default)
        return value if value > 0 else default
    except ValueError:
        return default


AI_TIMEOUT_SECONDS = _float_env(
    "AI_TIMEOUT_SECONDS", _float_env("OPENAI_TIMEOUT_SECONDS", 60.0))
OPENAI_TIMEOUT_SECONDS = AI_TIMEOUT_SECONDS


def get_api_key() -> str | None:
    """Return the OpenAI API key or ``None``. Never log the return value."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key.lower() in _PLACEHOLDER_KEYS:
        return None
    return key


def get_gemini_api_key() -> str | None:
    """Return the Gemini API key or ``None``. Never log the return value."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key.lower() in _PLACEHOLDER_KEYS:
        return None
    return key


def get_provider_name() -> str:
    """Choose the explicitly requested provider, or an available configured one."""
    if AI_PROVIDER in {"gemini", "openai"}:
        return AI_PROVIDER
    if get_gemini_api_key():
        return "gemini"
    if get_api_key():
        return "openai"
    return "gemini"


def get_provider_model() -> str:
    return GEMINI_MODEL if get_provider_name() == "gemini" else OPENAI_MODEL


def get_provider_display_name() -> str:
    return "Gemini" if get_provider_name() == "gemini" else "OpenAI"


def get_provider_api_key() -> str | None:
    return get_gemini_api_key() if get_provider_name() == "gemini" else get_api_key()


def has_api_key() -> bool:
    return get_provider_api_key() is not None


# --- Database ----------------------------------------------------------------
def _resolve_db_path() -> Path:
    raw = os.getenv("DATABASE_PATH", "").strip()
    if not raw:
        return BASE_DIR / "data" / "decisionforge.db"
    path = Path(raw)
    return path if path.is_absolute() else BASE_DIR / path


# Resolved at import time; tests monkeypatch this attribute.
DB_PATH: Path = _resolve_db_path()
