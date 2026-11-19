# 2026-11-17 autokernel

## C13 fold recorded (operator-approved 2026-11-17)

Champion candidate C13 = `bda43aa17c11b671e0e203e7eb7bf4f1303bc273` (branch `llama.cpp-experimental-c12-lb49-sinks-20261117` = C12 `457d5fc52` + 4 LB4.9 sinks commits; default-off, compiled out when GGML_IQK_FLASH_ATTENTION=OFF as in the C12 recipe). Evidence: ak-lb49-sinks-gate-c12-20261117 PASS (80 cases, max NMSE 1.75e-9, mutant red on all 4 routes); lb49-sinks-identity-c12-20261117 PASS (default-off greedy identical).

Records: champion headline now C13 (C12 predecessor, C10 last promoted); AKX-ALL-LB4.9 ticked in autokernel-akx-program.md (AKX-ALL-LB4 left open, it names the iqk FA fold decision); manifest row V11-143. Open fold work now rebases on C13. No compiles or inference run.

## Operator-invoked wrap-up, 2026-11-17 (autokernel, ad hoc, no lane)

### Champion and decisions

- **Champion headline: C13 = `bda43aa17`** (C12 `457d5fc52` + LB4.9 sinks, default-off, compiled out); **C12 = C11 + bundle1**. Recorded in `fda6fd8a7`.
- **Operator decisions today (v11 checklist, recorded in `2f5b17729`):** D2 keep turn-1 grammar OFF and flip llguidance; D3 quality cap 4096 with truncation counts; D4 promote C13 and move CH-18 to v12; D8 build-preflight row only (`V11-C13-BUILD-PREFLIGHT`). D1 ratified `1fb5f4474` (V6R-4b forward-port rule). **D6 / D7 remain open** (operator decision queue).
- **Other closures:** INF-40 confirm run (operator go) -> result DROP; WRAP-5 build-repro -> not reproducible (tool misuse, no upstream post); Python 3.13 re-pin research `043120e83` (C6 controller-proof bundle). HIP port policy: run last, cap 10 more runs.

### Results filed today (`compute-flags/filing-done/*20261117*`, `*20261116*` verdicts, autokernel rows)

| Row | Verdict | What it means |
|---|---|---|
| `ak-asm-aiter-vs-c12-timing-20261117-r2` | science | AITER port candidates: topksoftmax **8.39x** (A3B), i8gemm **1.49x**; no port fmoe-g1u1 0.86x, bf16gemm 1.07x. Indicative (kernel-only vs graph time, no quiet q3). 2 port boxes filed |
| `ak-mmq-h10b-c12-census-20261117-r3` | MOE_RUN_INVARIANT | H10b: MoE path run-invariant on C12; dense 27B in-process defect persists at about the C10 rate (1/15) |
| `ak-lb49-sinks-gate-c12-20261117`, `lb49-sinks-identity-c12-20261117` | PASS | LB4.9 gates pass on C12; default-off greedy identity holds -> C13 fold |
| `akx31-edge-q38fn-{cpu,gpu}-20261117` | EDGE_PASS both | C12 clears the edge gates. Finding: **v10 production HIP iq4_nl MUL_MAT_ID overflows to non-finite on near-f16-max activations** (half-precision sum), filed as EDGE-HIP-NONFINITE; `akx31-qdec-c12-gpu` r1 QDEC_FAIL as recorded, r2 FUTILITY_NO_RESIDENCY (instrument) |
| `inf48-race2-fixtures-20261116-r2` | FIXTURES_READY 7/7 | race mutants all have a changed kernel; r1 was 0/7 |
| `rvp-att-canary-r4g-20261116` | PASS | ATT canary plumbing closed (r4f FAIL_PARTIAL_PATH preceded it) |
| `ak-gpu-signals-ctr-20261116-r2` | PASS 10/10 | all counter passes both surfaces, ISA witness no contradiction (r1 PARTIAL 0/10) |
| `inf48-eqv-fa-rescale` | rescale bug CAUGHT (by rescore); r2 FUTILITY_INSTRUMENT | spawned FA-ALLMASK-NAN and FA-HS256-MMA-PRECISION boxes |
| `fa-bugfix-gpu-20261117-r2` | FAIL_ALLMASK with progress | fix `c5babe0fd` passes 228/240; 12 hsk=128 decode cases remain; hs256 precision loss localised to CDNA D256 tune; r3 running |
| `inf86-g5-nsession-20261117` | BOUNDED_NULL_1 | **G5: no cross-session eviction** up to 8 sessions at 16K/56K, 0 wasted re-prefill |
| `inf86-template-preserve-20261117-r2` | NO_DEFECT | production template renders prior turns byte-stable |
| `inf86-pr25592-c12-ab-20261117-r2` | NO_GAIN | PR #25592 does not cut our waste (older-turn suffix); not a fold candidate |
| `inf40-moespec-confirm-c12-20261117` | DROP | MoE-Spec -4.30% decode geomean vs +5% bar; registry integration does not proceed |
| `wrap8-static-chunks-ab-20261117` | INCONCLUSIVE_NOISE | identity holds (ppl byte-equal); speed inside noise |
| `up-farows-hip-gpu-20261116` r2..r13 | diagnostics | **src[7] graph presence corrupts** the FA node even when ignored (r10 GRAPH_PRESENCE; NR 0/32 garbage vs NA/NB coherent) -> side-channel redesign `c32f096a9`; r13 and c13/c12 builds died on the llama-ui-assets network download |
| `up-convsnap-*` (11-15/16) | DROP | convsnap no gain |
| `c12-cpu-validate-20261116` r1..r4 | r2 DROP at old KLD bar; r3 INVALID_UNITS under amended bar (gates passed); r1/r4 build/proof futility | r5 running |

