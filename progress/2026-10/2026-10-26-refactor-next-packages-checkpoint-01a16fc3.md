# Refactoring next-package checkpoint — 2026-10-26

Root documentation in `/mnt/raid0/llm/worktrees/refactor-audit-01a16fc3-root` on local branch
`refactor/handoff-audit-20261024-01a16fc3`, starting from
`e8748d8ecb1b0917ef1ad003f114581d8f648785`. Future root publication targets
`codex/refactor-handoff-audit-01a16fc3`; the old review remote stays unchanged. No canonical
checkout, application code, serving runtime or kernel was changed by this documentation work.

Root `bb6410b1fa76553ab8d2d26dad5ee9816fb1ee5d` was privately published on the named codex
branch after local gate PASS. Workspace-58's 12:45/13:25 review did **not** accept or merge it.
The owner requested the checkbox/generated-index/ownership corrections documented below; the
local publication receipt remains historical evidence, not owner acceptance.

## Integration candidate

Owning main reviewed and published `851955112b8ba8c2911a7684469551afa1541623` on the historical
`refactor/orchestrator-integration-01a16fc3` review branch, relative to immutable base `84f6f6f1`.
The expanded union passed 2,897, skipped 8, and failed 0 of 2,905; all four coverage floors are
100%. AST, focused suite, Ruff and accepted-scope formatting, compile/diff, 32 NI63 pins and four
P5 preservation proofs pass. The original formatter runner's terminal `FAIL` is preserved; an
independent immutable-base scope correction establishes zero introduced formatter paths.
This validates one private candidate. [Integration review](../../research/refactor-audit-2026-10/integration-validation-review-2026-10-26.md).

## Current source packages

**O8 CI** has B1-tested pre-fixture local-only merge `753e0287a1ae6b06f2a5c91269899ff8cc8452b5`, with parents
`713edf671614e69f67028100c08cc8f08b02d52f` and `851955112b8ba8c2911a7684469551afa1541623`.
Its focused check actually passed 13 tests. Official q1 B1 collection attempt 1 failed before
collection: custody hashing followed public-carrier directory symlinks. That attempt ran no
tests. The helper's repaired symlink metadata proof passed. B1 attempt 2 collected 20,646 baseline
tests plus an error for an unregistered `slow` marker; no candidate collection ran. The source
owner corrected only the external harness while preserving strict marker handling. The terminal
strict collection result passed: baseline 20,658 total/20,645 selected and candidate 20,666
total/20,653 selected; 0 removed, 8 intended additions, and 13 identical exclusions. This proves
collection parity only, not a full-suite result.
Full baseline comparison, native capture and coverage are incomplete; O8 is unchecked.

B2 baseline completed at 13:13:11 UTC: **31 failed, 20,517 passed, 85 skipped, 19 xfailed,
6 passed subtest events in 2,146.45 s**. The parent-case denominator is 20,643. Nine module-skip
case nodes give 20,652 JUnit testcase nodes; the 20,658 header additionally counts six subtest
events. Native conformance was NULL because of an unnamed collection-skip case; shared grading
failed without emitting JSON. Sixteen ignored runtime paths leaked in the baseline checkout.
Tracked source custody for three repositories and source-harness custody matched. There was no
candidate full run, and this result does not establish an accepted known-failure set.

Original receipts are immutable under
`/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/b2-baseline-first-native/` (`junit.xml`, `native/`,
`producer.status`, `shared-grade.status`, `shared-grade.log`, custody/status files).
The owner's next steps are to repair native report compatibility, classify all 31 failures by
reason and name the unnamed JUnit case, close runtime isolation gaps, then review a dry run and
rerun the baseline. Do not start a candidate phase or silently accept baseline failures.

**P3 autopilot actions** has prepared the merge of checkpoint
`bbccaaefed8f0f482b0b712f5d7ed06e14ef719b` with integration `851955112`.
The first 34-file selection returned 817 passed, 1 skipped, 3 failed. The expanded 90-file
selection returned 1,917 passed, 2 skipped, 11 failed over 600 s. After targeted legacy-adapter
and test-double repairs, the final 12-file selection returned **402 passed, 1 skipped in 39.49 s**.
Compile, protected P5 and W3e bytes, diff/hash, and no-new-Ruff proofs pass. Raw Ruff exit 1 is
preserved with 16 inherited E701 findings in `tests/unit/test_mutation_diagnostics.py`. These are separate selections;
there is no current all-1,930-pass result.

