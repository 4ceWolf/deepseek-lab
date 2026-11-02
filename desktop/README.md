# DeepSeek Workspace desktop

A native Qt application with a separate, persistent local agent service. It uses installed Python, PySide6 and the Linux Secret Service. No browser shell, Electron runtime, package installation or account setup is required by this source build.

## Installed on this machine

DeepSeek Lab is installed as an editable user-local application. Find **DeepSeek Lab** in the app menu or run `~/.local/bin/deepseek-lab`. Code, documentation and persistent state remain in `~/Projects/deepseek-lab/`; the menu launcher and command wrapper reference that source. Chromium is now installed for website-account mode. Choose **Chat → Sign in** to authenticate in the dedicated browser. The account connection itself has not yet been tested.

The repeatable user-local registration command is `python3 install_desktop.py`; it does not install system dependencies or launch the application. See [installation record](../docs/INSTALLATION-2026-10-22.md).

## Launch from source

From the project folder on the host:

```sh
sh run-desktop.sh
```

Inside a Flatpak terminal, the installed Qt runtime is on the host:

```sh
flatpak-spawn --host sh /home/user/Projects/deepseek-lab/run-desktop.sh
```

The first launch starts desktop/service.py as a detached local process and connects through a Unix socket readable only by the user. Closing or reloading the window leaves that service and its requests running. The old localhost testing website is separate and continues using its own records and memory-only connection.

## Everyday use

Choose **Chat** in the mode selector for the experimental native **Website account** view. With no API key, the app starts here. Choose **Code** for API tasks. It reuses a dedicated DeepSeek website login through a bundled, separate bridge; this mode does not use your paid API key. Choose **Sign in / Reconnect** to open a dedicated system Chrome/Chromium profile. Google sign-in is subject to the provider's browser policy; the app does not bypass login restrictions. The optional executable picker supports an existing Chrome/Chromium installation. Node 22+ and that browser are required; this build installs or downloads neither.

Website chats have their own saved local history, drafts, elapsed time, custom instructions, Auto/On/Off thinking, and Search toggle. Search is available with the bridge's Flash route and is disabled with Pro. Auto uses complexity cues and message length to choose on/off; it cannot apply the API's distinct effort levels. Replies stream into native widgets; reasoning stays outside the visible answer. The bridge is based on inspected upstream code, not a provider-supported consumer OAuth API. Website quotas still apply, usage is marked unknown, and existing website history is not imported.

The website provider has **no commands, file access, memory tools or API-agent tool loop**. Those remain in the separate API workspace. Closing the chat window keeps a request running in the local service. Stop closes the website bridge and retains partial output; an interrupted chat must be replaced with a new one rather than replayed. Complete chats can continue after reconnecting while the bridge's saved lineage remains available. Forget login removes the dedicated profile/auth files, retaining local transcript text. Website auth is stored in a private local directory with restrictive filesystem permissions, not in the API key's Secret Service entry. Do not share that directory or the browser debugging endpoint.

**Build validation is offline. Live sign-in, current private endpoint compatibility, search results, and Google login have not been verified.** This machine currently lacks system Chrome/Chromium. The UI reports this prerequisite without installing anything. Official website access remains available through the window's **Official website** button.

See [website provider implementation and verification](../docs/WEBSITE-ACCOUNT-BUILD-2026-10-22.md).

1. Open a project, connect a DeepSeek key and choose command permissions.
2. Keep reasoning on Auto or choose an explicit effort. Native Auto raises effort for proofs, detailed technical work and failed executable checks; Max remains explicit. The output ceiling can be manually raised to 131072, while saved/default limits stay unchanged. Set an output ceiling and maximum model/tool rounds per turn. Each round can incur an API request; these settings are not a dollar spending cap.
3. Chat, inspect files, review proposed patches and watch command requests/output. The model can search docs and memory through real tools, and save task checkpoints.
4. Add global instructions, additional project instructions or a project AGENTS.md. Inspect the combined instructions before the next turn. Saved controls are used for subsequent turns; command permissions remain enforced by the service.

Command modes:

- Commands disabled: proposals can be discussed, no shell command starts.
- Approve every command: every command waits for an exact approval.
- Ask when needed: only literal `pwd`, `ls` and `ls -la` run automatically. Everything else asks.
- Full access: commands run without individual approval. They execute on the laptop, not inside the earlier pure-function sandbox.

Commands have working-directory receipts, input records, combined PTY output, elapsed time, exit status and stop/timeout controls. Approval binds the exact command, directory path and timeout. Directory identity is checked before spawn. Changing the command requires a new receipt. The same permissions apply to commands requested during development. Mode changes affect new requests; switching to disabled also denies pending approvals. Stop commands explicitly to terminate already-running commands.

