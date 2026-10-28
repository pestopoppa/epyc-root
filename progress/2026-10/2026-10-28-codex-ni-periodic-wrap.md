# NI periodic checkpoint — 2026-10-28

Roster `codex-ni-01a16d6b`. Final update after the owned T96 job ended at 20:52:03 UTC (outer rc1, cleanup verified, all physical locks released). This checkpoint distinguishes completed native work, failed postprocessing, reviewed source integration and still-open inference gates. No index row, live scratch, grant, queue, FILLERS status or HOLD was changed.

## Completed source and native work

### SSU-F18: moved-lineup compiler regression

Reviewed source is pushed to orchestrator branch
`codex/ssuf18-moved-lineup-20261028`, commit
`833a2f4e870b9c12ffabe7ac1bbc3efa4b594baf`.
Lane: `/mnt/raid0/llm/worktrees/mains/codex-ni-ssuf18-moved-lineup-20261028`.
Seven test/fixture files, +188/-8; no production logic, deployment or reload.

The original tmp plugin no longer exists. Committed YAML overlays preserve
the documented worker-to-architect_critic move, not lost byte identity.
Current compiler coverage is 44 cases, not historical 35: baseline 44 pass;
moved 43 pass plus the deliberately retained exact
`assert regenerated.startswith("full:")` failure. The ordinary regression
runs both variants, compares exact testcase identities and unique cases,
requires consistent JUnit counters/zero errors/skips, verifies unchanged
declaration bytes, excludes ambient pytest plugins/addopts, disables
bytecode writes and isolates each pytest cache. It tests that isolation
with an invalid ambient plugin/option. Two accidental context/topology
restatements were corrected in tests; the deliberate wire pin remains.

Final R6 validation: 45 passed in 9.78 s, one
existing warning; Ruff, diff checks and normal commit hooks passed.
`/mnt/raid0/llm/tmp/ssuf18-final-r4-20261028.log`.
GitNexus impact for all edited tests was LOW, zero upstream callers; no
serving function changed. Exact root handoff/progress text is in
`/mnt/raid0/llm/tmp/ssuf18-root-wrap-draft-20261028.md`. The owner integrated this source in orchestrator main `bc1cf9780905d65e5088aedcf240d20a9643caa3`; no deployment. This root checkpoint records the task boundary. [belief: cc]

### FA6a: full OFF operator gate

Normal row completed rc0 at 17:47:20 UTC, 312.229 s, nonpartial. Native log
ends with 2978/2978 tests passed, ROCm0 OK and 2/2 backends passed (CPU
skipped). Source/version equivalence documents why the current full suite
satisfies the old 640-case task expectation; it is not a replacement partial
threshold. 3,076 recorded-PID HIP/KFD/positive-VRAM samples, writer and
cleanup verified; captured PIDs absent. Broader V11-FA-6, FA4 and promotion
remain open. No decision-grade or deployment warrant was created.

Evidence: `/mnt/raid0/llm/tmp/codex-fa6a-native-20261028/run-20261028T174207Z-635872/`.
Root source wrap branch tip `f7d2ca7db55b483b9e8a962bac90f8de5fd1ca5e`
was promoted by the owner as
`6ea9817a9ccb63c64511a277aa6f9d22119d6c7d`; owner index/citation checks
passed. The prior smoke note is explicitly historical. FA6 claim released.
[belief: cc]

### RTG57 P3 and HPR bounded findings

Dedicated RTG57 P3 full run finished rc0 at 17:26:00 UTC, 4776.752 s,
nonpartial, 20 native decode-only rows, all captured servers/runner dead.
Scope remains indicative diagnostics, with CPU sibling co-tenancy and
parked no-cache-idle-slots limitations; no quality, production residency or
deployment claim. Evidence:
`/mnt/raid0/llm/tmp/codex-kvu16h-runner-20261028/run-20261028T160623Z-105416/`.
Owner promoted corrected wrap as
`59533ef9a3b60c8097b98174e4f9a33a284a388b`.

