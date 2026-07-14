# Package exports

Source: `src/hermes_cognee_memory/__init__.py`

The package exposes `CogneeMemoryProvider` as its public API. Consumers should import the provider
from `hermes_cognee_memory` instead of depending on internal module names.

The repository-root `__init__.py` re-exports the same class for Hermes's standalone plugin loader.
It contains no provider state or registration singleton, so each Hermes load can create a fresh
provider instance.
