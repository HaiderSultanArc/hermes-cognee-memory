"""Bounded local provenance for exact Cognee memory deletion."""
from __future__ import annotations

import json
import os
import stat
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from uuid import UUID

_VERSION = 1
_MAX_FILE_BYTES = 5 * 1024 * 1024


class ProvenanceStoreError(RuntimeError):
    """Raised when provenance cannot be read or updated safely."""


class ProvenanceStore:
    """Persist entry-to-session mappings without storing memory content."""

    def __init__(self, hermes_home: str, *, max_entries: int = 10_000) -> None:
        self.path = Path(hermes_home).expanduser() / "cognee" / "provenance.json"
        self.max_entries = max(1, min(int(max_entries), 100_000))
        self._lock = threading.RLock()

    @staticmethod
    def canonical_entry_id(value: str) -> str:
        try:
            return str(UUID(str(value)))
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError("entry_id must be a UUID") from error

    def _read(self) -> dict[str, dict[str, Any]]:
        try:
            metadata = self.path.lstat()
        except FileNotFoundError:
            return {}
        except OSError as error:
            raise ProvenanceStoreError("Could not inspect Cognee provenance") from error

        secure = stat.S_ISREG(metadata.st_mode) and not metadata.st_mode & 0o022
        if hasattr(os, "getuid"):
            secure = secure and metadata.st_uid == os.getuid()
        if not secure:
            raise ProvenanceStoreError("Cognee provenance file has unsafe ownership or permissions")
        if metadata.st_size > _MAX_FILE_BYTES:
            raise ProvenanceStoreError("Cognee provenance file is too large")

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ProvenanceStoreError("Cognee provenance file is unreadable") from error
        if not isinstance(payload, dict) or payload.get("version") != _VERSION:
            raise ProvenanceStoreError("Cognee provenance file has an unsupported format")
        entries = payload.get("entries")
        if not isinstance(entries, dict):
            raise ProvenanceStoreError("Cognee provenance entries are invalid")
        return entries

    def _write(self, entries: dict[str, dict[str, Any]]) -> None:
        parent = self.path.parent
        try:
            parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            metadata = parent.lstat()
            secure = stat.S_ISDIR(metadata.st_mode)
            if hasattr(os, "getuid"):
                secure = secure and metadata.st_uid == os.getuid()
            if not secure:
                raise ProvenanceStoreError(
                    "Cognee provenance directory has unsafe ownership or type"
                )
            parent.chmod(0o700)
        except ProvenanceStoreError:
            raise
        except OSError as error:
            raise ProvenanceStoreError("Could not prepare Cognee provenance directory") from error

        fd = -1
        temp_name = ""
        try:
            fd, temp_name = tempfile.mkstemp(prefix="provenance.", suffix=".tmp", dir=parent)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                fd = -1
                json.dump(
                    {"version": _VERSION, "entries": entries},
                    handle,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_name, 0o600)
            os.replace(temp_name, self.path)
            temp_name = ""
            os.chmod(self.path, 0o600)
        except OSError as error:
            raise ProvenanceStoreError("Could not update Cognee provenance") from error
        finally:
            if fd >= 0:
                os.close(fd)
            if temp_name:
                try:
                    os.unlink(temp_name)
                except FileNotFoundError:
                    pass

    def record(self, entry_id: str, *, dataset_name: str, session_id: str) -> str:
        """Record a server-acknowledged memory and return its canonical UUID."""
        canonical_id = self.canonical_entry_id(entry_id)
        dataset = str(dataset_name or "").strip()
        session = str(session_id or "").strip()
        if not dataset or len(dataset) > 200:
            raise ValueError("dataset_name is required and must be at most 200 characters")
        if not session or len(session) > 200:
            raise ValueError("session_id is required and must be at most 200 characters")

        with self._lock:
            entries = self._read()
            now = time.time()
            entries[canonical_id] = {
                "dataset_name": dataset,
                "session_id": session,
                "forgotten": False,
                "recorded_at": now,
                "updated_at": now,
            }
            if len(entries) > self.max_entries:
                oldest = sorted(
                    entries,
                    key=lambda key: float(entries[key].get("updated_at", 0)),
                )[: len(entries) - self.max_entries]
                for key in oldest:
                    entries.pop(key, None)
            self._write(entries)
        return canonical_id

    def get(self, entry_id: str) -> dict[str, Any] | None:
        """Return a validated mapping, or ``None`` when the ID was never recorded."""
        canonical_id = self.canonical_entry_id(entry_id)
        with self._lock:
            entry = self._read().get(canonical_id)
        if not isinstance(entry, dict):
            return None
        dataset = entry.get("dataset_name")
        session = entry.get("session_id")
        forgotten = entry.get("forgotten")
        if not isinstance(dataset, str) or not isinstance(session, str):
            raise ProvenanceStoreError("Cognee provenance entry is invalid")
        if not isinstance(forgotten, bool):
            raise ProvenanceStoreError("Cognee provenance entry is invalid")
        return dict(entry)

    def mark_forgotten(self, entry_id: str) -> None:
        """Retain a tombstone after the server confirms exact deletion."""
        canonical_id = self.canonical_entry_id(entry_id)
        with self._lock:
            entries = self._read()
            entry = entries.get(canonical_id)
            if not isinstance(entry, dict):
                raise ProvenanceStoreError("Cognee entry provenance was not found")
            entry["forgotten"] = True
            entry["updated_at"] = time.time()
            self._write(entries)
