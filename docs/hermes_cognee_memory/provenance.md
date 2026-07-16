# Cognee provenance store

Source: `src/hermes_cognee_memory/provenance.py`

`ProvenanceStore` keeps the minimum local metadata needed to authorize exact memory deletion:
the Cognee entry UUID, dataset name, session ID, timestamps, and forgotten state. It never stores
the question, answer, or recalled content.

The store lives at `$HERMES_HOME/cognee/provenance.json`. Writes use a same-directory temporary
file plus `os.replace`; the directory is mode `0700` and the file is mode `0600`. Unsafe,
oversized, malformed, or unsupported files fail closed, so a damaged ledger cannot authorize an
unrelated server deletion.

The ledger retains successful deletions as tombstones so stale session results can be suppressed.
It is capped at 10,000 entries by default and evicts the least recently updated records when full.
That bound means very old provenance and tombstones can eventually expire; such an entry is no
longer deletable through Hermes without a separately verified server-side mapping.
