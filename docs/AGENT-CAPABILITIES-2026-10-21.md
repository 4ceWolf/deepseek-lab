# Five-capability testing pass

Scope: execution/verification, durable task state, evidence-based diagnosis, budgets, independent checks. No boot-care testing.

## Changes

- Jobs can define named requirements linked to supplied case indices. Invalid indices, duplicate IDs and uncovered cases are rejected. If no explicit mapping is supplied, the contract is one requirement covering all tests.
- Task state persists requirements, evidence-file references, remaining steps and reported usage. JSON records are replaced atomically after a flush/fsync, avoiding partially written state files.
- An original source change detected before an attempt prevents a paid request based on stale code. Changes during a request are flagged for review; originals are never automatically overwritten.
- Read-only `--inspect` checks saved candidate hashes, check files, current-source identity and pending-request status. It makes no API calls and never resubmits a possibly billed request. This detects accidental corruption; unsigned local records are not tamper-proof against an attacker who rewrites the entire archive.
- Truncated replies remain rejected even when their partial code happens to pass syntax. Assertions such as "all tests passed" do not override the external verifier. Failure evidence and remaining steps are saved after the two-attempt limit.

Requirement status is deliberately conservative: a candidate must pass the complete supplied suite before requirements are marked passed-supplied-cases. This does not establish that tests fully cover the prose requirement.

## Live checks

Three structured evidence cases ran against both raw DeepSeek and the ECU, same inputs and a 2,048 output cap. Both passed 3/3: missing observations did not justify a cause; current error/listing evidence outweighed an injected success claim in an old log; parsing success plus failed functional tests and truncation did not justify accepting a fix.

Raw used 817 total tokens; ECU used 1,757. ECU output tokens were lower (233 versus 463), but system-instruction overhead made total use higher. No quality or efficiency superiority is established on this sample. Records: ../evaluations/evidence-20261021T151813Z/ .

A live reconcile(current, desired) repair passed four isolated tests in its first attempt, covering deletions before sets, sorted groups, unchanged entries, empty input and preservation of inputs. It used 366 tokens. Its saved ledger names three requirements and leaves patch review outstanding. No source was overwritten. Records: ../data/coding-runs/2a06cc04657d45f0b8f495ceb02ab53b/ .

Total paid use this pass: seven requests, 2,940 tokens. No automatic reruns of completed evaluations.

## Local adversarial checks

Added tests for candidate-hash mismatch after saving, source drift before a request, truncated-but-correct code, false prose success claims and invalid requirement coverage. Existing checks cover isolation, no network/home access, readonly mounts, denied introspection, execution timeouts, input mutation, pending-provider errors, explicit dry-run and attempt bounds.

Final verification: all 42 local tests passed. Inspection also checks the original snapshot, proposed source and review diff for consistency with saved evidence. The live run's inspection reported no evidence issues, unchanged original source and no pending provider request. No extra API requests were made for this inspection.

The scope remains small pure-Python modules. Persistent ledgers and read-only recovery are implemented; general multi-step task planning/resumption and multi-file repository execution are not. Diagnosis cases are small synthetic judgments, not proof of reliable real-world diagnosis. Desktop work remains deferred.
