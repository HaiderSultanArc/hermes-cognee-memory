# Hermes Cognee Memory Release Plan

## Purpose

This plan finishes `hermes-cognee-memory` as a standalone, user-installed
Hermes memory provider without bundling unrelated Hermes Agent changes into the
same task.

The intended result is:

- Cognee remains in its own repository.
- Hermes Agent core requires no Cognee-specific runtime changes.
- The modified `/home/haidersultanarc/hermes-agent` working tree is returned to
  its pre-task tracked state without touching unrelated untracked files.
- The standalone plugin is reviewed, tested, committed, published, installed
  through Hermes's existing plugin mechanism, and verified against a real
  Cognee service.
- The memory-prompt hardening and safe-mode discovery fixes are deferred to
  separate, independently justified Hermes PRs if they are pursued later.

## Architecture Decision

Cognee is an external memory service and should integrate at Hermes's existing
standalone memory-provider boundary:

```text
Hermes session
    -> user-installed MemoryProvider plugin
    -> local/HTTPS Cognee API
    -> session cache + persistent Cognee graph
```

The supported activation path is a plugin directory installed under the active
Hermes home:

```text
$HERMES_HOME/plugins/cognee/
```

The plugin repository root exports `CogneeMemoryProvider`; Hermes discovers the
subclass and creates fresh provider instances. The package wheel is a release
artifact, not the activation mechanism. No pip entry-point bridge or
Cognee-specific Hermes core hook is required.

## Repositories And Paths

| Purpose | Path | Rule |
|---|---|---|
| Standalone Cognee plugin | `/home/haidersultanarc/arc-function/hermes-cognee-memory` | Primary implementation and release repository. |
| ArcHermes development fork | `/home/haidersultanarc/arc-function/ArcHermes` | Only location for future ArcHermes code changes. Keep untouched during the Cognee release. |
| Other/live Hermes checkout | `/home/haidersultanarc/hermes-agent` | Remove task-related tracked edits; do not use for future development. |
| Planning and preserved patches | `/home/haidersultanarc/arc-function/hermes-cognee-memory/specs` | Holds this plan, operational evidence, and optional patch archives. |

## Current State

### Architecture correction — 2026-07-18

- The configured Cognee dataset is now one persistent graph for the agent/profile rather than one
  dataset per gateway conversation. This prevents unbounded dataset creation and allows improved
  knowledge to remain recallable across Hermes sessions.
- Hermes's stable `gateway_session_key` remains required for primary gateway agents, but it is
  combined with the Hermes session ID and hashed into a privacy-safe Cognee `session_id`. Raw
  gateway identifiers are not sent as identifiers, and distinct Hermes sessions retain separate
  session-cache boundaries inside the shared dataset.
- Separate Cognee datasets or authenticated identities are reserved for deliberate agent, tenant,
  or trust boundaries. They are not a conversation-lifecycle mechanism.

### Implementation update — 2026-07-16

- Exact per-entry forgetting is implemented in the Cognee and plugin development
  checkouts. New session Q&A records retain their remember UUID as Cognee `data_id`;
  `POST /api/v1/forget/entry` synchronizes session-cache and graph/vector deletion.
- The plugin exposes `cognee_forget` only for UUIDs recorded in its bounded,
  content-free `$HERMES_HOME/cognee/provenance.json` ledger. Confirmed deletes become
  tombstones. Unknown IDs, other datasets, malformed ledgers, broad deletion, and
  query-based deletion fail closed.
- Source validation passes (36 focused Cognee tests and all 77 plugin tests). Cognee
  commit `bab0e7ab6` and plugin commit `170626c` are pushed; the plugin is installed in
  the live Arc'ion profile and the rebuilt Cognee service is healthy. A live two-entry
  canary proved exact deletion: after graph improvement, deleting the first UUID removed
  it from recall while the adjacent second entry remained, and both disposable entries
  were then deleted. The full canary completed in 24.7 seconds. The existing 11-record
  bootstrap used legacy grouped-session persistence and is not retroactively individually
  deletable.
- The normal Hermes gateway message path already forwards its stable
  `gateway_session_key` to memory providers. A regression test now protects that
  contract; no new generic lifecycle hook was needed. Auxiliary agents without a
  conversation scope continue to fail closed.
- Cognee is bound to `127.0.0.1:8000`; the published debugger port was removed.
- The plugin now separates short request (15s), graph recall (45s), and synchronous
  improvement (300s) timeouts. Shutdown flush uses 310 seconds so a valid in-flight
  improvement can finish. Profile configurations use those operation-specific values
  instead of the temporary 90-second catch-all.
- Cognee session improvement now applies pending frequency weights before feedback
  weights and Q&A persistence. Focused tests cover stage order, repeated-use
  increments, idempotent retry skipping, and non-fatal unsupported adapters.
- The active Ladybug-backed graph adapter now persists node and edge frequency weights.
  Live validation reinforced three recalled nodes and three recalled edges from `0.0`
  to `1.0`, then proved retry idempotence through persisted session metadata.
