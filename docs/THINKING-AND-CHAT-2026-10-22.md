# Stronger native Auto reasoning and chat modes — 2026-10-22

User goal: get stronger, efficient reasoning from DeepSeek without suggesting that prompts can transfer another model's capabilities. No weights are trained and no Astra-equivalence claim is made.

## Checked provider controls

Official documentation checked on 2026-10-22:

- https://api-docs.deepseek.com/guides/thinking_mode/
- https://api-docs.deepseek.com/api/create-chat-completion/

Thinking can be enabled/disabled; effort supports low/high/max. Temperature/presence/frequency controls do not provide extra reasoning capability in thinking mode. Requests carrying tools must return the prior assistant reasoning_content for the turns included in the conversation; the native client preserves it with retained assistant/tool exchanges. The API supports output ceilings above this app's former 16384 maximum. Thinking uses generated tokens; hiding its display does not make it free.

## Native Auto v2

Auto now recognizes mathematical proofs/formal reasoning and detailed technical requests with multiple requirements as high-effort work. Explicit requests for maximum reasoning select max; a basic negation guard avoids treating 'do not use maximum reasoning' as an opt-in. Bounded transformations/greetings retain the no-thinking path. This is a heuristic router, not semantic proof of task difficulty.

A real run_check that finishes with a positive nonzero exit code raises remaining Auto tool rounds from none/low to high. It does not create an additional model retry loop: existing round/token/cost limits still apply. Timeouts, denied approvals and network failures do not themselves trigger extra reasoning. A prior failed verification can also raise effort on a substantive follow-up. Manual effort selections remain authoritative, including when chosen for recovery. Max is not selected automatically merely because a check failed.

The reasoning instructions emphasize assumptions, known limitations/open problems, counterexamples and executable evidence, with concise final explanations and a stopping rule. These are operating instructions and tools, not an intelligence upgrade or benchmark result.

The native output ceiling can now be explicitly set from 128 to 131072. Saved/default values remain unchanged (default 4096), and admission budgets still reserve against the chosen ceiling. Larger ceilings allow more thinking/final output and can incur higher usage; they do not guarantee better answers. Truncation still stops explicitly. The legacy website lab's limits are unchanged.

## What the chat options actually do

Normal chat opens official https://chat.deepseek.com/ in the default browser. The website handles account login, including Google if offered; no API key is passed by our app. This is a website handoff, not an embedded native account-chat connection. Website conversations/authentication stay separate and do not receive the local ECU instructions, environment snapshot, memory, command tools or artifact renderer.

Native conversation calls DeepSeek's API with the connected key, selected model, ECU instructions, environment, relevant history and available tool schemas. The local service handles model requests and local records independently of the window. Inline local images/artifacts belong to this native workspace; image display does not currently send image bytes to the model. No supported consumer OAuth-to-API bridge is implemented.

For difficult native work, select the model deliberately and leave Auto enabled, or choose High/Max explicitly for a specific need. More thought and a different model cannot guarantee parity with Astra. Real task comparisons and executable outcomes remain the standard for any quality claim.

## Verification

Four new reasoning tests cover effort selection, negated Max, bounded transformations, failure-vs-permission/timeout distinctions, manual override, actual outgoing low→high requests after a failing executable check, and max effort with an explicit 131072 ceiling. Combined with the existing suites: 110 offline checks (93 backend/controller, 15 native UI, 2 HTML browser). No live provider reasoning-quality comparison, paid call, installation, keyring write or visible launch occurred.
