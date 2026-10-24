# Incident ledger, 2026-10-21 .. 2026-10-23

Every rule in SKILL.md section 4 was paid for by one of these. Source: the append-only REVISION
log in `/mnt/raid0/llm/tmp/compute-calendar-20261021.md`, `compute-flags/*.log`, and the owner
duties list in `docs/guides/agent-workflows/compute-fillers.md`. Times are UTC.

| When | What happened | Cost | Rule it bought |
|---|---|---|---|
| 10-21 day | W6.1, DS41 ABA segment B and PB-HOL-1 D1 ended early; END-only watchers, nobody noticed | repeated idle CPU | watch STEP boundaries; peers write `<block>_FREED`; keep a short filler queued |
| 10-21 | `calibrate_served_shapes` (self-claiming) wrapped in an outer `region-lock run` | 1 h deadlock | check whether a tool claims regions itself before wrapping it |
| 10-21 ~16:00 | two DS41-1017 servers at once; earlyoom killed 13 processes incl. 3 Claude sessions | sessions lost | ONE DS41-class server host-wide; `ram_admit <gib> ds41`; RAM is a booked bin |
| 10-21/22 night | CT-18 HTTP 400 (37.5k-token fixture vs 32k ctx), chunk-KV/speech `rc=64`, D4 `rc=125` sat unnoticed | GPU idle ~22:15-06:30 | every owner watches its own jobs; why → fix → re-queue without waiting |
| 10-22 05:19 | FREED watcher died on a zsh no-match glob | CPU idle 70 min | watchers are bash files keyed on mtime (`find -newer`) |
| 10-22 09:33 | `v11-arm-builds` FAILED rc=12 (cherry-pick conflict) | V11 GPU items blocked | builds first, in their own lane; the test's `--precond-cmd` re-checks at grant time |
| 10-22 09:5x | `f8-day-q0` rc=2: bare `python3` under region-lock resolved to the orchestrator `.venv` 3.11 | slot lost | explicit interpreters under region-lock |
| 10-22 10:03-10:43 | `akx-all-27b-run` inner claim (gpu-quiet excl + q0-q3) exceeded its row; `rc=75` | MI210 idle 40 min | inner claim must match the row's resources |
| 10-22 12:24-12:45 | q3 build granted while a GPU job's 184-191 claim folded to q3 | MI210 idle 21 min | never grant q3 under a folded GPU job; GPU jobs choose no-fold or get q3 kept free |
| 10-22 12:44 | region-lock `--no-fold-siblings --cpu-list 184-191` → "maps to no regions", rc=1 in 4 s | GPU idle again | GPU-only = gpu-quiet claim with no CPU region, job tasksets itself (`filler_run6+`) |
| 10-22 12:50 | ungranted second-ASR job started on q2 by a subagent | foreign claim | every model execution (ASR/TTS too) needs a row and a grant |
| 10-22 16:47 | old `grant-f8-gitnexus` early branch granted q0-q3 25 s before chain v11 granted the whole host to the noise run; session aborted | quiet run lost | one live writer per region set; retire every superseded branch; fallbacks never fire while the predecessor holds the regions |
| 10-22 17:0x | 1 of 196 llama-server tasks (early ROCr thread) escaped `taskset 184-191` | residency false-pass | re-pin all tasks / `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0`; check every `/proc/<pid>/task/*/status` |
| 10-22 19:27 | `c2-q38fn-b-rerun` launcher `--class cpu+gpu` refused the `regions=0-95` grant (`rc=2`) | quiet slot lost in 30 s | launcher class must match the grant shape; `filler_run8` cpu + gpu-quiet exclusive + claim-cpus |
| 10-22 19:28 | `kpf60-p0-gpu` window exactly its 1800 s min; poll lag → `rc=3` | slot lost | window ≥ min + poll + 60 (300 s in practice) |
| 10-22 19:36 | NEW-10 smoke ran Q38FN without its registered serving env; fused-decode repack bug aborted it | run lost | quality jobs copy the role's serving env from `model_registry.yaml` |
| 10-22 22:3x-05:5x | owner session rate-limited; last queued job ended 02:13 | host idle 4-5 h | book chains to the END of the night with backlog depth |
| 10-23 00:40 | `kpf18-item3-v2-sameshape` rc=75 47 s after the previous GPU job's `.ended` | first blamed on grant timing | writers now wait for claims/flocks to RELEASE; **correction 11:4x:** the job's own engine double-claimed its mi210_0 flock, so the practice stays but the incident was the job's |
| 10-23 06:45 | `s5-rtepfx2-stagger` given exactly its 2700 s min by block writer v1 → `rc=3` | slot lost, second time | the margin goes in the writer's `step()`, not in memory; audit every live writer |
| 10-23 07:0x | block writer v1 had an `EXIT` trap writing `BLOCK_..._ENDED`; stopped with SIGKILL | (avoided) | SIGKILL writers with done-flag traps; version, never edit, a running script |
| 10-23 07:2x | block writer v2 waited on ALL claims while a no-fold GPU job co-ran | CPU block stalled | claim-wait only on the regions the grant needs (v3) |
| 10-23 08:46 | `rtepfx2` rc=7: linkage gate compared `kernels/production` symlink parents to `ldd` realpaths | false FAIL | classify harness false-FAILs before re-queueing; fix = realpath |
| 10-23 09:55-10:02 | `ch28-lbh-build` rc=1 three times: `ctest -N \| grep -q` SIGPIPE under pipefail | q3 slot churn | no `grep -q` on a producer under pipefail; after the third failure ask for a dry-run outside a grant |
| 10-23 09:0x | ch28 writer v1 floor 1500 s raised to 1800 s in v2 before it fired | (near-miss) | same margin rule, caught by the writer audit |
| 10-23 06:4x | `dhm-mining-full` done 20:02 the day before, poller still polling; `df2-ubatch-census` done offline, poller alive | would re-run done work | never grant an id whose work is complete; mark the row COMPLETE and STOP it |
| 10-23 11:1x | side agent flagged q0-q2 idle 14:20-17:50 in the plan | (caught before it happened) | one afternoon writer with parallel lanes replaced eight single-purpose writers |
| 10-23 23:5x | day chain v3 released the GPU to yarn right after CH-27 while inf66 (quiet, GPU idle) was next; `grant_ok` admits regardless of live claims | (caught before it fired) | quiet-block end flag that the GPU writer waits on |
| 10-24 00:5x | lane-gpu: after c3-gate-bc every remaining item was precond-blocked, so the yarn filler (7800 s) would have taken the GPU over inf66's quiet slot | (caught) | lane runner restarted with no filler |
| 10-24 01:11 | lane runner `held()` matched `SHARED`, region-lock prints `SHRD`; it granted c3-gate-g under c3-gate-bc's quiet run | region-lock blocked the acquire 189.8 s; bc undisturbed | match `HELD\|EXCL\|SHARED\|SHRD` in every writer |
| 10-24 01:17 | inf66 rc=68: launch check read the main thread's `Cpus_allowed_list`; `OMP_PROC_BIND=spread` pins it to place 0 ("0" ≠ "0-95") | false FAIL | the union of all thread masks must lie within the grant's CPUs (owner fix, new pin) |
| 10-24 01:17-05:00 | event watcher re-touched its stamp at re-arm, 4 s after `inf66.ended` | whole host + GPU idle 3.7 h | stamp persists across re-arms (watcher v2) |
| 10-24 06:37 | day chain re-granted inf66 before its fix landed | (revoked 30 s later, before the launcher poll) | revoke = move `.grant` aside + `.ended reason=revoked` |
| 10-24 06:37 | CH-27 had no FILLERS row or launcher at its slot | quiet slot went to the next items | a peer registers row + pid before its slot; the writer skips and releases |

Operator rulings that fix the objective (not incidents):

- 10-21: DS41/Nemotron speed tests are indicative; pair them with GPU work and measure the GPU's
  effect. Quiet only for champion baselines.
- 10-22: "being queued implies BEING ready" (QUEUED vs BACKLOG); RAM is a calendar resource;
  "unwritten code should NEVER be a blocker"; every DS41-1017 test except the noise floor is held
  until AK kernel work (short one-off checks allowed by cost); `WINDOW_CONFIRMED=1` only inside a
  grant; GPU + CPU inference may co-run in production once pinned.
- 10-23: when a code blocker clears, the owner arms and requests a slot in the same turn.