- A complete installed-plugin `/api/v1/improve` run finished with
  `PipelineRunCompleted` in 73.56 seconds after the local OpenRouter output-token budget
  was reduced from 8,192 to 6,000. The earlier 300-second failure was caused by provider
  credit retries, not frequency reinforcement.
- Live validation proved that hashed names are insufficient when Cognee runs with
  backend access control disabled: the single shared Kuzu graph leaked synthetic
  canaries across datasets. The local service now enables per-dataset backend access
  control while keeping loopback HTTP authentication disabled; fresh isolation
  validation is required after the configuration change.
- Plugin CI now covers Python 3.11, 3.12, and 3.13 and targets coverage at
  `src/hermes_cognee_memory` explicitly.
- Final quality gates and live two-conversation isolation validation remain in
  progress. `v0.1.0` must not be tagged until those pass and tagging is explicitly
  approved.

### Operational evaluation — started 2026-07-16

- Day-to-day comparison and soak-test findings are maintained in
  [`operational-evaluation.md`](operational-evaluation.md).
- Cognee is evaluated as supplemental associative and episodic memory. Curated
  `MEMORY.md`/`USER.md` remains the source of truth for exact durable facts, explicit
  corrections, and operator-reviewed guidance.
- Automatic Cognee recall remains disabled while Hermes labels provider-prefetched
  memory as authoritative. Explicit `cognee_recall` is the safe evaluation path.
- The evaluation is ongoing: each real use should record usefulness, latency, false
  positives, missed recalls, stale/conflicting facts, and any operational failure.
- The curated Codex memory bootstrap copied 11 bounded records into Cognee dataset
  `arc-function`; the manifest and initial retrieval results are recorded in
  [`memory-bootstrap-2026-07-16.md`](memory-bootstrap-2026-07-16.md).

### Validation update — 2026-07-15

- The plugin is published at `HaiderSultanArc/hermes-cognee-memory`; local `main` and
  `origin/main` both point to commit `9a1da4d`.
- The repository is a Hermes `MemoryProvider` plugin, not an Arc-Codex plugin. It has
  `plugin.yaml` and the required Hermes root export, but no Codex
  `.codex-plugin/plugin.json`, MCP server, app, hook, or skill bundle.
- A disposable Hermes profile named `cognee-e2e` was created without bundled skills.
- GitHub installation could not be tested because network elevation was declined. Hermes instead
  installed the exact clean `origin/main` commit through a local `file://` Git clone.
- Hermes reports `cognee` version `0.1.0` as installed, enabled, active, and available. The
  profile uses the default local URL and dataset template, and its configuration directory/file
  modes are `0700`/`0600`.
- An installed-plugin smoke test successfully loaded and initialized the provider, produced dataset
  `hermes-cognee-e2e`, exposed `cognee_recall` and `cognee_remember`, and activated the provider
  prompt block.
- No Cognee service is listening on `127.0.0.1:8000`. Recall therefore returns the expected bounded
  `Cognee request failed` response. Capture, graph improvement, later recall, and the public GitHub
  installation path remain unverified.
- With explicit user authorization, the same clean commit was installed into the active `arcion`
  profile through a local `file://` Git clone after GitHub network elevation was declined. Cognee
  version `0.1.0` is enabled and selected as `memory.provider`, using dataset
  `hermes-{identity}` (`hermes-arcion` for CLI sessions).
- The active profile's Cognee configuration uses `0700`/`0600` directory/file permissions,
  `auto_capture: true`, `auto_improve: true`, and `auto_recall: false`. No API key was stored.
- The active-profile loader smoke test passed: the provider initializes, contributes its prompt,
  and exposes `cognee_recall` and `cognee_remember`. A real recall still fails because the backend
  is offline. Hermes's `Status: available` currently means the provider/configuration loaded; it
  does not prove that the configured Cognee health endpoint is reachable.
- Day-to-day evaluation is installed but cannot produce or retrieve persistent memory until a
  Cognee service with `CACHING=true` is running at the configured URL. With the current defaults,
  automatic writes will be attempted and then exhausted by the provider's bounded retries.

Initial feature-utilization finding (superseded 2026-07-16):

- Cognee records graph-element usage and has a separate `apply_frequency_weights` pipeline for the
  “accessed more often becomes stronger” behavior. The current HTTP plugin does not invoke that
  pipeline, and Cognee's current HTTP API does not expose the SDK's `session.add_frequency_weights`
  operation directly.
- Cognee also supports feedback-weight reinforcement, but the plugin does not submit typed feedback
  entries linked to recalled QA IDs. A later feature audit should design both signals explicitly;
  merely calling `/api/v1/improve` does not activate frequency weighting.

Frequency reinforcement is now invoked by `/api/v1/improve` and has passed live validation.
Explicit feedback submission remains future work.

### Standalone plugin