The official q1 formatter closure ran 12:04:57–12:05:05 UTC with exit 0 for exactly
`eval_task_coverage_report`, `journal_shards`, and `test_journal_shards`: all three ASTs equal
before/after, format-check 3 passed, non-target bytes unchanged, no-new-Ruff `[]`, protected-file,
diff and source-custody proofs passed. Source **`fb5db1a0a24b92172643bb670c77a4343a508c96`** is
published on `codex/refactor-autopilot-actions-01a16fc3`, remote-exact verified with a clean
worktree. Owning main accepted P3 for this private branch only.

Raw final receipts:
`/mnt/raid0/llm/tmp/refactor-01a16fc3/autopilot-actions/format-closure-20261026/`
contains `commit.sha`, `ls-remote.txt`, `publish.exit` (0), `AST-custody.json`, and empty
`postpush-status.txt`. The committed source record
`fb5db1a0:docs/refactoring/2026-10-26-p3-reviewed-checkpoint.md` maps all 16 package findings to
their behavioral warrants. `final402-immutable/` retains the functional receipts;
`attempt2-receipts/` retains the failed expanded selection. Preserve all of them.

## Observations and limits

A native read observed the 1.35 GB `question_pool.jsonl`; its exact consumer is unproven. No fixture patch was
applied, and no EvalTower-constructor causal claim is supported. The CI host audit established
that a dashboard restart test polls live slots and creates host logs. A reviewed owned-dashboard
test fixture was applied after B1 (+26/−10); validation is pending. Production application logic
is unchanged; the new local candidate identity is being committed separately from B1-tested753e0287.

## Calendar coordination and root wrap-up

The operator requested coordination with the Claude compute owner. Current authorization is
literal q1 CPUs **24–47**, 8 GiB, correctness work under a live canonical grant, official filler9
launcher, and taskset/affinity proof. Claims on CPUs 0–95 are not authorized by that grant.
The latest P3 targeted grant (11:28–11:43 UTC) ended at 11:30 with PASS; B1 ended at 11:31 with
the custody-hash failure. Independent corrective rows are being prepared. Native coordination
is owned by `compute_coordination_finish`, succeeding the interrupted coordinator.

A prior ungranted Python metadata row edit was disclosed to the owner; its exact time is unknown,
bracketed 11:27–11:28 UTC. No application, test, build or timing-impact claim is inferred from
that disclosure. Corrective coordination uses authenticated native IPC; no grant, queue or HOLD
file is authored by this documentation worker.

Root attempts `829152` and `831298` ended before admission. The later bare queued outer `881101`
and its exact child `881104` were TERM-cancelled before admission for calendar integration and
both verified absent. Its `FAIL`/143, done/failed flags and cancellation receipt remain under
`/mnt/raid0/llm/tmp/refactor-01a16fc3/wrapup-20261026/publish-run/`; this is cancellation history,
not a gate logic failure. No root checks, commit or push ran. The Oct 25 PASS covered prior
inputs only.

No root row is armed by this documentation worker. P3 source closure is complete; the root job
can run independently of the corrective CI row in a separate official q1 grant:
600 s maximum, 300 s minimum useful, 8 GiB. Its entry must check the exact grant, HOLD state and
`FILLER_DEADLINE`, reuse the official launcher's claim, and avoid a nested region claim or timeout
process-group manipulation. Root generation, citation, wiki, README and belief-freshness outputs
will be recorded only from that actual future run. There has been no ingestion or cleanup apply;
unmerged worktrees and evidence remain retained.

## Historical checkpoint accounting and owner correction