The shell is non-login `/bin/sh -c`; interactive input is supported through a PTY but this is not a full graphical terminal emulator. Output is bounded to 1 MiB per command. General commands can modify the host according to the selected mode. File proposal tools separately preserve originals until the user applies a patch.

See [thinking controls and how chat modes differ](../docs/THINKING-AND-CHAT-2026-10-22.md). Stronger effort is not a guarantee of another model’s capability.

## Environment context

Each native API request includes the observed service OS, selected project/docs/state paths, shell behavior, live command permissions and Dev mode, plus run model/effort/budgets and capability limits. DeepSeek can refresh this with get_environment. **Inspect effective instructions** shows the snapshot. This describes observations rather than assuming packages or system health, and does not enumerate environment secrets. It applies to native API chat, not the external Normal chat website. See [verification](../docs/ENVIRONMENT-AWARENESS-2026-10-22.md).

## Recovery, evidence and operating controls

Open **Review** to inspect verification receipts, saved requirements/remaining work and uncertain execution. **Review recovery…** starts a new continuation after reviewing the saved state; it never replays commands on its own. The resumed model uses your current command mode. A finished reply is distinct from verification. DeepSeek can use **run_check** to attach command results to source hashes; changing those files makes the old evidence stale.

**Budgets, routing & context…** in ECU configures task token/USD admission estimates, supplied model prices, optional cheaper-model routing and context compaction. Zero disables a budget. Actual usage and uncertain reservations carry across messages; recovery retains its earlier cap/prices. Prices must be supplied and kept current. These are local estimates, not a provider billing guarantee. Context compaction retains user messages and raw stored history while omitting older assistant/tool groups from requests; oversized retained context stops explicitly.

Review also offers **Create coding worktree**, **Open worktree…** and **Inspect Git diff**. Git commands follow normal approvals. Worktrees start from committed HEAD and preserve the original checkout; uncommitted work is not copied automatically. Reviewed patches have guarded **Roll back this patch** backups. Backups preserve original bytes and modes; interrupted patch writes reconcile by observed hashes without overwriting conflicts.

See [audit findings](../docs/GAP-REVIEW-2026-10-22.md) and [controls, test evidence and limits](../docs/RELIABILITY-CONTROLS-2026-10-22.md).

## Documentation and memory

Choose a documentation directory, filter its files and preview Markdown/text. Project file previews can be explicitly attached to a message. The model can search/read docs on demand and see actual tool results in the conversation. Sensitive file suffixes, .env files, private/generated directories and paths escaping the chosen root are excluded by these file tools.

Memory has separate project and personal scopes. It is stored independently from chats in the service database, retrieved through a search tool rather than bulk-loaded. Entries carry source/date information and remain marked unverified. Add/edit/delete memory in the Memory panel. Old chat messages that already contained a memory are retained as historical evidence after that memory is deleted; deletion is not retroactive chat erasure.

## Visual artifacts

In API chat, ask for a chart, flow diagram or comparison table. DeepSeek can create bar, line and donut charts, flowcharts and tables in the central **Artifacts** tab. Inspect Data, edit and save the JSON Specification, adjust zoom, or export a saved revision as HTML, SVG, PNG, CSV or JSON. The Appearance tab previews editable colors and palettes; save changes to keep them. Text labels can match chart colors. Single-series bars support a different color per category. Source labels describe provenance; they do not certify accuracy. Old revisions are retained in storage and stale edits are rejected. Flow diagrams use a simple grid layout; complex graphs may cross. Tables and long diagrams can be inspected with Fit width and scroll controls.

HTML exports include offline color controls and styled SVG/JSON downloads. Browser edits stay in the exported file and do not automatically change app records. DeepSeek can revise existing artifacts through the update tool, with stale-edit protection. See [appearance and HTML details](../docs/ARTIFACT-APPEARANCE-2026-10-22.md).

See [feature limits and verification](../docs/VISUAL-ARTIFACTS-2026-10-22.md). This feature uses the native API agent and does not extend the external Normal chat website.

## Local image previews

Use **Add image…** to display a project PNG, JPEG or WebP in the conversation. DeepSeek can also publish a local image through a tool. Every preview has **Open image / Save original**, which can save the snapshot even if preview decoding fails. Images stay local: this feature does not send image bytes to the model or add image understanding. Project boundaries still apply. Files are limited to 8 MB; previews to 16 million pixels. The latest 12 task images are displayed within the global 200-image metadata window. See [GUI, image limits and authentication](../docs/GUI-AND-IMAGES-2026-10-22.md).

## Keys and local data