HPR raw-r2 retrospective audit: existing producer validator clean on six
64k cells/36 HTTP 200 requests, no errors, complete prefix captures, all 42
cell/request hashes matching; existing witness validator clean on 36 windows
and 127,870 during-request samples. Native contract remains UNVERIFIED and
policy_verdict null; no timing grading or historical regrade. Original
INVALID_SIM_DISAGREES and contamination notes remain. Evidence/draft:
`/mnt/raid0/llm/tmp/codex-hpr-raw-harvest-20261028/`.
Source wrap `0eed918d1dbe842d387d387b42ee027d750e538a` was pushed and owner
integration was observed as root `c61cf73670`. The separate HPR fixture-env
repair is already main `1d65cc0e2e893ffcdb001ad76dd7b4ed5c99f2e0`.
[belief: cc]

### USAGE provenance source

Reviewed source `c2650210ca1fe766c6ab62945ec9475ed6535c00` is integrated in
orchestrator main `4c1fbd2bfc1341e6861802bd10a6524b5fc433ff`. No deployment
or API reload. Final 359-test suite and lint passed. Source adds native-source
allowlisting, nullable reported/estimated/unknown accounting, request-local
ledger, cache replay custody downgrades, async context capture, 0600 append
files and fork-safe locks/FD closure/cleared copied usage. Persistence is
flush/write, not fsync. Budget enforcement and native source enrollment/
planning-context canary are not supplied by this source integration.
[belief: cc]

## Own repaired inference rows

### T96: native complete, outer postprocessor failed

The old failed attempt had three complete arms plus two of four cells in
its fourth arm; it never completed six arms. New source preserves it and
starts a fresh atomic ABBAAB comparison with verified descendant cleanup.
Actual same-launcher smoke began 19:40:11 on free/ungranted primary 48-49:
rc0, 74.491 s, two real HYBRID tiny-geometry iterations, writer/cleanup true.
This smoke does not establish normal T96/F32 pair completion or accuracy.
All 19 source pins match and canonical full model shard SHAs are attributed.

READY `rtg57-c5-vkq-t96-repair-20261028` was published 19:53; exact 0-95,
min 5100 / window 5700 s, 110 GiB. Keeper armed 20:09:42, controller 1831442,
official grant 20:09–21:44. Full run root:
`/mnt/raid0/llm/tmp/codex-rtg57-t96-repair-20261028/run-20261028T201026Z-1835607/`.
First benchmark PID 1853225 started 20:13:25 and was alive at the 20:15 audit.
The job later ended at 20:52:03 UTC: outer rc1 after all six native arms completed. Detailed failure/replay and limits are below. [belief: cc]

Peer timing disclosure is preserved prospectively in
`attempt-0/out/HOST_ACTIVITY_DISCLOSURE.json`: one unpinned `python3 -`
draft correction around 20:13:14.809 UTC, with unknown PID, duration,
affinity and RSS. Identity capture was 20:11:24.662; first process record
was 20:13:28.128. The timestamp lies in pre-native eviction/setup, but an
unknown lifetime does not exclude overlap or impact. No automatic sample
drop, regrade, no-impact assertion or rerun. The unchanged producer hashes
all out-directory files before its native receipt, binding this disclosure.

An additional peer disclosure reports `gitnexus impact main --direction
upstream --repo epyc-root` around 20:23 UTC, roughly 1-2 s, with uncaptured
PID/affinity/RSS and unknown impact. It is preserved separately in
`attempt-0/out/HOST_ACTIVITY_DISCLOSURE_GITNEXUS_2023.json`. Native second-arm
F32 PID 1898487 started 20:20:39 and was verified alive after the event;
the reported timestamp falls in that process lifetime. Exact cell/sample
overlap is unavailable. The first HYBRID/F32 pair is potentially affected;
no pair is automatically dropped, regraded or rerun. Both disclosures must
accompany any final descriptive timing conclusion.

A third peer note reports `git status --short --branch` in research around
20:27 UTC, about 0.2 s; PID/affinity/RSS and impact remain unknown. Separate
sidecar `HOST_ACTIVITY_DISCLOSURE_GITSTATUS_2027.json` records the nearby
second F32 process observation and latest row timestamp 20:25:37. Approximate
event boundaries do not identify a specific cell or exclude adjacent setup
overlap. Preserve all three notes; no automatic data removal or rerun.

### KPF64: READY armed; no full FB result

Completed F/E/EB and earlier partials are unchanged. New full FB starts
fresh and then runs existing F-FB analysis/pairwise emitters against F.
56,911.8 s is a token-scaled planning projection, not measured completion.
Requested 88,200 s / min 87,600 s on 0-23, 46 GiB; full FB/contrast remain open.

