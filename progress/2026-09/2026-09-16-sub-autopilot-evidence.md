# 2026-09-16 — sub-autopilot-evidence (AutoPilot promotion-evidence hardening)

Zero inference, no process management. Orchestrator worktree
`/mnt/raid0/llm/worktrees/sub-autopilot-evidence`, branch `sub/autopilot-evidence-20260916`
(not merged, not pushed). Commits: `203cb6e2` (AP-53 + AP-55), `b7a61c02` and `06cf82dc` (W3).
Offline tests: 1311 passed across the autopilot, journal, baseline, safety-gate and snapshot
suites. The vidya adapter suite passed 11.

## AP-53: rejected-mutation ledger (ticked)

**Measurement** (current run, trials 0–1505, all shards; unit = one journal trial row):
- 133 trials re-proposed a config an earlier trial had already rejected: 9.7% of all trials,
  31.3% of keyed trials.
- By type: structural 105, numeric 15, code 9, prompt 4.
- The median gap from the first rejection was 91 trials. Only 8 of the 133 were blacklisted at
  dispatch, and 59% were rejected again.

**Landed:**
- A harness-written JSONL ledger, fed by 15 reject paths in `actions.py`.
- The ledger feeds the mutation prompt through `_build_mutation_context`, so `prompt_forge.py` is
  untouched.
- A planner-prompt fold of still-standing hard-rejected configs. Replayed over the live journal, it
  would flag 48 of 216 keyed trials.

## AP-54: does the agent under evaluation read the wiki? (ticked)

**Answer: AMBIGUOUS.**
- Nothing injects wiki content into eval rollouts.
- The builtin file tools have no path check, and REPL tools reach all of `/mnt/raid0/llm`, so the
  wiki is reachable.
- The traces keep only tool names, so absence cannot be shown.

AP-54b is filed as a compute-gated A/B and was not run. The fence is proposed, not implemented. It
needs an operator choice: `AUTOPILOT_TOOL_SENTINELS` is always on in production, so a per-request
eval flag is the recommended arming mechanism.

## AP-55: infra fingerprint and NON_COMPARABLE, parts (a) and (d) (row stays open for (b) and (c))

- `infra_fingerprint.py` digests six components: orchestrator, evaluator, kernel, recipe, models and
  host.
- Trials record the fingerprint plus a `comparability` verdict against the tier baseline's
  fingerprint. A mid-trial regime change marks the trial NON_COMPARABLE.
- The fingerprint and verdict are carried into the measurement tuple, `eval_details`, and the
  baseline-promotion events.

## Evidence-plane W3: segment snapshots (row stays open)

- A chained snapshot row is appended to each closing shard, folded under the live authority scope.
- Rebuild = snapshot + tail fold, proven equal to a full fold in a test.
- Fixed a false prefix drift on tail-only supersessions.
- Fixed the authority path consuming snapshots across a mismatched epoch scope.
- Live read-only finding: the latest snapshot (through trial 1458, from the terminalizer) is
  correctly `prefix_invalidated`; the only difference is `t0_audit`. The live epoch (2026-08-10)
  postdates every journaled trial.

W6 was skipped: the handoff marks it audit-current and nothing adjacent needed changing.

## Belief kernel

- The autopilot-journal adapter carries `infra_fingerprint` and `comparability`; the grade is
  unchanged.
- Fixed `sys.path` in the adapter's end-to-end test.
- Added a README row for the rejected-mutation ledger and filed task VB-AP53-RATE.

## Main session to schedule

- Merge the branch.
- AutoPilot restart: AP-53, AP-55 and W3 are all loop-side.
- Regenerate the index state; `--check` fails only on FRESHNESS.
- Operator decision on the AP-54 fence arming.