`/home/haidersultanarc/arc-function/hermes-cognee-memory` currently contains a
complete but uncommitted initial implementation:

- No commit or `HEAD` exists yet.
- No Git remote is configured.
- Source, tests, CI, docs, license, metadata, and lockfile are untracked.
- Generated environments, caches, coverage output, build output, and egg-info
  are ignored by `.gitignore`.
- The current full test suite reports 58 passing tests.
- Python 3.11, 3.12, and 3.13 have passed locally.
- Ruff, lockfile validation, branch coverage, wheel build, and sdist build have
  passed.
- The repository is not yet published, so
  `hermes plugins install HaiderSultanArc/hermes-cognee-memory` cannot work.

### Hermes checkouts

`/home/haidersultanarc/hermes-agent` currently has nine modified tracked files:

- `AGENTS.md`
- `CONTRIBUTING.md`
- `agent/memory_manager.py`
- `hermes_cli/main.py`
- `tests/agent/test_memory_provider.py`
- `tests/hermes_cli/test_startup_plugin_gating.py`
- `website/docs/developer-guide/memory-provider-plugin.md`
- `website/docs/user-guide/features/plugins.md`
- `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/developer-guide/memory-provider-plugin.md`

Those edits contain three separable ideas:

1. Mark recalled memory as untrusted data.
2. Skip early plugin discovery when `--safe-mode` is present.
3. Correct generic standalone memory-provider documentation.

None is required for Cognee to load or run. The same checkout also contains an
untracked `shared.txt` that must be treated as unrelated and left untouched.

`/home/haidersultanarc/arc-function/ArcHermes` is currently clean and must stay
clean throughout the Cognee release.

## Phase Order

| Phase | Purpose | Exit condition |
|---|---|---|
| 0 | Scope freeze and preservation | Every current diff is classified; unrelated work is protected. |
| 1 | Restore Hermes task boundary | Cognee leaves no tracked changes in either Hermes checkout. |
| 2 | Standalone plugin release-candidate audit | Plugin contract, security boundary, metadata, docs, and CI are internally consistent. |
| 3 | Reproduce the complete quality gate | Supported Python matrix, coverage, lint, build, and real loader tests are green. |
| 4 | Create and publish the repository | Initial commit is pushed and CI passes on the public GitHub repository. |
| 5 | Disposable-profile end-to-end validation | Published install, setup, capture, recall, and improve work against a real Cognee service. |
| 6 | Release and optional production adoption | `v0.1.0` is tagged; active-profile installation is a separate explicit decision. |

## Shared Rules

- Do not add Cognee-specific code to Hermes Agent core.
- Do not reintroduce the generic pip memory-provider bridge.
- Do not edit `/home/haidersultanarc/hermes-agent` except to preserve and remove
  the currently identified task-related tracked changes.
- Do not move any Hermes changes into ArcHermes during this plan.
- Never use `git reset --hard`, `git clean`, or a blanket deletion in a mixed
  workspace.
- Preserve `/home/haidersultanarc/hermes-agent/shared.txt` unchanged.
- If an unexpected changed or untracked file appears, stop the cleanup and
  classify it before continuing.
- Use `uv` for the plugin's Python environment, tests, linting, locking, and
  builds.
- Keep the plugin dependency-free at runtime beyond Hermes and the Python
  standard library.
- Keep Cognee access local by default. Plain HTTP is loopback-only; remote
  services require HTTPS.
- Never commit API keys, `.env` files, service credentials, private chat data,
  or test captures containing real user content.
- Use synthetic canary text for end-to-end memory validation.
- Persistent graph memory uses the configured agent/profile dataset across conversations.
- Session-cache isolation follows Hermes's stable `gateway_session_key` plus Hermes session ID;
  raw gateway identifiers must not be sent as Cognee identifiers.
- A primary non-CLI provider without a stable gateway session key fails closed.
- Publication, pushing, tagging, GitHub release creation, active-profile setup,
  and destructive test-profile cleanup require explicit user authorization at
  execution time.

---

# Phase 0: Scope Freeze And Preservation

## Purpose

Record exactly what exists before cleanup so unrelated work cannot be lost and
independent Hermes improvements can be reconsidered later without remaining in
the Cognee task.

## Parent Context

The Cognee implementation review surfaced two legitimate but unrelated Hermes
hardening opportunities. They should not remain mixed into this release. Since
the edits are uncommitted, they can be preserved as review patches and removed
from the active checkout without changing Git history.

## In Scope

- Reconfirm the status of all three relevant directories.
- Export separate patch files for the three independent Hermes ideas.
- Record the file lists and hashes of the exported patches.
- Confirm that `shared.txt` is not included in any patch or cleanup command.
- Record the standalone plugin's baseline test count and repository state.

## Out Of Scope

- No source edits.
- No commit, push, or remote creation.
- No patch application to ArcHermes.
- No decision to upstream the independent Hermes changes.
- No deletion of generated plugin artifacts yet.

## Implementation Milestones

