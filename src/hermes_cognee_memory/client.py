"""Small dependency-free HTTP client for Cognee's memory API."""
from __future__ import annotations

import ipaddress
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class _NoRedirectHandler(HTTPRedirectHandler):
    """Keep authentication headers on the configured origin only."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        del req, fp, code, msg, headers, newurl
        return None


_NO_REDIRECT_OPENER = build_opener(_NoRedirectHandler())
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024



def urlopen(request: Request, *, timeout: float):
    """Open one request without following redirects that could leak X-Api-Key."""
    return _NO_REDIRECT_OPENER.open(request, timeout=timeout)


class CogneeAPIError(RuntimeError):
    """A bounded, user-safe error returned by the Cognee service."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def normalize_service_url(value: str) -> str:
    """Return a validated Cognee server root without ``/api/v1``."""
    raw = str(value or "").strip()
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Cognee service URL must be an absolute http(s) URL")
    try:
        parsed.port
    except ValueError as error:
        raise ValueError("Cognee service URL contains an invalid port") from error
    if parsed.scheme == "http":
        host = parsed.hostname.lower()
        is_loopback = host == "localhost"
        if not is_loopback:
            try:
                is_loopback = ipaddress.ip_address(host).is_loopback
            except ValueError:
                is_loopback = False
        if not is_loopback:
            raise ValueError("Plaintext Cognee URLs are limited to loopback; use https remotely")
    if parsed.username or parsed.password:
        raise ValueError("Cognee service URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("Cognee service URL must not contain a query or fragment")
    path = parsed.path.rstrip("/")
    if path not in {"", "/api/v1"}:
        raise ValueError("Cognee service URL path must be empty or /api/v1")
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")


class CogneeClient:
    """Synchronous adapter for the Cognee HTTP API used by Hermes threads."""

    def __init__(
        self,
        service_url: str,
        *,
        api_key: str = "",
        timeout: float = 15.0,
        graph_recall_timeout: float = 45.0,
        improve_timeout: float = 300.0,
    ) -> None:
        self.service_url = normalize_service_url(service_url)
        self.api_key = str(api_key or "").strip()
        self.timeout = max(0.1, float(timeout))
        self.graph_recall_timeout = max(0.1, float(graph_recall_timeout))
        self.improve_timeout = max(0.1, float(improve_timeout))

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> Any:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        request = Request(
            f"{self.service_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout if timeout is None else timeout) as response:
                response_body = response.read(_MAX_RESPONSE_BYTES + 1)
                if len(response_body) > _MAX_RESPONSE_BYTES:
                    raise CogneeAPIError("Cognee API response is too large")
        except HTTPError as error:
            raise CogneeAPIError(
                f"Cognee API returned HTTP {error.code}",
                status_code=error.code,
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            reason = getattr(error, "reason", error)
            raise CogneeAPIError(f"Could not reach Cognee: {str(reason)[:300]}") from error

        if not response_body:
            return None
        try:
            return json.loads(response_body)
        except json.JSONDecodeError as error:
            raise CogneeAPIError("Cognee API returned invalid JSON") from error

    def health(self) -> dict[str, Any]:
        result = self._request("GET", "/health")
        if not isinstance(result, dict):
            raise CogneeAPIError("Cognee health endpoint returned an unexpected response")
        return result

    def remember_qa(
        self,
        *,
        question: str,
        answer: str,
        context: str,
        dataset_name: str,
        session_id: str,
    ) -> dict[str, Any]:
        result = self._request(
            "POST",
            "/api/v1/remember/entry",
            {
                "entry": {
                    "type": "qa",
                    "question": question,
                    "answer": answer,
                    "context": context,
                },
                "dataset_name": dataset_name,
                "session_id": session_id,
            },
        )
        if not isinstance(result, dict):
            raise CogneeAPIError("Cognee remember endpoint returned an unexpected response")
        return result

    def ensure_dataset(self, dataset_name: str) -> dict[str, Any]:
        result = self._request("POST", "/api/v1/datasets", {"name": dataset_name})
        if not isinstance(result, dict):
            raise CogneeAPIError("Cognee dataset endpoint returned an unexpected response")
        return result

    def improve_sessions(
        self,
        *,
        dataset_name: str,
        session_ids: list[str],
        run_in_background: bool = True,
    ) -> dict[str, Any]:
        result = self._request(
            "POST",
            "/api/v1/improve",
            {
                "dataset_name": dataset_name,
                "session_ids": session_ids,
                "run_in_background": run_in_background,
                "build_global_context_index": False,
            },
            timeout=self.improve_timeout,
        )
        if not isinstance(result, dict):
            raise CogneeAPIError("Cognee improve endpoint returned an unexpected response")
        return result

    def recall(
        self,
        query: str,
        *,
        dataset_name: str | None = None,
        session_id: str = "",
        scope: str | list[str] | None = None,
        top_k: int = 8,
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "query": query,
            "search_type": None,
            "datasets": [dataset_name] if dataset_name else None,
            "session_id": session_id or None,
            "scope": scope,
            "top_k": max(1, min(int(top_k), 50)),
            "only_context": False,
            "include_references": True,
        }
        graph_scopes = {"auto", "graph", "all"}
        requested_scopes = {scope} if isinstance(scope, str) else set(scope or ["auto"])
        timeout = (
            self.graph_recall_timeout
            if requested_scopes.intersection(graph_scopes)
            else self.timeout
        )
        result = self._request("POST", "/api/v1/recall", payload, timeout=timeout)
        if not isinstance(result, list):
            raise CogneeAPIError("Cognee recall endpoint expected a list response")
        return [item for item in result if isinstance(item, dict)]
