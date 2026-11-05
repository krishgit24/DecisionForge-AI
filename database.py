"""SQLite persistence for saved analyses (standard-library ``sqlite3`` only).

Structured fields are stored as JSON text. API keys are never stored.
The default path is resolved at call time from ``config.DB_PATH`` so tests can
redirect it to a temporary file.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

import config


class DatabaseError(Exception):
    """Friendly wrapper around sqlite3 errors."""


SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT NOT NULL,
    description      TEXT NOT NULL DEFAULT '',
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    mode             TEXT NOT NULL DEFAULT 'live',
    model            TEXT,
    constraints_json TEXT NOT NULL DEFAULT '{}',
    alternatives     TEXT NOT NULL DEFAULT '[]',
    criteria         TEXT NOT NULL DEFAULT '[]',
    original_weights TEXT NOT NULL DEFAULT '{}',
    updated_weights  TEXT NOT NULL DEFAULT '{}',
    ratings          TEXT NOT NULL DEFAULT '{}',
    final_scores     TEXT NOT NULL DEFAULT '{}',
    rankings         TEXT NOT NULL DEFAULT '[]',
    ai_content       TEXT NOT NULL DEFAULT '{}'
);
"""

# Keys of the in-memory analysis dict that are stored inside ``ai_content``.
_AI_KEYS = (
    "summary", "rationales", "risks", "tradeoffs", "assumptions", "limitations",
    "verify_before_deciding", "initial_recommendation", "recommendation",
    "ratings_edited", "scenario_key",
)


def _path(db_path: Optional[Path | str]) -> Path:
    return Path(db_path) if db_path else Path(config.DB_PATH)


@contextmanager
def get_connection(db_path: Optional[Path | str] = None) -> Iterator[sqlite3.Connection]:
    path = _path(db_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, timeout=10)
        conn.row_factory = sqlite3.Row
    except (sqlite3.Error, OSError) as exc:
        raise DatabaseError(f"Could not open the database: {exc}") from exc
    try:
        yield conn
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise DatabaseError(f"Database operation failed: {exc}") from exc
    finally:
        conn.close()


def init_db(db_path: Optional[Path | str] = None) -> None:
    """Create the schema if needed. Safe to call on every start-up."""
    with get_connection(db_path) as conn:
        conn.execute(SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _results_json(results) -> tuple[dict, list]:
    scores = {r.alternative: r.score for r in results}
    rankings = [{"rank": r.rank, "alternative": r.alternative, "score": r.score} for r in results]
    return scores, rankings


def save_analysis(analysis: dict, results, db_path: Optional[Path | str] = None) -> int:
    scores, rankings = _results_json(results)
    now = _now()
    ai_content = {k: analysis.get(k) for k in _AI_KEYS}
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO analyses (title, description, created_at, updated_at, mode, model,
               constraints_json, alternatives, criteria, original_weights, updated_weights,
               ratings, final_scores, rankings, ai_content)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                analysis["title"], analysis.get("description", ""), now, now,
                analysis.get("mode", "live"), analysis.get("model"),
                _dumps(analysis.get("constraints", {})), _dumps(analysis["alternatives"]),
                _dumps(analysis["criteria"]), _dumps(analysis["original_weights"]),
                _dumps(analysis["weights"]), _dumps(analysis["ratings"]),
                _dumps(scores), _dumps(rankings), _dumps(ai_content),
            ),
        )
        return int(cur.lastrowid)


def update_weights(analysis_id: int, weights: dict, results, db_path: Optional[Path | str] = None) -> bool:
    scores, rankings = _results_json(results)
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "UPDATE analyses SET updated_weights=?, final_scores=?, rankings=?, updated_at=? WHERE id=?",
            (_dumps(weights), _dumps(scores), _dumps(rankings), _now(), analysis_id),
        )
        return cur.rowcount > 0


def list_analyses(db_path: Optional[Path | str] = None) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, mode, alternatives, criteria, rankings "
            "FROM analyses ORDER BY id DESC"
        ).fetchall()
    out = []
    for row in rows:
        rankings = json.loads(row["rankings"])
        top = rankings[0] if rankings else {}
        out.append({
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "mode": row["mode"],
            "n_alternatives": len(json.loads(row["alternatives"])),
            "n_criteria": len(json.loads(row["criteria"])),
            "top_alternative": top.get("alternative", "—"),
            "top_score": top.get("score"),
        })
    return out


def get_analysis(analysis_id: int, db_path: Optional[Path | str] = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM analyses WHERE id=?", (analysis_id,)).fetchone()
    if row is None:
        return None
    try:
        analysis = {
            "id": row["id"],
            "uid": f"db{row['id']}",
            "title": row["title"],
            "description": row["description"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "mode": row["mode"],
            "model": row["model"],
            "constraints": json.loads(row["constraints_json"]),
            "alternatives": json.loads(row["alternatives"]),
            "criteria": json.loads(row["criteria"]),
            "original_weights": json.loads(row["original_weights"]),
            "weights": json.loads(row["updated_weights"]),
            "ratings": json.loads(row["ratings"]),
            "final_scores": json.loads(row["final_scores"]),
            "rankings": json.loads(row["rankings"]),
        }
        analysis.update(json.loads(row["ai_content"]))
    except json.JSONDecodeError as exc:
        raise DatabaseError("The saved analysis is corrupted and cannot be opened.") from exc
    return analysis


def delete_analysis(analysis_id: int, db_path: Optional[Path | str] = None) -> bool:
    with get_connection(db_path) as conn:
        cur = conn.execute("DELETE FROM analyses WHERE id=?", (analysis_id,))
        return cur.rowcount > 0