1. Create an archive directory:

   ```bash
   mkdir -p /home/haidersultanarc/arc-function/hermes-cognee-memory/specs/archives
   ```

2. Record the pre-cleanup state:

   ```bash
   git -C /home/haidersultanarc/hermes-agent status --short --branch
   git -C /home/haidersultanarc/arc-function/ArcHermes status --short --branch
   git -C /home/haidersultanarc/arc-function/hermes-cognee-memory status --short --branch --ignored
   ```

3. Preserve the memory-context hardening separately:

   ```bash
   git -C /home/haidersultanarc/hermes-agent diff -- \
     agent/memory_manager.py \
     tests/agent/test_memory_provider.py \
     > /home/haidersultanarc/arc-function/hermes-cognee-memory/specs/archives/hermes-memory-untrusted-data.patch
   ```

4. Preserve the safe-mode fix separately:

   ```bash
   git -C /home/haidersultanarc/hermes-agent diff -- \
     hermes_cli/main.py \
     tests/hermes_cli/test_startup_plugin_gating.py \
     > /home/haidersultanarc/arc-function/hermes-cognee-memory/specs/archives/hermes-safe-mode-plugin-discovery.patch
   ```

5. Preserve the generic documentation correction separately:

   ```bash
   git -C /home/haidersultanarc/hermes-agent diff -- \
     AGENTS.md \
     CONTRIBUTING.md \
     website/docs/developer-guide/memory-provider-plugin.md \
     website/docs/user-guide/features/plugins.md \
     website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/developer-guide/memory-provider-plugin.md \
     > /home/haidersultanarc/arc-function/hermes-cognee-memory/specs/archives/hermes-standalone-memory-provider-docs.patch
   ```

6. Verify the archives and record checksums:

   ```bash
   test -s /home/haidersultanarc/arc-function/hermes-cognee-memory/specs/archives/hermes-memory-untrusted-data.patch
   test -s /home/haidersultanarc/arc-function/hermes-cognee-memory/specs/archives/hermes-safe-mode-plugin-discovery.patch
   test -s /home/haidersultanarc/arc-function/hermes-cognee-memory/specs/archives/hermes-standalone-memory-provider-docs.patch
   sha256sum /home/haidersultanarc/arc-function/hermes-cognee-memory/specs/archives/*.patch
   ```

## Test And Acceptance Criteria

- Each patch contains only its named concern.
- No patch contains Cognee-specific code.
- No patch contains `shared.txt`.
- ArcHermes remains clean.
- The standalone plugin tree is unchanged.
- The pre-cleanup status is recorded in the execution report.

## Future-Phase Compatibility

The archives are evidence and optional future inputs, not active work. Any
future Hermes PR must start from current ArcHermes `main`, reproduce the issue,
apply only one concern, and pass that repository's current tests.

---

# Phase 1: Restore The Hermes Task Boundary

## Purpose

Remove all Cognee-task leftovers from `/home/haidersultanarc/hermes-agent` while
preserving unrelated files and keeping ArcHermes untouched.

## Parent Context

The standalone plugin already works through Hermes's existing directory-based
memory-provider discovery. Therefore the Cognee task has a zero-core-change
runtime requirement.

## In Scope

- Restore the nine identified tracked files to their repository versions.
- Leave all untracked files untouched.
- Verify that no Cognee-task tracked diff remains.
- Verify ArcHermes is still clean.

## Out Of Scope

- No `git clean`.
- No `git reset --hard`.
- No deletion or modification of `shared.txt`.
- No patch application to ArcHermes.
- No upstream PR creation.

## Implementation Milestones

1. Reconfirm that the changed tracked-file list still matches the Phase 0 list.
   If it differs, stop and reclassify the new state.

2. Restore only the reviewed tracked files:

   ```bash
   git -C /home/haidersultanarc/hermes-agent restore -- \
     AGENTS.md \
     CONTRIBUTING.md \
     agent/memory_manager.py \
     hermes_cli/main.py \
     tests/agent/test_memory_provider.py \
     tests/hermes_cli/test_startup_plugin_gating.py \
     website/docs/developer-guide/memory-provider-plugin.md \
     website/docs/user-guide/features/plugins.md \
     website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/developer-guide/memory-provider-plugin.md
   ```

3. Verify tracked cleanliness without requiring unrelated untracked files to
   disappear:

   ```bash
   git -C /home/haidersultanarc/hermes-agent diff --exit-code
   git -C /home/haidersultanarc/hermes-agent diff --cached --exit-code
   git -C /home/haidersultanarc/hermes-agent status --short
   ```

4. Verify ArcHermes remains untouched:

   ```bash
   git -C /home/haidersultanarc/arc-function/ArcHermes diff --exit-code
   git -C /home/haidersultanarc/arc-function/ArcHermes diff --cached --exit-code
   git -C /home/haidersultanarc/arc-function/ArcHermes status --short --branch
   ```

## Test And Acceptance Criteria

