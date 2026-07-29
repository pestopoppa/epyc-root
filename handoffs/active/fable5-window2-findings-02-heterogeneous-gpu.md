# Window-2 findings 02 — Post-bandwidth-wall heterogeneous CPU+GPU serving (§4B)

**Verdict in one line**: the MI210 handoff's A/B/C decomposition asks "how do I run a model that doesn't fit?" — but every production model except the architect *fits*; the real problem is **fleet placement under a 64 GB HBM budget**, the top two plays (frontdoor residency, eval engine) are literally the same migration, the fork already ships every flag they need, and the only real gap is that the orchestrator is 100% GPU-unaware.

Substrate facts verified 2026-07-03 against `/mnt/raid0/llm/llama.cpp @ a30214db1` (raw reads; adversarially re-verified) and the 2026-07-02 MI210 session (`progress/2026-07/2026-07-02-mi210.md`, `/mnt/raid0/llm/tmp/mi210-build/*`). All GPU throughputs are **observations** (contended host, no P-GPU-1 yet) — they rank options, they gate nothing (R7).

## 1. Critique of the A/B/C framing (deliverable 1)

The handoff (`tmp/epyc_mi210_hybrid_inference_handoff.md`) is a competent survey of the *offload* literature, and its "measure first" instinct is right. Five structural corrections:

1. **It is model-centric; your problem is fleet-centric.** The unit of decision is not "a model that doesn't fit in HBM" but "seven roles, one 64 GB card, one 460 GB/s CPU pool shared with the evaluator." Ground truth (verified, findings docs stack-inventory): frontdoor Q8 37.8 GB *fits* (≈43 GB with KV); worker Q4 16.8 GB fits (and currently burns **86 GB of RAM in 5 private no-mmap copies**); ingest 80B Q4 48.4 GB fits; both vision models fit; only architect 122B (78.26 GB) does not. Family A (dense hybrid) targets a model class you do not deploy — every production text model is a sparse MoE. Family B has exactly one real instance (architect). Family C must now beat the *live* MTP self-speculation running on every role, not a no-spec baseline.
2. **The discriminating axis it misses: instrument throughput.** Your dominant workload is the evaluator (window-1: ~77% of traffic is the harness). The eval tower's bottleneck role defaults to **frontdoor** (`eval_tower.py:458`) — so GPU frontdoor residency *is* GPU eval acceleration. The handoff never mentions the evaluator. Related second miss: **quiesce-window economics** — a GPU-hosted lane is insulated from the production CPU stack, so measurements stop competing with serving; the campaign's 28–31 h quiesce window and half the blocked portfolio are downstream of single-substrate serving (R14).
3. **"Success ≠ beat full-HBM" is backwards for you.** For this stack, full-HBM residency of small-specialist roles is not the boring baseline to beat — it *is* the primary EV, because it simultaneously (i) accelerates the hottest interactive path, (ii) accelerates the evaluator, (iii) returns the vacated CPU bandwidth to the remaining roles, and (iv) creates the isolated measurement lane.
4. **The integration-target question is already answered.** vLLM 0.10.1 (the only image that computes on gfx90a) predates the `gemma4`/`qwen35` architectures entirely; the MI300 image hard-refuses gfx90a; and at matched fp16 the fork's HIP build is within ~10% of vLLM batch-1 (62.45 vs ~69 t/s, Qwen3-8B). The fork is the substrate. KTransformers/HybriMoE/Fiddler simulators (handoff §4) are dead weight for now — the one family-B case (architect) is testable with `-ot/-ncmoe` flags that already exist.
5. **Milestones 0–3 are oversized where they matter least.** Pinned-H2D copy benches, route-trace simulators, and cache-policy libraries serve families that are marginal here. The decisive set is six measurements (§5), four of which need no clean window and one of which is a log read. "Measure-first" survives; the *menu* changes. Also §5.4's warning ("if the CPU backend loops token-by-token, GPU drafting won't help") is not hypothetical for you — it is your recorded history: GDN recurrence made N-token verify ≈ N× single decode on CPU (`gpu-acceleration-path.md:76`), and dispatcher-v1 was net-negative for exactly the BW-contention reason.

