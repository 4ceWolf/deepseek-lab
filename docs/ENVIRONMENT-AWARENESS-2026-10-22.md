# Environment supplied to DeepSeek — 2026-10-22

The native API agent now receives an explicit environment snapshot in the system context of every model request. Previously it had the tool schemas and operating instructions, but no equally clear summary of actual OS, project/docs/state paths and permission mode.

The snapshot reports the service's observed OS, kernel, architecture and selected distribution fields; selected project, docs and state directories; service working directory; non-login /bin/sh command behavior; current command permissions and Ask-mode allowlist; current Dev mode; selected model and effective reasoning effort; configured output/model-round/tool-call budgets; and capability boundaries for artifacts, local images, memory, proposals and app staging. The model-loop time threshold is checked between rounds; running commands have their own timeout.

It refreshes on every provider request. get_environment supplies the same information on demand. Permissions and Dev mode use live settings, while project/model/effort/budgets describe the current run. Inspect effective instructions in the ECU panel now displays the environment too.

OS information is detected where the service runs, rather than hardcoding Arch Linux. The native host launcher observes the host runtime. In a container, the reported distribution would describe that runtime. Installed packages, file contents, system health and command success are explicitly unknown until inspected. Environment variables, API keys and credential contents are not enumerated.

Verification used a simulated provider to capture actual outgoing payloads, change permissions/Dev mode between model rounds, call get_environment through the tool loop and verify updated facts in both the tool response and next request. This confirms delivery, not a live model's comprehension or behavior. Existing backend/artifact/image and native UI checks were also run: 28 backend checks and 12 offscreen UI checks passed. No paid provider request or live keyring access was made.

This applies to the updated native app build. Official website Normal chat remains independent and does not receive local ECU context. Build only: no installation or visible launch; an already running older build will need the updated code and an idle service restart when the user is ready.