- `/home/haidersultanarc/hermes-agent` has no modified or staged tracked files.
- `shared.txt` remains present and unmodified if it was present at Phase 0.
- `/home/haidersultanarc/arc-function/ArcHermes` remains clean.
- No Cognee code exists in either Hermes checkout.
- The three preserved patches remain outside both repositories.

## Future-Phase Compatibility

A future Hermes improvement starts as a separate task, branch, plan, and PR in
`/home/haidersultanarc/arc-function/ArcHermes`. Passing this phase does not
approve or reject any preserved patch.

---

# Phase 2: Standalone Plugin Release-Candidate Audit

## Purpose

Treat the standalone repository as the entire Cognee deliverable and verify
that its code, metadata, documentation, and release automation agree on one
supported architecture.

## Parent Context

The plugin currently has a working root export, provider implementation, HTTP
client, setup flow, security controls, tests, CI workflow, and release
metadata. This phase is an audit-first pass; changes are made only for concrete
release blockers.

## In Scope

- Verify the root plugin export and Hermes discovery contract.
- Verify `plugin.yaml`, package metadata, setup flow, and documentation agree.
- Verify supported versions: Python 3.11-3.13 and Hermes 0.18.2-compatible API.
- Verify generated artifacts remain ignored and will not enter the initial
  commit.
- Review CI coverage for all declared Python versions.
- Review network and memory isolation controls.
- Review all files for secrets and machine-specific paths.

## Out Of Scope

- No Hermes core changes.
- No Cognee SDK dependency inside Hermes.
- No generic pip activation path.
- No broad or query-based memory delete tool. Exact provenance-backed deletion is in
  scope.
- No automatic remote-service deployment.
- No feature expansion beyond release blockers.

## Interfaces And Data

The release contract is:

- Root export: `CogneeMemoryProvider` from repository-root `__init__.py`.
- Metadata: `plugin.yaml` with `name: cognee` and `kind: exclusive`.
- Runtime package: `hermes_cognee_memory/`.
- Configuration: `$HERMES_HOME/cognee/config.json` plus optional
  `COGNEE_API_KEY` in the active profile `.env`.
- Activation: `hermes plugins install HaiderSultanArc/hermes-cognee-memory`.
- Setup: `hermes memory setup cognee`.
- Capture: `POST /api/v1/remember/entry`.
- Exact deletion: `POST /api/v1/forget/entry` through `cognee_forget`, authorized by
  `$HERMES_HOME/cognee/provenance.json`.
- Recall: `POST /api/v1/recall` for session and graph scopes.
- Persistence: `POST /api/v1/datasets` followed by
  `POST /api/v1/improve` at a real session boundary.

## Implementation Milestones

1. Review the complete non-generated source tree:

   ```bash
   git -C /home/haidersultanarc/arc-function/hermes-cognee-memory status --short --ignored
   ```

2. Confirm the plugin-loading tests exercise real installed Hermes discovery:

   ```bash
   uv run pytest -q tests/test_plugin_loading.py
   ```

3. Confirm the local HTTP contract test covers health, capture, session recall,
   graph recall, dataset creation, and improvement:

   ```bash
   uv run pytest -q tests/test_http_integration.py
   ```

4. Confirm no activation docs instruct users to use `pip install`.

5. Confirm no runtime dependency on the Cognee Python SDK appears in
   `pyproject.toml` or source imports.

6. Confirm `.gitignore` excludes at least:

   - `.venv/`
   - caches and bytecode
   - coverage output
   - `build/`
   - `dist/`
   - `*.egg-info/`
   - `.env`

   If `.env` is not currently ignored, add it before publication.

7. Review `.github/workflows/ci.yml`. Prefer testing all declared versions
   (`3.11`, `3.12`, `3.13`) unless there is a documented reason to use only
   minimum/maximum versions.

8. Search tracked candidates for secrets, absolute developer paths, temporary
   URLs, and private data. Any secret-like value blocks staging and commit.

## Test And Acceptance Criteria

- The root plugin module exports one provider class and no singleton
  registration object.
- Hermes discovery returns a fresh instance for each load.
- `plugin.yaml`, README, `after-install.md`, and `pyproject.toml` agree on the
  plugin name and supported versions.
- The plugin runtime has no third-party dependency other than Hermes itself.
- Plain HTTP remains restricted to loopback; remote endpoints require HTTPS.
- Redirects are not followed with authentication headers.
- Response sizes, queue sizes, retry counts, timeouts, prefetch concurrency, and
  prompt context are bounded.
- Gateway sessions use a hash of the effective Hermes session key plus Hermes session ID and never
  raw user/chat identifiers; the configured dataset remains stable across conversations.
- Missing primary gateway scope fails closed before worker/client activation.
- No secrets or real conversation content are candidates for commit.
- No generated artifact is staged.

## Future-Phase Compatibility

Keep the provider on public Hermes/Cognee contracts. Do not import private
Hermes internals merely to make the first release pass.

---

