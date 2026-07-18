# Cognee memory provider

Source: `src/hermes_cognee_memory/provider.py`

`CogneeMemoryProvider` implements Hermes's exclusive `MemoryProvider` contract. It owns the
provider lifecycle, persistent dataset and session scoping, background capture queue, recall prefetch workers,
session improvement, and the `cognee_recall` and `cognee_remember` tools.

Key boundaries:

- only completed primary-agent turns are captured automatically;
- the configured dataset remains stable across conversations so improved knowledge forms one
  persistent graph;
- gateway scope and the Hermes session ID are hashed into a deterministic Cognee session ID,
  keeping raw user/chat identifiers out of the service while separating session cache entries;
- writes and improvement share one bounded FIFO worker so improvement cannot pass pending writes;
- recall output is bounded and rendered as untrusted evidence;
- repeated recall failures open a circuit breaker and allow one recovery probe after cooldown;
- graph recall and synchronous improvement receive separate, bounded timeout budgets;
- Cognee owns deletion, reinforcement, decay, retention, and graph-processing semantics;
- built-in curated Hermes memory is not mirrored because it remains a separate reviewed source of
  truth.

Call `shutdown` when the provider is no longer used. It stops new work, waits within configured
bounds for queued writes and prefetch threads, and preserves failed-write state so improvement is
not falsely reported as complete. The default flush window is deliberately longer than the
synchronous improvement timeout; reducing it can abandon graph persistence during teardown.

Before the first capture, the provider ensures that the active dataset exists. Successful captures
advance the provider's in-memory acknowledgement counter so session improvement cannot overtake a
queued or failed write.