Persistent keys use `secret-tool` / Linux Secret Service. Key validation and replacing/removing a key are explicit UI actions. The key is never saved in the SQLite store, source, command arguments or logs. If the credential store is unavailable/locked, the UI reports that condition; it does not silently write plaintext credentials. The real desktop keyring round trip is not exercised by the offline build tests.

Default storage: data/desktop/workspace.sqlite3, private agent.sock, service.log, development stages and rollback copies. Override DEEPSEEK_DESKTOP_DATA to select another private state directory. Conversations, drafts, tool results, command receipts, ECU settings, memories and task checkpoints survive window closure. On service interruption, pending work is marked interrupted and is never automatically repeated; prior requests/commands may have executed or been billed. Review receipts before resubmitting.

Current UI lists the most recent 300 tasks and 100 runs/commands; full records remain in SQLite. Large command output is fetched on selection. Files/docs scanning is capped at 1,200 files. These bounds prevent unbounded background rendering.

## Modifying the app

Enable Dev mode. The model can read desktop source, create a staging copy, edit that copy and run Python syntax validation. It can use ordinary commands for further tests, subject to command permissions. Dev validation is syntax-only and does not establish functional safety.

Review the stage's diff, open its preview window, and activate only while tasks and commands are idle. Activation preserves rollback copies and checks that live files still match the staged base. The already-imported service keeps running; UI changes appear when its window reloads. Use **Restart idle agent service** to load backend changes. Restart is refused while tasks or commands are active or commands await approval; a draining service rejects new work before exiting. The client verifies the old service has stopped and reconnects to a replacement that reloads saved state and the keyring connection. This is an idle restart, not rolling replacement during active work. Arbitrary full-access commands can still damage the app; staging cannot guarantee protection from arbitrary shell actions.

The preview window uses the existing agent service/state directory. It is a real development client, not a sandboxed service: any tasks you explicitly submit in that preview use the same permissions and API connection. Model tools cannot activate stages or change permission settings; those are UI actions. A backup that has diverged since activation will not be rolled back over newer edits without review.

## Build checks

Backend tests use temporary projects, fake credentials and mocked model responses. Native interaction tests use Qt's offscreen platform, so no visible app or persistent service is launched. Tests cover permissions, exact approvals, command I/O, timeouts, docs/memory scoping, stale patches, stage activation/rollback, reasoning replay with tools, drafts, limits, restart recovery and socket reconnection.

```sh
python3 -m unittest desktop.test_desktop desktop.test_artifacts desktop.test_images desktop.test_reliability desktop.test_reasoning
QT_QPA_PLATFORM=offscreen python3 -m unittest desktop.test_ui
python3 build_desktop.py
```

The distributable is an editable source bundle for the installed native runtime, not a self-contained binary with Qt bundled. No installation, menu registration, autostart registration, system service registration or visible launch occurs during build.

## Quieter layout

Chat and Code share one window. Sidebar hides/shows history. Code’s Workspace button reveals ECU, files, docs, memory and Dev controls; Activity reveals the command console and opens automatically for a new approval. More → Show tool details (Ctrl+O) expands full tool messages. Chat Settings holds browser/account options and instructions. [Client references and design decisions](../docs/UI-REFERENCES-2026-10-22.md).

### Islands and Learning

The native shell now follows the Islands preview. More → Reduce motion disables the short fades. Memory keeps revision history, including user edits. The Learning panel shows model-proposed ECU lessons with supporting task checks; review before activation and use Roll back when needed. These tools are available in API Code mode, not website chat, and do not train weights.

Website sign-in loads up to 100 recent account conversation titles. Select an imported conversation to read its history; use Open original on website to continue that original conversation. Refresh website history retries fetching the index. Imports do not issue model requests. See `docs/ISLANDS-LEARNING-HISTORY-2026-10-22.md` for evidence and limits.

### Drawing commands and service reliability

DeepSeek can now draw using the bounded command language in `docs/DRAWING-COMMANDS.md`. The app renders these as native editable/exportable visuals. Website Chat accepts fenced programs or complete valid command-only replies; API Code has `draw_visual`. Drawing commands cannot execute OS actions.

Linux service launch uses a transient user systemd unit when available, so launcher exit does not terminate the backend. This does not install a boot/autostart service. Other systems retain the detached-process fallback. See `docs/BUG-CHECK-2026-10-22.md` for fixes and verification.

### Live visuals inside messages

Ask for an interactive explanation, graph, simulation or calculator. DeepSeek can emit a `deepseek-visual` specification; API Code can also call `create_interactive_visual`. The native card appears in the conversation itself. Controls compute locally, settings survive chat switches/reloads, and Export offers offline interactive HTML, a PNG snapshot, or JSON with current state. The separate Artifacts tab is hidden. See `docs/INLINE-INTERACTIVE-VISUALS-2026-10-22.md` for the format and supported features.
