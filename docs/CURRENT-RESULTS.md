# Quieter native UI — 2026-10-22

Chat/Code now share one window, workspace and command controls start collapsed, Chat settings move out of the transcript, and tool JSON is available on demand. This follows inspection of Kun, DeepSeek Harness, Codex and Claude Code. [Research and changes](UI-REFERENCES-2026-10-22.md).

# Installed and launched — 2026-10-22

DeepSeek Lab is now a registered user-local desktop application, launched and observed in Niri. Chromium 154.0.8037.97-1 was installed from the official Arch Linux archive after the configured mirror lacked its detached signature. Package verification remained enabled. The local agent service responds, the app uses approval for every command, and the browser library can launch Chromium with its sandbox enabled. Website account sign-in remains a user action. See [installation details](INSTALLATION-2026-10-22.md).

# Website account native build — 2026-10-22

Added an experimental native website-account chat window with Search (Flash only), Auto/On/Off thinking, streamed responses, durable independent conversations/drafts, instructions, elapsed time and login removal. No paid API key or agent tools are used by this mode. The bundled MIT bridge and Apache-2.0 browser library run separately from the API agent; no installation or browser download was performed. See [implementation and limits](WEBSITE-ACCOUNT-BUILD-2026-10-22.md). Live account/website compatibility is not yet validated; system Chrome/Chromium is absent on this host.

# Current results — 2026-10-22

Improved [native Auto reasoning and clarified chat modes](THINKING-AND-CHAT-2026-10-22.md): proof/complex-task selection, evidence-based low→high escalation, explicit Max and optional larger ceilings. 110 offline checks; no Astra-equivalence or live reasoning-quality claim. Normal chat remains an official-website handoff.

Completed the [gap review](GAP-REVIEW-2026-10-22.md) and [reliability controls](RELIABILITY-CONTROLS-2026-10-22.md): reviewed recovery, source-aware command receipts, guarded rollback, permission-controlled Git worktrees, task budget estimates/routing and history-preserving compaction. 106 offline checks passed, including a real temporary Git worktree. Build only; prices are supplied estimates, and no live-provider reliability claim is made.

Verified and strengthened [environment context](ENVIRONMENT-AWARENESS-2026-10-22.md): actual OS and paths, live permissions/Dev mode, run settings and capability boundaries now accompany every native provider request. get_environment rechecks them on demand. Verified outgoing mock-provider payloads; no live-model comprehension claim.

Added [editable artifact appearance and interactive HTML exports](ARTIFACT-APPEARANCE-2026-10-22.md): chart/text color controls, matching labels, per-category bars, light/dark presets, offline HTML controls and chat-driven revisions with conflict protection. 84 offline checks passed; build only.

Updated the [native dark GUI and local image previews](GUI-AND-IMAGES-2026-10-22.md): rounded island surfaces, clearer ECU fields, scrolling command panel, inline project images and a save-original fallback. 78 offline checks passed; build only.

Added [native visual artifacts](VISUAL-ARTIFACTS-2026-10-22.md): charts, flow diagrams, tables, editable specifications, source labels and exports. Build only; offline checks, no installation or paid API request.

Added [normal account chat](ACCOUNT-CHAT-2026-10-21.md): a native toolbar action opens official DeepSeek consumer chat in the default browser, without an API key. Website login does not authenticate the ECU/API agent. Browser opening and sign-in were not performed during the build.

Newest deliverable: [native desktop build](DESKTOP-BUILD-2026-10-21.md), with independent agent service, four command modes, docs, memory, ECU controls, keyring integration and staged Dev mode. Build only: no installation or visible launch. The editable bundle is dist/deepseek-workspace-native.zip; first-launch live-keyring/provider checks remain unverified.

Latest priority: [long-task tests](LONG-TASK-2026-10-21.md). ECU and raw DeepSeek both completed eight connected implementation stages without repairs and passed the same final 148 checks plus 240 unseen stress checks. ECU used 14.39% fewer total tokens and 47.42% less summed response time in this one comparison. A separate ECU fresh-context continuation passed 208 checks. This is sustained single-module work, not yet an hours-long multi-file repository benchmark.

