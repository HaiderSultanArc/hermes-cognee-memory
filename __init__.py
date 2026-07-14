"""Cognee user-installed memory provider for Hermes Agent.

Hermes discovers the exported ``MemoryProvider`` subclass and creates a fresh
instance for each provider load.
"""

from __future__ import annotations

if __package__:
    from .hermes_cognee_memory.provider import CogneeMemoryProvider
else:
    from hermes_cognee_memory.provider import CogneeMemoryProvider

__all__ = ["CogneeMemoryProvider"]
