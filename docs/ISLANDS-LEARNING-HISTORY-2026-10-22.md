# Islands, versioned learning and website history — 2026-10-22

## Shipped source changes

The installed editable native Qt app now follows the selected Islands direction: graphite surfaces, a persistent conversation sidebar, a readable central text column, a quiet toolbar and a bounded composer. Memory, documentation, Learning and ECU controls are available without putting their forms on the main conversation. Website Chat has the same basic composition. Code retains command activity, artifacts, review, key management, files and Dev staging.

Short native opacity transitions introduce mode changes, newly added messages, settings and workspace/activity panels. Streaming updates do not repeatedly animate the transcript. More → Reduce motion disables new transitions; the preference persists. No action depends on animation completion. This is a native implementation of the approved concept, not the HTML concept page embedded as the app.

## Learning: what actually changes

API Code mode can already save and retrieve project/personal memory. It can now revise its own entries with an expected revision. Prior versions are retained atomically, stale revisions are rejected, cross-project edits are rejected, and model edits cannot overwrite user-authored notes. User edits preserve the same ID and history too. Memory → Version history shows previous text; edit an entry to restore text from an earlier version. All notes retain provenance, dates and an unverified label.

The new `propose_ecu_lesson` tool saves one bounded project lesson per task run: title, lesson, rationale and IDs of checks from that same run. It does not change settings, permissions or model weights. Proposals appear in Learning. Activation requires current successful `run_check` receipts with unchanged scoped source hashes, an idle API agent, and the user's review action. A successful command is evidence for that command, not proof of model-quality improvement or relevance; the interface states this explicitly.

At most five active lessons, totaling 2,400 characters, enter future API turns as advisory project guidance. They do not override current user requirements, base instructions or command permissions. Reject and Roll back are available. Activations, rollbacks, proposals and memory revisions are logged. No hidden background model calls, self-scores, automatic benchmark wins or autonomous permission escalation have been added.

Website account chat remains tool-free. The model's memory-revision and ECU-proposal tools are available in API Code mode, not the website bridge. This is persistent application learning, not weight training, and no improvement percentage has been established. Future evaluation should compare baseline and candidate lessons on held-out tasks before automating promotion.

## Website history

The previous bridge connected an account but never queried its remote history. Sign-in now fetches up to 100 recent conversation titles; Refresh website history repeats that read-only fetch. Conversations already represented by a locally tracked chat are not duplicated. Selecting an imported entry fetches its visible messages on demand; unrelated transcripts are not fetched in bulk. Drafts in local chats survive switching to imported history.

Imported histories are explicitly read-only. Open original on website continues the original in DeepSeek's supported UI. Local chat creation and continuation through the existing bridge are unchanged. Imported reasoning and attachments are excluded. Failed imports keep local chats unchanged, display an error, and do not send or replay model messages. The index uses the app's private state; Forget login clears it. Transcripts are rendered on demand, not silently saved into memory or used as training data.

Research references: [DeepSeek-backup-web endpoint documentation](https://github.com/Map9876/DeepSeek-backup-web), [DeepSeek Web Chat Import](https://github.com/wpc0323/deepseek-web-import). Those are unofficial clients, not provider guarantees. Implementation here uses bounded requests to the fixed DeepSeek origin through the existing private authenticated gateway. The live response used `chat_messages` and REQUEST/RESPONSE fragments; the adapter also accepts the older `messages` shape. Changes in these private endpoints can still break importing.

## Verification

- 45 combined native UI, website-provider and learning tests passed before the final small refinements. These include motion on/off, history selection and draft restoration, memory conflicts/protection, fresh-check gates, rollback and persistence.
- 99 broader backend/controller tests passed, including the six learning checks then present.
- 10 Node gateway/parser checks passed, including the live-observed history response shape.
- Focused UI checks were repeated after fixing the native reading-surface background.
- Live saved-account reconnection succeeded. The directory returned 5 conversations; one selected conversation loaded 10 messages. Only counts/schema metadata were exposed in diagnostics, not its contents. No generation request was sent and no API usage was incurred by these checks.
- Native screenshot: `build/previews/desktop-islands.png` uses clearly illustrative fixture conversation/results, not a live model success claim.

The service was not running when work resumed, so it was started in a transient user-session systemd unit (`deepseek-lab-session`). This is not an installed/enabled boot service. Source, docs, state and the installed launcher remain under their established paths. Reopening the desktop app picks up the UI changes; backend changes require the service to load the updated source.

## Follow-up: OpenCode-style disclosures, input and Chat artifacts

User requested removing the separate Activity window/panel and expanding work in the conversation. The toolbar Activity entry and the separate vertical command pane are removed. Thinking and tool request/results now have individual display-only disclosure links. The command approval/input/output controls sit in the conversation's scroll flow behind an Activity disclosure, preserving exact approvals, elapsed time and outputs. No new OS command permission is granted. Inspired by the display/inference distinction in [OpenCode's thinking documentation](https://docs.opencode.ai/docs/tui/); expanding a block never changes reasoning effort or provider context.

Both composers now send on Enter, use Shift+Enter for a newline, and retain Ctrl+Enter. The editor preserves IME composition and ignores repeated keydown sends. Website Chat creates an initial local conversation when necessary; previously a new installation could remain unable to send until New chat was clicked.

Website Chat has a native Artifacts tab with its own per-conversation storage. A concise provider instruction describes the `deepseek-artifact` fenced JSON format. Completed assistant responses and selected remote histories are checked for valid bounded chart/table/flowchart specs. Valid specs render in the existing native visual/data/specification/appearance editor with HTML/SVG/PNG/CSV/JSON exports; the transcript links to the preview. A manual JSON import is also available. Artifact edits are versioned with conflict rejection. Arbitrary provider HTML/JavaScript is not executed; website attachments or website-only artifact formats are not imported automatically. Local tools remain disabled in website mode. This adds prompt overhead for visual-format instructions; no reduction in thinking cost is claimed.

History follow-up: all five account histories loaded through the service. A native UI traversal initially opened four, revealing that the deduplication rule hid one original website conversation with a local copy. That filter was removed so the full remote directory remains visible. Current history is still read-only; the original website link continues the original thread. Service state and the displayed app must both be updated when source changes.

Verification: 42 native UI/provider checks passed, including ordinary Enter, Shift+Enter, independent thinking/activity disclosures, hidden raw provider thoughts, exact command approvals, artifact capture and revision conflicts. No real generation request was made during history/UI verification. Roblox Caffeine is configured separately; see `/home/user/Projects/roblox-caffeine/README.md`.
