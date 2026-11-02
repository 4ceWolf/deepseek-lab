# Native website-account chat build — 2026-10-22

## Shipped behavior

Normal chat opens a native Qt conversation window. It supports local saved chats/drafts, Flash/Pro selection, Auto/On/Off thinking, optional chat instructions, Search On/Off, streamed text, elapsed time and stop/reconnect. The Search control automatically unchecks and disables on Pro because that combination is disabled by the inspected bridge. Search forwards the website search flag; it does not implement a separate search engine or guarantee website citation formatting.

Auto combines native complexity cues with request length, mapping to website thinking on/off. No distinct low/high/max reasoning levels or token-saving guarantees are claimed. Thinking text is stored separately and is not rendered as the final answer. A missing final answer, missing message receipt or premature stream termination is a failure, not an opportunity to promote thinking into visible content.

The API provider and its ECU/tools remain unchanged. The website path cannot run commands, call file/memory tools or enter the API agent loop. Chat instructions are text sent to the website provider. No API key is needed in website mode. Website quotas/restrictions remain applicable; local usage is explicitly unknown rather than reported as measured zero. Existing website conversations are not automatically imported.

## Architecture and isolation

- `desktop/webchat_view.py`: native chat window and controls; uses the existing request worker pool and safe Markdown renderer. Untrusted images do not trigger external or local resource loads. User-clicked HTTP/HTTPS links can open in the browser.
- `desktop/webchat.py`: service-owned website connection/chat workers, separate SQLite record kinds, partial-response persistence, context/output bounds and no automatic retries. A global single-flight website request avoids competing session parents. Service restart marks unfinished website turns interrupted; active login/website work blocks intentional service restart.
- `desktop/web_bridge/server.mjs`: private loopback gateway, random per-process local authentication key, origin rejection, bounded request schema, chat-only normalized events, fixed provider origin, suppressed upstream logs and sanitized errors. Bootstrap key travels over a private child-process pipe. It is not the user's paid DeepSeek key.
- `desktop/web_bridge/runtime/`: generated JavaScript from pinned upstream source. Separate Node process, not code loaded into the API agent. No personal browser CDP session is intentionally attached; only the app's managed profile endpoints are reused.
- Closing/hiding the native chat window leaves service-owned work running. Stop closes the website adapter/browser connection and saves partial text; the provider may already have processed the request. Incomplete chats cannot be continued/replayed; start a new chat after reconnecting.

Auth snapshots and the dedicated browser profile live under the service data directory's `website-account/`. The directory is owner-only; the child sets a restrictive creation mask and auth snapshot writes use owner-only permissions. Website credentials are separate from the API key's Linux Secret Service entry. They are filesystem-protected, not encrypted by our app. No tokens/cookies/passwords enter UI requests, task/event logs, source bundles or exports. Forget login removes the dedicated browser profile/auth/lineage files and preserves local transcript text; old website chats become read-only/incomplete for continuation purposes.

## Bundled source, licensing and build

Source reference: [kittors/deepseek-web-api](https://github.com/kittors/deepseek-web-api/tree/9b62d6a17ba502fa6aefa2dceb527d1e925aa6ce), commit `9b62d6a17ba502fa6aefa2dceb527d1e925aa6ce`, MIT. Original source and license are retained under `desktop/web_bridge/upstream/`.

The browser automation library is the unmodified npm `playwright-core` 1.64.1 distribution, Apache-2.0, verified against its published SHA-512 integrity value. License/NOTICE files are retained. Provenance is recorded in `desktop/web_bridge/PROVENANCE.json`. Its bundled installation/helper scripts are inert package files; none were run.

`desktop/web_bridge/build.mjs` generates the runtime using Node's built-in TypeScript stripping after expanding this pinned source's constructor parameter properties. Local adaptations: dedicated browser attachment only; five-minute login deadline; explicit stream-frame bound; recognized website terminal-status events; no thought-to-answer fallback; require terminal event, message receipt and nonempty final text. This is a pinned-source build adapter, not a general TypeScript compiler. No package manager, install script or browser download is needed for this build step. Rebuild with Node 22+ after editing the upstream TypeScript; the generated JavaScript is included for ordinary launch.

Runtime prerequisites for website mode: installed Node 22+ and system Chrome/Chromium, plus the native app's existing Python/Qt runtime. The build includes the browser library, not a browser. Chrome/Chromium was not found on this machine; the UI handles that missing prerequisite explicitly. No system package installation, browser download, account login or visible app launch occurred while building/testing.

## Verification

Offline validation: 93 existing backend/controller checks, 13 website backend/process checks, 17 native Qt checks, two existing artifact-browser checks, and six Node gateway/stream checks: **131 checks** total when all suites pass.

New checks cover: no API-key requirement or API-provider invocation; separate transcript/task/command records; continuation IDs; instructions and hidden reasoning; Search rejection on Pro; Auto vs explicit thinking; incomplete stream persistence without replay; cancellation; interrupted startup; login removal; login cancellation without late reconnection; safe logs; actual bundled adapter startup and authenticated status without opening a browser; loopback authentication/origin enforcement; tool-field removal; sanitized upstream failures; strict stream completion and no thought-only answer promotion; native control state, draft restore, failure presentation and offline preview rendering.

Previews use fixture data and are labeled as offline builds. They do not establish live provider quality. Existing Python/API/reliability tests remain part of regression validation. Browser-export tests remain offscreen and use no user account.

## Remaining live checks

An actual account sign-in is still required to validate current private website endpoints, proof-of-work worker version, streaming variants, search behavior and multi-turn continuity. Google sign-in remains governed by DeepSeek/Google browser policies; no login restriction bypass is implemented. Upstream code can break when the website changes. This remains an experimental provider rather than a supported OAuth integration or a verified replacement for the API coding agent.

The existing source bundle is rebuilt with these files; no installation or launch is performed. Prior research: [source investigation](UNOFFICIAL-WEB-CLIENTS-2026-10-22.md).
