# Islands dark GUI and local images — 2026-10-22

The native app now uses a charcoal canvas with rounded, separated surfaces for tasks, conversation, commands, the composer and ECU controls. Buttons have quieter borders, selected tabs use filled backgrounds, and form labels sit above full-width fields. Keyboard focus remains visible. The command panel scrolls when short, so compact layouts do not overlap command approval/input controls. No animation or additional dependency was introduced.

## Local images in conversation

The native API workspace can display saved project PNG, JPEG and WebP files inline. Use Add image or the model's publish_image tool. Files are snapshotted in private local storage, so a preview does not depend on the original file path remaining available. An Open image / Save original action accompanies each preview. Its native dialog can save the original bytes even when Qt cannot render the image; rendered images can also be copied to the clipboard.

The provider receives tool metadata, never image bytes. This is local artifact display, not model image understanding. The snapshots do not go to DeepSeek just because they appear in the conversation. Image content is not searchable memory and is not included in periodic state responses. Paths must stay in the selected project and honor private-directory restrictions. External URLs and arbitrary file:// images in model Markdown remain blocked. Nothing fetches remote images automatically.

Limits: 8 MB per image; previews require a decodable image no larger than 16 million pixels. State lists up to 200 recent image metadata records globally; the conversation loads up to 12 recent images for its task. Snapshots remain in the database beyond these display limits. Large images are scaled for inline rendering; save original preserves the original bytes. Images can contain private information, so explicit display/save actions should be treated like sharing any local screenshot. The image browser does not currently provide deletion/history management.

## Authentication boundaries

The native ECU/API agent authenticates with a DeepSeek API key, stored through the Linux Secret Service when configured. Its persistent local service provides commands, docs, memory, charts and local image previews.

Normal chat is a browser handoff to official chat.deepseek.com. DeepSeek handles account sign-in, including Google when offered. It is a separate consumer session, not an OAuth credential for the native agent. Website login does not provide API access or activate local tools. This build cannot modify the official website or Codex's own conversation renderer/authentication.

## Verification and packaging

25 temporary-state backend/artifact/image tests, 10 offscreen Qt interaction tests and 43 existing controller/server/executor/capability checks passed. Checks cover image snapshot persistence, project/symlink boundaries, metadata-only tools, inline rendering, blocked external resources, save-original fallback, existing commands/approvals, charts and settings. Wide, compact, artifact and image fixture previews were rendered and inspected. This is not a full screen-reader or high-DPI accessibility audit.

Build only: no installation, actual API calls, keyring writes or visible app startup. A Sober window screenshot was separately captured through Niri by window ID, without focus changes, game input or process interruption. The personal screenshot is excluded from the app distribution.

The refreshed dist/deepseek-workspace-native.zip remains an editable source bundle for installed Python/PySide6/secret-tool, not a self-contained executable.
