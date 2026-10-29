# AutoKernel concurrent target coordination — implementation handoff for review

**Status: PROPOSED — operator review; implementation and hardware launch NOT authorized.**
**Prepared:** 2026-09-14. **Parent:** [unified surface program](autokernel-unified-surface-program.md) (INF-73).
**Purpose:** finish resource coordination around the existing research loops so any supported CPU/GPU target pair can advance efficiently. This document owns this proposed follow-up; the parent retains its existing tasks.

## Start here

The operator selected **efficient overlap before dual launch**, rather than whole-batch serial rotation. Keep independent target preparation active while admitting expensive stages according to their actual resource footprints. Model names belong in example configurations and hardware acceptance results, never in scheduling branches.

This is a documentation checkpoint. Do not interpret open implementation tasks below, the parent's historical completion banner, or prior campaign launch permission as authorization to implement this proposal. The next action is operator review of this document. No implementation, builds, benchmarks, restart, or production promotion was performed in preparing it.

### Review checklist

- [x] CTC-DOC: capture generic requirements, current code seams, evidence limitations, and proposed acceptance criteria. ✅ 2026-09-14
- [ ] CTC-REVIEW: operator review the proposal and authorize a subsequent implementation session.

### Proposed implementation sequence (gated by CTC-REVIEW)

