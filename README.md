# DeepSeek Control Lab

A local conversation and efficiency workbench. It does not fine-tune model weights or automatically generate teacher/student training data.

Current controller: **ecu-v3.5-auto**. See [current results](docs/CURRENT-RESULTS.md) and the [raw-versus-tuned reliability report](docs/RELIABILITY-2026-10-21.md). A [native desktop app](desktop/README.md) is now built with installed Qt tools; the user requested build only, so it is not installed or launched. Weight training is excluded.

The [isolated coding executor](docs/CODING-EXECUTOR.md) adds a bounded propose/test/repair loop for small pure-Python modules. It saves a proposal and verification evidence without modifying the original source. Run `python3 coding_agent.py examples/verified-repair/job.json` for local checks only, or add `--live` for at most two paid attempts using the connected workspace.

## Start

Requires Python 3.10 or later; no packages to install.

```sh
python3 server.py
```

Open http://127.0.0.1:8765. Click **Connect key**, paste your DeepSeek key, then send a task. Connecting validates your key against DeepSeek's model list. It switches Demo off. Disconnect removes the key from memory; restarting also removes it.

## Experiments

- Edit operating instructions, model and output ceiling before sending a message. Main-chat reasoning stays Auto; manual effort is available in comparisons.
- For small supplied Python modules, Coding focus plus the Python output check can select the tested compact direct-answer route. Syntax passing does not establish functional correctness; run relevant tests separately.
- Use a new conversation to avoid earlier answers biasing an experiment.
- **Compare effort** sends the same task and instructions into two fresh conversations, sequentially. Both use the selected model, token ceiling, and Demo setting. Live comparisons make two paid calls.
- Mark responses Pass or Fail and attach your observations.
- **Run log** shows exact submitted request bodies and full responses, including reasoning when returned, usage, timing, finish reasons, errors, and reviews.
- **Export all logs** downloads a readable JSON archive. Local records are in `data/lab.sqlite3`.
- Output ceilings include reasoning; low ceilings can truncate the final answer. Token counts are actual API-reported counts. Demo has no usage. Dollar costs are not estimated because billing rates vary; inspect DeepSeek's balance dashboard for charges.

## Privacy and boundaries

The server binds only to 127.0.0.1. The API key is held in server memory, excluded from logs, and never put in browser storage. Do not expose this service with port forwarding. Other software on this computer can access the local service. Prompts and results are saved unencrypted locally and sent to DeepSeek during live runs; use a trusted computer. Do not include other credentials in your prompts.

“Everything” means submitted conversation requests, returned responses, settings used for each request, API-reported usage, errors, reviews, and connection events. Unsubmitted edits, keystrokes, the API key, and HTTP authorization headers are not recorded. Requests that fail after submission remain logged and may still have been billed. No automatic retries are performed. Drafts are not preserved across refreshes.

The initial version is text-only and does not execute tools. Required reasoning-history handling must be added before enabling thinking with tools. Previous reasoning is retained in logs, but omitted from subsequent plain chat requests per DeepSeek's documentation.

An authorized local agent can use the same endpoints after you connect: GET `/api/state`, GET `/api/events`, POST `/api/session` with `title`, POST `/api/run` with `session_id`, `prompt`, `instructions`, `model`, `effort`, `max_tokens`, and `demo`, and POST `/api/note`. These calls are recorded identically to UI calls. The key cannot be retrieved through any endpoint. API calls require JSON and local Host/Origin checks.

Stop the server with Ctrl+C. To remove saved data, stop it and delete the `data` directory. Export first if you want to retain your work.

## Verification

```sh
python3 -m unittest -v test_server.py
```

References: https://api-docs.deepseek.com/guides/thinking_mode/ and https://api-docs.deepseek.com/quick_start/pricing/