# Phase 3: Reproduce The Complete Quality Gate

## Purpose

Produce fresh, repeatable evidence that the exact release candidate works on
every supported Python version and builds cleanly.

## In Scope

- Locked dependency synchronization.
- Full tests on Python 3.11, 3.12, and 3.13.
- Branch coverage threshold.
- Ruff.
- Lockfile validation.
- Wheel and sdist build.
- Archive-content inspection.
- Git whitespace and staging review.

## Out Of Scope

- No publication.
- No active-profile installation.
- No reliance on previously reported test results.

## Implementation Milestones

1. Validate Python 3.11:

   ```bash
   uv sync --python 3.11 --extra dev --locked
   uv run --python 3.11 pytest -q
   ```

   Expected baseline: `58 passed`.

2. Validate Python 3.12:

   ```bash
   uv sync --python 3.12 --extra dev --locked
   uv run --python 3.12 pytest -q
   ```

   Expected baseline: `58 passed`.

3. Validate Python 3.13:

   ```bash
   uv sync --python 3.13 --extra dev --locked
   uv run --python 3.13 pytest -q
   ```

   Expected baseline: `58 passed`.

4. Run the release-quality gate on the default development interpreter:

   ```bash
   uv sync --locked --extra dev
   uv run ruff check .
   uv run pytest --cov=hermes_cognee_memory --cov-branch --cov-fail-under=85
   uv lock --check
   uv build
   ```

5. Inspect the wheel and sdist contents. They must include the runtime package,
   metadata, license, README/package metadata, and required source, but no
   `.env`, `.git`, `.venv`, tests containing private fixtures, caches, coverage
   databases, or local absolute paths.

6. Stage only after all gates pass, then validate the actual initial commit
   candidate:

   ```bash
   git add \
     .github \
     .gitignore \
     LICENSE \
     README.md \
     __init__.py \
     after-install.md \
     hermes_cognee_memory \
     plugin.yaml \
     pyproject.toml \
     tests \
     uv.lock
   git diff --cached --check
   git status --short --ignored
   ```

## Test And Acceptance Criteria

- All three Python versions pass the full suite.
- Branch coverage is at least 85%.
- Ruff reports no errors.
- `uv lock --check` succeeds.
- Wheel and sdist build successfully.
- The staged diff has no whitespace errors.
- No generated, secret, or private file is staged.
- The staged release candidate contains no Hermes core file.

## Future-Phase Compatibility

The quality gate becomes the release checklist and CI contract. If supported
Hermes or Python versions change later, update metadata, CI, docs, and tests in
one release.

---

# Phase 4: Create And Publish The Repository

## Purpose

Turn the reviewed standalone tree into a real Git repository that Hermes can
install from GitHub.

## Parent Context

The repository currently has no commit and no remote. Publication is the only
remaining reason the documented install command returns 404.

## In Scope

- Review the staged initial tree.
- Create the initial commit.
- Create the public GitHub repository.
- Add the canonical SSH remote.
- Push `main`.
- Verify GitHub Actions.
- Verify the repository is publicly readable.

## Out Of Scope

- No PyPI publication.
- No Hermes core PR.
- No production-profile setup yet.
- No release tag until end-to-end installation passes.

## Implementation Milestones

1. Review the staged files and diff summary:

   ```bash
   git status --short
   git diff --cached --stat
   git diff --cached --check
   ```

2. Create the initial commit:

   ```bash
   git commit -m "feat: add Cognee memory provider for Hermes"
   ```

3. Create the public repository named:

   ```text
   HaiderSultanArc/hermes-cognee-memory
   ```

   Repository creation is an external action and requires explicit approval.
   The current machine does not have `gh` available, so creation may use the
   GitHub UI or another already-authenticated GitHub workflow.

4. Configure the canonical remote:

   ```bash
   git remote add origin git@github.com:HaiderSultanArc/hermes-cognee-memory.git
   git push -u origin main
   ```

5. Verify the remote state:

   ```bash
   git remote -v
   git status --short --branch
   git log -1 --oneline --decorate
   ```

6. Verify the public URL loads and GitHub Actions passes for all configured
   Python versions.

## Test And Acceptance Criteria

- `main` has an initial commit.
- The local tree is clean apart from ignored build artifacts.
- `origin` points to the intended repository.
- The public GitHub URL returns the repository, not 404.
- GitHub Actions passes.
- The README install command references the actual repository owner/name.
- No secret appears in Git history, workflow logs, or release artifacts.

## Future-Phase Compatibility

Do not rewrite the initial commit after other users can install it. Fix any
post-publication issue with a normal follow-up commit and release note.

---

# Phase 5: Disposable-Profile End-To-End Validation

## Purpose

Prove that the published repository—not the local checkout—installs and works
through Hermes's real user-facing flow against a real Cognee API service.

## Parent Context

Unit tests and the local HTTP contract test prove the provider code. This phase
proves repository installation, Hermes discovery, profile isolation, setup,
network configuration, session capture, graph persistence, and later recall.

