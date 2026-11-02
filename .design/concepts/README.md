# DeepSeek Lab GUI concepts — 2026-10-22

Scope: user requested concept exploration and visual previews before another UI rebuild. These are standalone, local HTML sketches of a native desktop design. The installed Qt app, service, settings, provider sessions, and project data are unchanged. No model requests were made.

## Directions

1. **Islands** — soft graphite, two principal surfaces, readable central conversation, compact composer. Review and command activity open only when wanted; memory/docs/ECU have stable sidebar entries. Recommended default. Tradeoff: users must open detailed evidence.
2. **Studio** — warm paper, horizontal navigation, compact project sidebar, persistent change/artifact inspector. Better comparison and document review. Tradeoff: less room for conversation on small laptop screens; the inspector should become a drawer in production.
3. **Workbench** — cool charcoal, navigation rail, project list, open changes and command output. Better sustained execution monitoring. Tradeoff: greater density and less conversational calm. Prefer an optional work layout, not the default.

Recommendation: Islands as the everyday shell, with Studio's side-by-side review as an optional panel and Workbench's terminal available during long tasks. Preserve user layout choice instead of automatically rearranging the whole screen.

## Product invariants for implementation

- Native desktop app remains the product; these HTML files are previews, not a proposed replacement website.
- Keep the agent service independent of window reloads.
- Chat/Code mode and provider/permission state must remain unambiguous. Shown samples depict API Code mode. Website chat must not imply access to local tools.
- Auto reasoning beside the model selector; advanced ECU controls in a dedicated panel.
- Keep command approvals visible at the point they are needed, with exact command, directory, permission state, elapsed time and output available.
- Docs, memory, key/account management and Dev mode remain accessible; they need not crowd the main screen.
- Preserve full recorded evidence even when process details are collapsed. Status labels must distinguish sample model claims from verified tool results.
- Production implementation should cover empty, streaming, disconnected, approval, error/recovery and narrow-window states, resizable panes, accessibility, settings persistence and keyboard shortcuts. These have not been implemented by this concept pass.

## Preview files

- islands.html / islands.png
- studio.html / studio.png
- workbench.html / workbench.png
- islands-ecu.png (secondary settings state)

Each page links to the other two. Memory/docs/ECU, model/permission controls and review open illustrative dialogs. Escape closes a dialog and returns focus; process details expand. Send only displays a preview notice. No provider calls, uploads, command execution or settings persistence occur. Some navigation controls only demonstrate selection and do not change the underlying fixture conversation. Ctrl shortcut labels are proposed affordances, not bound preview shortcuts.

## Evidence and verification

Inspected existing desktop-quiet-code.png and the project's prior source-backed UI reference report (docs/UI-REFERENCES-2026-10-22.md). This pass explored compositions locally; it did not perform a fresh competitor survey or copy competitor assets/code.

Rendered all three with installed Chromium and the project's pinned Playwright runtime at 1440 × 960. Visually inspected each screenshot. No page horizontal overflow or internal conversation/diff clipping observed at that size. Exercised ECU open, Escape dismissal, process expansion and mock send on all three. No mobile/zoom/screen-reader/full contrast certification is claimed. The pages are desktop concept boards, not responsive production UI.

Reproduce with Python make_previews.py and Node render.mjs in this directory (renderer imports the project's existing Playwright runtime). All preview result counts, commands, diffs, connection indicators and memory counts are fixtures, not measured live outcomes.
