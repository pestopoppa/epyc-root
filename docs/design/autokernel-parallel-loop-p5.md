# AutoKernel parallel loop, P5: hand-back verifier and failure classifier

Plan: `/mnt/raid0/llm/tmp/ak-parallel-loop-audit-20261121/REPORT.md` section 4, P5 (approved 2026-11-21).
Code: `scripts/coordination/akloop/` (`handback_verify.py`, `failclass.py`, `replay_failclass.py`). Tests:
`tests/coordination/test_akloop_p5.py` (34). Pure read-only tooling: no compute, no writes outside the notify path.

## (a) Hand-back verifier

`handback_verify.py --text handback.md | --claims claims.json [--rerun] [--fetch] [--json-out stamp.json]`

Runs `.claude/skills/row-owner-loop/references/handback-checklist.md` mechanically. Claim types and proofs:

| claim | proof |
|---|---|
| `pushed` sha [branch] | `origin/main` is in `git branch -r --contains sha`; if a branch is named, `git cherry origin/main branch` is empty |
| `branch_contains` | `git merge-base --is-ancestor` |
| `published` id | `ready/<id>.json` exists, or a `SMOKE-QUEUED` marker in `dryrun/<id>/` |
| `smoke_pass` id | the LAST `==== dry run PASS|FAIL` line of `launcher.out` is PASS and `PASS.json` is not older than the publish |
| `filed` id | `filing-done/<id>.FILED` |
| `built` lib symbol | symbol bytes present in the library (content proof, never mtime) |
| `ticked` id file | `origin/main:file` line is `[x]` and carries a `[belief:` / `[no-belief:` tag |
| `tests` | a test `log` is parsed (N passed, no failures, optional `expect_passed`), or `cmd` is re-run under `--rerun`; with neither it is unprovable |
| `file_exists` | path exists |

Stamp: `VERIFIED` only if there is at least one claim and every claim verified; anything else, including a hand-back
with zero checkable claims or an unknown claim type, is `UNVERIFIED`. Output is `epyc.handback.stamp.v1` JSON with
per-claim `ok`/`detail`/`proof`. Exit 0 = VERIFIED, 1 = UNVERIFIED, 2 = usage. Text extraction is line-pattern based
(`pushed <sha> [to <branch>]`, `published <id>`, `smoke passed <id>`, `filed <id>`, `ticked <ID> in <file>`,
`built <lib> with <symbol>`, `branch <b> contains <sha>`); structured JSON is the reliable path and what a brief should
ask subagents to append. Wiring it into the brief report shape is a follow-up for the owner of `brief.py` (not touched here).

### Automatic stamping (2026-11-23)

`akloop/handback_auto.py` runs the verifier on every AK subagent hand-back, called from the existing PostToolUse(Agent|Task)
hook `scripts/hooks/posttool_handback_sweep.py` (no settings.json change). An AK hand-back is one whose dispatch prompt
carries the brief.py CLAIMS contract or whose report has a `CLAIMS:` line; other subagents are untouched. The stamp reaches
the dispatching model as additionalContext (stamp, reason, failed claim TYPES only, never subagent text) and every stamp is
appended to `/mnt/raid0/llm/tmp/handback-stamps/stamps.jsonl` (`HANDBACK_STAMP_LEDGER` overrides). No CLAIMS block = UNVERIFIED.
Why this hook: already registered for the event and fed the returned text; a file watcher has no hand-back file to watch;
wrapping brief.py would cover only owner-generated briefs, not the returning report. Tests: tests/coordination/test_akloop_handback_auto.py.

## (b) Failure classifier

`failclass.py --fail FAIL-N.json | --result RESULT.json [--launcher launcher.out] [--route]`

The AK-FAILRULE-1 report (`/mnt/raid0/llm/tmp/ak-failrule1-20261106/REPORT.md`, classes compile, correctness_gate,
timing_loss, noise, harness_error, other, over experiments.db rows) is folded into the one split that decides who acts:

- `harness`: the pipeline, job wiring or instrument failed and the candidate was never judged. Klasses: admission_refused,
  launcher_not_started, no_ended_record, residency_unproven, build_missing, job_script_error, smoke_wiring,
  result_contract, window_or_stop, instrument_noise, incomplete_run.
- `candidate`: judged and lost. compile, correctness_gate, timing_loss, noise.
- `ok`: not a failure. `unknown`: no rule fires.

Ordered first-match rules over (1) the pipeline's `reason` string, (2) the job's own error text from `launcher.out` /
`launcher_out_tail`, (3) the RESULT.json `verdict`/`status` token (parentheticals and `_`-suffixes handled; an unrecognised
verdict token is `unknown`, never silently falls through to `status: complete`). Every result names its rule.

Routing: `route()` sends only `side=harness` through the existing `rowflow/notify.py emit()` path (kind
`ak-harness-failure`, owner `pipeline-mgmt`, idempotent per row+klass+rule, alerts.jsonl plus bus message; a non-live flags
tree never posts to the bus). Candidate, ok and unknown are never routed.

Cheap-model fallback: `FallbackClassifier` / `set_fallback()` is an interface only. Nothing registers one, so an
`unknown` stays `unknown`; if one is registered it is consulted only for unknowns, its answer is tagged `fallback:`, and
an exception inside it is swallowed.

## Replay and agreement (run 2026-11-21, `python3 scripts/coordination/akloop/replay_failclass.py`)

Corpus: 929 `dryrun/*/FAIL-N.json` (with their `launcher.out`) and 71 AK `RESULT.json` files reached through the
`result_path` of `ak*` rows in `ready/`, `retired/`, `withdrawn/` (cross-checked against `filing-done/<id>.verdict.json`).

| set | records | gold-labelled | agree | agreement |
|---|---|---|---|---|
| FAIL-N.json (harness vs candidate) | 929 | 789 | 788 | 99.9% |
| RESULT.json (ok / candidate / harness) | 71 | 58 | 58 | 100% |

The one FAIL disagreement is `autokernel-r18d-pp512-v10-private-20261102` (job wrote ALL DONE yet rc was nonzero; the
rules say unknown, the template gold said harness).

Read these numbers with the following caveats, they are not an independent accuracy estimate:

1. The gold labels (`TEMPLATE_GOLD`, `TOKEN_GOLD` in `replay_failclass.py`) were written by the same author, from the
   clustered reason templates and verdict tokens, so agreement measures rule/label consistency, not truth. 507 of the 789
   labelled FAIL records are one template (admission refused) and 182 another (launcher never started).
2. The genuinely hard family is a job that exits nonzero before its first progress. 140 FAIL records have no template
   gold; the rules classify 35 of them from the job's own text (27 pipeline-env, 10 script traceback, 3 serving infra,
   2 build failure, ...) and leave 105 `unknown` (`job_exit_unexplained`). Those are mostly job-internal smoke gates
   (`SMOKE_FAIL`, `smoke rc=-11 cases=0`), where harness versus candidate cannot be told from the log alone. That is the
   population the unwired model fallback is for. Coverage over all 929 is 91% classified (824), 9% unknown (105 plus 1
   unmatched).
3. RESULT.json: 58 of 71 carry a gold token; 13 have no verdict/status (bare data dumps such as `loop_rc` or `rows`
   records) and stay `unknown` (13 of 71 unknown).
4. Cross-check against the filed verdict for the 68 RESULT rows that have one: every `ok` row (33) filed as
   SCIENCE/PARTIAL/RECEIPT, no `ok` row filed as NO-RESULT; the single harness/NO-RESULT pairing agrees. A candidate-side
   row filed as SCIENCE-VERDICT is expected (a verdict that the candidate lost is still a science verdict).

Zero-LLM-turn criterion from the plan ("harness failures no longer consume a main-thread turn") is met in mechanism:
a harness classification emits one pipeline-mgmt notification. Hooking `failclass.py --route` to the keeper's
`record_fail` or `watch_rows.sh` is a one-line follow-up in files owned by other lanes and was left alone.
