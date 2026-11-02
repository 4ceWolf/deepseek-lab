# Style, reasoning, and weight training

ECU v3.3 adds a brief warm, direct, candid conversational style to each request, including requests with saved instructions. Exact output contracts take priority. This is a style preference, not a transfer of another assistant's identity or capabilities.

Standalone greetings and thanks in fresh general/auto chats disable thinking. Attached files preserve low effort. Existing low defaults, high routing for difficult or consequential tasks, failure escalation, and manual comparison overrides remain. No automatic paid retries were added. The total output cap is not a separate reasoning budget: cutting it too hard can truncate useful answers. Low effort cannot guarantee short reasoning on every request. Quality and savings need live measurements; these changes alone establish neither.

Research checked 2026-10-21:

- DeepSeek documents thinking disabled or enabled with low/high/max effort. Default service behavior is high. https://api-docs.deepseek.com/guides/thinking_mode/
- Published V4 weights are under MIT, permitting modification subject to its terms. https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main/LICENSE
- Published V4 Flash is 284B total parameters; Pro is 1.6T. Training these full models requires substantial resources; activated parameters do not equal total weights to store. https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash
- The hosted API provides model inference. No public hosted fine-tuning endpoint was found in the documentation reviewed. Sending messages does not update its weights. https://api-docs.deepseek.com/

Actual weight training would require choosing an available checkpoint, a compatible training stack, suitable compute, licensed training data, independent held-out evaluations, and deployment of the trained model. A smaller checkpoint with adapter training is a different capacity/cost tradeoff and cannot be assumed to match the hosted model. Do not confuse the published V4 Flash checkpoint with the currently served V4.1 Flash release.

No weight training or paid inference was performed for this change. Keep this controller change provisional until tested for output quality and token use.
