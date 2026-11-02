# Client research and quieter UI — 2026-10-22

User feedback: the installed interface was cluttered. User requested study of Kun, DeepSeek Harness, Codex and Claude Code and a similar interface. This change adapts their navigation and disclosure patterns to our native Qt app; it does not import their frontend code, logos, assets or runtimes.

## Research

| Reference | Evidence inspected | Pattern used here |
| --- | --- | --- |
| [DeepSeek GUI / Kun](https://github.com/seekhust/DeepSeek-GUI/blob/master/README.en.md) | Code-mode screenshot, README and [Sidebar.tsx](https://github.com/seekhust/DeepSeek-GUI/blob/master/src/renderer/src/components/chat/Sidebar.tsx) | Explicit work modes, conversation/history column, settings separated from the main work surface, controls grouped with the composer. |
| [DeepSeek Harness Chat](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/ui-chat/README.md) | Chat/conversation/session component references | Process details can be folded while answers remain visible; recorded events remain available independently of their display. |
| [Codex app](https://learn.chatgpt.com/docs/changelog) | Official OpenAI documentation describing project/thread navigation, collapsible sidebar sections and review surfaces | Conversation-first center with optional workspace/review controls; preserve separate review and artifacts. |
| [Claude Code](https://code.claude.com/docs/en/interactive-mode) | Official interactive-mode reference and Anthropic's [terminal-interface announcement](https://www.anthropic.com/news/enabling-claude-code-to-work-more-autonomously) | Compact status and detailed transcript disclosure; Ctrl+O toggles our tool details. |
| [Cherry Studio](https://github.com/CherryHQ/cherry-studio) and [Chatbox](https://github.com/chatboxai/chatbox) | Public project overviews, secondary survey only | Additional general-purpose clients supporting DeepSeek; not installed, benchmarked, or copied. |

Kun's README also describes stable prompt prefixes, bounded tool context, native cache accounting and progressive tool discovery. These are relevant future ECU comparisons, not improvements implemented by this UI change. Kun is the runtime inside DeepSeek GUI, not the name of a separate UI toolkit.

The sources above were inspected through public documentation/source. Kun's published screenshot was visually reviewed. No claim is made that all referenced applications were installed or used interactively. The public Codex app documentation route redirected to the current ChatGPT desktop docs; the official changelog supplied the specific sidebar/review descriptions.

## Implemented

- One main window with Chat and Code modes. Website chat is embedded instead of opening another full conversation window. With no API key, initial entry is Chat; the user can still choose Code.
- Chat retains only history/new chat, account access, transcript and composer. Model, thinking and Search remain by the composer. Browser path, reconnect, login removal and chat instructions live in a separate Settings dialog.
- Code starts with the workspace-controls dock and command console closed. Sidebar and Workspace buttons expose them. A newly encountered pending approval opens Activity; the user can close it without every poll reopening it.
- Tool request/result JSON is collapsed by default into short work summaries. More → Show tool details, or Ctrl+O in Code, restores it. Complete stored messages are unchanged.
- Verbose reasoning counters, effort explanations and process identifiers no longer occupy the main task status; detailed effort information remains in its tooltip and records.
- API commands, website-account isolation, approval enforcement, saved transcripts, docs/memory, artifacts, patch review and Dev controls are preserved.

No model requests, login actions or API billing are needed for this redesign. The agent service is independent of the window and does not need a restart for the UI update.

## Important account-auth discovery

Current official Harness source documents an account sign-in controller and account-backed models: [account controller](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/api/account-controller/README.md), [provider guide](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/providers.md). This is new evidence beyond our earlier unofficial-client investigation and deserves a separate provider-integration assessment. It does **not** establish that consumer website sessions, free chat quotas, billing or access permissions are interchangeable with Harness account access. No Harness auth integration is added in this UI change.

## Verification

Native offscreen interaction coverage checks mode switching, hidden settings, keyboard dismissal, collapsed tool details with unchanged raw history, normal task sending, command approvals, docs/memory, artifacts, recovery and website chat controls/draft restore. Wide and compact fixture previews are generated under `build/previews/`. Native Qt controls supply their existing keyboard/focus behavior; no screen-reader certification is claimed. Website sign-in/search behavior is unaffected and is not validated by UI fixture tests.

Observed result: all 20 native Qt interaction checks passed, including keyboard send in embedded Chat and approval visibility across modes. The installed app was reopened through its desktop entry while preserving the existing service process. Follow-up focused checks also cover the compact permission summary and wide quiet-layout preview.
