# INF12 R13 and YARN E1 memory admission audit

Date: 2026-11-01. This is an isolated review packet. No production source, grant,
ready row, receipt, launcher, or current R13 process was changed.

## INF12 R13: actual prior attempt

The attempt started 2026-11-01 00:38:29Z (`20261101T003829Z-2260396`), ran native
work, and ended as a partial rather than a pre-grant refusal. Native state `/mnt/raid0/llm/tmp/codex-ni-inf12-g2-20261030-r13/outputs/20261101T003829Z-2260396/STATE.json`
records `rc=75`, `partial=true`, `work_started=true`, phase
`Accurate_Retrieval__eventqa_131072__base`, direct child reaped, at 01:05:30Z.
The adjacent `job.log` records `stop_reason=work-deadline`, child rc 143, and
`stopped_on=Accurate_Retrieval/eventqa_131072/base rc=75`. A 444-line JSONL was
observed in the pinned shared `full-results-a2a745...` output tree; line count
does not attribute completed official records to this attempt.

The terminal was preserved as
`/mnt/raid0/llm/tmp/compute-flags/grants-archive-ws58/codex-ni-inf12-gate2-triton36-r13-20261030.ended.keeper-1793495132`
(`rc=75`, `job-rc-75:exited`). Keeper rearm evidence is
`/mnt/raid0/llm/tmp/compute-flags/ws58-keeper-state/rearm-codex-ni-inf12-gate2-triton36-r13-20261030.1793495132`;
it confirms the old window began at 00:38:29Z on `mi210_0,184-191`. This explains
why the active `grants/<id>.ended` was absent: the terminal was archived during
same-ID rearm. It is not grounds to synthesize or rewrite a receipt. Older
attempts under this reused ID remain distinct exposures and must not be folded
into the 00:38 attempt.

A later attempt was observed at the initial packet snapshot as PID 3151123, born
01:06:51Z, grant 01:08–01:38Z, native run id `20261101T010825Z-3201456`. That
snapshot is stale for current status; its boundary and filing belong to the C3
owner. This audit makes no claim about that or any current attempt outcome.

**Root cause / repair:** the scientific run reached its task-level work deadline
while in `eventqa_131072/base` and correctly returned rc75/partial.
The no-`.ended` appearance is a same-ID rearm/archive lifecycle issue, not a
missing native terminal. Preserve every attempt and its exposure. After the
live boundary, carry only verified resumable output forward under a fresh row ID
and the canonical hard-gated engine. Do not change the official population,
source order, evaluator, allocator recipe, or verdict rule. The original status
remains diagnostic partial; INF12 Gate 2 is still open, with no verdict. The
predeclared denominator remains 3,671 official records per arm (7,342 total for
base and Delta-Mem); the 444-line partial JSONL is not completion and does not
support a per-arm result or score.

## YARN-E1-MEM: admission refusal and source scope

The 2026-10-31 21:02:33Z launcher log and native `.ended`/`.FILED` say
`rc=6`, `t1-admission`, missing T1 fields `dryrun_pass`, `launcher_path`,
`job_path`, and `source_manifest`; no native work began. The armed manifest did
already pin nested `launcher.path` and `job.path`, plus
`source_manifest=/mnt/raid0/llm/tmp/codex-ni-next-gpu-prep-20261031/SOURCE.sha256`
with hash `e00ddd70be99f2e96b5db3f92ce9e348fb4ab78096f80e277583fe9ac3633f2c`.
The current launcher and job hashes are respectively
`2de2f8a2ca145885cbad13fe850141d5359d38441d41ad2563ba329d6584531b` and
`618a412d8e4283ebb71dab5a65babb2bca59e949ad50ef63935e2f231781922b`.
The nested-path fields do not prove a T1 pass. Do not add `dryrun_pass=true` or
retroactively turn the 9.6-second smoke into qualification.

The task's pinned ROOT main scope is unchanged: attribute the historical ~15 GiB
KFD overshoot per phase using own-PID KFD VRAM and the hipMalloc shim, compare
E1 image `9a3f1392a` with W image `b0ba1d427`, and identify whether W removes it.
The six planned diagnostic cells are E1/A0/low, W/A0/low, E1/A1/low,
W/A1/low, E1/A1/high, W/A1/high; native needle stages are 128k/240k and
400k/500k respectively. Higher VRAM is worse. This task has no quality or
champion verdict, and the original A1 ≤55 GiB criterion remains the handoff's
done-when. The current row is still diagnostic and open; no cells have run.

**Repair proposal for MAIN review:** make a fresh row ID after preserving the
failed ID and receipt; migrate the launcher to the reviewed canonical v14
engine/schema; pass through only required keeper `WS58_*` qualification inputs
instead of erasing them via `env -i`; add a source-bound qualification fixture
mode that exercises the native server/result writer/completion predicate and a
controlled rc75/partial cutoff on the same entry; qualify through the keeper's
one-use nonce and native GPU quiet claim before any grant. The fixture must not
alter the six science cells, image pins, memory metric, arm order, or existing
phase interpretation. Preserve current source paths and large model assets by
reference; no model copies. Until that proposal is reviewed and the canonical
qualifier is deployed, the row is not grantable and no qualification claim is
made.