## In Scope

- Use a disposable Hermes profile.
- Install from the published GitHub repository.
- Run the real memory setup flow.
- Validate against a reachable Cognee service with `CACHING=true`.
- Use synthetic canary content only.
- Validate CLI behavior first, then gateway isolation if a safe test gateway is
  available.
- Validate exact forgetting for one newly captured synthetic entry.

## Out Of Scope

- No installation into the active `arcion` profile yet.
- No real private conversation data.
- No broad or query-based Cognee deletion test.
- No exposure of an unauthenticated Cognee service to an untrusted network.
- No destructive profile or dataset cleanup without explicit approval.

## Implementation Milestones

1. Confirm Cognee health and required API version:

   ```bash
   curl -fsS http://127.0.0.1:8000/health
   ```

   If Cognee is remote, use its HTTPS URL instead. Do not send an API key to a
   plain-HTTP remote origin.

2. Create a fresh test profile:

   ```bash
   hermes profile create cognee-e2e
   ```

3. Install the published plugin into that profile:

   ```bash
   hermes --profile cognee-e2e plugins install HaiderSultanArc/hermes-cognee-memory
   ```

4. Configure the provider interactively:

   ```bash
   hermes --profile cognee-e2e memory setup cognee
   ```

   Enter the API key only through Hermes's secret prompt. Never place it in a
   command, plan, transcript, or test fixture.

5. Verify discovery and selected provider:

   ```bash
   hermes --profile cognee-e2e memory status
   hermes --profile cognee-e2e plugins list
   ```

6. Run a synthetic CLI canary session. Example canary meaning:

   ```text
   Cognee E2E canary: the blue rover carries seven cedar tokens.
   ```

   Complete the session normally so capture and improvement can run. Start a
   new session and ask for the canary fact. Confirm the answer comes from
   recalled memory rather than current conversation context.

7. Verify expected API behavior through Cognee logs or an approved local
   inspection path:

   - health check succeeded;
   - Q&A entry was accepted;
   - session and graph recalls were issued;
   - the dataset was created idempotently;
   - improvement completed synchronously;
   - the canary was recallable after the original Hermes session ended.

8. If gateway testing is available, run only synthetic test identities and
   verify:

   - two DM/session keys use the same configured dataset but different hashed session IDs;
   - one intentionally shared group/thread scope and Hermes session produce the same session ID;
   - a new Hermes session produces a new session ID without creating another dataset;
   - raw sender/chat IDs never appear in dataset or session identifiers;
   - primary non-CLI initialization without `gateway_session_key` fails closed;
   - cron/delegated/non-primary contexts do not auto-write.

9. Capture a second synthetic canary, retain its returned entry UUID, complete graph
   improvement, and invoke `cognee_forget` only after an explicit test instruction.
   Verify the exact UUID disappears from session recall and graph/vector retrieval while
   an adjacent canary remains recallable. Repeat the same UUID once and require an
   idempotent `already_forgotten` result from the local tombstone.

10. Record cleanup requirements for the disposable profile and synthetic Cognee
   dataset. Perform deletion only after explicit approval because Hermes profile
   deletion and Cognee dataset deletion are destructive.

## Test And Acceptance Criteria

- Installation succeeds from GitHub with no local symlink or checkout fallback.
- Hermes discovers `cognee` as an exclusive memory provider.
- Setup stores non-secret config under the disposable profile and the API key
  only in that profile's `.env`.
- `hermes memory status` reports Cognee as active and reachable.
- A completed turn reaches `/api/v1/remember/entry`.
- A real session boundary triggers dataset creation and `/api/v1/improve`.
- A later session recalls the synthetic canary from Cognee.
- A newly created entry can be forgotten by exact UUID without deleting its dataset or
  an adjacent memory.
- Recalled text is bounded and labeled as untrusted reference data by the
  provider itself; the plugin must not depend on the deferred Hermes prompt
  patch.
- No real private content is sent during validation.
- No raw gateway identity appears in a dataset name.

## Future-Phase Compatibility

Keep the disposable-profile procedure as the manual release smoke test until a
safe automated integration environment can run a real Cognee service in CI.

---

# Phase 6: Release And Optional Production Adoption

## Purpose

Publish a stable initial release after the exact public installation path has
passed end-to-end validation.

## In Scope

- Confirm final clean state and CI.
- Create an annotated `v0.1.0` tag.
- Publish release notes.
- Document compatibility and operational limitations.
- Offer, but do not automatically perform, installation into the active
  `arcion` profile.
- Record unrelated Hermes improvements as deferred work only.

## Out Of Scope

- No automatic Cognee service deployment.
- No automatic installation into every Hermes profile.
- No Hermes core PR bundled with the release.
- No promise of guaranteed persistence through prolonged Cognee outages.
- No unsafe mapping of Hermes delete operations to Cognee's broader forget operations;
  only the reviewed exact-entry contract is supported.

## Implementation Milestones