**A sixth family the handoff half-names and should be promoted**: (D) **op-offload prefill** — weights stay in CPU RAM, the backend scheduler ships large-batch matmuls to the GPU. This is *already in the fork* (`ggml_backend_cuda_device_offload_op`, `GGML_OP_OFFLOAD_MIN_BATCH` default 32, `ggml-cuda.cu:5479,5659`) — grouped-layer streaming for prefill is a config knob, not a build. Long-context ingest (80B, SSM, spec-forbidden, 14–20 t/s) is its natural customer.

## 2. What exists TODAY (verified capability matrix)

| Capability | State | Evidence |
|---|---|---|
| Full-GPU residency of a role model | **EXISTS in fork; verified live on MI210** | gemma4-31B Q4 `-ngl 99`: pp512 839.7, tg128 30.01 t/s; Qwen3.6-27B (qwen35 GDN hybrid) **runs clean**: Q4 32.88 t/s (33% roofline), **Q8 28.69 t/s at 47% roofline / 766 GB/s** — Q4_K is dequant-bound on gfx90a, Q8 is the sweet spot |
| MTP/NEXTN head with independent device | **EXISTS (separate-head path); verified** | draft loads with own `devices/n_gpu_layers/tensor_buft_overrides` (`server-context.cpp:1178-1191`); measured gemma4-31B+MTP on GPU: 43.25 t/s = 1.44× plain, 59.7% acceptance. Embedded-MTP (no `-md` file) inherits target placement. The old frontdoor same-file `-md` launch was a production bug and was fixed on 2026-07-03; current same-realpath Qwen NEXTN roles omit `-md`. |
| Draft-on-GPU + target-on-CPU | **EXISTS as plumbing, this split untested** | `-devd/--spec-draft-device`, `-ngld/--spec-draft-ngl`, `-otd` (`arg.cpp:3517-3610`) |
| MoE expert placement (family B) | **EXISTS, static-at-load** | `-ot <regex>=<buftype>`, `-cmoe`, `-ncmoe N` (`arg.cpp:2322-2349`; applied once at load, `llama-model-loader.cpp:1158-1161`) |
| Op-offload prefill (family D) | **EXISTS, env-tunable** | `GGML_OP_OFFLOAD_MIN_BATCH` (`ggml-cuda.cu:5659`) |
| HIP build | **fp8 guard merged at HEAD** (a30214db1); complete build only in worktree `llama.cpp-mi210-hip` — canonical `build-hip/` has zero ggml-hip objects; LD_LIBRARY_PATH hazard: devcontainer prepends the CPU `build/bin` → HIP binaries segfault unless the HIP dir + `/opt/rocm/lib` are prepended | substrate dive §2 |
| Orchestrator | **ZERO GPU awareness** — no `-ngl/--device/-ot` in any launch builder; binary resolves to the CPU build; registry acceleration types have no device field. A latent seam exists: per-role `binary_dir` override (`orchestrator_stack.py:569-585`) + a `ServerConfig.gpu_layers` scaffold referenced only by its own test | substrate + orchestrator dives |

## 3. EV-ranked options + the proposed architecture (deliverable 2)

**The proposed architecture has a name: "instrumented placement."** One serving fabric (the fork), roles placed across {CPU-NUMA-quarters, GPU} by registry data, chosen by measured EV per GB of HBM, with the evaluator treated as a first-class role in the placement problem. Placement is data (`device`, `ngl`, `binary_dir`, env in the registry acceleration block), never code — that is the model-agnosticity clause of the North Star extended to substrate-agnosticity.

EV ranking for *this* substrate and workload (single-user latency-first + harness-dominated traffic):

