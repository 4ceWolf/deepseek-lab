# Project gap review — 2026-10-22

Scope: native desktop agent, execution lifecycle, durable state, evidence, context, costs and coding recovery. Review precedes the current reliability additions. Previous tests and historical evaluations remain valid only for their documented scope. No claim that every possible gap can be eliminated by an audit.

Confirmed gaps from source inspection:

1. A queued command can start after Stop because cancellation only kills already registered processes. Fix launch/stop synchronization and persist cancellation.
2. Awaiting approvals survive service restart, even when their owning run is interrupted. Invalidate them and require a fresh request.
3. A normal provider stop clears all remaining checkpoint work, confusing a finished reply with verified task completion. Preserve task state and separate observed command checks from model claims.
4. Interrupted work has no explicit recovery review/continuation path. Add user-triggered recovery without replaying commands, with uncertainty disclosure and duplicate protection.
5. Recorded commands do not consistently identify project/session; the command UI lists unrelated work. Attach project provenance and scope the UI.
6. Store.list loads all matching records before callers slice them. Move polling limits into SQLite queries.
7. Context overflow stops the task; older complete tool exchanges have no bounded retrieval/compaction path. Keep all user instructions and checkpoints, compact older assistant/tool groups, retain raw history and allow retrieval.
8. Output ceilings are not aggregate usage/spending controls. Add per-run-chain admission budgets and user-supplied pricing estimates, retaining uncertain in-flight reservations on interruption.
9. Patch proposals lack user-facing rollback copies; Git isolation has no integrated workflow. Add guarded patch rollback and permission-controlled worktree requests.
10. No receipt distinguishes a passed executable command, source freshness, untested changes, outstanding steps and uncertain execution. Add actual command/source evidence and clear limits.

Implementation and validation results are recorded separately in RELIABILITY-CONTROLS-2026-10-22.md. All changes are build-only and tested with temporary projects and mocked provider responses. Live provider/keyring, hours-long production workloads and full accessibility testing remain outside this offline pass.
