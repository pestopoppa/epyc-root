# 2026-10-22 — KPF-26.1 window 1 INVALID: diagnosis and runner v2 (3c4ca599 + subagent)

KPF-26.1 window 1 (seed 261, q3 19:40-19:56Z) came back INVALID: arm-A pass rate 0.4375 is below the predeclared 0.6 baseline gate (B 0.354, A2 0.444; 18 pass->fail / 6 fail->pass A->B, sign p 0.011). Main stopped the `--repeat` poller (4160530, verified dead) so window 2 would not burn a grant on the same defect, and set the queue row to BACKLOG with a named blocker.

Diagnosis (subagent, no inference): not a harness bug. Prompt digests, expected answers, extraction and the server log are all clean. The task format forced no-CoT arithmetic: 14-row sums and rankings with thinking off and "reply with the number only". Arm-A failures: 42 numeric wrong, 12 a distractor note number, 3 a table qty, 24 a wrong but valid name; none truncated.

Fix on orchestrator branch `feat/kpf261-outcome-runner-20261022`:
- `cb7caf09` (subagent): brief work plus a final `ANSWER:` line, graded on that line only; max_tokens 1024.
- `0ea2b050` (main's review): the DOTALL `findall` captured from the FIRST `answer:` to the end, so work text could leak the expected number. Now only the first line after the LAST marker is graded.
- 21 unit tests pass.

Deployment: new job `jobs/s5-kpf261-outcome_job.v2.sh` (runner `kpf261_outcome_run.v2.py`, sha256 5d0b5ed8, `--max-tokens 1024`, out `kpf261-outcome-out-v2`); dry run clean; poller 619631 re-armed on filler_run8 at 20:03Z; row ARMED and passes `--for-grant`; workspace-58 told. Both windows rerun on v2. The gate and decision rule are unchanged.

Not filed: lowering the 0.6 gate (declined, it was predeclared). Filed as a conditional step in KPF-26.1d: a smaller table if arm A is still < 0.6, decided from arm A only.