Actual same-launcher smoke began 19:41:40 after T96 released q2:
rc75/partial=true, 221.849 s wall, 204.511 s real-request span, 165 native
requests, no errors, writer/cleanup true; all 27 PID/birth entries absent.
It used a tiny synthetic corpus through the actual scratch server/replay
entry, not the experiment corpus. All 86 source pins match; canonical model
full SHA is attributed rather than redundantly re-read. READY was published
19:53 and armed 20:07:38, controller 1819555. No new full FB result is inferred.

Both rows passed the exact live-v5 read-only READY gate; row validators had
zero refusals and only the expected unarmed-BACKLOG warning. Claims released.
Root wrap is already pushed on `codex/t96-kpf-ready-20261028` at
`88a6aa22a65f8ce4206844e333cd825b105128aa` (four files, two checked prep
children, experiment parents open); index-check 0/citations/diff/hooks passed
before the timing notice, README emitted no warnings. Exact overlap of those
commands with grant startup remains unreconciled. Owner promotion is pending.
[belief: cc]

## Active failure / peer work

### META-ASSERT-1a: failed original smoke, no READY

Source 520ad4f55 is already on an experimental branch directly atop current
champion C5 c72ec82f5. Existing HIP Release/gfx90a instrument and libraries are
sealed; original build manifest verified, build mtimes postdate the fix,
and compiled foreign_host_view symbol was proven. No champion/frozen tree
or existing build was modified.

Original same-launcher full-suite smoke on 19:43:41 produced two complete
native rc0 runs, then a third rc1: qwen4exp/MI210/MoE NMSE vs CPU OK
(1.02e-13), roundtrip float-equality FAIL. Same run CPU roundtrip OK;
Meta NMSE OK/roundtrip SKIP. Overall 59.020 s/rc1, cleanup true, captured
PIDs absent. All three outcomes remain in
`/mnt/raid0/llm/tmp/codex-meta-full-arch-20261028/smoke-20261028T194341Z-1569442/`.
Two passes do not erase the third failure or qualify READY.

An isolated copied-test-only executable, linked to unchanged sealed
libraries/get-model object, adds mismatch bits/count/maxdelta, direct raw
weight comparison and fresh-original-context replay. GitNexus LOW test-only
impact; strings proved instrumentation compiled. Diagnostic ran 19:54:54,
62.361 s, six instrumented full rc0 runs, GPU released. In observed cases,
all 91 weight tensors and 16,384 logits compared identically. This did not
reproduce or explain the original intermittent failure. It is explicitly
not the original gate, not a clean original smoke and not READY. Evidence:
`diagnostic/smoke-20261028T195454Z-1692823/`; original artifacts unchanged.
Further heavy investigation was paused through the T96 timing boundary and may resume only on coordinated free resources.

### INF-12 / INF-33 — worker-reported facts, not task closure

INF-12 bounded smoke:
`/mnt/raid0/llm/tmp/codex-ni-inf12-g2-20261028/outputs/20261028T193252Z-1510374/STATE.json`
reports rc0, complete, 165 s, nonpartial, but cleanup covers direct child only
and descendants_censused=false. Gate2 remains open. Later STATE at
`20261028T200118Z-1754146` is internally inconsistent (rc0/wall0/no child,
status running) and is excluded from acceptance. Launcher/job remain at
that packet root; no readiness inferred from the inconsistent record.

INF-33 private patch:
`/mnt/raid0/llm/tmp/codex-hgdn-private-20261028/UPSTREAM-FUSED-RECURRENT.patch`,
SHA 03d19aca5b716c88042029838f3a8331ee1b06167cb888353bf9f0349f1c0c64.
Earlier three fixtures passed in 4.36 s before later grad/cache refusal
hardening. Those cases were initially held during T96. Post-release, the real upstream CPU-oracle fixture suite passed six cases in 4.32 s on CPUs 128-129 under the 32-33 mutex/caps. Log: `test-upstream-cpu-oracle-20261028.log`; fixture SHA `2a5a432eb520cceae07ab8db325d7220e46556927978c58e82ab4f9f988898a9`, upstream forward SHA `5910c0c23789384ebfb7e46aa8ab4c4dcfcbff662e21754ccf3d2d19ab848486`. Synthetic weights/dimensions and independent CPU recurrence seam only; no chunk/Triton, trained checkpoint, full HF package, ROCm or GGUF claim. Limits remain in PROVENANCE.txt.

