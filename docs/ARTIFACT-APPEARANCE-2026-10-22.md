# Editable appearance and interactive HTML artifacts — 2026-10-22

The native Artifacts tab now has an Appearance panel: background, ordinary text, title, secondary text, grid and surface colors; an editable chart palette; matching legend/value labels; and light/dark presets. Single-series bar charts can color each category separately. Presets preserve the color grouping and matching choices. Swatch labels choose black or white text from relative luminance.

Appearance changes preview immediately without a model request. Save changes commits a normal artifact revision; exporting uses that saved revision. The JSON Specification remains available for exact data and style edits. Existing artifacts acquire default appearance settings when rendered, so old records remain usable.

DeepSeek can also create styled artifacts and call get_artifact/update_artifact to revise existing ones through API chat. Updates require the latest integer revision and the artifact's project. The UI refreshes a model revision automatically when there are no local edits. If manual edits are present, they remain in the editor and the UI reports the newer revision. Saving stale edits is rejected rather than replacing newer work.

## HTML export

Choose HTML in the export control. The result is a standalone file containing the validated chart/diagram/table, inspectable full data and local color controls. In a browser you can change palette/text/background colors, toggle matching labels, reset colors, and download the currently styled SVG or specification. No connection or API key is needed to adjust an exported file. Save the specification to retain browser edits; reopening the original HTML starts from its original colors. Browser edits do not write back into the app automatically.

This is an interactive HTML wrapper around supported structured artifacts. The native app still renders SVG rather than embedding arbitrary model-generated HTML or JavaScript. HTML layout/code is a fixed application template; model text is escaped and JSON is protected against script-tag injection. A Content Security Policy authorizes only the fixed script's SHA-256 hash, and no external scripts, fonts or chart libraries are loaded. Palette and style colors must be #RRGGBB. Existing PNG/SVG/CSV/JSON exports remain available.

Appearance applies to the artifact; app and HTML page chrome retain their own theme. Flow layout, data-size bounds and graph-edge/CSV limitations from the original visual-artifact build still apply. User-selected colors can have low contrast; the app does not change or reject a deliberately chosen palette.

## Chat modes

Native conversation supports the ECU, local inline images and these artifacts using a DeepSeek API connection. Add image/publish_image stores image snapshots for display; image bytes are not sent to the provider. It does not add model image understanding.

Normal chat opens the official DeepSeek website, which uses its separate account sign-in rather than an API key. These local app features do not modify that website, and website authentication cannot be substituted for an API credential. Exported HTML files themselves do not require either login method.

## Checks

27 backend/artifact/image checks, 12 native offscreen UI checks, 2 offscreen browser checks and 43 existing controller/server/executor/capability checks passed (84 total). The browser checks exercise actual color input events, matching/reset behavior, SVG and JSON downloads, 390px reflow, blocked injection and no remote resource requests. Native checks exercise palette color selection, preview vs saved revision, presets, HTML export, model restyling, automatic refresh and preserved conflicting manual edits.

Offscreen Qt WebEngine is used only for verification with the already installed host runtime; the app itself does not depend on or embed WebEngine. Native appearance, a light chart and HTML render screenshots are in build/previews. desktop-interactive.html there is an illustrative fixture, not benchmark data.

Build only: no dependency installation, visible app/browser startup, real keyring access or paid provider requests. The source ZIP was rebuilt and verified. Full assistive-technology/high-DPI coverage remains unverified.