Row-hygiene fixes: controller-in-GPU-grant flock self-deadlock fixed `e8d969919` (Pipeline); keeper builds from git archive need a seeded offline UI dist (lesson filed below).

### Rows live or queued at wrap-up (queue_status 20:14Z)

- RUNNING: `c12-cpu-validate-20261116-r5` (q0+q1, to 04:03Z 11-18), `fa-bugfix-gpu-20261117-r3` (MI210, to 23:18Z), `inf86-g4-restore-reuse-20261117-r2` (q2, to 23:03Z).
- GRANTABLE/QUEUED: `inf75-c12-w5s-census-20261117-r3` (host), `v11-c13-build-preflight-20261117-r2` (quarter), `q38p1-c13-20261117-r2` (2 quarters).
- SMOKE-QUEUED (GPU, dryrun/*/GPU-SMOKE-QUEUED.json): `ak-c12-greedy-aa-bisect-20261117-r3`, `akx31-qdec-c12-gpu-20261117-r3`, `c13-farows-sidechannel-gpu-20261117-r2`, `c13-q81-sum-overflow-gpu-20261117`, `c6-admission-live-proof-r7`, `up-farows-hip-gpu-20261116-r14`.
- UNFILED-ENDED: 0.

### Wrap-up bookkeeping

- Handoff checklists were synced per verdict in `7eb59441d`, `487484074`, `2f5b17729` and siblings; this wrap-up adds no new box flips.
- Lessons (9) appended to `docs/guides/agent-workflows/compute-fillers.md`.
- Index `Next action` cells refreshed for INF-06, INF-48, INF-65, INF-70, INF-82, INF-83, INF-85, INF-86; pruning outcome in the wrap-up commit message and the session report.

## Research intake: Exstill arXiv 2611.18859 (intake-2669..2673)

**Source.** Exstill, "The Most Efficient Single-Chip Processor for the Next Token" (arXiv 2611.18859v1, 2026-11-13). It describes a chip that has not been fabricated yet: one model architecture is fixed in the datapath, and the weights plus all KV caches stay on the die. All chip figures are pre-silicon estimates, compared against a B300 running vLLM as shipped. Credibility 1. Filed `stage1-unverified` / `read_depth: PARTIAL`. The operator chose option (a): no arXiv HTML rendering exists, the PDF quotes were checked by hand, and no anchor mark is possible.

**Deep dives (two sweeps, the operator's cap).**
- Sweep 1: the paper, Gimlet's draft-model disaggregation blog (intake-2670), and NVIDIA's spec-decoding co-design blog (Mitra et al., intake-2671).
- Sweep 2: NVIDIA's attention co-design blog (intake-2672) and Gimlet's recursive self-optimization post (intake-2673, knowledge-only).
- The four blogs are `dive-verified`, with anchor marks written by the script.
- Declined at the cap: Ranjan 2026 (recommended for the next intake), NVIDIA co-design Part 1, MoESD, 2605.09992, Jouppi 2021.

**Ranked techniques.**
1. Verify-batch tile alignment: choose the draft length D so that G(1+D) lands on our FA/MMQ tile boundaries.
2. Two-line decode decomposition: the intercept is the fixed per-step charge, the slope is bytes over bandwidth.
3. AK planner Amdahl-ceiling prune (loop efficiency).
4. Keep the Pareto front of near-miss candidates per workload (loop reuse).
5. Re-sweep D whenever a drafter changes device or speed.
6. Split-K reduction share at short KV (folded into item 1).

Energy-delay scoring, bits-per-byte quality and model/silicon co-design are knowledge-only.

**Boxes (operator-approved, commit `acf9c6b6b`).**

| Box | Handoff |
|---|---|
| RKA-VERIFY-TILE | `rocm-kernel-authoring.md` (INF-48) |
| INF70-TWOLINE | `cpu-decode-roofline-program.md` (INF-70) |
| AK-AMDAHL-PRUNE | `autokernel-loop.md` (INF-06) |
| AKX-PARETO-RETAIN | `autokernel-akx-program.md` (INF-82) |

The K3 D re-sweep trigger landed in `speculative-decoding.md` (INF-50) through Pipeline in `dc07bb9f4`. Commit `06200fcf1` then set intake-2670's `handoffs_updated` to point at it.

**PDF-anchor gap.**
- The anchor extractor accepts text media only, so a PDF-only arXiv paper cannot be `dive-verified`.
- New raw-anchor root: `/mnt/raid0/llm/state/vidya/raw-anchors` (owned by the current user, mode 700). It holds the four blog HTML snapshots.
- `source_revision` must equal the artifact's `effective_url` exactly.
- Lesson added to `.claude/skills/research-intake/SKILL.md` (fetch-route notes).

**Validation.**
- `validate_intake.sh`: 218 errors, the same count as clean origin/main; none are on intake-2669..2673.
- `index_state.py --check`: 0 problems.
- `vidya sync`: exit 0.

## Research intake: BLACKFURY Exact (intake-2674), Stages 1-4

- **Source:** github.com/Maharajahu/qwen3.8-27b-nvfp4-blackfury-exact-tensorfold @ 2790f0472. A single author's Apache-2.0 patches on TensorFold 6e9af93 (TensorFold is intake-1924), serving Qwen3.8-27B NVFP4 + DFlash2 on one RTX 5090 under Windows. Credibility: null (repo). Receipts are careful (hash-bound, offline verifier, identical token IDs), but there is no independent reproduction and rebuilt binaries were not GPU-run.
- **Controlled results:** paired gate+up FP4 launch +0.891% decode with DFlash2 and +1.835% without drafter, no prefill gain. Exact long-context attention tail (grid 8 to 40 blocks, same reduction order): kernel 94.59 to 47.90 us, +4.58% warm decode at 129k+2k. 12-branch shared-prefix replay +34.21% aggregate. The README's +10.20% is cross-release, not controlled.
- **Deep dives:** one sweep of the two allowed. Four dive-surfaced sources were all declined as already indexed or dived: TensorFold (intake-1924), DFlash2 blog, z-lab/dflash, and the NVIDIA Qwen3.8-27B-NVFP4 card (sibling intake-756).
- **Ranked techniques:** (1) exact-order split-KV / tail widening for MI210 long-context decode FA (high; any weight quant); (2) bitwise token-ID gate for exact-order kernels (loop principle); (3) paired gate+up launch (low, about 1-2%, mostly absorbed by the HIP graph); (4) synchronized branches (serving, knowledge only); (5) NVFP4 (already in tree; gfx90a emulation costs the same as IQ4_NL).
- **Boxes landed (operator-approved 2026-11-17):** INF48-FAVEC-TAIL and INF48-GATEUP-PROBE in handoffs/active/rocm-kernel-authoring.md; INF06-EXACT-LANE in handoffs/active/autokernel-loop.md. intake-2674 citation added to AKX-ALL-LB3 in handoffs/active/autokernel-akx-program.md.
- **Decision:** NVFP4 stays excluded for the architect role (knowledge only).
- **Loop-efficiency principles:** exact-order lane gated by token-ID identity, skipping the quality eval; A-B-B-A ordering with a fresh process per cell; a same-binary microbenchmark is not an end-to-end gain; a control that produces different text cannot isolate a kernel effect.
- **Commits:** intake entry 5fdde0371; Stage 4 9bcbeb92a (boxes, deep-dive Markdown, digest, disposition, index regen). Validator: 218 errors, all older entries, none on intake-2674. index_state --check: 0 problems.
- **Lessons:** (a) for a repo intake, the `source_artifact.entry_url` of a claim anchor must equal the entry's `url` (the repo URL), not the raw-file URL, or `--check-anchors` reports `source_unavailable` and writes no mark. (b) `intake_dive_digests.py --ids N-N` emits the whole same-day run that overlaps N (here 2674-2693), not only N. (c) `discovered_via` takes only seed, input, expansion or search, and repo entries need an explicit `arxiv_id: null`.
