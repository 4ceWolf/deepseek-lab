# DeepSeek website-session clients: source investigation

Reviewed 2026-10-22. Scope: whether an authenticated consumer website session can supply chat responses to our native desktop interface without an official API key.

**Finding:** existing projects implement this architecture. They capture website session credentials, call private chat endpoints, parse streaming events, and expose a local compatibility API. This establishes an implementation precedent, not proof that these revisions work with the user's account today. No third-party client was executed, installed, connected to an account, or given credentials during this review.

## Candidates and exact revisions

| Project | Inspected default-branch revision | Commit date | Assessment |
| --- | --- | --- | --- |
| [kittors/deepseek-web-api](https://github.com/kittors/deepseek-web-api) | `9b62d6a17ba502fa6aefa2dceb527d1e925aa6ce` | 2026-07-25 | Strongest architectural reference among these four; still experimental. |
| [JuanCMPDev/deep-proxy](https://github.com/JuanCMPDev/deep-proxy) | `84c1b58f7ee560d645bd48b83e9f5a93524931e2` | 2026-04-26 | Useful browser refresh and stream-parser reference; integration gaps remain. |
| [sums001/Deepseek-API](https://github.com/sums001/Deepseek-API) | `14d6227d2f0104038677872984eaddee59937e0e` | 2026-06-30 | Simple Python reference; unsuitable as an unchanged agent backend. |
| [jonathanyly/DeepSeekPow](https://github.com/jonathanyly/DeepSeekPow) | `258782d1df26fae1a6128e6b416e3fb4b099f23e` | 2026-06-13 | Protocol experiment, not an application foundation. |

Commit dates above come from the GitHub commits API. Repository `pushed_at` can be newer because of other branches or pull requests; it is not evidence the inspected main-branch implementation was updated. The first three declare MIT licenses. No license file or declared license was found for DeepSeekPow, so copying its code would need separate license clarification.

## What the source establishes

### kittors/deepseek-web-api

- Browser login uses Chrome/Chromium through Playwright/CDP. Auth capture reads the website token and cookies; auth snapshots are written atomically with owner-only file permissions. This is plaintext protected by filesystem permissions, not keyring encryption.
- The local server defaults to loopback and protects its compatibility endpoints with a separately generated/configured local key. That key authenticates the local bridge; it is not a paid DeepSeek API key.
- It maps website streams into chat/Responses shapes and persists session lineage. This supports conversations created or tracked by the bridge. The inspected routes do not establish a complete importer for all existing website chats.
- Reasoning effort maps to a boolean thinking switch: low/high/max do not remain distinct provider effort levels through this adapter.
- Tools are serialized into a prompt and parsed from generated text. This is not the official structured tool protocol. An open issue reports malformed DSML tool markup reaching clients. That report is not independently reproduced here.
- Unit-test files, a lockfile and CI configuration exist. They were not executed in this investigation and do not establish current live-site compatibility.
- Output mapping uses zero input tokens and an upstream output-token value. Those fields cannot be accepted as complete measured usage by our existing budgeting code.

Sources: [architecture](https://github.com/kittors/deepseek-web-api/blob/9b62d6a17ba502fa6aefa2dceb527d1e925aa6ce/docs/architecture.md), [auth snapshot](https://github.com/kittors/deepseek-web-api/blob/9b62d6a17ba502fa6aefa2dceb527d1e925aa6ce/src/browser/authDump.ts), [local authentication](https://github.com/kittors/deepseek-web-api/blob/9b62d6a17ba502fa6aefa2dceb527d1e925aa6ce/src/server/authMiddleware.ts), [effort mapping](https://github.com/kittors/deepseek-web-api/blob/9b62d6a17ba502fa6aefa2dceb527d1e925aa6ce/src/deepseek/models.ts), [usage mapping](https://github.com/kittors/deepseek-web-api/blob/9b62d6a17ba502fa6aefa2dceb527d1e925aa6ce/src/deepseek/mapResponses.ts), [open parser report](https://github.com/kittors/deepseek-web-api/issues/11).

### JuanCMPDev/deep-proxy

- Go proxy with browser-based credential refresh, private completion requests, proof-of-work handling, and JSON-patch stream parsing. The browser refresh path supplies token, cookie and an additional website header; a single pasted cookie is not the whole implemented authentication flow.
- Credential files are written with owner-only permissions. The server defaults to loopback, but the inspected server and handler do not enforce a local client authentication key.
- Tool use is also prompted text converted into compatibility calls. The synchronous response reports output tokens as total usage without measured input usage.
- Test files cover several components. This review did not run them. The request translator flattens message history into a prompt, so this is not evidence of importing or preserving the user's complete website history.

Sources: [refresh](https://github.com/JuanCMPDev/deep-proxy/blob/84c1b58f7ee560d645bd48b83e9f5a93524931e2/internal/auth/refresher.go), [credential storage](https://github.com/JuanCMPDev/deep-proxy/blob/84c1b58f7ee560d645bd48b83e9f5a93524931e2/internal/auth/credfile.go), [server](https://github.com/JuanCMPDev/deep-proxy/blob/84c1b58f7ee560d645bd48b83e9f5a93524931e2/internal/proxy/server.go), [request translation](https://github.com/JuanCMPDev/deep-proxy/blob/84c1b58f7ee560d645bd48b83e9f5a93524931e2/internal/proxy/translate_request.go), [response translation](https://github.com/JuanCMPDev/deep-proxy/blob/84c1b58f7ee560d645bd48b83e9f5a93524931e2/internal/proxy/translate_sync.go).

### sums001/Deepseek-API

- Python browser login captures token/cookies and creates a local OpenAI-shaped endpoint. Session saving does not explicitly impose restrictive file modes. The inspected server has rate limiting but no client-key authentication.
- The checked request schema has no function-tool fields; text-only prompt flattening and rough character-based token estimates are implemented. Open pull requests proposing tools are not merged capabilities of this revision.
- A user reports account suspension in issue 18. This is an unverified individual report; neither causation nor suspension probability can be determined from it. Another issue reports excessive new website conversations when ordinary clients omit the custom conversation identifier.
- No test directory was present in the inspected default-branch tree.

Sources: [authentication](https://github.com/sums001/Deepseek-API/blob/14d6227d2f0104038677872984eaddee59937e0e/deepseek/auth.py), [request schema](https://github.com/sums001/Deepseek-API/blob/14d6227d2f0104038677872984eaddee59937e0e/server/schemas.py), [format/usage](https://github.com/sums001/Deepseek-API/blob/14d6227d2f0104038677872984eaddee59937e0e/server/openai_format.py), [server](https://github.com/sums001/Deepseek-API/blob/14d6227d2f0104038677872984eaddee59937e0e/server/api.py), [account report](https://github.com/sums001/Deepseek-API/issues/18), [conversation report](https://github.com/sums001/Deepseek-API/issues/11).

### DeepSeekPow

The small example embeds a placeholder bearer header and invokes a Go solver through Python. The solver subprocess has no timeout unless supplied by its caller; the shown caller does not supply one. A prebuilt solver binary is present in the repository tree. No license, automated tests, secure credential store or full desktop integration was established. Source was read; binaries were not downloaded or executed.

Sources: [chat example](https://github.com/jonathanyly/DeepSeekPow/blob/258782d1df26fae1a6128e6b416e3fb4b099f23e/chat.py), [solver wrapper](https://github.com/jonathanyly/DeepSeekPow/blob/258782d1df26fae1a6128e6b416e3fb4b099f23e/Solver/solver.py).

## Implication for our app

An experimental **Website account** provider is technically plausible: official browser sign-in, a separate local adapter process, normalized chat events, and our native renderer. A browser can be needed for authentication while the conversation interface remains native. This is session reuse, not a supported consumer OAuth integration.

Use kittors as a design reference first. Do not treat any inspected project as a verified drop-in dependency. Initially limit an adapter to ordinary chat; separately validate tools before enabling agent operation. Keep our command permissions, schema validation, durable task state and stop controls outside the adapter. Never execute prose that merely resembles a command.

Preserve a distinct website capability profile: thinking on/off where supported; token usage unknown/partial where appropriate; website quotas still apply. Do not display estimated counts as measured savings or fabricate zero cost. Session expiry should request login, and ambiguous interrupted responses should not be replayed silently. Existing website-history import needs separate endpoint research and validation.

Private endpoints, browser requirements and provider restrictions can change. No claim of unlimited usage, account safety, current live compatibility, or API-equivalent reasoning/tool controls is supported by this source review. The desktop implementation and existing build remain unchanged.
