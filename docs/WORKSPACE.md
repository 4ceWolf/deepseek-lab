# DeepSeek Workspace

Updated 2026-10-20. Run `./start.sh` from this project, then open http://127.0.0.1:8765/ . Keep that server running while using the app. API keys stay in memory and must be reconnected after a restart.

The main task view always requests Auto reasoning. The separate comparison view retains explicit effort settings for experiments. Auto is a deterministic heuristic: low for ordinary work, high for recognized complex or consequential tasks and follow-ups to failed checks or truncated results. It is not a proven optimal classifier, and there is no automatic paid retry loop.

Select up to 12 UTF-8 text files, totaling at most 100 KB. Preview or remove each before sending. Contents are submitted to DeepSeek and retained in the local conversation and request logs. File selection grants no filesystem write access. New tasks and conversation switches clear unsent selections. Attached contents remain in that conversation's subsequent context, subject to the existing context limit.

Implemented: persistent task conversations, file selection and previews, Auto routing with explanations, optional syntax checks, demo mode, provider connection, comparison experiments and exportable logs.

Not implemented: autonomous project navigation, patch application/diff review, terminal execution, isolation for arbitrary generated code, installed desktop packaging, or automatic functional-test repair loops. This is a local browser workspace foundation, not feature parity with Codex. Existing historical experiments remain available but do not validate this updated routing policy.
