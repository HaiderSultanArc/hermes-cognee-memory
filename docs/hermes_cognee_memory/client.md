# Cognee HTTP client

Source: `src/hermes_cognee_memory/client.py`

`CogneeClient` is the dependency-free synchronous transport between Hermes and Cognee. It supports
health checks, dataset creation, Q&A capture, session improvement, and recall.

The client deliberately keeps the network boundary narrow:

- service URLs must be HTTP(S), with plaintext HTTP limited to loopback hosts;
- credentials, query strings, fragments, and unexpected URL paths are rejected;
- redirects are not followed, preventing `X-Api-Key` from being forwarded to another origin;
- responses are capped at 2 MiB and endpoint response shapes are validated;
- transport and response errors are converted to `CogneeAPIError` with bounded messages.

An empty successful `/improve` response is rejected. Upstream Cognee returns `{}` when another
improvement already holds the same single-session lock; treating that response as completed could
advance the provider checkpoint past captures that the competing run did not see. Rejection sends
lock contention through the provider's bounded retry and session-end catch-up paths.

The transport uses operation-specific timeouts: short requests keep the base timeout, recall that
can enter the graph uses the graph-recall timeout, and synchronous improvement uses the improvement
timeout. This prevents slow graph work from being reported as an outage without making health and
session-cache failures wait for the longest budget.

The client is synchronous because Hermes invokes it from bounded provider worker and prefetch
threads. Concurrency and retries belong to the provider, not this transport layer.

The client intentionally does not expose Cognee deletion operations. Memory lifecycle policy remains
owned by the upstream Cognee service rather than being redefined at the Hermes integration layer.
