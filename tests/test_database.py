import sqlite3

import pytest

import database as db
import decision_service as ds


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    db.init_db(path)
    return path


def sample():
    return ds.load_sample("tech_stack")


def test_init_creates_table_and_is_idempotent(tmp_path):
    path = tmp_path / "nested" / "x.db"
    db.init_db(path)
    db.init_db(path)
    with sqlite3.connect(path) as conn:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    assert "analyses" in names


def test_save_and_reload_round_trip(db_path):
    a = sample()
    results = ds.compute_results(a)
    new_id = db.save_analysis(a, results, db_path)
    loaded = db.get_analysis(new_id, db_path)
    assert loaded["title"] == a["title"]
    assert loaded["ratings"] == a["ratings"]
    assert loaded["original_weights"] == a["original_weights"]
    assert loaded["rankings"][0]["alternative"] == results[0].alternative
    assert loaded["final_scores"][results[0].alternative] == pytest.approx(results[0].score)
    assert ds.compute_results(loaded)[0].alternative == results[0].alternative


def test_persistence_across_new_connections(db_path):
    a = sample()
    db.save_analysis(a, ds.compute_results(a), db_path)
    db.save_analysis(ds.load_sample("pm_tools"), ds.compute_results(ds.load_sample("pm_tools")), db_path)
    # simulate an app restart: nothing cached, brand-new connection, init again
    db.init_db(db_path)
    rows = db.list_analyses(db_path)
    assert len(rows) == 2 and rows[0]["id"] > rows[1]["id"]


def test_update_weights_changes_ranking_and_keeps_original(db_path):
    a = sample()
    i = db.save_analysis(a, ds.compute_results(a), db_path)
    new_w = {"Budget Cost": 3, "Time to Build": 5, "Learning Curve": 4, "Scalability": 10, "Maintainability": 7, "Community Support": 4}
    assert db.update_weights(i, new_w, ds.compute_results(a, new_w), db_path)
    loaded = db.get_analysis(i, db_path)
    assert loaded["weights"] == new_w
    assert loaded["original_weights"] == a["original_weights"]
    assert loaded["rankings"][0]["alternative"] == "Django + Bootstrap"


def test_delete_and_missing(db_path):
    a = sample()
    i = db.save_analysis(a, ds.compute_results(a), db_path)
    assert db.delete_analysis(i, db_path) is True
    assert db.get_analysis(i, db_path) is None
    assert db.delete_analysis(i, db_path) is False


def test_no_api_key_is_stored(db_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret-123")
    a = sample()
    db.save_analysis(a, ds.compute_results(a), db_path)
    with sqlite3.connect(db_path) as conn:
        dump = "\n".join(conn.iterdump())
    assert "sk-test-secret-123" not in dump


def test_corrupted_row_raises_friendly_error(db_path):
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO analyses (title, created_at, updated_at, ratings) VALUES ('x','t','t','{bad')")
    with pytest.raises(db.DatabaseError):
        db.get_analysis(1, db_path)
