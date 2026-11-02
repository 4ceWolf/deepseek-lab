# Recovery, verification and operating controls — 2026-10-22

This build follows GAP-REVIEW-2026-10-22.md. It addresses the identified lifecycle, recovery, evidence, context, cost and coding-isolation gaps. It is not a certification that no defects remain.

## Recovery and task state

Review → Review recovery shows saved requirements, completed claims, remaining work, command states and unresolved provider reservations. Continuing is explicit; stale/double continuation requests are rejected. Uncertain command/provider state requires acknowledgment in that review. Ordinary messages cannot bypass unresolved execution: use recovery or a separate task. The service does not replay commands; the resumed model can request new commands under the current permission mode. In Full access those new requests can execute without individual approval.

Checkpoints survive normal follow-ups as well as recovery. They are model-maintained state, not independent proof of completion. A finished model reply no longer clears a checkpoint's outstanding work. The main status says reply finished and points to Review for verification.

Commands stopped while queued cannot subsequently launch. Stop and process registration are synchronized. Service startup invalidates old pending approvals, and interrupted processes remain explicitly unknown rather than being killed using potentially reused PIDs. Disabling commands cancels queued/pending work; already running commands still require Stop. Project/docs changes are blocked while tasks or commands/approvals remain active. Command records identify their project and owning run; the UI scopes activity to the current project/task plus manual project commands.

## Evidence receipts

run_check uses the same command permissions as run_command and records hashes of 1–20 existing project source files. Review shows exact command status, exit code, output excerpts and whether the scoped source hashes still match. Failed commands and stale/unavailable source evidence are never converted into successful verification by a model's final reply. An exit-0 receipt establishes only that command result and scope freshness; it does not establish that a test was meaningful, covered all requirements or proves correctness.

Receipts can be refreshed/exported. Model calls get_task_receipt for a bounded preview; full records stay available in Review. Receipts inspect up to 300 recent project commands and 100 task patches and hash at most 200 distinct scoped files per refresh. Source/output changes after a receipt require refresh. Manual commands are not automatically attributed to the task. Requirements and completion claims are explicitly unverified.

## Coding safety

Review → Create coding worktree requests a detached Git worktree at committed HEAD through the command approval system. Finish/approve that receipt, then Open worktree. The original checkout, including uncommitted work, is preserved. Uncommitted files are not copied into the new worktree. Inspect Git diff is also a normal permission-controlled command. Worktrees are retained; there is no automatic deletion, commit, merge or publish operation.

Reviewed file proposals save a private original-byte backup and permissions before writing. Roll back this patch refuses when content or file mode has changed since application. New-file rollback removes the newly created file. Apply/rollback operations are serialized in the service. Unique temporary files, flushed writes and atomic replacement avoid clobbering an existing temporary filename.

Apply/rollback write-intent records are reconciled against actual file hashes on service startup. Matching states are recognized; uncertain/conflicting states require manual review, and reconciliation never writes over the source. These are single-file protections, not a transactional snapshot of arbitrary shell actions or the entire operating system. Concurrent external writers and power-loss/filesystem failures are not comprehensively tested.

## Budgets and routing

ECU → Budgets, routing & context configures task token and USD estimate budgets; zero disables a budget. Task accounting carries across ordinary messages and recoveries. A resumed run retains its parent's caps/prices; new normal runs use saved settings but carry prior accounting. Unsettled provider reservations are retained and included conservatively, with their run IDs shown. Missing/inconsistent usage stops the loop instead of assuming a free request or retrying it.

Request admission estimates input from serialized UTF-8 bytes, tool schemas and protocol allowance, plus the output ceiling. This can reject requests whose actual token use would be lower. It is a conservative admission estimate, not an exact tokenizer or guaranteed provider billing cap. Actual returned usage updates accounting. In-flight requests can still be billed on interruption. There are no automatic provider retries.

Dollar estimates require positive, user-supplied input/output USD prices per million tokens. No prices are silently invented, fetched or verified. Use current cache-miss input/output rates and update them when provider prices change; cache discounts, promotions and invoices may differ. Previous unpriced task usage remains unknown and prevents a reliable USD admission estimate; start a separately budgeted task when necessary. Estimates and local records do not enforce the provider account's billing balance.

Optional economy routing uses deepseek-flash for none/low-effort tasks only when supplied rates show it is no more expensive on both input/output and strictly cheaper on at least one. Missing or unfavorable rates leave the selected model unchanged. High/max-effort tasks are not downgraded by this option. No benchmark claim of equal quality or a specific cost reduction is made.

## Context and bounded data access

Compaction preserves every user message and the most recent two complete user/assistant/tool groups. Older assistant/tool groups can be omitted from the outgoing request, never from stored history. Saved requirements/checkpoints accompany continuation. read_history retrieves saved messages, including character-paginated serialized JSON for oversized messages. If retained user instructions and recent exchanges cannot fit, the run stops explicitly rather than silently deleting them. With compaction disabled, the configured byte ceiling still stops oversized requests. Tool schemas/system instructions are included in the admission calculation.

Earlier assistant decisions/tool observations can be absent from a compacted request; retrieve/reinspect them when relevant. This is deterministic context reduction, not a claim of lossless semantic summarization. Large old conversations can still require a reviewed new task.

Polling now limits records inside SQLite, rather than loading entire histories before slicing. Freshness hashing is reused within a receipt and automatic Review refresh follows state changes. Build/export does not include task data or credentials.

## Verification

106 offline checks passed: 46 native backend/artifact/image/reliability checks, 43 existing controller/server/executor/capability checks, 15 offscreen native UI checks and 2 offscreen HTML browser checks. The new reliability suite has 18 checks covering queued cancellation, expired approvals, permission changes, durable checkpoints, failed-check vs false model claims, source freshness, token/USD admission rejection, supplied-price routing, unknown usage, conservative recovery accounting, normal-follow-up accounting, duplicate recovery rejection, raw-history retention/chunk retrieval, strict context limits, guarded byte/mode rollback, interrupted patch reconciliation, scoped SQL polling, and actual Git worktree preservation of dirty original files.

UI checks exercise recovery acknowledgment, displayed receipts, explicit budget/rate controls, and worktree command approval. Rendered Review, wide/compact, image and artifact views were inspected. The HTML artifact controls continue to pass their offscreen browser checks.

No dependencies were installed, no visible app/browser was launched, no real keyring was written and no paid provider call was made. Production keyring/provider integration, tokenization/billing accuracy, full assistive-technology coverage and hours-long real repositories remain unverified. The pre-change source bundle was retained in dist/archive. The updated distributable remains an editable source ZIP requiring the installed native runtime.