The private `bb6410b1` checkpoint changed two result lines relative to its own parent, both with `[belief: cc]`: `RESUME-4` for private integration
validation and `P3` for reviewed private source `fb5db1a0`, actually published and verified.
O8 remains unchecked. The owning main applied RTG-60 next action: `Complete CI collection,
baseline and native validation`; this documentation worker did not edit that row. Existing
AutoKernel holds, P5 one-era boundary and production-serving protections remain.

That two-line comparison did not answer the owner's merge review: this is a new handoff relative
to canonical main, introducing 27 checked lines. The correction audits all 27. Twenty-one retain
explicit per-line commit/path evidence with narrow historical/private scope; six are reopened
because their cited material does not establish closure (historical hermetic collection,
containment fixes, O6(part), O7(part), P1(part), D3(part)). O4 is narrowed to the reviewed four
findings; its other historical associations are a separate unchecked item. None of this equates
commit association or WIP with completed work.

The correction removes only this branch's newly tracked `.index-state.json`/`.index-graph.json`
and restores its two generated master rollup/count changes. Workspace-58 regenerates them under
the wrap-up lease at merge. Review against fetched current main `a876d3c9` found canonical RTG-60
already reserved for `loop-state-offraid-backup.md`; the old private row collided with that identity.
All six current-main domain indices had no refactoring owner or RTG-61. Owning main applied
RTG-61 in this candidate's routing index as its sole owner, with next action `Repair CI report
compatibility and runtime isolation, then rerun baseline`. The canonical RTG-60 backup row is
preserved at merge. This worker did not edit the index row.

Main reviewed and approved this metadata correction for a normal codex-branch fast-forward push,
as permitted without a compute row by the owner's 12:45 instruction. Only native text/git review
and whitespace checks apply to this correction; no fresh validator, generation, grading or ledger
execution is claimed. Owner acceptance and main merge remain pending after private publication.

## Historical private wrap-up gate receipt (bb6410b1; not owner acceptance)

The admitted branch-only wrap-up passed index regeneration/check, citation checking, and diff
checking against this documentation. README freshness returned 0 and belief-ledger
freshness returned 0; both outputs are retained for reporting, with no ingestion.
Scratch cleanup produced a plan and fleet report only; unmerged worktrees, evidence, and the
owner-controlled CI run remain retained. The 2 result checkbox flips carry [belief: cc].
The wiki manifest advances only recognized sources summarized in the reviewed section; its
whole-repository compilation watermark stays unchanged. Commit/publication is performed only
if the final repeated checks and exact-path private-index review pass. Durable gate and publication
receipts are under `/mnt/raid0/llm/tmp/refactor-01a16fc3/wrapup-20261026/calendar-publish-run`. No main promotion or runtime change is authorized.

## Owner 16:40 follow-up: wiki ownership and live runbook warning

The owner verified the prior evidence/index corrections in privately published `d3cba7b6`, including
21 cited checks/6 reopened, generated index removal, restored counts and unique RTG-61. The branch
is still **not merged**. Three further metadata corrections are prepared for main review:

- Withdraw only our `wiki/source_manifest.json` contribution, leaving the owner's newer
  `f6ba6877c` sweep (41 sources) untouched at merge. Reverse the exact branch-merge-base delta;
  do not copy current main wholesale or rewrite the owner watermark.
- Withdraw only our 44-line `wiki/tool-implementation.md` section. Its factual evidence already
  exists in the integration review/chronology; the synthesis is retained under that research
  record's “Findings retained for the next operator wiki sweep” section. The owner compiles it
  at the next operator sweep. Existing peer wiki content remains unchanged.
- Keep `epyc-orchestrator/scripts/lib/executor.py:77`/`:90` in the runbook's standing-offender
  list: fix pending in `refactor/scripts-cleanup-reviewed-01a16fc3@6efa56265b68f402af736a1c1a2ee3df447849c1`;
  remove the line when it merges. That cleanup is unmerged, so source-candidate acceptance cannot
  retire a live main warning. The two approved path-prefix clarifications remain.

Original gate/manifest receipts and the withdrawn synthesis are preserved as historical scratch
artifacts. No source/test edits, toolchain checks, wiki sweep, ingestion, commit or push have run
for this draft. Prior checkbox/index fixes remain intact; main reviews before metadata publication.
