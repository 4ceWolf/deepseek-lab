# Cross-domain review

Date: 2026-10-21. Questions, assistant answers, rubric and initial engine snapshot were frozen before requests. Frozen SHA256: d67167cd1c27efc2a4b728a5351aea1df1f5a0addd5eab255be4d973d25ae7c7.

This is an educational diagnostic, not an independent model ranking. The assistant authored and reviewed the tasks, had prior source access, and has no comparable token/runtime measurement. The practical coding exercise also reuses a function tested previously; it is not a new held-out coding benchmark. Seven subject areas are bundled into two requests; they are not seven independently sampled evaluations.

## Initial responses

- Frontiers: both correctly identify the mathematical open problems as unresolved. Both discuss decision assumptions, consciousness uncertainty, recovery, and causal identification. DeepSeek's Navier–Stokes wording conflates the smoothness question with "energy conservation fails": viscous flow already dissipates kinetic energy, and that phrase is not an accurate alternative statement of the problem. Its causal-design list could be read as requiring all listed features; those are not universal prerequisites. The assistant's answers are more restrained but remain short explanations, not proofs or a comprehensive review. Both omit detailed domain/function-space conditions for Navier–Stokes.
- Concrete initial DeepSeek: low effort spent 3,869 of 4,096 completion tokens on reasoning and truncated during answer 2. Answer 1 is largely useful; the result cannot pass a seven-part task. Frozen assistant decision arithmetic independently checks: A=28, B=30, perfect-information net=53. A reflection about x=0.5 maps 0.2 to 0.8 as stated. The assistant could make the psychology design more specific about its meaningful-effect threshold and sample-size calculation; neither was numerically specified in the task.
- Style/access: both offer a practical step and distinguish conversation from training. DeepSeek admits no execution or weight-write access. The assistant answer explicitly distinguishes its own local tools from the tool-free DeepSeek workspace. No attempt was made to execute commands on provider infrastructure; the application sends no execution tools. Model claims are corroborated by the local request construction and DeepSeek tool documentation, not accepted on self-report alone.

## Follow-up and tradeoff

Thinking disabled completed all seven practical answers with 1,575 total tokens versus 4,761 initially (66.92% fewer). This is NOT equal-quality savings: the initial answer was incomplete; the new answer contains errors, and the style text also changed between calls. No causal efficiency claim can be isolated from this comparison.

The thinking-off response's set {1/4+i, 3/4-i} is NOT invariant under reflection about Re(z)=1/2. Reflection preserves the imaginary coordinate. The correct pair could be {1/4+i, 3/4+i}. It got the general set-versus-point distinction right but supplied a wrong witness.

Its psychology answer invented the detail that the same researchers delivered/scored the manipulation. These are possible confounds, not supplied facts. "No advantage" without a precision criterion is not sufficient falsification. Double-blinding needs qualification because participants receive different belief instructions. Its causal inference, decision arithmetic and Linux checks were otherwise useful. "Rigorous certified computation" only establishes global regularity with an actual all-time argument, not just certified finite-time simulation.

Both frozen assistant code and thinking-off DeepSeek code passed 1,560 local tests: exhaustive bracket strings of length 0–4 plus ignored text and deep/unclosed examples. The independent oracle repeatedly removes matching adjacent pairs. This is meaningful bounded testing, not proof of general coding reliability.

The revised short style response was 993 total tokens versus 786 initially, so it did not demonstrate savings. It still used the stock phrase "Fair frustration". Style remains provisional. A before/after checkpoint hash establishes a changed artifact, not improved intelligence; held-out evaluation is separately needed. Persistence across sessions alone is not proof of training, because app memory can also persist.

## Controller decisions

Keep Auto routing: do not globally disable thinking based on this test. Retain the brief warm/direct style guide and add explicit guidance to acknowledge frustration briefly, verify counterexamples, and separate possible explanations from observed facts. These instructions address observed failure patterns but have not demonstrated general quality improvement. No per-question answer keys were added to the controller.

One corrective conversation follow-up is stored separately. It is prompted repair on already-seen material, not fresh evaluation or weight training. No model weights were modified.

The corrective reply acknowledged the incorrect reflected set, supplied the correct reflected pair, distinguished unknown experimenter behavior from evidence, and required a prespecified equivalence margin plus successful belief manipulation. It completed successfully, but still used 1,272 reasoning tokens. Correction within this conversation worked; transfer to unseen tasks is untested.

Six paid requests used 13,240 total API tokens, including corrective conversation context. No automatic retries. All 19 local controller/server/workspace/validation tests passed after edits. The final generic counterexample guidance was added after the follow-up request and has not yet been live-tested.

Sources checked:
- https://www.claymath.org/millennium/navier-stokes-equation/
- https://api-docs.deepseek.com/guides/tool_calls/ — execution functions are supplied by the application; the model does not execute them itself.
- Weight and API research: ../../docs/STYLE-AND-TRAINING-2026-10-21.md

Full prompts, final responses, returned reasoning, usage and routing are in the JSON artifacts and data/lab.sqlite3. API keys are excluded. Earlier recovery lost some original raw logs: this archive does not retroactively restore them.
