# Thinking-mode research and tuning direction

Checked 2026-10-20. Scope updated by user: dependable coding, general Linux knowledge, strong efficient reasoning. Personal machine history is secondary. These are research findings and proposed policies, not measured improvements or model weight training.

## Verified API behavior

DeepSeek exposes disabled thinking and low/high/max effort, defaulting to high. Temperature and frequency/presence penalties have no effect in thinking mode. With tools attached, prior reasoning_content must be retained; without tools it is ignored on subsequent requests. No numerical-only or free hidden-reasoning switch is documented.
Source: https://api-docs.deepseek.com/guides/thinking_mode/

The completion API exposes max_tokens and finish_reason. Treat a length termination as incomplete, never as a successful coding result. JSON output requires both its API setting and a JSON instruction; validation remains necessary.
Source: https://api-docs.deepseek.com/api/create-chat-completion/

Caching is automatic, best-effort, and depends on matching persisted prefixes. Record actual cache hits and misses; do not equate discounted input with fewer tokens or assume a cache hit.
Source: https://api-docs.deepseek.com/guides/kv_cache/

Tool calls request application actions; the model does not execute functions itself. Strict schema mode is beta and constrains arguments, not the correctness or safety of an action.
Source: https://api-docs.deepseek.com/guides/tool_calls/

## Engineering direction to evaluate

- Low effort for bounded, well-specified changes with inexpensive objective checks. High for difficult debugging, concurrency, unfamiliar architecture, or consequential Linux changes. Max only when harder tasks justify its measured cost.
- Avoid automatically trying low before every hard task: failed attempts and repeated context can cost more than selecting high initially.
- Select relevant code and Linux documentation; keep stable instructions first for caching. Do not bulk-load personal history.
- Check generated code with syntax checks and meaningful functional tests. A passing parser or confident answer is insufficient evidence.
- Linux support should establish distribution, runtime versus host, permissions, service manager and relevant live state before proposing changes. Prefer read-only diagnosis, scoped changes and a recovery path.
- Bound retries, elapsed time and spend; record failures and truncated responses. Never label unchecked work as verified.
- Evaluate new tasks independently of tuning examples. Compare correct completions, tokens including retries, cache-adjusted cost, latency and failure types across effort levels.

## Current implementation gap

engine.py currently defaults nearly all coding and OS tasks to low effort and increases effort only for explicit phrases. This is a heuristic, not a validated difficulty detector. The lab currently declares no execution tools attached; research into tool use does not mean a dependable coding executor has been implemented. No claim of 50% savings at equal reliability is established by this research.