Current scope is the [five agent capabilities](CURRENT-SCOPE.md), explicitly excluding further boot-care work. Latest [capability tests](AGENT-CAPABILITIES-2026-10-21.md) add persistent requirements/evidence, atomic state, stale-source detection and read-only recovery. Raw and ECU both passed three evidence cases; ECU used more total tokens. A new live coding repair passed four checks in one attempt with 366 tokens.

Newest engineering addition: [isolated coding executor](CODING-EXECUTOR.md). A bounded propose/test/repair loop now runs small pure-Python modules in an OS sandbox, saves patches and actual verification evidence, and preserves the source. First live repair passed four checks in one attempt, 308 tokens. This backend is command-line driven; arbitrary repository and Linux execution remain unsupported.

Latest: [reliability, raw baseline and efficiency report](RELIABILITY-2026-10-21.md). Current controller is **ecu-v3.5-auto**. Desktop app deferred; weight training excluded. A new narrow compact coding route passed two new coding tasks with 47.57% fewer tokens and 60.44% less response time than raw; not a general improvement claim. The first broader candidate used more tokens than raw despite faster responses. This pass used 32 calls / 19,120 tokens. Original starting responses were recovered and regraded separately at 9/10. The small repository bug-fixing benchmark is now prepared and run; real-repository and VM-level validation remain future work.

Earlier cross-domain session:

- [Both models' questions and answers](../evaluations/cross-domain-20261021T102125Z/ANSWERS.md)
- [Review, errors, limits and token counts](../evaluations/cross-domain-20261021T102125Z/REVIEW.md)
- [Corrective DeepSeek reply](../evaluations/cross-domain-20261021T102125Z/correction-result.json)
- [Weight training and style research](STYLE-AND-TRAINING-2026-10-21.md)

That session used controller ecu-v3.4-auto. No weight training was performed. Six requests, 13,240 total API tokens; both bracket implementations passed 1,560 checks; 19 local application checks passed at that time. Current raw records live in this project's evaluation folders and data/lab.sqlite3; some historical raw records were lost before recovery.

Historical desktop deferral is superseded by the native build above.

## 2026-10-22 — Islands, learning and website history

Selected Islands concept implemented in native Qt, with short fades and a persistent Reduce motion option. Added versioned model memory updates, user-reviewed ECU lesson proposals with fresh check receipts and rollback. Website sign-in now fetches remote history titles and opens selected conversations read-only; live verification loaded 5 titles and one 10-message transcript without a generation request. See [implementation and limits](ISLANDS-LEARNING-HISTORY-2026-10-22.md). No measured capability/token-saving improvement or weight training is claimed.

Follow-up: removed the separate Activity pane/toolbar entry; thinking and tool details expand in the conversation. Both composers support Enter to send and Shift+Enter for a newline. Chat mode now has validated native chart/table/diagram artifacts with editing/export, plus remote history selection. The full remote list is retained even when a local chat exists. See ISLANDS-LEARNING-HISTORY-2026-10-22.md for verification and limitations.

## Bug check and drawing commands

Added interpreted drawing primitives and an API `draw_visual` tool; a live website reply produced an editable/exportable workflow. Fixed delayed-send draft loss, task-switch draft timers, stale artifact save callbacks, long-transcript overflow, native PNG background/antialiasing and launcher-dependent service lifetime. Broad suite: 152 checks passed; focused follow-ups passed too. See BUG-CHECK-2026-10-22.md and DRAWING-COMMANDS.md for evidence and limits.

## Inline interactive visuals

Interactive cards now render directly in Chat and Code messages, with native sliders, toggles, selections, draggable points, local calculations, animation/time scrubbing, reset, persisted exploration state and offline interactive HTML export. The Artifacts output tab is hidden. One live DeepSeek reply produced a working inline card. Full suite: 169 checks passed; export checks passed with zero network requests/page errors. See INLINE-INTERACTIVE-VISUALS-2026-10-22.md for the format, implementation and limits.
