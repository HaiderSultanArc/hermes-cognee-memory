from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from hermes_cognee_memory.client import (
    CogneeAPIError,
    CogneeClient,
    _NoRedirectHandler,
    normalize_service_url,
)


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def read(self, *_args):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_normalize_service_url_accepts_server_root_and_api_prefix():
    assert normalize_service_url("http://localhost:8000/") == "http://localhost:8000"
    assert normalize_service_url("https://memory.example/api/v1/") == "https://memory.example"


@pytest.mark.parametrize(
    "value",
    [
        "file:///etc/passwd",
        "memory.example",
        "https://user:pass@memory.example",
        "https://memory.example/path",
        "https://memory.example?debug=1",
        "http://:8000",
        "http://localhost:notaport",
    ],
)
def test_normalize_service_url_rejects_unsafe_or_ambiguous_urls(value):
    with pytest.raises(ValueError):
        normalize_service_url(value)


def test_redirect_handler_never_forwards_api_key_headers():
    handler = _NoRedirectHandler()
    request = handler.redirect_request(
        None,
        None,
        302,
        "Found",
        {"Location": "https://attacker.example/stolen"},
        "https://attacker.example/stolen",
    )
    assert request is None


def test_recall_posts_expected_payload_and_api_key(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return FakeResponse(
            [
                {
                    "source": "graph",
                    "kind": "graph_completion",
                    "search_type": "GRAPH_COMPLETION",
                    "text": "Haider prefers boring solutions.",
                }
            ]
        )

    monkeypatch.setattr("hermes_cognee_memory.client.urlopen", fake_urlopen)
    client = CogneeClient(
        "http://localhost:8000/api/v1",
        api_key="secret",
        timeout=7.5,
        graph_recall_timeout=8.5,
    )

    result = client.recall(
        "What does Haider prefer?",
        dataset_name="hermes-arcion",
        session_id="session-1",
        scope=["session", "graph"],
        top_k=6,
    )

    request = seen["request"]
    assert request.full_url == "http://localhost:8000/api/v1/recall"
    assert request.get_header("X-api-key") == "secret"
    assert request.get_header("Content-type") == "application/json"
    assert seen["timeout"] == 8.5
    assert json.loads(request.data) == {
        "query": "What does Haider prefer?",
        "search_type": None,
        "datasets": ["hermes-arcion"],
        "session_id": "session-1",
        "scope": ["session", "graph"],
        "top_k": 6,
        "only_context": False,
        "include_references": True,
    }
    assert result[0]["text"] == "Haider prefers boring solutions."


def test_remember_qa_posts_typed_entry(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["request"] = request
        return FakeResponse({"status": "session_stored", "entry_type": "qa", "entry_id": "q1"})

    monkeypatch.setattr("hermes_cognee_memory.client.urlopen", fake_urlopen)
    client = CogneeClient("http://localhost:8000", api_key="")

    response = client.remember_qa(
        question="What should we use?",
        answer="Use the boring solution.",
        context="Hermes conversation",
        dataset_name="hermes-arcion",
        session_id="session-1",
    )

    request = seen["request"]
    assert request.full_url == "http://localhost:8000/api/v1/remember/entry"
    assert request.get_header("X-api-key") is None
    assert json.loads(request.data) == {
        "entry": {
            "type": "qa",
            "question": "What should we use?",
            "answer": "Use the boring solution.",
            "context": "Hermes conversation",
        },
        "dataset_name": "hermes-arcion",
        "session_id": "session-1",
    }
    assert response["entry_id"] == "q1"


def test_improve_sessions_posts_background_persistence_request(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return FakeResponse({"status": "queued"})

    monkeypatch.setattr("hermes_cognee_memory.client.urlopen", fake_urlopen)
    client = CogneeClient("http://localhost:8000", improve_timeout=123)

    result = client.improve_sessions(
        dataset_name="hermes-arcion",
        session_ids=["session-1"],
        run_in_background=True,
    )

    request = seen["request"]
    assert request.full_url == "http://localhost:8000/api/v1/improve"
    assert json.loads(request.data) == {
        "dataset_name": "hermes-arcion",
        "session_ids": ["session-1"],
        "run_in_background": True,
        "build_global_context_index": False,
    }
    assert result == {"status": "queued"}
    assert seen["timeout"] == 123


@pytest.mark.parametrize(
    ("scope", "expected_timeout"),
    [
        ("session", 7),
        ("session_context", 7),
        ("graph", 46),
        ("auto", 46),
        (["session", "graph"], 46),
        (None, 46),
    ],
)
def test_recall_selects_timeout_by_scope(monkeypatch, scope, expected_timeout):
    seen = {}

    def fake_urlopen(_request, timeout):
        seen["timeout"] = timeout
        return FakeResponse([])

    monkeypatch.setattr("hermes_cognee_memory.client.urlopen", fake_urlopen)
    client = CogneeClient(
        "http://localhost:8000",
        timeout=7,
        graph_recall_timeout=46,
    )

    client.recall("query", scope=scope)

    assert seen["timeout"] == expected_timeout


def test_health_uses_server_health_endpoint(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        return FakeResponse({"status": "ok"})

    monkeypatch.setattr("hermes_cognee_memory.client.urlopen", fake_urlopen)
    assert CogneeClient("https://memory.example/api/v1").health() == {"status": "ok"}
    assert seen["url"] == "https://memory.example/health"


def test_oversized_response_is_rejected(monkeypatch):
    class OversizedResponse(FakeResponse):
        def read(self, amount):
            return b"x" * amount

    monkeypatch.setattr(
        "hermes_cognee_memory.client.urlopen", lambda _request, timeout: OversizedResponse({"ignored": True})
    )

    with pytest.raises(CogneeAPIError, match="too large"):
        CogneeClient("http://localhost:8000").health()


def test_http_errors_do_not_expose_server_detail(monkeypatch):
    def fake_urlopen(_request, timeout):
        del timeout
        body = json.dumps({"error": "session cache unavailable"}).encode()
        raise HTTPError("http://localhost", 503, "Service Unavailable", {}, BytesIO(body))

    monkeypatch.setattr("hermes_cognee_memory.client.urlopen", fake_urlopen)

    with pytest.raises(CogneeAPIError) as exc_info:
        CogneeClient("http://localhost:8000").health()

    assert exc_info.value.status_code == 503
    assert str(exc_info.value) == "Cognee API returned HTTP 503"


def test_recall_rejects_unexpected_response_shape(monkeypatch):
    monkeypatch.setattr("hermes_cognee_memory.client.urlopen", lambda *_args, **_kwargs: FakeResponse({"items": []}))

    with pytest.raises(CogneeAPIError, match="expected a list"):
        CogneeClient("http://localhost:8000").recall("query")
