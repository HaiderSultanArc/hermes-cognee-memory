from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path


def test_plugin_loads_through_real_hermes_memory_discovery(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    hermes_home = tmp_path / "hermes"
    plugin_dir = hermes_home / "plugins" / "cognee"
    shutil.copytree(project_root, plugin_dir, ignore=shutil.ignore_patterns(".venv", ".git", "__pycache__"))
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    memory_plugins = importlib.import_module("plugins.memory")
    discovered = {name: available for name, _desc, available in memory_plugins.discover_memory_providers()}
    first = memory_plugins.load_memory_provider("cognee")
    second = memory_plugins.load_memory_provider("cognee")

    assert "cognee" in discovered
    assert first is not None
    assert second is not None
    assert first.name == "cognee"
    assert second is not first


def test_root_plugin_module_exposes_provider_class_without_singleton_registration():
    project_root = Path(__file__).resolve().parents[1]
    module_name = "hermes_cognee_memory_test_plugin"
    spec = importlib.util.spec_from_file_location(
        module_name,
        project_root / "__init__.py",
        submodule_search_locations=[str(project_root)],
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        assert module.CogneeMemoryProvider.__name__ == "CogneeMemoryProvider"
        assert not hasattr(module, "register")
    finally:
        sys.modules.pop(module_name, None)
