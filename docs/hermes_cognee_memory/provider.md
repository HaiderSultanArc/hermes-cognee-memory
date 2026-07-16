# Cognee memory provider

Source: `src/hermes_cognee_memory/provider.py`

`CogneeMemoryProvider` implements Hermes's exclusive `MemoryProvider` contract. It owns the
provider lifecycle, dataset/session scoping, background capture queue, recall prefetch workers,
session improvement, and the `cognee_recall` and `cognee_remember` tools.

Key boundaries:

- only completed primary-agent turns are captured automatically;
- gateway datasets are derived from Hermes's stable session scope without exposing raw IDs;
- hard graph isolation requires Cognee per-dataset backend access control; names alone do not
  isolate a single shared Kuzu graph;
- writes and improvement share one bounded FIFO worker so improvement cannot pass pending writes;
- recall output is bounded and rendered as untrusted evidence;
- repeated recall failures open a circuit breaker and allow one recovery probe after cooldown;
- graph recall and synchronous improvement receive separate, bounded timeout budgets;
- built-in curated Hermes memory is not mirrored because the plugin has no safe remote entry-ID
  mapping for replacement or deletion.

Call `shutdown` when the provider is no longer used. It stops new work, waits within configured
bounds for queued writes and prefetch threads, and preserves failed-write state so improvement is
not falsely reported as complete. The default flush window is deliberately longer than the
synchronous improvement timeout; reducing it can abandon graph persistence during teardown.
