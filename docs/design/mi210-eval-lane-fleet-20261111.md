# MI210 eval-lane fleet (INF-45, operator option (c))

Date 2026-11-11. Status: DESIGN ONLY. No stack, registry, topology or code edit is made by this document; landing is
a stack change (class (b)) at or after the relaunch.

Box: `handoffs/active/numa-placement-and-contention.md` (line 2576 on origin/main 0ae751280): "Design and land the MI210
eval-lane fleet (eval-only role bound to a GPU slot fleet); size `-np` from E5/GPU batch data." Operator decision
2026-11-10: option (c), eval-lane fleet on the MI210 under the slot-fabric track, freeing all CPU quarters. The slot-fabric
handoff was folded 2026-11-03 into `handoffs/active/kv-cache-program.md` (`## Track: heterogeneous-slot-fabric-residency`,
line 1751); `handoffs/completed/heterogeneous-slot-fabric-residency.md` is the stub. Ratified principle that governs
this design (kv-cache-program.md:1759-1771): role-to-slot binding is policy data, never code; one fact per physical
resource; realized-first truth (probed, not launch intent); fail-closed residency; no mid-decode preemption.

Evidence tags: [M] measured with a cited artifact, [R] read from registry/code at the cited line, [D] derived here
(arithmetic shown), [UNKNOWN] not found; must be measured before it gates anything. Nothing below is a new measurement.

## 0. Decision summary

| Point | Decision |
|---|---|
| 1. Role | `eval_batch`, eval-only, one `server_mode` entry on `mi210_0`, no `shared_with`/alias, in no routing or escalation chain; reached only by `force_role: eval_batch`. |
| 2. `-np` | **np 8 target, np 4 floor.** The np 8 call rests on a PROXY grid (Qwen3.8 MTP, not DFlash2); one confirming dflash2 {4,8} cell at the eval mix is a landing precondition. |
| 3. Co-residency | **TIME-SHARE.** VRAM partition is arithmetically infeasible for any 27B-class eval model (sum shown in section 3). |
| 4. Wiring | topology entry, registry `server_mode.eval_batch`, `force_role` switch in `eval_tower.py` (no new code path needed for lane width), `/api/health` freshness panel. |
| 5. Acceptance | 50-question suite, zero CPU-quarter requests sampled during the run, ABA interactive-latency check against a measured A/A floor. |

## 1. Role: `eval_batch`

- Eval-only: serves requests carrying `workload_class=eval_batch` + `force_role=eval_batch`. Interactive routing never
  names it: it is absent from every escalation/consult list in `orchestration/model_registry.yaml` (the architect_critic
  entries at lines 374-429 are the pattern to NOT copy) and has no `alias_of`/`shared_with`.
