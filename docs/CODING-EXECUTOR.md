# Isolated coding executor

Implemented 2026-10-21. Desktop application remains deferred. This adds a command-line coding loop to the existing workspace server; it is not a general terminal agent or a new browser interface.

## Workflow

1. Supply a job JSON with a relative module path, public function name, contract and expected test results. The module must reside inside the job directory. Paths resolving outside it are rejected.
2. Run the original module in an isolated process to establish the actual failing evidence.
3. On an explicit live run, ask the connected DeepSeek model for a complete replacement module. The current ECU selects initial effort.
4. Verify its proposal outside the model. The child receives inputs only; expected answers remain in the parent evaluator.
5. If needed, send failure evidence back for one bounded repair attempt using low effort. Stop after two attempts, a provider error, insufficient remaining time, or success. A token-truncated response cannot pass.
6. Save the passing proposal and reviewable diff. Never automatically replace the source file.

Progress, requirements, attempts, actual check results and usage persist under data/coding-runs/<run-id>/. Provider request/response events also remain in data/lab.sqlite3. New executions mirror verification reviews into the workspace run log. A crash during a provider request leaves an awaiting/pending record; the implementation does not automatically resume or retry it because it might have been billed.

## Run

Jobs may include `requirements`, each with a unique `id`, a `description` and a list of zero-based `cases` indices. Every case must be covered. The task ledger records their verification evidence and remaining work. Use `python3 coding_agent.py data/coding-runs/<run-id> --inspect` for read-only recovery and evidence checks; it never repeats provider requests. See [current capability tests](AGENT-CAPABILITIES-2026-10-21.md).

From the project folder:

```sh
# Local verification only, no API call:
python3 coding_agent.py examples/verified-repair/job.json

# At most two paid requests using the already-connected workspace key:
python3 coding_agent.py examples/verified-repair/job.json --live
```

No key is accepted on the command line or written into the job. Connect through the existing workspace. The supplied example is deliberately buggy and remains unchanged after the run.

## Isolation and limits

Uses bubblewrap user/PID/network/mount isolation with a read-only system runtime, a read-only temporary source directory, empty temporary home, and cleared environment. It does not mount the host home, project tree, credentials or test expectations. Inside Flatpak, a host launcher starts bubblewrap; candidate code still runs inside that new sandbox. If isolation is unavailable it fails closed, never falling back to normal host execution. Requires Linux with working user namespaces, bubblewrap, timeout and Python on the execution host.

The worker also restricts Python syntax and builtins to a small pure-function subset. Imports, arbitrary attribute access, classes, file I/O and shell access are unsupported. Supports JSON-compatible inputs/outputs, selected builtins and methods, expected ValueError/TypeError/StopIteration, and optional input-mutation checks. Tuples normalize to JSON arrays; booleans are distinguished from numbers. This is a constrained execution facility, not an unrestricted Python environment.

Bounds: 50 KB source, 200 KB test data, 2,000 cases, 256 MiB child address space, two seconds CPU, six-second sandbox wall timeout, nine-second outer launcher timeout, one MiB output file limit. Repair loop permits at most two provider requests with 4,096 completion tokens each. It will not start another request unless at least 150 seconds remain in its 300-second wall allowance. Provider/server timeouts also apply. These are execution/request bounds, not a guaranteed dollar spending cap or a strict input-token allowance.

Test expectations and checks can be incomplete or wrong. Passing them is evidence for those cases, not a correctness proof. This does not yet support multi-module dependency installation, arbitrary repositories, live Linux repairs, or automatically applying patches. The broad long-task agent remains future work; this loop makes bounded progress independently auditable.

## First live result

DeepSeek repaired cumulative(events), preserving zero totals and summing repeated keys. Original failed supplied checks; proposal passed all four in isolation on its first attempt. API usage: **308 total tokens**. Source unchanged. Records: ../data/coding-runs/c154c3aa342a464e9fe06d3b989aef75/ . This is a smoke test of the integrated workflow, not a new capability benchmark.

Verification: 36 local tests passed, including direct probes of network isolation, hidden host home, cleared child environment, read-only work mount, denied imports/I/O/introspection, infinite-loop termination, expected-answer separation, mutation detection, boolean/number distinction, two-attempt stop, dry-run mode and provider-error handling.
