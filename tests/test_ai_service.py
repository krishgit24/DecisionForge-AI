import json

import httpx
import openai
import pytest

import ai_service as ai
import decision_service as ds
from sample_data import SAMPLES


class FakeProvider(ai.LLMProvider):
    name, model = "fake", "fake-model"

    def __init__(self, replies):
        self.replies, self.calls = list(replies), 0

    def generate_json(self, system_prompt, user_prompt, response_model=None):
        self.calls += 1
        return self.replies[min(self.calls - 1, len(self.replies) - 1)]


def make_request(ai_lists=False):
    s = SAMPLES["tech_stack"]
    names = [a["name"] for a in s["payload"]["alternatives"]]
    crits = [{"name": c["name"], "direction": c["direction"], "weight": c["suggested_weight"]} for c in s["payload"]["criteria"]]
    req, errors = ds.validate_request(
        title=s["title"], description=s["description"], alternatives=[] if ai_lists else names,
        use_ai_alternatives=ai_lists, ai_alternative_count=4, criteria=[] if ai_lists else crits,
        use_ai_criteria=ai_lists, ai_criteria_count=6)
    assert not errors
    return req


GOOD = json.dumps(SAMPLES["tech_stack"]["payload"])


def test_valid_reply_is_parsed():
    payload = ai.DecisionAnalyzer(FakeProvider([GOOD])).analyze(make_request())
    assert len(payload.alternatives) == 4 and len(payload.ratings) == 24


def test_ai_suggested_lists_are_accepted():
    payload = ai.DecisionAnalyzer(FakeProvider([GOOD])).analyze(make_request(ai_lists=True))
    assert len(payload.criteria) == 6


def test_markdown_fenced_json_is_accepted():
    ai.DecisionAnalyzer(FakeProvider(["```json\n" + GOOD + "\n```"])).analyze(make_request())


def test_malformed_then_valid_uses_one_repair_retry():
    provider = FakeProvider(["not json at all", GOOD])
    ai.DecisionAnalyzer(provider).analyze(make_request())
    assert provider.calls == 2


def test_retries_are_bounded_and_failure_is_controlled():
    provider = FakeProvider(["{}garbage"])
    with pytest.raises(ai.AIServiceError) as err:
        ai.DecisionAnalyzer(provider).analyze(make_request())
    assert err.value.kind == "invalid_response" and provider.calls == 1 + ai.config.MAX_AI_REPAIRS
    assert "expected analysis format" in err.value.message
    assert "Please retry" in err.value.message


def test_pydantic_validation_failure_explains_field_without_echoing_input():
    class InvalidProvider(FakeProvider):
        def generate_json(self, system_prompt, user_prompt, response_model=None):
            self.calls += 1
            return json.dumps({"alternatives": "private user text"})

    provider = InvalidProvider([""])
    with pytest.raises(ai.AIServiceError) as err:
        ai.DecisionAnalyzer(provider).analyze(make_request())

    assert err.value.kind == "invalid_response"
    assert "alternatives" in err.value.message
    assert "private user text" not in err.value.message


def test_missing_ratings_are_rejected():
    data = json.loads(GOOD)
    data["ratings"] = data["ratings"][:-1]
    with pytest.raises(ai.AIServiceError):
        ai.DecisionAnalyzer(FakeProvider([json.dumps(data)])).analyze(make_request())


def test_out_of_range_rating_is_rejected():
    data = json.loads(GOOD)
    data["ratings"][0]["rating"] = 42
    with pytest.raises(ai.AIServiceError):
        ai.DecisionAnalyzer(FakeProvider([json.dumps(data)])).analyze(make_request())


def test_model_cannot_override_user_weights_or_direction():
    data = json.loads(GOOD)
    data["criteria"][0]["suggested_weight"] = 1
    data["criteria"][0]["direction"] = "benefit"
    payload = ai.DecisionAnalyzer(FakeProvider([json.dumps(data)])).analyze(make_request())
    assert payload.criteria[0].direction == "cost" and payload.criteria[0].suggested_weight == 9


def test_unsupported_request_is_reported():
    reply = json.dumps({"supported": False, "unsupported_reason": "Not a decision."})
    with pytest.raises(ai.AIServiceError) as err:
        ai.DecisionAnalyzer(FakeProvider([reply])).analyze(make_request())
    assert err.value.kind == "unsupported"


def test_explanation_failure_falls_back_to_deterministic_summary():
    a = ds.load_sample("tech_stack")
    a["mode"], a["recommendation"] = "live", None
    ds.attach_recommendation(a, ai.DecisionAnalyzer(FakeProvider(["nope"])))
    assert a["recommendation"]["source"] == "deterministic" and "warning" in a["recommendation"]