1. Re-run the Phase 3 quality gate on the exact release commit.

2. Confirm GitHub Actions is green on `main`.

3. Create and push the tag after explicit approval:

   ```bash
   git tag -a v0.1.0 -m "Release hermes-cognee-memory 0.1.0"
   git push origin v0.1.0
   ```

4. Publish release notes covering:

   - supported Python and Hermes versions;
   - required Cognee API and `CACHING=true`;
   - installation and setup commands;
   - local HTTP versus remote HTTPS rules;
   - data sent during automatic capture and recall;
   - persistent dataset and hashed gateway session semantics;
   - best-effort behavior during prolonged service outages;
   - exact-entry forget support, its local provenance ledger, and the legacy-entry
     limitation;
   - absence of broad and query-based delete/forget support;
   - upgrade and rollback instructions.

5. Verify a fresh install from the tag or default branch still works.

6. Ask separately whether to install and configure the release in the active
   Arc'ion profile. Do not infer approval from release publication.

7. Add the following optional Hermes follow-ups to a backlog, not to this
   release:

   - memory-context untrusted-data framing;
   - early safe-mode plugin-discovery gating;
   - generic standalone memory-provider documentation corrections.

   Each follow-up needs its own reproduction, current-main validation, branch,
   tests, review, and PR in `/home/haidersultanarc/arc-function/ArcHermes`.

## Test And Acceptance Criteria

- `v0.1.0` points to the exact commit that passed CI and end-to-end validation.
- Release notes accurately describe security and reliability limitations.
- The documented installation command works for a fresh profile.
- The active Arc'ion profile remains unchanged unless separately approved.
- No Hermes core change is part of the Cognee repository or release history.
- Deferred Hermes ideas remain clearly separate and uncommitted to ArcHermes.

## Future-Phase Compatibility

Future plugin releases should use normal semantic versioning, preserve the
standalone boundary, and verify against newly supported Hermes/Cognee versions
before widening version constraints.

---

# Global Completion Criteria

The Cognee task is complete only when all of the following are true:

- `/home/haidersultanarc/hermes-agent` has no task-related tracked changes.
- `/home/haidersultanarc/arc-function/ArcHermes` remains clean.
- The standalone plugin is the only implementation deliverable.
- The plugin has a committed and publicly reachable GitHub repository.
- CI passes for every declared Python version.
- The published install command succeeds in a disposable Hermes profile.
- Real Cognee capture, session-end improvement, and later recall pass with
  synthetic data.
- Exact forgetting passes for a newly captured synthetic entry without collateral
  deletion.
- Persistent cross-session graph recall and gateway session-cache separation are verified or
  explicitly marked as release blockers if the required real test path is unavailable.
- No secrets, private content, generated artifacts, or machine-specific paths
  are present in Git history.
- `v0.1.0` is tagged only after the public installation path passes.
- Active-profile installation remains an explicit post-release choice.

# Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Unrelated work is lost during Hermes cleanup | Export concern-specific patches first; restore only the nine reviewed tracked files; never run `git clean` or `reset --hard`. |
| Plugin appears green only because it imports the local checkout | Perform Phase 5 from the published repository in a disposable profile with no local symlink. |
| Real secrets enter Git or logs | Keep API keys in Hermes secret prompts/profile `.env`; scan staged files and archives before commit. |
| Gateway session cache crosses conversation boundaries | Hash the effective `gateway_session_key` together with the Hermes session ID, use that value only as Cognee `session_id`, and fail closed when gateway scope is missing. |
| Persistent memory fragments across conversations | Keep one configured dataset per agent/profile and reserve additional datasets for deliberate tenant or trust boundaries. |
| Cognee outage loses queued writes before shutdown | Keep bounded retries and flush windows, document best-effort limits, and require operator supervision for stronger guarantees. |
| Recalled memory injects instructions | Bound, flatten, deduplicate, and label provider output as untrusted reference data; do not depend on an unrelated Hermes prompt change. |
| A wrong or legacy UUID deletes unrelated memory | Require a local entry/session/dataset provenance tuple, confirm the returned UUID, retain tombstones, and expose no broad or query-based delete path. |
| Initial GitHub publication exposes an unfinished contract | Publish only after the staged release candidate passes the complete local gate; tag only after public end-to-end validation. |
| Future Hermes fixes become mixed back into Cognee | Keep archived patches outside both repos and require separate ArcHermes plans/branches/PRs. |

# Deferred Work

These items are intentionally not part of the Cognee release:

- Applying the memory-context hardening patch to ArcHermes.
- Applying the safe-mode discovery patch to ArcHermes.
- Updating upstream Hermes memory-provider documentation.
- Publishing the package to PyPI.
- Building a generic pip memory-provider bridge.
- Adding broad or query-based Cognee deletion/forget operations. Exact
  provenance-backed entry deletion is implemented separately.
- Automatically deploying or administering the Cognee service.
- Automatically configuring Cognee in the active Arc'ion profile.
