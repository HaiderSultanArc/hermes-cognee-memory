from __future__ import annotations

import json

from hermes_cognee_memory.config import DEFAULT_CONFIG, config_path, load_config


def test_config_path_uses_explicit_hermes_home(tmp_path):
    assert config_path(str(tmp_path)) == tmp_path / "cognee" / "config.json"


def test_load_config_merges_secure_profile_values_with_defaults(tmp_path):
    path = config_path(str(tmp_path))
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"top_k": 3}), encoding="utf-8")
    path.chmod(0o600)

    loaded = load_config(str(tmp_path))

    assert loaded["top_k"] == 3
    assert loaded["service_url"] == DEFAULT_CONFIG["service_url"]
    assert loaded["auto_recall"] is False
    assert loaded["request_timeout_seconds"] == 15
    assert loaded["graph_recall_timeout_seconds"] == 45
    assert loaded["improve_timeout_seconds"] == 300
    assert loaded["shutdown_flush_seconds"] == 310