### INF-34 — worker-reported failed final-source smoke, no READY

Private packet `/mnt/raid0/llm/tmp/codex-ni-inf34-dr3e-pgpu1-20261028`.
Final-source smoke `20261028T195804Z-1723280` failed outer rc2 after 146 s
on post-run host contamination. Both native arms completed/server rc0,
but the final guard saw new foreign llama-server PID 1749566 and ROCm
PIDs 1749421/1749530. No processes signaled; no throughput decision or READY.
Summary: `smoke/20261028T195804Z-1723280/runner-output/summary.json`;
log: `outputs/20261028T195804Z-1723280.smoke.log`.
The 19:36 source predates that final guard and is stale. Private source
remains uncommitted; model remained canonical, no private weight copy.
Any retry must recheck grant/lock and respect T96. Separate LOOP-11
pre-arm/orphan-cleanup claim/draft belongs to that worker.

## Private scheduler/class work: not deployed

Class gate lane:
`/mnt/raid0/llm/worktrees/mains/codex-ni-q3-class-arbitration-20261028`.
Kernel primitive 5 tests, real isolated canonical CLI 6 tests and canonical
lock/API 62 tests passed before timing. The bridge is inactive/private.
Fresh GitNexus rated canonical cpu_region_lock CRITICAL: 15 impacted
symbols, four direct callers, two serving flows/five modules. Source edits
and integration STOPPED on owner instruction. Review packet:
`/mnt/raid0/llm/tmp/codex-classgate-cgroup-20261028/REVIEW-BOUNDARY.md`,
blast-radius.json, tracked bridge patch and exact hashes.

Not established: complete serving/FIFO race coverage, derived booking-class
downgrade refusal, every direct entry migration and quiescence/adoption.
Existing serving APIs with external server work require careful ownership
review; descendant cgroups alone do not prove external server work drained.
No live policy, keeper, grant writer, queue or HOLD change occurred. The old
prototype remains unsafe for live use. Packet-local rearm log aliases are
already installed on owned packets without source-pin changes.

## Post-release wrap and remaining work

1. T96 terminal/cleanup and physical release were verified by the owner. Fix the failed postprocessor/launcher path before any next arm; preserve native evidence and use committed conclusions only unless producer-time warrant is proven.
2. Monitor KPF controller/grant/result; arming is not full FB completion. Scheduler remains sole grant writer and failures outrank new prep.
3. This isolated root branch contains the SSUF18 handoff/progress and periodic checkpoint. Source is already integrated; root owner handles generated index state and conflict-guarded promotion. No subagent index row edit or live-scratch cleanup.
4. Resume META failed-row diagnosis on a safely coordinated slot. Original intermittent roundtrip failure remains unexplained; no READY. Class work remains STOPPED pending explicit CRITICAL-impact continuation/adoption scope.

The coordination bus daemon PID 3327121 was dead at the last boundary;
zero routed action-required messages were owed. Direct parent/peer messages
are the coordination path. Shared scripts changes belong to other sessions
and remain untouched.

## Timing disclosure correction and expanded scope

Any earlier draft wording implying final SSUF18 validation preceded the
20:09 grant is withdrawn pending evidence. Its exact command, requested
130-131 taskset affinity, 45-pass/9.78 s log, related logs and source commit
are preserved in live
`attempt-0/out/HOST_ACTIVITY_DISCLOSURE_COORDINATION_UNBOUNDED.json`.
Actual test PID/start/end/runtime affinity/RSS were not captured. Reconcile
log/file/commit timestamps after release; do not infer a pre-grant interval.

That same sidecar preserves broader peer launcher drafts/HIL16 8.8 MiB copy,
parent read-only shell probes, this worker's ps/cat/stat and draft/annotation
writes, and the parent's further cat/ps continuation disclosure reported near
20:31:30 UTC. Clock is from the clock tool, not an additional shell probe.
Unknown intervals widen possible impact beyond the first pair; no arm/pair
is certified unaffected. No automatic data removal, regrade or rerun. All
further shell probes/prep stop until natural terminal/release.