- Bound to a GPU slot fleet on `mi210_0` (one llama-server process, `np` slots; "fleet" = the slot set of that process,
  GPU = `1 x K_gpu` in the fabric's `N x K` model, kv-cache-program.md:1788-1795). `-ngl 99`, `device: ROCm0`,
  host lane `GPU_HOST_LANE` (cores 184-191, `-t 8`) exactly as the existing GPU roles
  (`orchestration/stack_topology.yaml`, `architect_critic` block, `gpu_host_lane: true`, `numactl_policy: membind=3`).
- Distinct from the retired CPU `eval_batch_frontdoor` (warm launcher-only, default-off, port 18070 per the 2026-07-23
  pre-execution audit in numa-placement-and-contention.md:2616-2618). That was a CPU lane; this is a GPU lane. I did not
  re-verify on origin/main that the 18070 entry still exists in `stack_numa.py` [UNKNOWN]; the landing package must
  check for a name/port collision.
- Model: the model under evaluation. Eval verdicts attach to a weights file, so the lane loads whichever GGUF the
  queued eval needs, from the existing canonical recipes (section 2). The first population is the 27B because it is the
  only large model with a measured GPU np grid and a live recipe.
- Instrument-era warning [D]: a verdict taken on the GPU build is a different numeric path from the CPU build the role
  is served on (the repo already records CPU batch-shape logit drift: `docs/reference/inference-outcomes-week-2026-10-18-to-25.md:76`,
  SPEC-RNG.1.1/1.2). The lane must stamp an eval-instrument era row distinguishing `gpu-eval-lane` from the CPU
  eval path, and no GPU-lane score may be compared to a CPU-lane score without that boundary (MEASUREMENT.md era
  handling). The R3 note in numa-placement-and-contention.md:2256-2262 already demotes the older 2.258 vs 10.970
  wall-min figures to prior; this design does not use them.

## 2. `-np` sizing from GPU batch data

### 2.1 Data found

AGG GPU np-sweep rows [M], `epyc-inference-research` `data/inf61-q38-np-depth-mtp8-20260916/grid_summary.json`
(research commit `0a711890`; table reproduced in `handoffs/active/model-evaluation-queue.md` lines ~1533-1560 and
`progress/2026-09/2026-09-16-sub-gpu-runner.md` section 12). Qwen3.8-27B, MTP n-max 8, v9 kernel, category CANDIDATE,
unit = launch, between-launch spread up to 13.6%, MTP acceptance 0.39-0.47. Mean aggregate decode tok/s:

| np | 2k | 8k | 16k | 32k | per-request @2k [D] | share of peak @2k [D] |
|---|---|---|---|---|---|---|
| 1 | 46.4 | 45.2 | 44.0 | 45.5 | 46.4 | 39.7% |
| 2 | 63.0 | 59.8 | 58.0 | 59.1 | 31.5 | 53.9% |
| 4 | 91.8 | 92.2 | 78.6 | 88.0 | 22.9 | 78.6% |
| 8 | 112.3 | 99.6 | 97.3 | 95.2 | 14.0 | 96.1% |
| 16 | 116.8 | 97.2 | skip | skip | 7.3 | 100% |

np16 at 16k/32k and np32 at every depth failed at startup (`failed to allocate ROCm0 buffer`), card empty of other
tenants. Caveats stated by the source: each launch ran only `np` questions with heavy truncation at 2k; the n-max 4 grid
read higher at np>=2 (np8/2k 157.3, cross-session observation, no ABA), so absolute values are not shippable as a "best
config".

Live production-shape np data [M], KVU-1e (kv-cache-program.md:2348-2351; research `m4_np4_concurrent_live.json`
`07060eaa`): live :8083 (np4, kvu), fixed-length 1024-token generations, aggregate 40.2/39.9 tok/s at concurrency 1,
71.4/67.8 at 2, 95.3/93.1 at 4; per-request median 40.5/40.2, 36.4/34.9, 27.6/26.1. This is DFlash2 at np4; there is
no np8 DFlash2 row [UNKNOWN].

Counter-datum [M]: GPU 27B DFlash2 at 54k greedy, f16/n8, np1/np2/np4 all 42.8-43.8 tok/s
(`logs/agents/inference-serving-launch-20261106.md:28`, artifact `artifacts/compute/local-launch-optimization-20261106/`).
Read as "no aggregate gain from slots at 54k"; the source does not say whether those cells ran concurrent streams, so I
use it only as a ceiling warning: np scaling is context-dependent and the eval lane must be sized at the eval ctx.

Prefill: the brief cites "27B dflash2 np4 ~ 856 t/s prefill". The only 856 in the repo is Qwen3.6-27B Q8_0 `llama-bench`
pp512 = 856 t/s, tg128 = 28.69 t/s, 28.9 GB VRAM, 2026-07-02, contended host, OBSERVATION grade, a DIFFERENT 27B and
not np4/DFlash2 (memory `project_mi210_gpu_inference.md`; quoted at `docs/design/integrated-document-aggregation-plan-20261110.md:49`).
I use it as a proxy for prefill cost only, and flag that no DFlash2 np4 prefill row was found [UNKNOWN].

Eval max_tokens mix [UNKNOWN as a measured distribution]: `eval_tower.py` passes per-suite limits; the recipes carry
`n_predict` 384 (27B dflash2 np4, 35B MTP np4) and 512 (gemma judge np4). Section 2.3 gives the landing measurement.

Recipes [R] (`epyc-inference-research/artifacts/serving-recipes/`): `qwen3.8-27b-q8-gpu-dflash2-np4.json` (np 4, ctx 16384,
batch/ubatch 2048, f16 KV, FA on, non-unified, `-t 8`, cpu_list 184-191, dflash2 draft_n_max 8, n_predict 384);
`eval/gemma-4-26b-a4b-orig-q8-gpu-judge-np4.json` (np 4, ctx 32768, n_predict 512, `--reasoning off`; its GGUF
`gemma-4-26B-A4B-it-ORIG-Q8_0.gguf` is not present under `/mnt/raid0/llm/models` today, so this recipe is not launchable as
written); `eval/qwen3.6-35b-a3b-q8-gpu-mtp-longctx196k-np4.json`; `eval/qwen3.8-27b-q8-gpu-dflash2-longctx196k-np1.json`.

### 2.2 Knee

Objective: maximise aggregate tok/s subject to per-request latency being irrelevant to users (eval is batch) but bounded by
the per-question timeout in `eval_tower.py` (`_eval_question_timeout_s`). Reading the 2k..32k columns:

- np1 -> np4: +98% @2k, +104% @8k, +79% @16k, +93% @32k. Strongly worth it.
- np4 -> np8: +22% @2k, +8% @8k, +24% @16k, +8% @32k, at -39% per-request. Marginal but positive at every depth.
- np8 -> np16: +4% @2k, -2% @8k (the only two non-skipped cells); per-request halves again. Past the knee.

So the aggregate knee is **np 8** (np4 holds 79-93% of the np8-or-better peak, np8 holds 96-100%; np16 adds nothing and
cannot allocate at >=16k). Choose **np 8**. Fallback np 4 if the DFlash2 confirmation cell shows np8 below +10% over np4,
or if the eval ctx makes np8 not fit (2.4). Caveat: the knee is from the MTP proxy; DFlash2 speculative acceptance
behaves differently under batching (MTP n-max 8 was already shown to lose to n-max 4 at np>=2 in the same data), which is
why the confirmation cell is a precondition, not optional.

### 2.3 Landing measurement (stop-on-answer, per the measurement-sufficiency rule)

Question: does DFlash2 np8 beat np4 aggregate by >=10% on the eval question mix? One ABAB pair of launches
(np4, np8, np4, np8) on the dflash2 recipe, eval-mix prompts, fixed-length generation (`ignore_eos`, the KVU-1e lesson:
single-wave aggregate deltas were an answer-length artifact, kv-cache-program.md:3729-3734), own-PID VRAM sampled during
each cell, graphs state recorded (GPU-LEAK-1: leak is absent on the production argv, kv-cache-program.md:936). Stop on
answer; futility stop if two launches of the same np differ more than the 13.6% between-launch spread the INF-61 grid
reports. No compute is started by this document.

### 2.4 KV headroom at eval ctx [D]

KV bytes per token at f16 = 64 KiB for the production architect_critic shape (`orchestration/model_registry.yaml`
`serving_shape.kv_kib_per_token_f16: 64.0`; the coder_escalation alias row at the same file says 96.0, a registry
inconsistency to fix at landing, not here). q8_0 KV = 17/32 of f16 (check: 393,216 tok x 64 KiB = 24.0 GiB f16 -> 12.75 GiB
q8_0, which equals the observed 12.75 GiB in KVU-16a [M]).

| Eval shape (np x ctx per slot, non-unified like the recipes) | tokens | f16 KV [D] | q8_0 KV [D] |
|---|---|---|---|
| np 8 x 16,384 | 131,072 | 8.0 GiB | 4.25 GiB |
| np 8 x 32,768 | 262,144 | 16.0 GiB | 8.5 GiB |

On an otherwise empty card (time-share) either fits: weights 27.05 GiB + drafter 1.92 GiB (file sizes 29,047,086,048 B and
2,056,414,752 B) + compute buffers + KV. Measured non-KV for the production shape is 35.06 GiB (KVU-16a) and the registry
says 38.03 GiB (`vram_non_kv_gib`); use the larger as the planning value: 38.03 + 16.0 = 54.0 GiB worst case, under the
card's 63.98 GiB and the 60 GiB (61,440 MiB) own-PID guard used by the f8 gates. The eval ctx itself is [UNKNOWN] (the
tower's question lengths were not audited here); 16k covers the recipe default, long-ctx suites need the `longctx196k`
recipes at np1 or np4.

## 3. Co-residency with production :8083 (architect_critic)

### 3.1 VRAM sum

| Item | GiB | Source |
|---|---|---|
| MI210 VRAM total | 63.98 | `rocm-smi --showmeminfo vram` read 2026-11-11: 68,702,699,520 B |
| :8083 own-PID, sampled max, production shape (np4, pool 393,216, ub512, q8 KV, dflash2) | 47.81 | KVU-16a `handoff-kvu-16a-load-20261102`, kv-cache-program.md:2495 [M] |
| of which target KV | 12.75 | same [M] |
| of which non-KV | 35.06 | same (registry planning value 38.03, `vram_non_kv_gib`) |
| Free beside :8083, measured basis | 16.19 | 63.98 - 47.81 [D] |
| Free beside :8083, registry basis | 13.20 | 63.98 - (38.03 + 12.75) [D] |
| Smallest sensible eval lane model: Qwen3.8-27B Q8_0 weights alone | 27.05 | file size [D] |
| 27B weights + DFlash2 drafter | 28.97 | [D] |
| Qwen3.6-35B-A3B MTP Q8_0 weights alone (the frontdoor model) | 35.20 | file 37,801,097,504 B [D] |
| Qwen3-VL-30B-A3B (worker_vision) | 22.3 / 21049 MB | stack_topology.yaml comment; registry `vram_mb` |

Sampling caveat: the 47.81 GiB is a sampled maximum, not a lifetime peak (the registry row says so). A single live
`rocm-smi` read taken while writing this document showed 45.82 GiB (49,198,391,296 B) in use on the card; it is one sample
with no process attribution and is not used as a basis. The handoff text "about 19 GiB headroom beside :8083"
(model-evaluation-queue.md GPU-PLT-1) does not reproduce from the numbers above (16.19 or 13.20); I use the derived figures.

### 3.2 Choice: time-share

A partition needs the eval model resident beside :8083. The smallest eval model that is not the 27B-class (27B weights alone
27.05 GiB) already exceeds the free space by a factor of 1.7-2.0 (27.05 vs 16.19 or 13.20), before any KV for np slots.
The operator already ruled the same arithmetic once: DFlash2 "~43 GiB ... does not fit beside this 22.3 GiB VL on one MI210"
(stack_topology.yaml, STACKCHG-DFLASH2-20261003), which is why worker_vision runs on CPU cold. A partition would only fit a
model of roughly 12 GiB or less, i.e. a different, smaller model than any role it would evaluate, which makes the verdicts
non-transferable. **Partition is rejected; the lane is TIME-SHARED.**

Time-share contract:
1. Quiet-window only: the lane process runs only while :8083 is drained (preempt by drain, never by kill; no mid-decode
   preemption per the ratified axiom). Window grant is a `mi210_0` booking on the compute calendar (the existing flock;
   `inference-backlog-scheduling` skill, GPU bin with host threads 184-191, `min-window` >= model load time + eval).
2. One tenant per GPU instant. Because `eval_tower.py` keys lanes by server URL (`lane_key = url`, section 4), it cannot
   see :8083 and the eval lane as one physical resource. The one-fact-per-resource axiom therefore requires the calendar
   flock, not the tower, to be the arbiter; the lane's launcher refuses to start unless the :8083 process is proven absent
   from KFD (own-PID VRAM sample), not merely port-down.
3. Swap cost is paid per window: 27B weights 29.05 GB cold load. No load-time measurement for this card/path was found
   [UNKNOWN]; the first landing run records it, and the min-window is set from it.
4. Zero-cost special case [D]: when the queued eval targets the 27B itself, the eval lane can instead be the already
   resident :8083 weights in a quiet window with its existing np4 slots (no extra VRAM, no reload), but only if the lane is
   still a distinct role/URL; the recommendation is to NOT do this by aliasing (that would put eval_batch in the
   interactive process's role set), and to accept the reload.

Sub-option kept open, not chosen: a later "eval lane on the 2nd MI210" (operator reassesses placements when the 2nd MI210
arrives, stack_topology.yaml worker_vision comment) removes the time-share; the design keeps the lane's device a registry
field so that is a one-line change.

## 4. Wiring

All four are landing work (stack change). Described here by exact surface; none is edited now.

1. `orchestration/stack_topology.yaml` (epyc-orchestrator): new `roles.eval_batch` block mirroring `architect_critic`:
   `instances: [{cpu_shape: GPU_HOST_LANE, port: <new, unallocated>}]`, `gpu_host_lane: true`, `numactl_policy: membind=3`,
   no mlock. `drafter_selection: eval_batch: dflash2` when the loaded model is the 27B (the compiler fails on a
   multi-drafter model with no selection and forbids a default, stack_topology.yaml lines 55-75). Port is
   [UNKNOWN] until allocated against origin/main registry (rule: allocate IDs against origin/main).
2. `orchestration/model_registry.yaml`: `server_mode.eval_batch` with `device: ROCm0`, `slots: 8`, `serving_shape`
   (`n_ctx`, `kv_quant`, `kv_kib_per_token_f16: 64.0`, `vram_non_kv_gib` from the landing sample), `tier: cold` (started
   only by the calendar grant, like worker_vision's cold CPU stance), `model_role` pointing at the recipe's model, no
   `shared_with`. Because `eval_tower._eval_resource_lane` marks a lane GPU when the entry has `device`/`vram_gib`/`vram_mb`
   (eval_tower.py ~2568), lane capacity then equals `slots` automatically (`capacity = slots` in the `if gpu:` branch): no
   change to lane-width code. The hard-coded GPU role-name set in that function (architect_critic, coder_escalation,
   ingest_long_context, worker_vision, vision_escalation) needs no addition, because `device` already triggers it.
3. Eval tower routing switch (`scripts/autopilot/eval_tower.py`): the concurrent path is `_eval_batch` -> `_eval_resource_lanes`
   -> per-lane capacity; `workers = min(n, sum(lane_capacities))`. A question reaches the lane by
   `force_role: eval_batch` (read at `_eval_resource_lane`, which defaults to env `AUTOPILOT_EVAL_BOTTLENECK_ROLE`, default
   `frontdoor`); `force_role` also puts the question in `homogeneous_native_batch` placement (`_eval_batch_placement_mode`).
   So the switch is configuration: set `force_role` on the eval question set (or the env default) to `eval_batch`.
   Two traps from reading the code: (a) `AUTOPILOT_EVAL_CONCURRENCY` wins over the topology and can only LOWER `workers`
   (`workers = min(workers, override)` at `_eval_batch`); it must be unset or >= np or the lane runs below its slot count.
   (b) Generation width is the lane capacity but the SCORING pool is separate (`AUTOPILOT_EVAL_SCORING_CONCURRENCY`, default
   `min(16, cpu_count//12)`): at np 8 on a decode-bound GPU lane the scorers run on host CPU cores. That is client-side
   scoring, not serving, and does not break "zero CPU-quarter serving traffic", but the acceptance sampler must distinguish
   them (section 5). Also: orchestrator-side dispatch must keep `workload_class=eval_batch`, `request_priority=background`
   (numa-placement-and-contention.md:4686) so the request cannot be re-placed onto a CPU instance; that file (lines 4726-4733)
   records that the live placement machine RE-PLACES forced `eval_batch` requests onto a disjoint CPU instance and that
   the region-lock anchor is not consulted on that path. The role binding must therefore make `eval_batch` a role with NO
   CPU instance, so re-placement has no CPU target. Verify with the section 5 probe, not by reading config.
4. Dashboard-plane rule (`dashboard/README.md` lines 44-62): (i) a `dashboard/registry.json` entry for the lane's status
   surface; (ii) health probe = `/api/health` three-valued fold, not `/health` (transport-only, "stays green while the
   producer behind a panel is dead"); (iii) a freshness envelope in `dashboard/panels.py`: producer = the lane launcher's
   state file, timestamp field, staleness bound = the calendar window length + slack, `absence_means` = "lane not booked /
   :8083 in service (expected, not a fault)". The probe must prove its own server: served GGUF sha via `/props`, own-PID
   KFD VRAM > 0 and the `mi210_0` flock holder = this lane; a port that answers is not proof (a different model could hold
   it, the :8083 incident class).

Belief-kernel wiring (CLAUDE.md): the lane produces measurements. At landing add a row to
`scripts/vidya/adapters/README.md` source table and a task in `handoffs/active/vidya-belief-substrate-program.md`; write
side first. Not done here (design only, and index/task rows are the owning session's write).

## 5. Acceptance at landing

Run: the eval tower runs a 50-question suite (the core_v2 unit) with `force_role: eval_batch` through the lane inside a
granted `mi210_0` window.

A. Zero CPU-quarter serving traffic, sampled DURING the run (Observation Windows rule: a sample after the run proves nothing;
   two samples to act, name the count to claim). Observed set: every CPU llama-server instance port in the live topology.
   Per sample, record each port's `/slots` processing count and request counter, and the API `serving_calls`/`dispatch`
   rows tagged `workload_class=eval_batch` by serving port. Pass: 0 eval_batch requests on any CPU port for the whole window,
   and every one of the 50 on the lane port. Expected-and-excluded: the lane's own 8 host threads (184-191 fold to physical
   88-95, i.e. NPS4 node 3; `membind=3`) and client-side scorer CPU. The brief's "CPU-quarter traffic" is therefore defined as
   serving requests, not cores in use.
B. Residency proof: `verify_ggml_linkage.sh` (research repo) for the lane binary, non-zero own-PID VRAM sampled during the
   run, KFD process count; `ldd` is not evidence (dlopen).
C. Interactive latency on the CPU roles unchanged within 1.96%: ABA, with CPU-role interactive probes during the run
   versus the same probes before/after without it. The 1.96% floor is taken from the brief; I did not find its derivation in
   origin/main, so mark its source [UNKNOWN]. For comparison the recorded GPU serving p95_dev floor is 6.596% (n=24, unit =
   process launch, MEASUREMENT.md line 142) for a different quantity. Method rule: measure the A/A floor of the latency probe
   first; if the A/A spread exceeds 1.96% the pass criterion cannot be resolved and the result is INCONCLUSIVE, not PASS.
   The node-3 quarter shares cores with the host lane, so the probe set must include the node-3 CPU role.
D. Lane health: the section 4 probe reads `ok` during the window and `absence` (expected) outside it; the freshness panel
   goes stale on a killed launcher (inject by the launcher's own stop path, never by pattern kill).
E. Instrument stamp: era row for `gpu-eval-lane` written before the first score is recorded.

## 6. Open items that gate landing (each is a measurement or an allocation, not a decision)

1. DFlash2 {np4, np8} confirming cell at the eval mix (2.3). [UNKNOWN until run]
2. Model cold-load time on this card/path, to set min-window (3.2). [UNKNOWN]
3. Eval ctx / max_tokens distribution of the 50-question suite (2.1, 2.4). [UNKNOWN]
4. New port allocation, `eval_batch_frontdoor`/18070 collision check (1, 4.1). [UNKNOWN]
5. Registry inconsistency: `kv_kib_per_token_f16` 64.0 (architect_critic) vs 96.0 (coder_escalation alias), non-KV 38.03
   (registry) vs 35.06 (measured); reconcile in the landing package.
6. Source of the 1.96% floor (5C).

## Sources

- numa-placement-and-contention.md (origin/main) 2256-2262, 2569-2576, 2616-2618, 4686, 4726-4733.
- kv-cache-program.md (origin/main) 1751-1795 (slot-fabric track), 2348-2351 (KVU-1e), 2476-2495 (KVU-16a), 3729-3734, 936.
- model-evaluation-queue.md (origin/main) INF-61 re-collect (~1533-1560), GPU-PLT-1 (1287).
- progress/2026-09/2026-09-16-sub-gpu-runner.md section 12; logs/agents/inference-serving-launch-20261106.md:28.
- `orchestration/stack_topology.yaml`, `orchestration/model_registry.yaml`, `scripts/autopilot/eval_tower.py`
  (epyc-orchestrator origin/main 154023768).
- `epyc-inference-research/artifacts/serving-recipes/**` (the four recipes above).
- `dashboard/README.md` 44-62; MEASUREMENT.md 142; memory `project_mi210_gpu_inference.md` (856 t/s, 2026-07-02).
- Live read: `rocm-smi --showmeminfo vram`, 2026-11-11, single sample.
