"""UI smoke tests using Streamlit's AppTest (no network, temp database)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import config
import database

TIMEOUT = 60
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "ui.db")
    monkeypatch.setattr(config, "AI_PROVIDER", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")


def page(name):
    """Enter through app.py (like a real user) and switch to the requested page."""
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=TIMEOUT).run()
    if name != "app.py":
        at.switch_page(name)
    return at


def test_home_page_renders():
    at = page("app.py").run()
    assert not at.exception


def test_about_page_renders():
    at = page("pages/3_About_Project.py").run()
    assert not at.exception


def test_history_empty_state():
    at = page("pages/2_Analysis_History.py").run()
    assert not at.exception
    assert any("No saved analyses" in i.value for i in at.info)


def test_new_analysis_without_key_defaults_to_sample_and_full_flow():
    at = page("pages/1_New_Analysis.py").run()
    assert not at.exception
    assert at.radio(key="na_mode").value == "Sample demo"
    at.button(key="na_load_sample").click().run()
    assert not at.exception
    at.button(key="na_confirm").click().run()
    assert not at.exception
    assert any("Sample Demo" in w.value for w in at.warning)

    # change weights: scalability up, cost down -> leader should change to Django
    prefix = "new_" + at.session_state["na_analysis"]["uid"]
    for idx, val in enumerate([3.0, 5.0, 4.0, 10.0, 7.0, 4.0]):
        at.slider(key=f"{prefix}_w_{idx}").set_value(val)
    at.run()
    assert not at.exception
    assert any("leading alternative changed" in i.value for i in at.info)
    assert any("Django + Bootstrap" in m.value for m in at.markdown)

    at.button(key=f"{prefix}_reset").click().run()
    assert not at.exception
    assert any("Using the original weights" in c.value for c in at.caption)

    # save -> appears in history after a "restart" (fresh AppTest)
    at.button(key="na_save").click().run()
    assert not at.exception
    assert len(database.list_analyses()) == 1

    hist = page("pages/2_Analysis_History.py").run()
    assert not hist.exception
    assert not any("No saved analyses" in i.value for i in hist.info)
    hist.button(key="hist_1_del").click().run()
    hist.button(key="hist_1_yes").click().run()
    assert not hist.exception
    assert database.list_analyses() == []


def test_live_mode_without_key_disables_generate():
    at = page("pages/1_New_Analysis.py").run()
    at.radio(key="na_mode").set_value("Live GenAI").run()
    assert not at.exception
    assert at.button(key="na_generate").disabled


# --- live-mode UI flow with a fake provider (no network) ----------------------
import json

import ai_service
from sample_data import SAMPLES


class _FakeProvider(ai_service.LLMProvider):
    name, model = "fake", "fake-model"
    fail = False

    def generate_json(self, system_prompt, user_prompt, response_model=None):
        if _FakeProvider.fail:
            raise ai_service.AIServiceError("Rate limit reached. Please wait a minute and try again.", "rate_limit", retryable=True)
        if "explain a decision ranking" in system_prompt:
            return json.dumps({"explanation": "Fake explanation naming the top option.", "main_caveat": "Fake caveat."})
        return json.dumps(SAMPLES["tech_stack"]["payload"])


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    monkeypatch.setattr(ai_service, "OpenAIProvider", lambda *a, **k: _FakeProvider())
    _FakeProvider.fail = False
    yield _FakeProvider
    _FakeProvider.fail = False


def test_live_flow_validation_generation_and_ai_explanation(live):
    at = page("pages/1_New_Analysis.py").run()
    assert at.radio(key="na_mode").value == "Live GenAI"

    at.button(key="na_generate").click().run()  # empty form -> friendly errors, no AI call
    assert len(at.error) >= 2 and at.session_state["na_stage"] == "input"

    at.button(key="na_fill").click().run()
    at.button(key="na_generate").click().run()
    assert not at.exception and not at.error
    assert at.session_state["na_stage"] == "review"
    assert at.session_state["na_analysis"]["mode"] == "live"

    at.button(key="na_confirm").click().run()
    assert not at.exception and at.session_state["na_stage"] == "results"
    assert at.session_state["na_analysis"]["recommendation"]["source"] == "ai"
    assert not any("Sample Demo" in w.value for w in at.warning)


def test_live_failure_shows_error_and_retry_is_possible(live):
    at = page("pages/1_New_Analysis.py").run()
    at.button(key="na_fill").click().run()
    live.fail = True
    at.button(key="na_generate").click().run()
    assert not at.exception and at.session_state["na_stage"] == "input"
    assert any("Rate limit" in e.value for e in at.error)
    live.fail = False
    at.button(key="na_retry").click().run()
    assert not at.exception and at.session_state["na_stage"] == "review"