def test_explanation_success():
    a = ds.load_sample("tech_stack")
    a["mode"], a["recommendation"] = "live", None
    reply = json.dumps({"explanation": "Python + Streamlit fits.", "main_caveat": "Scalability."})
    ds.attach_recommendation(a, ai.DecisionAnalyzer(FakeProvider([reply])))
    assert a["recommendation"]["source"] == "ai"


def test_prompt_contains_no_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret-123")
    assert "sk-test-secret-123" not in ai.build_analysis_prompt(make_request())


# --- OpenAI error mapping (no network: the client is a stub) -----------------
class StubClient:
    def __init__(self, exc):
        self.chat = type("C", (), {"completions": type("X", (), {"create": staticmethod(lambda **kw: (_ for _ in ()).throw(exc))})()})()


REQ = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


@pytest.mark.parametrize("exc,kind", [
    (openai.APITimeoutError(request=REQ), "timeout"),
    (openai.APIConnectionError(request=REQ), "connection"),
    (openai.RateLimitError("rl", response=httpx.Response(429, request=REQ), body=None), "rate_limit"),
    (openai.AuthenticationError("bad key sk-secret", response=httpx.Response(401, request=REQ), body=None), "auth"),
])
def test_openai_errors_are_mapped_without_leaking_details(exc, kind):
    provider = ai.OpenAIProvider(client=StubClient(exc), model="m")
    with pytest.raises(ai.AIServiceError) as err:
        provider.generate_json("s", "u")
    assert err.value.kind == kind and "sk-secret" not in err.value.message


def test_missing_key_is_detected(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    with pytest.raises(ai.AIServiceError) as err:
        ai.OpenAIProvider()
    assert err.value.kind == "no_api_key"


def test_gemini_provider_uses_compatible_endpoint(monkeypatch):
    captured = {}

    def respond(request):
        captured["request"] = request
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]},
            request=request,
        )

    client = httpx.Client(transport=httpx.MockTransport(respond))
    provider = ai.GeminiProvider(api_key="local-test-key", model="gemini-test", client=client)

    assert provider.generate_json("system prompt", "user prompt", ai.AnalysisPayload) == '{"ok": true}'
    assert captured["request"].url == (
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent"
    )
    assert captured["request"].headers["x-goog-api-key"] == "local-test-key"
    assert "local-test-key" not in str(captured["request"].url)
    assert captured["payload"]["systemInstruction"]["parts"][0]["text"] == "system prompt"
    assert captured["payload"]["contents"][0]["parts"][0]["text"] == "user prompt"
    assert captured["payload"]["generationConfig"]["responseMimeType"] == "application/json"
    assert captured["payload"]["generationConfig"]["responseJsonSchema"]["properties"]["ratings"]["type"] == "array"
    assert captured["payload"]["generationConfig"]["thinkingConfig"]["thinkingLevel"] == "minimal"
    client.close()


@pytest.mark.parametrize(
    "status,message,kind,retryable",
    [
        (401, "bad key", "auth", False),
        (403, "permission denied", "auth", False),
        (404, "model unavailable", "request", False),
        (429, "quota exceeded", "rate_limit", False),
        (503, "service unavailable", "api", True),
    ],
)
def test_gemini_http_errors_are_mapped_without_leaking_details(status, message, kind, retryable):
    def respond(request):
        return httpx.Response(status, json={"error": {"message": message}}, request=request)

    client = httpx.Client(transport=httpx.MockTransport(respond))
    provider = ai.GeminiProvider(api_key="local-test-secret", model="gemini-test", client=client)
    with pytest.raises(ai.AIServiceError) as err:
        provider.generate_json("system", "user")
    assert err.value.kind == kind and err.value.retryable is retryable
    assert "local-test-secret" not in err.value.message
    client.close()


def test_gemini_timeout_is_reported_as_retryable():
    def respond(request):
        raise httpx.ReadTimeout("request timed out", request=request)

    client = httpx.Client(transport=httpx.MockTransport(respond))
    provider = ai.GeminiProvider(api_key="local-test-key", model="gemini-test", client=client)
    with pytest.raises(ai.AIServiceError) as err:
        provider.generate_json("system", "user")
    assert err.value.kind == "timeout" and err.value.retryable
    client.close()


def test_provider_selection_prefers_gemini_key(monkeypatch):
    monkeypatch.setattr(ai.config, "AI_PROVIDER", "")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")

    assert ai.config.get_provider_name() == "gemini"
    assert ai.config.get_provider_api_key() == "gemini-test-key"
