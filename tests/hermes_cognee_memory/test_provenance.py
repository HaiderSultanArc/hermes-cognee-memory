from __future__ import annotations

import json
import stat
from uuid import uuid4

import pytest

from hermes_cognee_memory.provenance import ProvenanceStore, ProvenanceStoreError


def test_record_get_and_tombstone_are_private_and_content_free(tmp_path):
    entry_id = str(uuid4())
    store = ProvenanceStore(str(tmp_path))

    assert store.record(entry_id, dataset_name="hermes-arcion", session_id="session-1") == entry_id
    assert store.get(entry_id)["forgotten"] is False

    store.mark_forgotten(entry_id)

    record = store.get(entry_id)
    assert record["dataset_name"] == "hermes-arcion"
    assert record["session_id"] == "session-1"
    assert record["forgotten"] is True
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    assert stat.S_IMODE(store.path.parent.stat().st_mode) == 0o700
    assert "question" not in store.path.read_text()
    assert "answer" not in store.path.read_text()


def test_store_is_bounded_by_least_recent_update(tmp_path, monkeypatch):
    clock = iter([1.0, 2.0, 3.0])
    monkeypatch.setattr("hermes_cognee_memory.provenance.time.time", lambda: next(clock))
    ids = [str(uuid4()) for _ in range(3)]
    store = ProvenanceStore(str(tmp_path), max_entries=2)

    for entry_id in ids:
        store.record(entry_id, dataset_name="dataset", session_id="session")

    assert store.get(ids[0]) is None
    assert store.get(ids[1]) is not None
    assert store.get(ids[2]) is not None


def test_corrupt_or_unsafe_store_fails_closed(tmp_path):
    store = ProvenanceStore(str(tmp_path))
    store.path.parent.mkdir(parents=True)
    store.path.write_text("not-json")
    store.path.chmod(0o600)

    with pytest.raises(ProvenanceStoreError, match="unreadable"):
        store.get(str(uuid4()))

    store.path.write_text(json.dumps({"version": 1, "entries": {}}))
    store.path.chmod(0o666)
    with pytest.raises(ProvenanceStoreError, match="unsafe"):
        store.get(str(uuid4()))


def test_invalid_entry_id_is_rejected(tmp_path):
    store = ProvenanceStore(str(tmp_path))
    with pytest.raises(ValueError, match="UUID"):
        store.record("not-an-id", dataset_name="dataset", session_id="session")


def test_symlinked_provenance_directory_is_rejected(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (tmp_path / "cognee").symlink_to(target, target_is_directory=True)
    store = ProvenanceStore(str(tmp_path))

    with pytest.raises(ProvenanceStoreError, match="unsafe ownership or type"):
        store.record(str(uuid4()), dataset_name="dataset", session_id="session")
