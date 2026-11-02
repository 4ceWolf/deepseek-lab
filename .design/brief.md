# Native workspace brief

Product: a native Linux desktop coding assistant backed by DeepSeek and an editable ECU. Current instruction: build only; no dependencies, installation, launcher registration, autostart, live key setup or visible launch.

Primary job: operate on a project while seeing what the model reads, proposes and executes. A separate local service owns requests and commands so window reloads preserve work. User pressure: keep the agent understandable, dependable and easily modifiable.

Visual direction: graphite editor workspace, cool blue primary actions, warm pending approvals, native text and controls. Tasks at left, conversation and collapsible command activity centrally, contextual ECU/files/docs/memory/Dev panels at right. Dense controls stay secondary to the conversation. Dock panels can be hidden to recover space on smaller displays.

Required states: no key, locked credential store, empty task, running task, waiting approval, denied/disabled command, command input/output, timeout, task error/incomplete output, saved memory, stale patch, staged source with syntax failure, preview and rollback, idle backend restart.

Verification: temporary-state backend tests, native offscreen Qt interaction tests, rendered wide and compact previews. Live credential-store round trip, actual paid model tool use and full assistive-technology testing remain first-launch checks.

Visual artifacts: central task-scoped tab with native SVG rendering, fit/zoom, source labels, accessible Data table, editable Specification and explicit exports. Empty, invalid-edit, saved-revision and stale-edit states are covered.

2026-10-22 refinement: Islands dark—charcoal canvas, rounded task/conversation/command/composer surfaces, filled selected tabs, quieter actions, full-width ECU form fields. Command controls scroll when compact. Local project images render inline with an always-present native save-original fallback; image bytes stay outside provider context. Preserve external-resource blocking.

Artifact appearance: explicit draft preview vs saved revision, color pickers, light/dark presets, category/series palette grouping, matching labels, and fixed-template interactive HTML export. Model revisions refresh only when manual edits are absent; conflicts preserve edits. HTML requires no connection and reflows to one column at narrow widths.

Reliability controls: central Review tab presents observed receipts, saved claims/requirements and uncertainty before explicit recovery. ECU budget dialog keeps supplied rates and conservative admission estimates distinct from billing guarantees. Git worktrees/diffs use existing command approvals. Main status distinguishes a finished reply from verification.

Website account addition: separate native conversation window with its own history/composer, model, Auto/On/Off thinking, explicit Search On/Off checkbox, optional chat instructions, dedicated-browser sign-in and Forget login. Keep API commands and tools isolated. Show missing-browser, login pending, stopped/incomplete, saved draft and unknown-usage states. Build only; no browser install/download or live account use.

2026-10-22 installation authorization: user requested needed dependencies and actual app installation. App-menu registration, icon, editable launcher, Chromium and first native launch are now authorized and completed. Keep code/docs/state in Projects; no account sign-in is automated.

2026-10-22 clutter feedback supersedes the initial dense layout: use one main window with Chat/Code modes, an optional history sidebar, a conversation-focused center and compact composer controls. Start with ECU/files/docs/memory/Dev and command output hidden; expose them via Workspace and Activity, with fresh approvals surfacing automatically. Website browser/auth settings and chat instructions belong in a Settings dialog. Tool details collapse by default and remain available with Ctrl+O. References and implementation evidence: docs/UI-REFERENCES-2026-10-22.md.

2026-10-22 interactive-visual direction: render native live cards at their location in the conversation, with text before and after. Do not route visual output to a separate pane. Retain the Islands palette, quiet borders and visible native focus states. Controls, time scrubbing, source/assumptions and export belong to the card. Preserve exploration values during streaming and chat switches, never autoplay, honor Reduce motion, and keep controls local to avoid model usage. Hide the legacy output Artifacts tab; preserve the Code Review workflow. Current implementation/evidence: docs/INLINE-INTERACTIVE-VISUALS-2026-10-22.md.

2026-10-22 reasoning disclosure refinement: replace the blue Markdown Thinking link with an inline native tool button. Use a muted label, native right/down chevron, restrained hover/expanded surfaces and visible keyboard focus. Keep the existing expansion action and reasoning content; preserve visual-card scrolling and state. Native click/Space and expanded/collapsed checks passed; desktop UI suite: 35 passed.
