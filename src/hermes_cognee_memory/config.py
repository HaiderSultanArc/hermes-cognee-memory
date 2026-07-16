"""Profile-scoped configuration for the Cognee memory provider."""
from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "service_url": "http://localhost:8000",
    "dataset_name": "hermes-{identity}",
    "auto_capture": True,
    "auto_improve": True,
    "auto_recall": False,
    "recall_scope": ["session", "graph"],
    "top_k": 8,
    "request_timeout_seconds": 15,
    "graph_recall_timeout_seconds": 45,
    "improve_timeout_seconds": 120,
    "prefetch_timeout_seconds": 3,
    "prefetch_max_concurrency": 2,
    "max_prefetch_chars": 6000,
    "recall_circuit_failure_threshold": 3,
    "recall_circuit_cooldown_seconds": 30,
    "writer_queue_size": 256,
    "write_retry_attempts": 3,
    "write_retry_base_seconds": 0.25,
    "shutdown_flush_seconds": 130,
}


def _hermes_home(value: str | None = None) -> Path:
    if value:
        return Path(value).expanduser()
    return Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()


def config_path(hermes_home: str | None = None) -> Path:
    return _hermes_home(hermes_home) / "cognee" / "config.json"


def load_config(hermes_home: str | None = None) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    path = config_path(hermes_home)
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        metadata = None
    except OSError:
        metadata = None
    if metadata is not None:
        secure = stat.S_ISREG(metadata.st_mode) and not metadata.st_mode & 0o022
        if hasattr(os, "getuid"):
            secure = secure and metadata.st_uid == os.getuid()
        if secure:
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    config.update(loaded)
            except (OSError, json.JSONDecodeError):
                pass
    return config


def save_config(values: dict[str, Any], hermes_home: str | None = None) -> None:
    path = config_path(hermes_home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    data = dict(DEFAULT_CONFIG)
    data.update(values or {})
    fd, temp_name = tempfile.mkstemp(prefix="config.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, path)
        os.chmod(path, 0o600)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