1. **Frontdoor residency = eval engine (one migration).** Qwen3.6-35B-A3B Q8 (37.8 GB + KV ≈ 43 GB) solo on the MI210. Expected: Q8 at 47% roofline observed on the 27B sibling ⇒ 2–4× the deployed 24.3 t/s, *plus* NEXTN MTP on top (1.44× measured on gemma4), *plus* ~380 GB RSS and the largest CPU BW share returned to the pool, *plus* every T1/T2 eval accelerates (statistical power per wall-hour — the 4A instrument gets faster too). Risks: MoE small-expert GEMM efficiency on gfx90a unmeasured; `qwen35moe` HIP op coverage unverified (the 27B GDN ran clean, the MoE hybrid has not been loaded). **This is Gate R (§5).**
2. **Vacated-CPU reallocation (free rider).** After frontdoor migrates, the 5-instance quarter topology frees; worker/architect/ingest inherit bandwidth. No work beyond the R14 re-plan; measure, don't assume.
3. **Embedder/classifier host + vision.** 6×BGE (ports 8090-8095) + reranker + the staged MLP classifier (whose "weights absent" comment is stale — weights exist since 2026-06-12) are batch-friendly, compute-bound, tiny. Unblocks K-EMB-1/N9 and K-DIV-1's semantic baseline. Low risk, low glory, schedule opportunistically after #1.
4. **Architect expert-split (the one real family-B case).** 122B A10B doesn't fit; `-ncmoe` keeps attention+shared+hot layers in HBM, cold experts in RAM. 12.19 t/s is the interactive-deep pain point; even 1.5× is user-visible. Decisive bench is one `-ncmoe` sweep (§5). Alternative: a ~3-bit requant fits entirely — but that re-opens a quality question the current evidence can't gate.
5. **Op-offload prefill for ingest/long-context.** Config-knob experiment; biggest TTFT effect on the 80B SSM role where decode-spec is forbidden.
6. **Drafter farm / GPU-draft-CPU-target — last, and now double-gated.** It must beat *live* per-role MTP self-spec (log-readable today, §5-M0) and survive the CPU batch-K verify cost on MoE+GDN targets (§5-M4). Window-1's ≥1.3× kill-gate stands. Expected outcome: stays dead for CPU targets; the drafter's real future is *on-GPU* pairs (e.g., GPU frontdoor + GPU EAGLE-3 head — the resurrection sweep's Dflash/EAGLE-3 items) where PCIe never enters the loop.

**Family verdicts**: A (dense hybrid) — drop as a family; it has no production instance (vision 7B fits trivially). B — keep exactly one instance (architect), decided by one sweep. C — reframe as "beat live MTP," expected negative for CPU targets. D (op-offload prefill) — promote to a named family. **New family E — placement/insulation** (the fleet knapsack + isolated eval lane) is the actual headline and was absent from the handoff.

## 4. The window-1 reversal, re-examined with hardware (deliverable 3)

The reversal **holds and strengthens**, with two refinements:

- *Frontdoor residency is the headline* — now supported by silicon: gfx90a Q8 effective BW 766 GB/s (47% roofline) vs the whole CPU's 460 GB/s shared across everything; GDN kernels run clean; MTP-on-GPU verified at 1.44×. Refinement 1: the naive "~3× from bandwidth alone" was optimistic for Q4 quants (33% ceiling, dequant-bound) — the frontdoor being Q8 rescues the estimate, and custom HIP dequant kernels (your `agentic-rocm` handoff) are the lever if the bench lands low.
- *GPU-drafting-CPU-targets is the weakest leg* — now weaker still: every production role already runs draft-mtp in production (frontdoor/architect NEXTN self-draft n-max 4; worker external MTP head n-max 2 — verified live ps), so the counterfactual improved from "no spec-dec" to "tuned self-spec." The `gpu-drafter-mi200-investigation.md` premise "frontdoor has zero spec-dec today" (line 257) is **stale** — a Stage-0 log read replaces its first measurement.
- Refinement 2 (new since window-1): **residency and eval-engine are the same card** — I ranked them #1 and #2 as if separable; the eval bottleneck role *is* frontdoor, so one migration buys both. This raises #1's EV and removes an ordering decision.

## 5. The smallest decisive measurement set (deliverable 4 — hard requirement)

Ordered; M0 costs nothing; M1–M3 need no production quiesce (GPU lane + side build); only M4 wants a brief window. **Every one lands in a named protocol or it doesn't gate.**

- **M0 — Live MTP acceptance log read (today, zero inference).** CLOSED 2026-07-03 by `epyc-orchestrator/scripts/benchmark/mtp_acceptance_report.py` and `orchestration/reports/mtp_acceptance_report_20260703T114323Z.{json,md}`. Current live self-MTP token α: architect_general `0.6854` (`3745/5464`), frontdoor `0.6582` (`26787/40700`), worker_general `0.8256` (`54378/65861`), aggregate `0.7580` (`84910/112025`); failed MTP roles: none. Frontdoor and worker_general are `ok_partial_port_traffic` because one quiet replica in each group had no acceptance lines yet; the role-level loud-fail gate cleared. This is the self-MTP baseline that any external drafter must beat, not external-drafter evidence.
- **M1 — Ratify P-GPU-1, then the frontdoor residency bench (Gate R).** Prereqs: fresh HIP build in the canonical tree (config exists; only worktree has objects) + `qwen35moe` op-coverage smoke (load, 32-token generation; if an op falls back to CPU the log says so — assert it doesn't). Bench: Qwen3.6-35B Q8 `-ngl all`, plain and `--spec-type draft-mtp`, P-BENCH-1-style reps, device-state capture per P-GPU-1. **Gate R: ≥1.8× deployed 24.3 t/s (observation baseline; re-anchor with one canonical CPU rep in the same window) → commit the orchestrator plumbing (R12) and migrate; <1.3× → residency demotes to eval-only hosting and the custom-HIP-kernel track becomes the critical path.**
- **M2 — Architect `-ncmoe` sweep (Gate B).** N∈{8,16,24,32} cpu-moe layers on the 122B; decode + prefill vs the 12.19 t/s observation. ≥1.5× with HIP-clean ops → adopt as the architect serving mode; else architect stays CPU and family B closes.
- **M3 — Op-offload prefill probe.** Ingest 80B, `-ngl 0`, `GGML_OP_OFFLOAD_MIN_BATCH` ∈ {32, 128, off}, long-prompt pp t/s vs CPU baseline. Pure config; decides family D in an afternoon.
- **M4 — CPU batch-K verify cost curve (the number family C actually turns on).** `llama-batched-bench`, K∈{1,2,4,8,16} on frontdoor (MoE+GDN) and worker (MoE): ms/pass and ms/verified-token. If cost ≈ K× (as the GDN history suggests), GPU-draft-CPU-target is arithmetically dead regardless of α — write that verdict once and stop re-litigating.
- **M5 (conditional, only if M0 shows α_MTP < ~0.6 and M4 shows sub-linear verify)** — the re-specified drafter A/B: v6 `--spec-type draft-simple`, aligned Qwen3.5-0.8B, **N≥24 prompts from `question_pool.jsonl`**, spec-off arm, ≥1.3× end-to-end kill-gate.

**α-harness re-specification (per the brief's silent-block guardrail)** — the staged `n5_frontdoor_drafter_retest.sh` should NOT run as-is: it pins a dead v5-only commit (a6c793fc6 is not in the v6 lineage; the only checkout at it has no build), its `-d .git` gate fails on the very worktrees it recommends, its compat checker is **fail-open for the exact tokenizer mismatch that caused the original silent block** (`check_draft_compatibility.py` never populates `issues`; qwen2-vs-qwen35 would PASS), its single synthetic 96-token prompt gives a CI spanning all three decision bins, and its `decision_grade = draft_total>0` would have graded the 2026-06-14 crash artifact (α=1.0 on 2 tokens, 23/24 prompts errored) as decision-grade. Required hardening (implement before any run is called α evidence): (1) `git rev-parse --git-dir` instead of `-d .git`; (2) binary provenance via `llama-server --version` hash == expected commit (the mtime heuristic is the silent-wrong-binary channel); (3) compat checker fail-closed on tokenizer-family/vocab/special-token mismatch, asserting the aligned specials 248044/248046/248044; (4) mandatory positive control (the live-MTP config) proving the measurement channel emits `draft_n`; (5) minimum-volume assertions (`completion_tokens ≥ 0.9·N` and `draft_n ≥ c·completion_tokens`) + reported CI; (6) failure taxonomy parsed from the server log (`no_spec_enabled | decode_failed_fallback | drafted_ok`) with the activated impl asserted; (7) production-like multi-prompt traffic with per-prompt + token-weighted α and incremental persistence; (8) spec-off arm in-window; (9) dual-track the commit pin to the v6 lineage (`draft-simple`), since v5 has no build and no deployment future.

## 6. Re-prioritization of the MI210 handoff (what to actually execute)

Keep: §1.1 measure-first staging (with the shrunken menu above); §7.1 env report; the §10 risk register rows on NUMA-locality of pinned buffers and misleading-benchmark hygiene (fold into P-GPU-1). Demote to appendix: family-A strategies A–D; the MoE cache-policy simulator suite; HybriMoE/Fiddler/KTransformers reproduction; FlexGen/Accelerate/DeepSpeed baselines; the vLLM integration branch (dead for current archs on gfx90a). Replace §11's "first Codex prompt" with: **M0 log read → P-GPU-1 ratification → canonical HIP build + op-coverage smoke → M1 residency bench → R12 plumbing behind Gate R → M2/M3 in the same GPU lane → M4 in the next brief window.** The handoff's own §5.4 verification warning graduates from checklist item to family-C kill criterion (M4).

## 7. Build seeds (the 2–3 things you will build)

- **R12 orchestrator GPU plumbing** — Accept: a role declares `acceleration: {device: rocm0, ngl: all, binary_dir: build-hip/bin, env: {LD_LIBRARY_PATH: ...}}` in the *master* registry; the compiled lean registry + stack manifest + runtime attestation all round-trip it; `orchestrator_stack.py start --only frontdoor` launches on the GPU and `attest_orchestrator_workers` proves it (the three-gates lesson: green pipeline ≠ stack-starts ≠ live==config). Cheapest decisive experiment before building: hand-launch the HIP llama-server on the frontdoor port with production args and run one eval batch through the unmodified orchestrator — if routing/quality/timeout behavior is unchanged, the plumbing is pure config transport and carries no serving risk.
- **Custom HIP dequant kernels (conditional)** — only if M1 lands in the 1.3–1.8× band; target the Q4_K/Q8 MMQ dequant gap (14 roofline points measured between Q8 and Q4_K). Accept: +15% tg on the residency bench, op-for-op parity vs `test-backend-ops`.
- **GPU eval lane in the campaign scheduler (R14)** — Accept: clean-window manifest entries carry a `substrate: gpu|cpu` field; GPU-lane items run while the CPU stack serves; the quiesce window shrinks to CPU-topology probes only (shape-keyed bracket, J2/J3, E1).

## Rider — OD-A: KTransformers Expert Deferral, and the scope of the §1.4/§6 demotion (2026-07-29)

Additive to §1.4, §2 (capability matrix row "MoE expert placement") and §5-M2. Filed by `mainA` on
operator direction (OD-A, `progress/2026-07/2026-07-29.md:485-487`). **Nothing here reverses a
verdict in this document.** It records that the demotion was scoped to *simulators* and never
evaluated the runtime technique, and it specifies what would decide the technique on its merits.

### R-A1. What was actually demoted

`:14` demotes "KTransformers/HybriMoE/Fiddler **simulators**"; `:69` demotes "HybriMoE/Fiddler/
KTransformers **reproduction**" beside "the MoE cache-policy simulator suite". The `(handoff §4)`
pointer at `:14` resolves to `tmp/epyc_mi210_hybrid_inference_handoff.md:458` (Workstream B), whose
only matching work item is `:581` "Implement in `simulator/moe_cache_policy.py`". The KTransformers
**runtime** was described in a different section of that handoff — `:190-203`, §2.3, "prior art for
heterogeneous runtime design / possible integration substrate" — which this document never cites or
engages. The load-bearing argument at `:14` is *substrate selection* (vLLM 0.10.1 is dead on gfx90a
⇒ the fork is the substrate), and it is sound. It simply does not reach a scheduling technique.

This document makes **no** claim that KTransformers is slow, unportable, AMX-bound or unbenchmarked.
The AMX argument that is often attached to it post-dates this document by 26 days
(`research/intake_index.yaml:45706`, 2026-07-29) and is the *rebuttal* package, not the basis.

**KTransformers has never been ingested** — zero entries across 937 in `research/intake_index.yaml`.

### R-A2. The technique, from primary source

SOSP'25, peer-reviewed, [DOI 10.1145/3731569.3764843](https://dl.acm.org/doi/10.1145/3731569.3764843);
implementation read at `kvcache-ai/ktransformers@a8062bfa` (v0.6.4), Apache-2.0.

Shared experts → GPU, routed experts → CPU. At layer `k` the top-k routed experts are split by
routing score: the highest-scoring `topk − n_deferred` are computed immediately; the lowest-scoring
remainder are launched but **not waited on**, and their output — computed on layer `k−1`'s
activations — is accumulated into layer `k+1`'s MoE output. Residual connections absorb the delay.
The deferral distance is **exactly one MoE layer** (`buffer_depth = 2`, hardcoded); only the *count*
of deferred experts is tunable. The async vehicle is `cudaLaunchHostFunc`/`hipLaunchHostFunc` — a
host callback enqueued on the inference stream — over a lock-free queue whose `sync(allow_n_pending)`
returns while deferred work is still running.

**Decode-only by design** (paper §4.1, explicit): in prefill a token batch touches nearly all
experts, so both halves of the split hit almost every expert, roughly doubling memory traffic and
cancelling the benefit.

### R-A3. Three corrections to the OD-A premise as handed to me

1. **"≤0.5% accuracy drop" is the aggressive setting, not the default.** The figure is DeepSeek-V3
   on LiveBench at **6 deferred of top-8** (paper §6.3). The shipped `kt-kernel` README grades 5–7 as
   "may introduce noticeable accuracy loss; use with care" and the CLI **defaults to 2**. It is a
   tunable quality/speed tradeoff, not a quality-neutral one. The suite scores (Table 2) are
   single-run without CIs or seeds on ≤200-problem benchmarks — observation-grade by our own grammar.
2. **"Not AMX-dependent" is correct, and the reason is stronger than assumed.** Deferral is
   ISA-agnostic Python on a shared base class (`kt-kernel/python/experts_base.py`); all five CPU
   backends inherit it, including `LLAMAFILE` (AVX2) and an AMD BLIS/AOCL path. More to the point:
   deferral runs **only in decode**, and the paper's own Fig. 14b / §6.4 report AVX-512 *beating* AMX
   in decode (AMX tile setup is overhead at low arithmetic intensity). The phase where deferral
   applies is the phase where our missing AMX is least relevant.
3. **The speed claim is narrow.** Up to **1.45×** decode, batch-1, decode-only, zero prefill benefit.
   Fig. 10 saturates fast: 2 deferred → −19% layer time, 3 → −26%, **4 → no further benefit** (CPU
   saturated). The system-level 1.25–4.09× figures are KTransformers-vs-llama.cpp totals, not
   deferral.

### R-A4. Why the near-uniform routing-skew verdict does not bind this

`mi210-big-model-and-acceleration-roadmap.md:254` gates expert-hybrid offload on a routing-skew
profile, and the 2026-07-17 production-representative GLM-5.2 pass came back near-uniform globally
(19,123,200 selections, `top_32=15.19%`, entropy `0.9987`, Gini `0.0664`). That verdict is sound for
what it tested: **hot-expert caching**, where a cacheable hot set must justify streaming weights over
PCIe. Deferral is not a caching scheme — experts stay resident in CPU RAM and only **activations**
cross PCIe (~10 KB, ~1 µs per crossing per `gpu-drafter-mi200-investigation.md:132,137`). Routing
skew is orthogonal to it. This is a genuine gap in the existing gate, not a reason to reopen caching.

### R-A5. What it would take on our stack — and why it is not a port

The capability-matrix row at `:26` ("MoE expert placement — EXISTS, static-at-load") understates the
constraint. Verified in `production-consolidated-v8` @`67a433bf4`:

- **CPU and GPU never run concurrently.** `ggml-backend.cpp:1665` drains the GPU
  (`ggml_backend_synchronize`) before every CPU split; `ggml-cuda.cu:786,794` are blocking
  copies; `ggml-backend.cpp:1678` calls a CPU `graph_compute` that blocks (`ggml-cpu.cpp:190`).
  Per-layer cost is additive: `t_gpu_attn + t_d2h + t_cpu_ffn + t_h2d`.
- **The CPU backend has no async surface at all** — `ggml-cpu.cpp:197-209` leaves `synchronize`,
  `event_record`, `event_wait` NULL, and `ggml-cpu.cpp:395-400` reports `.async = false,
  .events = false` (verified directly). Cross-backend event waits are explicitly unimplemented
  (`ggml-cuda.cu:2189-2200` aborts).
- **The existing pipeline machinery cannot be reused.** `llama-context.cpp:400-405` requires
  `n_devices() > 1` (we have one MI210) **and** `!has_tensor_overrides()` — and any
  `-ot`/`-cmoe`/`-ncmoe` sets that true (`llama-model.cpp:1044`, verified). The flag that creates the
  CPU-expert split is the same flag that disables pipelining. Even enabled it pipelines across
  micro-batches and excludes CPU backends by construction.
- **Only decode is in scope for us too**, for a different reason: op-offload is HIP-active with
  threshold ubatch ≥ 32 (`ggml-cuda.cu:5348`), and for `MUL_MAT_ID` the batch size *is* `n_tokens`,
  so prefill already pulls experts back onto the GPU. This independently agrees with the paper.

**The important structural point:** within one MoE layer the chain is straight-line
(attn → router → experts → residual → next attn), so there is *no independent work to overlap*.
Fixing the scheduler alone buys **zero**. Deferral is precisely the graph-level restructuring that
manufactures the independent work a concurrent scheduler could then exploit — the two are
complements, and both are required. That is the real shape of the effort, and it is why "port a
30-line scheduling rule" understates it by an order of magnitude.

Scope of a real attempt, on `llama.cpp-experimental` → v9 per the kernel workflow, never on frozen
v8: (a) emit deferred-expert graph nodes consuming layer `k−1` activations, per architecture, in the
model build path; (b) build a genuinely async CPU backend; (c) make the scheduler dependency-aware
(`ggml_backend_sched_split` at `ggml-backend.cpp:764` carries no dependency metadata and `:1549` is a
flat sequential loop). (b) is the deep one and it touches **every CPU-only serving path** — which is
all of production today.

### R-A6. What already ships, and what is already measured

Static CPU-expert offload is **not** the gap: `-ot` (`arg.cpp:2524`), `-cmoe` (`:2530`), `-ncmoe`
(`:2537`) all exist, applied once at load (`llama-model-loader.cpp:1164-1180`), matching
`LLM_FFN_EXPS_REGEX` (`common/common.h:1076`, verified) — which correctly does **not** match
`*_shexp`, so shared experts stay GPU-side, the same placement the paper uses. We have already run
it: Hy3-IQ1_M (~92 GB, over-HBM) hybrid `--cpu-moe --fit on` measured **11.51 t/s decode vs 5.21 t/s
CPU-only (2.2×)**, 5/6 tasks both lanes (`speculative-decoding-mtp-refresh.md:190`, observation-grade).

Capacity is a non-issue and should stop being discussed: our four MoE models are **90–97% expert
weight**, so the GPU-side residue is 2.5–6.2 GiB of weights plus KV — ~5.2 / ~5.5 / ~3.0 / ~12.3 GiB
for qwen36-35B-Q8 / gemma4-26B-Q4KM / qwen3next-80B / qwen35-122B against 64 GB. All four at once fit
in ~26 GiB.

### R-A7. Falsifiers — what would kill this

- **F1 (primary, and cheap).** The overlap ceiling is `min(t_gpu, t_cpu) / (t_gpu + t_cpu)` per
  layer. That ratio is **unmeasured** and is directly measurable from a static `-cmoe` run with
  per-split timing. If the GPU side is small relative to CPU expert time, the ceiling is small and
  no amount of kernel work redeems it. KTransformers' own Fig. 10 saturating at 3–4 deferred experts
  says the CPU becomes binding quickly even on their hardware.
- **F2.** If M2 (§5, `:60`) fails its own pre-agreed `≥1.5×` gate, family B closes and deferral has
  no host to attach to.
- **F3.** PCIe round-trip latency × 2 × n_layers per token could consume the overlap. We have **no
  measured H2D/D2H bandwidth anywhere in either repo**; the KB figures contradict each other
  (`gpu-acceleration-path.md:16` "~64 GB/s H2D" is the bidirectional aggregate misapplied to one
  direction, `:306` says "PCIe 5.0", `heterogeneous-slot-fabric-residency.md:72` says "~26 GB/s").
  Measured link state this session: `0000:43:00.0` `LnkCap`/`LnkSta` = **16 GT/s x16 (Gen4)**.
- **F4.** Quality at a deferral count that actually buys speed (≥3–4). Must clear our own eval tower,
  not the paper's single-run suites.
- **F5 (the one that should scare us).** An async CPU backend regressing ordinary CPU-only serving.
  Production is CPU-only today; a change to CPU backend async semantics risks the thing that pays the
  bills for a decode-only, batch-1, GPU-lane-only upside.

Vendor-side risk worth recording: the one shipped correctness bug in deferral was an **intermittent
data race on shared pinned buffers** on the `LLAMAFILE` (AMX-free) backend — the exact path an
AMX-free host would use — fixed in `e7d1c1d` with a permanent repro harness retained in-tree. And
issue [#1612](https://github.com/kvcache-ai/ktransformers/issues/1612) ("AMX only?") has sat open and
unanswered since 2025-11-15. The non-Intel/non-CUDA corner is the least-exercised one, and it is ours.
ROCm support is labelled Beta, developed on gfx1100 and gfx936; **no evidence of anyone running it on
gfx90a**, and `torch==2.9.1` is an exact pin.

### R-A8. Recommendation

**Do not authorize kernel work.** Run F1 first — it is one instrumented `-cmoe` decode run and it
decides the entire question before anything is built. F3 is a ~30-line `hipcc` microbenchmark
(`rocm-bandwidth-test` is **not** installed; `hipcc` is) and closes the largest measurement vacuum in
this whole area regardless of OD-A's outcome. Both are small, and both produce evidence that is
useful even if deferral is declined.

Explicitly **not** recommended: adopting KTransformers as a runtime. That means a forked SGLang
running parallel to v8, against this document's own sound "the fork is the substrate" finding.

### R-A9 — Tasks

- [x] OD-A researched against primary sources; demotion scope established as simulator-only ✅ 2026-07-29
- [ ] **F1 — per-split GPU/CPU timing under static `-cmoe`** on one MoE model; report
      `min(t_gpu,t_cpu)/(t_gpu+t_cpu)` per layer. Decision rule to pre-register before running.
      **This gates everything else in this rider.** Needs the GPU lane (region `q3` lock, P2-1b).
- [ ] **F3 — measure H2D/D2H PCIe bandwidth** (`hipcc` microbenchmark; `rocm-bandwidth-test` absent).
      Independently valuable; corrects three contradictory KB figures.
- [ ] **M2 `-ncmoe` sweep** (§5 `:60`) — designed, still unrun; bounds the synchronous baseline.
- [ ] **OPERATOR DECISION — ingest-or-reaffirm KTransformers** (`intake_index.yaml:45670`). It has
      never been ingested. Per the never-dismiss-without-asking rule this is not a self-authorized
      call, and no intake row was created by this rider.
- [ ] **OPERATOR DECISION — instrument-era / gate amendment.** If F1 justifies proceeding, `:26`
      ("static-at-load") and `mi210-big-model-and-acceleration-roadmap.md:254` (skew gate) need
      amending to record that the skew verdict tested caching, not overlap.
- [ ] Registry defects found mid-flight (unrelated to OD-A, filed here so they are not lost):
      `epyc-inference-research/orchestration/model_registry.yaml:1520` records
      `baseline_experts: 8` for `qwen3next`, but the GGUF says `expert_used_count = 10`
      (`expert_count = 512`); the 122B row records `size_gb: 69` against 72.88 GiB actually on disk.
- [ ] `gpu-acceleration-path.md:306` states PCIe 5.0; the link is measured Gen4 x16. `:16`'s
      "~64 GB/s H2D" is the bidirectional aggregate applied to one direction.

## Progress checklist

- [x] Findings deliverable produced (M0-M5; M0 CLOSED 2026-07-03) ✅
- [x] OD-A rider filed — KTransformers Expert Deferral scoped, costed, falsifiers named ✅ 2026-07-29
