from __future__ import annotations

import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from hermes_cognee_memory.client import CogneeClient
from hermes_cognee_memory.provider import CogneeMemoryProvider

ENTRY_ID = "1e72631c-d08a-4c6d-8552-50a53d4d035c"


class CogneeContractHandler(BaseHTTPRequestHandler):
    requests = []

    def log_message(self, *_args):
        return

    def _json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def _send(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        type(self).requests.append(("GET", self.path, None, dict(self.headers)))
        assert self.path == "/health"
        self._send({"status": "ready", "health": "healthy", "version": "test"})

    def do_POST(self):
        payload = self._json_body()
        type(self).requests.append(("POST", self.path, payload, dict(self.headers)))
        if self.path == "/api/v1/remember/entry":
            assert payload["entry"]["type"] == "qa"
            assert payload["dataset_name"] == "hermes-arcion"
            self._send(
                {"status": "session_stored", "entry_type": "qa", "entry_id": ENTRY_ID}
            )
            return
        if self.path == "/api/v1/recall":
            assert payload["search_type"] is None
            assert payload["scope"] in {"session", "graph"}
            if payload["scope"] == "session":
                assert payload["datasets"] is None
                self._send(
                    [
                        {
                            "source": "session",
                            "qa_id": ENTRY_ID,
                            "question": "Preferred approach?",
                            "answer": "Use the boring solution.",
                        }
                    ]
                )
            else:
                assert payload["datasets"] == ["hermes-arcion"]
                self._send(
                    [
                        {
                            "source": "graph",
                            "kind": "graph_completion",
                            "text": "Prefer boring, maintainable solutions.",
                            "dataset_name": "hermes-arcion",
                        }
                    ]
                )
            return
        if self.path == "/api/v1/datasets":
            assert payload == {"name": "hermes-arcion"}
            self._send({"id": "d1", "name": "hermes-arcion"})
            return
        assert self.path == "/api/v1/improve"
        assert payload == {
            "dataset_name": "hermes-arcion",
            "session_ids": ["session-http"],
            "run_in_background": False,
            "build_global_context_index": False,
        }
        self._send({"status": "queued"})


def test_real_http_transport_and_provider_lifecycle():
    CogneeContractHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), CogneeContractHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    service_url = f"http://127.0.0.1:{server.server_port}"

    provider = CogneeMemoryProvider(
        config={
            "service_url": service_url,
            "dataset_name": "hermes-{identity}",
            "auto_capture": True,
            "auto_recall": True,
            "recall_scope": ["session", "graph"],
            "top_k": 5,
            "request_timeout_seconds": 2,
            "prefetch_timeout_seconds": 2,
            "max_prefetch_chars": 2000,
        },
        client_factory=CogneeClient,
    )
    try:
        provider.initialize(
            "session-http",
            hermes_home=tempfile.mkdtemp(prefix="hermes-cognee-http-test-"),
            platform="cli",
            agent_context="primary",
            agent_identity="arcion",
        )
        assert provider._client.health()["status"] == "ready"
        provider.sync_turn("Preferred approach?", "Use the boring solution.")
        provider.queue_prefetch("preferred approach")
        context = provider.prefetch("ignored")
        provider.on_session_end([])
        provider.shutdown()

        assert "Prefer boring, maintainable solutions." in context
        paths = [request[1] for request in CogneeContractHandler.requests]
        assert paths[0] == "/health"
        assert sorted(paths[1:]) == sorted(
            [
                "/api/v1/remember/entry",
                "/api/v1/recall",
                "/api/v1/recall",
                "/api/v1/datasets",
                "/api/v1/improve",
            ]
        )
    finally:
        provider.shutdown()
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
