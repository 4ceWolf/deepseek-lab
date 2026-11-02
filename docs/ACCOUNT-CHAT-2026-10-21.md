# Normal account chat — 2026-10-21

Added a Normal chat toolbar action and a native account-chat dialog. The dialog opens only the official https://chat.deepseek.com/ URL through the user's default browser. It works without an API key and reports browser-launch failure with a manual URL. Build-only restrictions remain: no browser was actually opened, no sign-in attempted, no installation and no visible app launch.

DeepSeek documents Google sign-in for its consumer app, but the public API requires an API key. No supported third-party consumer-login OAuth flow was found that grants this desktop workspace model API access. Consequently this implementation is a supported handoff to the official consumer chat, not an embedded Google login or a replacement API authentication method.

Google/DeepSeek website credentials, tokens and cookies stay in the browser. Website chat history remains on DeepSeek's consumer service. The native ECU agent, local memory retrieval and host-command tools continue to use the API connection. The desktop app does not scrape the consumer service or use private website endpoints.

Offline native tests verify that the action works while the key is disconnected, sends only the fixed HTTPS URL to the browser handler, makes no agent run/API request and gives visible recovery on browser failure. Browser launching is mocked, so real sign-in availability for the user's region/account remains unverified. Fetching the live chat page through the research tool returned HTTP 403.

All seven headless native UI tests passed, including the two new account-chat checks. The editable native bundle was rebuilt with the updated UI and documentation.

Sources checked:

- https://api-docs.deepseek.com/news/news250115/ — official consumer app announcement lists email/Google/Apple login.
- https://cdn.deepseek.com/policies/en-UK/deepseek-open-platform-terms-of-service.html — accounts may be shared, while API keys remain necessary for API calls.
- https://api-docs.deepseek.com/ — official API authentication example.