- [ ] CTC-1: derive stage footprints from recipes and preserve each target's execution adapter.
- [ ] CTC-2: add stage admission and remove conflicting whole-batch physical claims.
- [ ] CTC-3: extend the existing supervisor for concurrent target preparation and fair stage admission.
- [ ] CTC-4: extend original interval accounting and continuation recovery for multiple stage windows.
- [ ] CTC-5: integrate existing cold-load/hot-residency admission and evaluate coexistence applicability.
- [ ] CTC-6: preserve target histories, accumulators, anchor reuse and pruning through rollout.
- [ ] CTC-7: publish accurate per-target phase, waiting reason and resource ownership in the dashboard.
- [ ] CTC-8: complete focused integration and approved hardware acceptance; leave campaigns continuous after acceptance.
- [x] CTC-Q-A ✅ 2026-10-22 (validator on main, wired into every grant writer via grant_ok.sh by workspace-58, root 1740e3b19; first in-the-wild refusal kpf60-p0-gpu fixed by its owner): required QUEUE/booking fields `prior=<path|none, checked by whom>`, `decision=<one line>`, `min_effect=<% or count>`, `substrate=cpu|gpu|either` in `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md` rows and GRANT lines, with a ~20-line validator in `scripts/coordination/` run by the grant writer that rejects a grant whose row lacks them. (proposed to workspace-58/stage-3 2026-10-21; build A+B on agreement; source: `/mnt/raid0/llm/tmp/inference-backlog-audit-20261021/REPORT.md` §4)
- [x] CTC-Q-B ✅ 2026-10-22 (prior_check.py on main; its output path is the prior= field validate_fillers enforces at grant time): scripted zero-compute `prior_check.py`: given model + recipe/argv + metric, grep the belief ledger (`source_observed.assertion.applicability{recipe,build_sha,execution_digest}`), `/mnt/raid0/llm/tmp/*/RUN_RECORD.json|*.jsonl`, research `artifacts/` and AK campaign stores; its output path is the `prior=` field of CTC-Q-A. (proposed to workspace-58/stage-3 2026-10-21; build A+B on agreement; source: `/mnt/raid0/llm/tmp/inference-backlog-audit-20261021/REPORT.md` §4)
  - *(2026-10-22, f8; CTC-Q-A and CTC-Q-B stay open.)* `prior_check.py` and `validate_fillers.py` built on root `f8/prior-check` (49 tests passed, but run inside stage-3's quiet baseline, disclosed in `HOST_ACTIVITY_DISCLOSURES.md` and cleared by the floor sensitivity check); FILLERS.md column 6 is now peak host RAM GiB. Not landed on main and not yet wired into the grant writer.
  - [x] re-run the `f8/prior-check` tests and land the branch: `prior_check.py` + `validate_fillers.py` on main (`74b3cef5a`, `21954debe`, then `7d79e98ec`, `633771131`, `78d54c50b`, `32ddfd5c1`). ✅ 2026-10-22
  - [x] queue semantics "queued means ready" (2026-10-22 ruling) in `validate_fillers.py`: ready=y needs ARMED + live launcher pid; ready=n rows are BACKLOG with blocker+owner; REGISTERED/ready=n is an error; terminal rows (COMPLETE/CANCELLED) skip field checks; `min_effect` accepts `n/a (<reason>)`. Main `03a4b109d` + `a367d1df0` (operator D9 acks for `scripts/coordination/**`); rule text in `docs/guides/agent-workflows/compute-fillers.md`. ✅ 2026-10-22
  - [x] wire `validate_fillers.py --row <id> --for-grant` into the grant writer (no caller on main yet: only the doc and the module reference it), then tick CTC-Q-A/CTC-Q-B. (split 2026-10-22, f8 wrap-up) ✅ 2026-10-22
  - *(2026-10-22 13:15Z, workspace-58; NOT ticked, evidence inconclusive.)* The admission wrapper `/mnt/raid0/llm/tmp/compute-flags/grant_ok.sh <row> <GiB> [ds41]` (validate_fillers `--for-grant`, then ram_admit) is wired into `grant-akx-after-speech`, `grant-lb4-day`, `grant-locals` and `grant-q2-afternoon`. Two armed writers still call only `ram_admit.sh`: `grant-night-kpf64-20261022-v3.sh` (armed 12:39Z) and `grant-night-q2-20261022.sh` (11:44Z). The older evening chain writers end before the ~21:45Z re-plan.
  - [x] workspace-58: route `grant-night-kpf64-20261022-v3.sh` and `grant-night-q2-20261022.sh` through `grant_ok.sh` (re-arm with the old poller killed by PID) before the ~21:45Z re-plan; then tick the wire-in item above and CTC-Q-A/CTC-Q-B. ✅ 2026-10-22
    - *(2026-10-22 13:2xZ, workspace-58)* Wired: every live grant writer calls `/mnt/raid0/llm/tmp/compute-flags/grant_ok.sh <row> <GiB>` (validate_fillers `--for-grant` + ram_admit) before writing a grant. Night writers were re-armed: evening chain v10 (C2 re-run; the operator-requested gpu-cpu-noise experiment is RAM-admitted only), GPU chain v5, q2 v2, kpf64 v4; day writers since 12:25Z. First refusal in the wild: `kpf60-p0-gpu` (prior/decision/floor fields), returned to stage-3. CTC-Q-A/CTC-Q-B parent ticks are left to f8 (handoff owner).
  - [x] **CTC-Q-A2 — `grant_ok.sh` refuses a grant whose shape cannot run.** Two checks before the grant is written: (a) the grant's regions match the launcher's declared class (a `cpu+gpu` class needs `mi210_0` in `regions=`; a `gpu` class needs `mi210_0` and no CPU quarter unless the row says so; read the class from the FILLERS row or the launcher's `class=` log line); (b) the window is at least the row's min-window plus the poll margin (launcher poll interval + 60 s), not merely equal to it. Origins, 2026-10-22: c2-q38fn-b-rerun #2 refused rc=2 at 19:27Z (cpu+gpu launcher, `regions=0-95` grant; slot lost); kpf60-p0-gpu refused rc=3 (v6 window exactly 1800 s = its min, lost to poll lag). The night writers since 19:3xZ already add min+margin by hand; this moves both checks into the gate. Owner: workspace-58 (calendar owner). Done when both refusals reproduce as `grant_ok.sh` refusals in a dry run and every live writer uses it. (filed 2026-10-22, workspace-58 wrap-up) ✅ 2026-10-29 (audit: compute-flags/grant_ok.sh header documents --window-s >= min-window+300 and --regions class match (L10-13); test_grant_ok_v2.sh present; docs commit 8a73e2bbc) [no-belief: audit-reconciliation]
    - *(2026-10-23 14:0xZ, workspace-58 wrap-up; NOT ticked, the gate is unchanged.)* Third reproduction of check (b): `s5-rtepfx2-stagger` refused rc=3 at 06:45Z, because block writer v1 gave it a 2626 s window against its 2700 s min-window. That was the calendar owner's error, the same defect as kpf60 on 10-22. Mitigation the same day: every live writer was audited at 07:0xZ for window ≥ min-window + 300 s (all OK), and the re-run got 3000 s and completed 09:55Z. The live `/mnt/raid0/llm/tmp/compute-flags/grant_ok.sh` (942 B, mtime 2026-10-22 11:54Z) still runs only `validate_fillers --for-grant` + `ram_admit`, so neither check is in the gate yet. It is untracked (no copy in git), so the fix is a versioned copy beside it plus a tracked source under `scripts/coordination/`. Owner: workspace-58 (calendar owner); this wrap-up subagent does not edit `compute-flags/`. Related, from the same day: an owner-side double claim can also look like a grant-timing refusal (kpf18-item3 rc=75, below in `compute-fillers.md` owner duty 28). Check (a)'s class-to-regions match would not catch that one.
    - *(2026-10-23 15:3xZ, workspace-58 wrap-up; box stays open.)* IN PROGRESS: a workspace-58 subagent is building grant_ok v2, which adds checks (a) and (b) above, together with CTC-Q-C.1. It lands as a versioned copy beside the live `compute-flags/grant_ok.sh` plus a tracked source. Not landed at this checkpoint.
- [x] CTC-Q-C: derive the booking class from the decision, not by default: QUIET only if `decision` names a champion/candidate baseline or a keep gate with a cited quiet floor file; TIMING-PAIRABLE if indicative; CORRECTNESS otherwise; the grant writer sets the gpu-quiet claim from the class. (proposed to workspace-58/stage-3 2026-10-21; build A+B on agreement; source: `/mnt/raid0/llm/tmp/inference-backlog-audit-20261021/REPORT.md` §4) ✅ 2026-10-22
  - *(2026-10-22, workspace-f8; operator D9 ack via AskUserQuestion.)* Landed root eb5e162ee: `scripts/coordination/validate_fillers.py` `derive_booking_class` (quiet = champion/candidate baseline or keep gate with a cited floor file, or a row that measures a floor for a named build; pairable = indicative/timing; correctness otherwise), a declared class stricter than derived is REFUSED under `--for-grant`, `--print-class <row>` for grant writers (interface `/mnt/raid0/llm/tmp/ctc-q-c/INTERFACE.md`; only block-timing-quiet sets the gpu-quiet claim); 70 tests. workspace-58 cut the live copy over at ~21:00Z from `git show origin/main:` (backup validate_fillers.py.bak-pre-ctcqc-20261022), reclassified s5-hsprof1-beam-reader / s5-cme7-poker-smoke / s5-stackup-bundle to block-correctness; whole-file run 79 rows, 0 refusals. No quiet window moved.
  - *(2026-10-22 late evening, workspace-58 wrap-up; derived observation.)* At the 21:0xZ cutover, the `/workspace` shared-clone working copy of `validate_fillers.py` was 68 lines behind origin/main because the shared clone's checkout was stale. Re-checked at this wrap-up: the shared clone is at `796a77e06`, which contains `eb5e162ee`. Its copy now matches HEAD (407 lines, no diff), so the lag has resolved. Nothing filed, for two reasons: the live grant path (`compute-flags/grant_ok.sh`) runs the `compute-flags/` copy, and the shared clone's checkout is advanced by its owner sessions.
  - [x] CTC-Q-C.1 grant writers read the class via `--print-class` and set `--gpu-quiet` from it (workspace-58 adopts it in new writers from 2026-10-22). ✅ 2026-10-29 (audit: compute-flags/grant_ok.sh references validate_fillers.py --print-class and gpu-quiet derivation (L13-15); commit 8a73e2bbc "CTC-Q-C.1 class") [no-belief: audit-reconciliation]
    - *(2026-10-23 15:3xZ, workspace-58 wrap-up; box stays open.)* IN PROGRESS: in the same grant_ok v2 subagent as CTC-Q-A2 (class from `--print-class` sets `--gpu-quiet`). Not landed at this checkpoint.
- [ ] CTC-Q-D: sweep-merge pass at registration: list rows with the same (model, build, argv-hash) or the same DS41-class server; a new row must join that session (shared load/anchors) or state why not. (proposed to workspace-58/stage-3 2026-10-21; build A+B on agreement; source: `/mnt/raid0/llm/tmp/inference-backlog-audit-20261021/REPORT.md` §4)
  - *(2026-10-26, ws58.)* registration sweep checker merged 688973660; live integration not active.
  - [x] **CTC-Q-D-PREP — prepare and control-test the owner registration and grant integration.** MAIN accepted the sealed [source packet](../../artifacts/coordination/ctc-qd-registration-20261027/README.md); native export, registration, recovery, both writer, race and atomic grant controls passed on private fixtures. ✅ 2026-10-27 [no-belief: operational source preparation, no measurement] The parent stays open: WS58 must bind producers and source custody, review cutover and adopt at a writer-restart boundary; UNKNOWN peers remain visible and live integration is not established.
- [ ] CTC-Q-F: gating probe first by rule: any booking with a numeric bar lists a <=30-min pre-check whose failure cancels the block; the launcher runs it first and aborts (e.g. the 7b AK Q38FN SPEC has a test-backend-ops pre-check but needs the TOP_K share measurement and the abort). (proposed to workspace-58/stage-3 2026-10-21; build A+B on agreement; source: `/mnt/raid0/llm/tmp/inference-backlog-audit-20261021/REPORT.md` §4)
- [x] CTC-Q-G: filler_run2: exit after one window unless --repeat; refuse to delete a grant held by a running sibling. Hazard seen 2026-10-22 in `/mnt/raid0/llm/tmp/fillers-3c4ca599/filler_run2.sh`: launchers keep polling their grant id after their window ends, so a re-written grant is taken by a stale launcher, and a second launcher then writes a bogus `refused:own-port` `.ended` that deletes the live grant. Fix on a copy (never edit the running script); test with two launchers on one grant id. (filed 2026-10-22, f8) Done ✅ 2026-10-22 (3c4ca599): `/mnt/raid0/llm/tmp/fillers-3c4ca599/filler_run5.sh` (new copy of filler_run2.sh, CLI identical plus `--repeat`); dry-run `dryrun5_out.txt` beside it proves kill-then-immediate-re-arm succeeds (filler_run2 control fails), one-launcher-per-id holds, a running sibling's grant is left untouched, one-window exit and `--repeat`, rc2/3/4/124, complete and class gpu unchanged. Documented in `docs/guides/agent-workflows/compute-fillers.md` owner duty 6.
- [x] CTC-Q-H: fix the `filler_run*.sh` lock inheritance in a NEW launcher version (never in place): start the poller's `sleep` with the lock fds closed (`sleep 45 8>&- 9>&-`) so an orphaned sleep cannot hold the launcher lock after the poller is killed (seen twice 2026-10-22; owner duty 6 in `docs/guides/agent-workflows/compute-fillers.md`). (filed 2026-10-22, 3c4ca599) Done ✅ 2026-10-22 (3c4ca599): `/mnt/raid0/llm/tmp/fillers-3c4ca599/filler_run5.sh` (new copy of filler_run2.sh, CLI identical plus `--repeat`); dry-run `dryrun5_out.txt` beside it proves kill-then-immediate-re-arm succeeds (filler_run2 control fails), one-launcher-per-id holds, a running sibling's grant is left untouched, one-window exit and `--repeat`, rc2/3/4/124, complete and class gpu unchanged. Documented in `docs/guides/agent-workflows/compute-fillers.md` owner duty 6.

## 1. Outcome, constraints and non-goals

One supervisor manages independently progressing CPU and GPU targets. While one target waits for a remote planner/critic or edits a candidate, the other may compile, profile or measure when resources permit. The supervisor must not hold all hardware for idle preparation.

The implementation must be agnostic to model identity, quantization, source commit and recipe name. It supports models already executable through installed adapters; it does not promise support for every architecture or accelerator. Current ROCm0/mi210_0 limitations are hardware-adapter limitations and must remain explicit.

Preserve the existing planner/critic, source mutation, profiling, screen, confirmation, accumulation, serving gates, source validation/LOO, journal recovery and anchor pruning. No replacement planner, general workflow framework, new statistical grading rule or new production-promotion authority is part of this change.

Efficient preparation overlap is mandatory. Simultaneous CPU/GPU measurements are conditional on recipe-specific evidence and existing admission authority. They are neither universally enabled nor universally prohibited. No numerical throughput speedup is promised before observing stage durations.

## 2. Current structure and concrete gaps

The research code inspected is in `/mnt/raid0/llm/worktrees/mains/autokernel-unified-research-20260908`, at `5ac7b7e47c52f6fe8ce2db4aca99679374d0652f` during this review. All paths below are relative to that research repository unless marked root. Re-resolve symbols against the implementation checkout before editing; line numbers and running campaign tips change.

| Current component | What it already does | Required narrow change / trap |
|---|---|---|
| `scripts/kernel_rnd/autokernel/loop/serial_roster.py:build_targets` | Builds target argv from enrolled targets plus owned source/build/request paths; checks independent roots and attaches shared history | Preserve target adapter choice. Currently generated targets use explicit CPU/GPU serving launches; this is not automatically equivalent to the historical GPU screen workflow. |
| `loop/legacy_targets.py:validate_resources` | Validates a target against owned CPU/GPU resources | Returns all declared CPUs, not the stage's footprint. Separate allocation validation from footprint resolution. |
| `loop/run.py:main` | Acquires CPU/GPU claims in an outer `ExitStack` before profiling and `run_pooled()` | Replace whole-batch physical claims in coordinated mode. Adding inner locks underneath them would deadlock or preserve over-exclusion. |
| `loop/run.py:gate_for`, `measure_for`, `reprofile`, `build_champion`, `confirm_measure` | Own actual compilation, correctness, profiling, comparisons and anchor maintenance | Place admission at these real execution boundaries, including callbacks reached during promotion/guard repair. |
| `loop/pool.py:drive` and pipeline tail | Parallel formation with serialized target-local execution/commit | Keep target-local ordering; cross-target admission must compose with it without locking during actor calls. |
| `loop/serial_run.py:_drive` | One `state['active']` child, target selection, continuation/recovery and required source validation | Add active children keyed by stable target identity and parent-owned admission; preserve single-target compatibility. |
| `loop/scheduling.py` and `loop/serial_scheduling.py` | Opportunity selection and held-resource accounting | Selection explicitly is not execution permission. Keep actual admission separate, serialize accounting updates in the parent. |
| `loop/claim.py:hold_cpu`, `hold`, `publish_intervals` | Existing region/device locks, real `HeldCpuClaim` observations | Stage claims need repeated intervals. `publish_intervals` currently permits only 1–2 contexts. SMT folding must be correct at actual acquisition, not just validation. |
| `loop/serial_scheduling.py:reopen_held_receipts` | Reads one CPU interval with at most one nested GPU interval | Extend for multiple stage windows; do not flatten gaps into held time. |
| `execution/inference_window.py` | Shared flock; windowed spawner and a specialized borrowed-CPU-coverage path | Reuse exclusion primitive where applicable. Borrowing expects a special role/payload absent from current `loop.claim.hold_cpu`; renaming the role alone is not sufficient. |
| `controller/gpu_hot_residency_runner.py` and `gpu_load_admission.py` | Cold serialized/overlap admission and exact persistent-session reuse | Loader window is released after positive residency proof. Preserve device ownership while the session remains resident. These seams are not evidence that current loop callbacks already use them. |
| `loop/serving.py`, `bench.py`, `cpu_profile.py`, `hotspots.py` | Actual server/bench/profiler execution | Audit direct subprocess paths; protect complete instrument lifecycle, not only the most visible spawn. |

**Profiling compatibility is load-bearing.** `run.py:build_context` and `reprofile` explicitly report that selected GPU serving profiling is unavailable; legacy GPU screening does call `hotspots.profile`. Scheduling must not migrate an established GPU target to the unprofiled route merely because it is easier to roster. The historical screen → confirm → serving-gate adapter must remain selectable with its original model/surface/pair configuration. Other models configure their own supported workflow.

**Runtime owner compatibility is load-bearing.** `install_runtime_owner`, runtime restoration and source LOO consume concrete `original_claims` objects. Stage scoping must give them current held contexts at execution time. Do not retain a released claim inside a long-lived owner or fabricate a still-held wrapper. Review `runtime_admission.py`, `runtime_calibration.py`, `direct_gpu_control.py`, `direct_historical_control.py`, and `source_loo.py` at these call sites; retain recipe/evidence state independently of ephemeral leases.

## 3. Model-independent target and footprint contract

Reuse `CanonicalResolvedRecipe`, enrollment and existing owned-target records. The supervisor's concurrency option is `--max-active-targets`, default `1`; acceptance uses `2`. No CPU target named GLM or GPU target named Qwen is built into the implementation.

For each stage resolve: target identity, original attempt/batch identity, selected source/build, instrument and recipe identity, logical CPU affinity, physical region set, memory placement, GPU devices, and bounded build jobs where applicable. These values come from existing records rather than a second model registry.

Allocation validation proves a footprint is contained in owned resources. Runtime footprint resolution chooses the recipe's actual CPUs; build footprint uses the declared build allocation. Verify child affinity rather than relying only on parent affinity. Include main model, drafter, offloaded work and helper processes in the stage footprint. Unsupported mixed-device/offload configurations retain their existing explicit refusal rather than being labeled GPU-only.

Fold logical SMT siblings into the same physical region using the existing topology helper. A GPU helper thread on logical 184 is not disjoint from a CPU worker on physical 88. A full-region CPU claim therefore conflicts with such helpers. A reduced partition is a different recipe; preserve full-target confirmation and existing mechanism-transfer requirements.

Target-local mutable state remains separate. Sharing Git object storage or reading historical records does not grant shared branch/worktree mutation. Preserve existing cross-target source validation and LOO obligations; independent preparation must not race a source-assembly or promotion transaction.

## 4. Admission lifecycle and minimal supervisor extension

Keep existing loop callbacks and add a coordinator-supplied stage context. Conceptual interface: `stage(kind, target, attempt, footprint)` yields currently held claim objects and closes them after verified teardown. It is infrastructure called by trusted execution code, not planner-authored resource authority.

The existing parent supervisor owns the ready-stage queue. Use a local parent/child control channel scoped to the launched child; bind requests to the parent's captured child identity and original target/batch. Messages need only request, grant, release, cancellation and status; reuse installed IPC/lifecycle helpers where applicable. The implementer must not create a second scheduler daemon or a new externally exposed service for this seam.

Default admission order is FIFO among compatible ready requests. If the oldest request conflicts with current activity, independent compatible work may proceed, but repeated new conflicting work cannot jump ahead of it. A target has at most one running batch and one outstanding heavy-stage request for the initial implementation. Existing opportunity budgets still govern which target gets its next batch; queue waiting itself is not a spent hardware opportunity.

Acquire coordinated admission first, then physical CPU regions in canonical order, then device claims. Acquisition is transactional: release partial claims before retrying an unavailable external resource. Do not wait holding the GPU while requiring CPU regions held by the other target. The actual flock/provider claim remains the ownership fact, regardless of a scheduler grant.

| Stage | Claim lifetime and initial coexistence |
|---|---|
| Remote planning/criticism and ordinary source edits | No physical claim. Keep target-local source ownership and existing author restrictions against manual local builds/inference. |
| Configure/compile/link | Existing single build slot and actual pinned CPU footprint. Exclude this program's CPU measurements. GPU overlap only under applicable existing coexistence evidence. |
| Cold model load/repack/NUMA placement/warmup | Acquire before the first operation; treat host-memory effects as part of the stage. Default serialize with sensitive peer measurements. |
| Profile/correctness/calibration | Separate queued stages using their real backend footprints and instrument lifecycle; never perform them silently during a peer's measurement. |
| A/B and confirmation | Hold through the owning instrument's indivisible matched unit, warmup and teardown. Initially protect the complete comparison call; split only where the existing protocol explicitly supports interruption between blocks. |
| Persistent GPU session between requests | Keep device/residency ownership while memory remains allocated; host admission may be released if background behavior and the existing contract permit it. Never advertise the occupied GPU as free. |
| Promoted-anchor build/guard/rebaseline/LOO | Use the same admission seam; preserve original order and guards. Source mutation/publication remains serialized within its owner. |
| Large copy/hash/prune/repack | Include consequential host work in admission so a supposedly idle target cannot poison its peer through maintenance. Small status/journal writes need no heavyweight lease. |

Stage timeout starts on admission, not when waiting begins. Waiting publishes `waiting_resource` and heartbeat. A stop removes pending requests and lets already-running work follow the instrument's existing drain behavior. Parent restart reconciles known children and outstanding grants before issuing replacements. Unknown cleanup blocks only conflicting hardware work; the healthy peer may continue preparation.

Do not hold a cross-target physical lease through actor calls. Nested target callbacks must reuse the current compatible lease or explicitly close it at a safe boundary; they must not reacquire the same exclusive lock through another file description.

## 5. Resident GPU overlap: evidence and proposed evaluation

The earlier draft's blanket requirement that all CPU/GPU measurements never overlap is withdrawn. So is the suggestion that contention can automatically be absorbed by a higher champion floor.

The source distinguishes `cold_serialized`, `cold_overlap`, and `hot_resident`. `HotResidencyRunner._cold_start` protects loading and residency proof, then releases the load window before returning the session. This establishes an available implementation seam, not a measured guarantee for all resident workloads.

Historical evidence to inspect:

- Root `progress/2026-09/2026-09-08-ak-rebuild-20260828.md`, especially the early contention report and later qualifications: CPU scatter 0.80% → 7.223% during the GPU seed chain; adjacent quiet/concurrent subsets 0.509%/2.151%; GPU floor 3.536% → 10.255% with concurrent CPU activity. These are differently scoped subsets and instruments, not a single universal multiplier.
- Root `progress/2026-09/2026-09-05-inf70-audit.md`: sibling overlap correction and MTP outlier observations. Earlier disjoint-core interpretations were wrong.
- Parent handoff §3.4, §8.7 and §8.17: measured contention, recipe-specific coexistence and later correction of blanket foreign-load vetoes.

The reviewed records do not isolate the impact of already-loaded, persistent GPU inference with physically disjoint host cores on a simultaneous CPU measurement. Active GPU dispatch can still use host cores, memory and fabric; its magnitude is unmeasured here. Idle residency and active inference must be distinguished.

CTC-5 first searches existing applicable coexistence records. If none fits, a subsequently authorized hardware check uses the actual target recipes and compares: CPU alone, GPU alone, CPU with the GPU resident but idle, and both actively measuring with disjoint physical host placement. Warm and prove residency before the overlap interval; annotate any load/reload separately. Observe both targets' throughput/variance and in-window placement, host pressure and residency. Preserve randomized/counterbalanced units and sample counts required by the owning protocol; do not invent numerical acceptance bands in this document.

Bind eligibility to recipe/instrument/placement and neighbor-envelope identities using the existing admission provider. A successful pair does not certify arbitrary models, changed concurrency, runtime knobs, partial offload or third-party neighbors. Loss of persistent identity routes back through cold admission. A fresh-process benchmark remains fresh-process: replacing it with a persistent server is an instrument change and outside the scheduling patch.

If no ratified acceptance rule can authorize overlap, record the finding and keep physical measurements serialized while preserving preparation overlap. Selecting or amending such a rule is a specific operator decision; it does not prevent implementing the basic concurrency path after CTC-REVIEW.

## 6. Noise floors and validity

Stable, explicitly declared coexistence can define a distinct measurement environment with its own prospective calibration. It does not automatically establish performance under quiet production conditions. Conversely, unexpected asymmetric contention cannot be repaired after the fact by widening the acceptance threshold.

Apply the instrument's existing invalidation/rescheduling and evidence-use rules. Preserve usable completed data at its original unit; do not rerun whole batches unnecessarily or add an estimator. For strict matched comparisons, keep conditions common across arms. For A2 discovery, parent §8.17 records that ordinary foreign builds/agents/load are recorded noise, not a new refusal condition. Scheduling our own jobs is distinct from policing unrelated sessions.

Reuse calibration if its complete identity and validity still match. Recalibrate when the instrument's rules require it after a changed anchor, recipe or environment. Do not require a fresh A/A on every queue handoff, automatically copy a historical floor into a changed instrument, or discard a valid floor solely because a supervisor restarted.

## 7. Accounting, continuation and target-state migration

`claim.publish_intervals` and `serial_scheduling.reopen_held_receipts` currently accept one CPU context and optional GPU context. Add a versioned multi-window representation while retaining v1 readers. Each stage window retains original acquisition/release observations and target/batch binding. A GPU interval must remain nested inside its host coverage; a device residency interval spanning requests is distinct from host execution intervals.

Sum actual held-resource intervals, preserving gaps and device-only residency. Charge no physical time for remote actor waits or queue waits. Handle a formation-only batch with zero heavy windows as a real recorded refusal, not missing evidence or fabricated resource usage. Settle each research attempt once despite several stage receipts. Close and persist each window as it ends so a later crash cannot erase completed evidence.

`serial_run._drive` currently has a single `active` slot. Extend state with active records keyed by stable target identity, plus pending admission and per-target continuation references. Version state explicitly; read existing single-active state as one entry. Parent serializes state/accounting updates even when children finish out of order. Never overwrite an unresolved active child or apply one target's continuation to another.

The current config digest rejects changing the roster in place. For rollout, drain the existing router at a completed batch boundary and create a new router state with explicit references to verified completed target continuations. Preserve writable target stores and original evidence; do not edit a config digest to bypass checks. Imported continuations keep their original bindings, with a recorded routing transition rather than rewritten historical argv.

For an added target, use its authoritative source lineage, anchor and COR metadata. Reuse verified immutable builds where valid; allocate separate writable workers/builds. Historical stores are read via `archive.SharedHistory`; do not copy/regrade experiments or replay keeps twice. An externally advanced stale bundle follows the established recovery/reconciliation procedure, not an unconditional fresh benchmark or empty accumulator.

Keep `pool.promote_anchor` and `prune_anchor_generations` semantics. Protect live anchor/COR and any still-referenced builds; release temporary builds once existing retention rules permit. Separate target stores must not cause indefinite duplicate build retention or unconditional regeneration of previously measured anchors.

## 8. Dashboard and belief integration

Extend existing status producers in `loop/status.py`, `heartbeat.py`, `run.py` and the serial supervisor. Root dashboard ownership remains `dashboard/` under the existing plane rule. Reuse the current autokernel registry page; no additional dashboard service.

For every target show phase, last heartbeat, waiting reason/resource owner, active attempt, current accumulator and continuation state. Show persistent GPU occupancy separately from active measurement. A queued target is live and waiting, not stopped or stale. The supervisor heartbeat cannot conceal a dead target producer. Keep existing plot and history consumers intact.

If implementation emits new coexistence measurements/findings, wire them at production time through existing native evidence and belief export. Register the source in root `scripts/vidya/adapters/README.md` and a task in `handoffs/active/vidya-belief-substrate-program.md` when that producer is introduced. Reuse ClaimTuple grading; scheduling receipts are not performance claims. This documentation-only handoff introduces no new measurement producer.

## 9. Focused verification and acceptance

CTC-1–4 tests should exercise real callback boundaries with fake children, not reproduce implementation internals. Existing tests remain authoritative for accumulators, continuation binding, anchor guards and pruning.

| Acceptance case | Required evidence |
|---|---|
| Generic targets | At least three synthetic model identities and different affinities produce footprints from recipes; swapping names leaves scheduling decisions unchanged. |
| Workflow preservation | Enabling coordination preserves CPU instrument and GPU profile → screen → confirm → serving-gate configuration, pair counts and promotion rules. |
| Useful overlap | Two slow actor phases overlap; one target performs admitted hardware work while its peer is preparing. Whole-batch serialization fails this test. |
| Exclusion and fairness | Owned CPU measurement/build conflict; pending request is not starved; partial claim failure releases resources. |
| Hidden work | Profile, calibration, correctness, promoted-anchor rebuild and guard calls all pass through admission. |
| Hot session | Load and proof precede overlap; idle residency remains owned; identity loss forces cold admission; absent coexistence authority prevents active overlap. |
| Recovery | Stop while queued, crash in a stage, out-of-order target completion and router restart preserve original outcomes and prevent duplicate children. |
| Accounting | Multiple and zero-window batches settle correctly; queued time is excluded; old records still read. |
| Accumulation | Sub-noise positive accumulation, full-target confirmation, COR advancement, required-target gates and bounded pruning retain their existing behavior. |
| Hardware after authorization | Current GLM CPU and Qwen GPU examples each complete at least two valid A/B paths; observe ten stage handoffs, preparation overlap, accurate live dashboard and external GPU residency evidence. A measured null is acceptable loop-health evidence. |

Hardware validation is an observation milestone, not a stopping limit. After an approved implementation and launch, leave the supervisor continuous until operator stop or an existing declared resource/budget stop. Existing budget rollover and per-target failure policies must not silently convert unlimited operation to a fixed batch count.

## 10. Review boundaries and rollout examples

The live CPU campaign observed during planning used `/mnt/raid0/llm/tmp/aku-glm53-continuous-20260912-v7` and `/mnt/raid0/llm/tmp/aku12a-glm53-five-loop-store`. The historical GPU store is `/mnt/raid0/llm/autokernel/loop-memory`. These are discovery pointers only; re-read their current state before any future rollout.

Earlier examples cited Qwen tip `ef81196d5`, COR `445e93a8`, tg128 screen/confirmation and DFlash2 serving. They describe that campaign's history, not generic defaults or required future commits. The enrolled production alias `architect_general@8083` describes a different serving recipe (native MTP/np2 in the inspected export) from the historical DFlash2/np4 gate. Do not substitute it based on matching model name. Resolve the intended research workflow and artifacts explicitly from that campaign's retained configuration.

Still subject to review: the staged concurrency proposal, its FIFO admission behavior, and any measured-overlap policy not already authorized. Explicitly outside this follow-up: new model architectures, a new GPU serving profiler, instrument conversion, generalized multi-host scheduling, and rewriting measurement governance. Those are not prerequisites silently added to this work.

The previously reported LOW GitNexus impact on `_drive`, `hold_cpu` and `publish_intervals` is only a static callgraph observation. Closure callbacks and runtime claim consumers above show why it is not a correctness assurance. Re-index the implementation checkout and review these consumers before editing.

- [ ] GPUQUIET-WRITER-PREFERENCE: gpu-quiet EXCLUSIVE starves under AK lanes' back-to-back shared claims (timed out at 600 s on 2026-10-07 02:42Z, FIFO off). Needs FIFO default-on or writer preference. Owner: workspace-ec, coordinate with workspace-89. Done when an EXCLUSIVE acquire succeeds within its timeout while AK shared lanes are running.

### 2026-10-28 INF-74 / RUN14 joint gate result - no deployment

- Private direct-gate cross-contract controls passed (unresolved matching-peer refusal at registration and grant including a forged recomputed receipt, explicit separation, stale-catalog refusal), plus 53 existing integration controls; synthetic controls only. The joint RUN14/NI interface audit then reproduced a same-UID child escaping the proposed cgroup (`cgroup.procs` empty while the child lived), false acceptance of asserted `attachment_fenced=true`, an owner-death/pidfd-check-to-spawn race, and region/publication-lock self-block. So `MUTATORS_SHARE_LEASE=false`; no live deployment is safe. Before reconsideration: protected cgroup authority or proven equivalent, an owner-bound grant -> quiet -> receipt handoff, and tests proving descendants cannot escape and cleanup/lock release is verified. Fixture children all reaped. Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261028-coordination/inf74-0303.txt`, `gpu-fence-defect-0306.txt`, `/mnt/raid0/llm/tmp/refactor-01a16fc3/gpu-lock-handoff-20261028/RUN14-NI-INTERFACE.md`. No deployment or checkbox claim. [belief: cc]
- [ ] **INF-74-CGROUP-ROOT — land the root-owned cgroup delegation script.** (filed 2026-10-28, workspace-58 wrap-up) Operator chose root-owned cgroup delegation as the fix for the same-UID descendant escape above. Codex delivers the script (operator runs it, it is a protected-authority change); then add the escape/cleanup tests named above and re-run the INF-74 gate before any cutover. Cutover stays rejected until this box and the owner-bound grant→quiet→receipt handoff land. [no-belief: not-a-result]