Another parent continuation required an unpinned goal-attachment `cat`,
reported at 20:32:56 UTC (clock tool; exact command interval/affinity/RSS
uncaptured). It is preserved separately in
`HOST_ACTIVITY_DISCLOSURE_CONTINUATION_203256.json`, impact unknown.

Parent continuation also reported an unpinned
`ps -p 1831442 -o pid=,stat=,etime=` around the 20:42:20 UTC report clock:
controller live, elapsed 32:28. Actual probe interval/affinity/RSS unknown;
`HOST_ACTIVITY_DISCLOSURE_CONTINUATION_204220.json` preserves it. Controller
liveness is not a completed native result; no new native-arm scan occurred.

Parent then started one blocking Python pidfd watcher (exec session 46239)
on captured job PID 1835607 to replace repeated probes. Startup time,
affinity and RSS were not recorded; impact unknown. The one-time activity
is preserved in `HOST_ACTIVITY_DISCLOSURE_PIDFD_WATCHER.json`, reported at
20:45:17 UTC. It blocks without recurring scans. Parent verifies terminal
and physical release before work resumes; no additional observer is started.

## T96 terminal and postprocessor recovery

Official `.ended`: rc1 at 20:52:03 UTC, reason `job-rc-1:exited`, start 20:10:25. Job result: 2494.415 s, nonpartial, cleanup true; all 46 captured PID/birth entries absent and controllers 1831442/1835607 absent. The six native ABBAAB arms and 24 raw rows completed. Failure was afterwards: projector inferred PROTOCOL/SOURCES/driver paths from `run/attempt/out` depth and raised FileNotFoundError before writing its tuples or COMPLETE. No native benchmark failure is inferred from that outer postprocessor error. [belief: cc]

Original receipt SHA256 `894b2ae725a963f162589446f88491bdbba25c4858497804c5abe3b76ff7d634`. All 19 original source pins and captured canonical model full SHAs verified without rehashing model weights. All seven host-activity sidecars were producer-bound by the unchanged native receipt. The post-run SSUF timestamp reconciliation is separate, leaving hashed evidence unchanged: commit 833a2f4e is 20:12:25 UTC; final test-log mtime 20:12:25.137880288. Thus final SSUF validation did overlap the grant's pre-native setup. Exact start is not reconstructed from the 9.78 s duration. No no-impact assertion. [belief: cc]

Independent replay reproduces the native descriptive **COSTS** classification under the unchanged indicative -1% rule. F32-minus-HYBRID median throughput effects (higher is better): N1/8k -0.3920%, N5/8k +3.5216%, N1/32k -1.0950%, N5/32k +0.2812%. The N1/32k median crosses the native -1% threshold. Unbounded co-activity means no clean-window or unaffected-pair claim; no automatic pair drop, regrade or rerun. This does not establish F32 accuracy, production cost, carrier/adoption or a deployment gate. [belief: cc]

Private fixed reader: `/mnt/raid0/llm/tmp/codex-rtg57-t96-projection-recovery-20261028/projector.py`, explicit producer root or default script root, never output-depth inference. Six complete-writer regression tests passed in 0.177 s, covering nested default CLI completion and producer/rule/raw/disclosure tamper refusals. Original packet/source/receipt remain unchanged. `AUDIT.json` records the independent six-arm check.

Producer-time projected ClaimTuple proof is absent: original `projected-claims.json` is 0 bytes because the projector failed before tuple construction. No measurement ingest is authorized. Four post-run debug reader objects are `REPLAY-DEBUG-NOT-INGEST.json`, explicitly not backfilled measurements. Only the accepted contaminated descriptive conclusion enters via [belief: cc]. The failed-row launcher/postprocessor repair continues; no full benchmark repeat is required merely to recover retained evidence where the exact source contract validates it.

### T96 retained-data recovery follow-up

The isolated reader now resolves the declared producer root and passes six CLI completion/tamper fixtures. Local recovery completed with rc0 at `/mnt/raid0/llm/tmp/codex-rtg57-t96-projection-recovery-20261028/local-20261028T211601Z-2247614/result.json`; the exact task and evidence reconciliation is in the same packet's `TASK-RESOLUTION.md`. This recovery made zero new inference requests and did not rerun the benchmark. The original job remains rc1, the native six-arm result remains descriptive with unknown co-activity, and no measurement ingest, retroactive tuple, replacement original completion, or replay-only inference READY was created. Adoption and independent correctness gates remain open. [belief: cc]
