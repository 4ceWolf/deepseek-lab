# Native desktop build — 2026-10-21

Built only, following the user's instruction. No packages installed; no desktop menu entry, autostart entry or system service registered. No visible app window or permanent new agent service was launched. The existing browser lab was not restarted or changed. Native Qt interaction checks ran offscreen with temporary state and fake model replies.

## Delivered

- Native PySide6/Qt window, using the already installed host runtime. It is a QWidget application, not a website wrapper.
- Independent Unix-socket agent service with persistent chats, drafts, tool results, task checkpoints and usage. UI reloads leave model requests and commands in the service. Reconnect behavior is covered through real temporary sockets and mocked provider work.
- ECU controls for reasoning Auto/manual, model, output cap, tool round budget, global and project instructions, plus an effective-instructions viewer and project AGENTS.md support.
- Project file inspection, explicit selected-text attachments, reviewable proposals and stale-source checks before applying a patch.
- Openable documentation directory with relative file list, filtering, Markdown preview and model search/read tools. Embedded Markdown resources do not fetch arbitrary local or network data.
- Separate project/personal memory with dates, provenance, unverified state, model search/save tools and user add/edit/delete actions.
- Persistent API-key integration through Linux Secret Service; validate, replace and remove controls. Key text is excluded/redacted in conversations, drafts, memory, event records and tool results. There is no plaintext fallback.
- Four command modes: full access, ask when needed, approve every command and disabled. Ask mode automatically permits only literal pwd/ls/ls -la using system binaries. The default is approval for every command. Models cannot change permissions or approve themselves.
- Live PTY command receipts: exact command, cwd, environment label, approval fingerprint, elapsed time, input, output, exit code, stop and timeout. Working-directory identity is checked again at execution. Commands execute on the laptop under the selected policy; this general host command interface is separate from the earlier restricted executor.
- Dev mode: model-readable app source, separate editable stages, changed-file diffs, syntax checks, preview window, explicit activation and rollback. Active tasks and commands block activation. Preview windows share the existing service but cannot silently replace it with unactivated stage backend code.
- Idle backend restart with a draining guard. The client waits for old-service disappearance and reconnects to a replacement. Saved state and keyring connection reload; live process replacement during active work is not attempted.

## Verification

The previous 43 controller/executor checks passed during this build. Added backend coverage includes 18 offline tests: disabled commands, narrow automatic permissions, exact approval hashes, PTY input/output, timeout, directory replacement, docs/memory scope, symlink/path escape, stale patches, actual tool-result replay, reasoning retention with tool calls, draft preservation, round limits, key redaction, service interruption, private socket reconnect, staged activation/rollback and idle restart guards/client sequencing. Native UI coverage includes five offscreen Qt tests for task send/reconnect, actual command approval/output, docs/memory/settings/focus, error reporting and wide/compact rendering.

These checks total 66 across the installed test environments. No paid inference or real keyring write was used for the desktop build. Syntax compilation and bundle integrity are checked during packaging.

## Build artifacts

`dist/deepseek-workspace-native.zip` is an editable source bundle for the installed native Python/Qt runtime. `dist/BUILD-MANIFEST.json` lists file hashes and `dist/SHA256SUMS` identifies the archive. User data, SQLite databases and actual credentials are excluded. The build does not bundle Qt or produce a self-contained executable; that would require packaging tools not currently installed.

The source entry point is `sh run-desktop.sh` on the host. Launching is deliberately left to the user. [Desktop usage and architecture](../desktop/README.md) documents the controls, data paths, limits and future launch command. Headless fixture previews are in build/previews/desktop-wide.png and desktop-compact.png.

## First-launch verification still needed

Actual Secret Service unlock/save/load, a real DeepSeek tool conversation, a visible window in the user's compositor, interactive terminal applications beyond the simple PTY test, screen-reader behavior and production recovery across an OS restart remain unverified. Mocked API/keyring tests prove the wiring and boundaries, not the availability of the user's live provider/keyring session. Arbitrary self-edits can still introduce defects; Dev validation is syntax-only until additional tests are explicitly run under the command policy.

Model replies currently arrive after each provider request rather than token-by-token. Command output is live. Cancelling an in-flight model request takes effect when the network call returns or times out; host command stop is immediate. Records awaiting a response after service interruption are reconciled as interrupted rather than automatically repeated.
