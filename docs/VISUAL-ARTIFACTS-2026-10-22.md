# Native visual artifacts — 2026-10-22

DeepSeek's API agent can now call `create_artifact` for native bar, line and donut charts, flow diagrams and tables. The central Artifacts tab groups visuals by task. Each visual has a source label, readable data, editable JSON specification, zoom controls and explicit SVG/PNG/CSV/JSON exports. The model can retrieve saved specifications with `get_artifact`.

Edits validate before saving, increment revisions and preserve prior versions in the database. Stale revisions and access from another selected project are rejected. Prior revisions are retained for inspection in storage; there is no revision restore browser yet. Specifications contain data rather than executable HTML or JavaScript. SVG is generated locally with escaped text. CSV exports neutralize formula-like text. Keys are redacted before persistence as with other tool data.

Charts support 1–24 labels and 1–6 series; donuts use one nonnegative series. Tables support 10 columns and 100 rows. Flow diagrams support 24 nodes and 60 edges, using a simple deterministic grid; complex diagrams can have crossing edges. Full labels and graph edges remain available in Specification even where visual labels are abbreviated. Flow CSV/Data currently lists nodes; JSON includes edges. Source labels preserve provenance but do not independently verify facts.

These visuals belong to the native API workspace. The Normal chat button still opens DeepSeek's official website separately; this feature does not alter that website. This is structured visual support, not arbitrary executable web artifacts.

Verification: 22 backend/artifact tests, 9 native offscreen UI tests, and 43 existing controller/server/executor/capability checks. Tests use temporary state, fake credentials and simulated model responses. They exercise all five SVG renderers, bad data, escaped markup, CSV protection, a full model-tool round trip, persistence, edits, revision guards, task/project separation, and file exports. Qt rendering was inspected in build/previews/desktop-artifacts.png. No live provider call, keyring write, visible app launch or installation occurred. Runtime integration with a real provider remains a first-launch check.

The updated ZIP is an editable source bundle requiring installed Python, PySide6 with Qt SVG, and secret-tool for persistent keys. It is not a standalone packaged executable.