## Decision evidence boundary

The intended scientific outputs are phase-level own-PID peak/series VRAM and
hipMalloc traces joined to the six phase cells; the diagnostic denominator is
those six declared cells. The 9.6-second smoke is admission evidence only.
No metric threshold, pass, failure, or finding about the E1/W memory mechanism
is inferred from missing outputs or from a failed admission. Durable filing and
task-status changes remain with their owning sessions.

## INF12 R13: separate 21:02Z attempt

Attempt `20261031T210259Z-128495` started at 2026-10-31 21:02:59Z and ended at
21:30:31Z (`STATE.json`, 1,652s, `rc=75`, `partial=true`,
`work_started=true`) during the
`Accurate_Retrieval__eventqa_131072__base` phase. The retained attempt evidence does not attribute a count of completed native
items within that phase. Its `job.log` records
`stop_reason=work-deadline`, child PID 135764 / start ticks 160307451,
`CHILD_REAPED ... rc=143`, and `stopped_on=... rc=75`. The state says the
direct child was reaped but descendants were not censused. The child PID is
now absent; this does not establish native result completeness.

Exact attempt artifacts and SHA-256: `STATE.json`
`df5ab284279732c07809477a5c2764a9520a7ad5efe8890cd801482997c50a7c`,
`job.log` `931a31687ae03c5168a2287cf869756e0dc4b9147cf5c93b529e810cb9e14c5b`,
`GPU-SAMPLES.tsv` `a7c411b3f030fb30d2fc049a697bbd049ba181166deae094395c073e42d2a0dc`.
Its archived terminal is
`/mnt/raid0/llm/tmp/compute-flags/grants-archive-ws58/codex-ni-inf12-gate2-triton36-r13-20261030.ended.keeper-1793482232`
(SHA-256 `82bad0bd1f6bcd61cbf6ed0578577726b0764e9e81f3e657801d672e7400d5de`),
with `rc=75`, `job-rc-75:exited`, 1,800s grant, start 21:02:59Z. A later
same-ID launcher-up event at 21:30:48Z is after that terminal. The archive entry records the terminal for this attempt; no terminal should be
synthesized. The attempt directory has no run-specific native JSON/JSONL. The
stable shared results tree was not attributed or hashed because rearmed attempts
may write there; preserve that ambiguity and all exposures.

The root cause is the 30-minute task grant ending while native execution was in
the 131,072-context base phase. The completed-item count is not attributable from
retained attempt-local evidence. This is separate from the 00:38:29Z attempt
(`20261101T003829Z-2260396`). A fresh-ID continuation
proposal must wait for owner boundary, verify exact pins and every existing
resumable row/hash before reuse, retain source order and resume identity, and
complete the declared 3,671 official rows per arm (7,342 total) before any
per-arm score. No redraw, changed scientific rule, or current-result inference.

## YARN r2 isolated packet

Packet: `/mnt/raid0/llm/tmp/codex-ni-inf12-yarne1-repair-20261101/yarn-packet-r2`.
It pins the actual max N19 rendered prompt at 498,965 tokens (rendered SHA
`8307912edb92fa5df0de817f687e0651fa5e05209aefbb2de9c03db303caa5c4`), both
images, model edge identity, template, recipe and split KV mode. Request manifest
SHA `2ea9ec467f77fffdf3079d70c1a96e03041e62c2e9d2d380c53eb31c638c30e0`,
recipe SHA `fbff79e22b601fb32210338fd3bd90e4a124730a439fa019dc10c14ede3a8161`,
fixture SHA `f25a42521e041e0dc6530075fb6df3afc3695d044f34c5857bc215b1e0f28cdf`,
source dependency SHA `e958f225c98dd4000c453492548dda05331fba34a93938207f2bee87c0dbd20f`.
The six diagnostic cells are unchanged. The required unit is paired E1/W A1/high;
each image must do the 400k seed and exact 500k N19 event. Tokenizer metadata is
CPU-only and is not qualification. Behavioral/model-free contract tests: 8 passed, including empty/cross-recipe
event rejection, prompt/hash/KV/context refusals, and owner-booking/window checks.
Python compilation, `bash -n`, and all 52 source hashes passed.

Work-unit timing and owner-booked long-native window remain unmeasured. The
private candidate launcher refuses before the engine without a pinned owner
booking and takes `--min-window` only from the validated accepted manifest. Historical
v10 planning gives a 4.76h three-pair floor before current-image loads, probes,
analysis and cleanup; a 25% planning reserve would be about 5.95h, not an
adequacy claim or READY. `WORK-UNIT-CALIBRATION-REQUIRED.json` remains MISSING /
UNPROVEN and no READY was published. Qualification may verify the exact max
request and cutoff behavior, but cannot stand in for a complete paired work-unit
calibration or the six-cell science verdict.
