# Window-2 findings 03 — Portfolio audit, resurrection sweep, and proposed master-queue rewrite (§3 + §8.4)

> **Fold destination** (BRF-T1-F10, BRF-T1-1, route 1a, 2026-11-02): absorbs 4 handoff(s) as `## Track:` sections at the end of this file (`cpu-fused-decoder-blocks.md`, `laguna-s21-cpu-port.md`, `moe-spec-cpu-spec-dec-integration.md`, `v9-kernel-per-request-speculative-params.md`). The body above the first track is the former `fable5-window2-findings-03-portfolio-and-master-queue.md`.

**Method**: index-driven per the brief — master index + 6 domain indices + `bulk-inference-campaign.md` read in full by dedicated agents; owning handoffs sampled only to confirm ambiguous lines (~20 sampled of ~349). **115 outstanding items triaged** (routing 26 + acceleration 23 + CPU 8 + research 26 + hermes 6 + pipeline 11 + campaign/queues 15). This is a **proposed** rewrite artifact — no live index was edited (CLAUDE.md rule).

Triage totals: **keep 72 · revive 15 · reorder 15 · merge 8 · kill 5**. Full per-item tables with deciding facts live in the evidence bundle (`/tmp/claude-1000/.../scratchpad/dives/portfolio-*.md` this session; deciding facts reproduced below only where they change the queue).

> **APPLIED 2026-07-03 (operator-directed).** The write-authority constraint that held this as a *proposal* was lifted by explicit operator request ("reprioritize all backlog work keeping your strategic recommendations front of mind"). The §4 rewrite + the DGX→MI210 un-stalings were applied to the live `master-handoff-index.md` (§F rewritten to an ordered GPU queue; §A0 strategic-priorities block added; §B2-F3 un-gated) and to 10 owning handoffs/indices. A parallel intake/deep-dive sweep (findings-05) added 22 missed-tasks + the kernel roofline analysis. See [completed findings-05](../completed/fable5-window2-findings-05-intake-sweep-and-roofline-completed-through-2026-08-13.md) §7 for the full list of files touched. Edits are uncommitted pending operator review.

## 1. The five findings that shape the queue

1. **Three gates already fired and nobody noticed.** `pipeline-integration-index` still says "DGX-GATED (no training GPU)", "reopen only with GPU availability", "GPU/Spark rebench when available" — all pre-date 2026-07-02. `speculative-decoding-mtp-refresh.md:104` itself says "Trigger now due (2026-07-02): the MI210 has landed" while the acceleration index shows "No open MTP action." The gpu-drafter handoff's own header flipped to "hardware gate now OPEN."
2. **One internal contradiction.** Routing index L86 holds AB-MCTS on "W4/W6 readiness currently blocked" while its own L41/L74-75 record authority live and readiness green — an agent pointed at the index would wait on a gate that opened.
3. **The evidence-plane trigger releases a whole shelf.** Items gated on "N2 ledger vectors" now have 200+ trusted vectors live: EV-4/H5 calibration, K-DIV-1 thresholds, K-SKILL-1 paired validation, F1-W3 ledger run, J16's N2 conjunct, Q3-2 accept gates, and — highest leverage — **the DAR-1 regret replay is now runnable and is queued nowhere** (the freeze row treats itself as terminal).
4. **The campaign's cost model is stale.** `bulk-inference-campaign.md` line 47 still says "authority remains disabled until readiness passes" (it passed 2026-07-02), Queue 1 is 100% closed items, and the 28–31 h quiesce window + "E2-first makes every later eval cheaper" arithmetic assumes CPU-only eval. Re-plan after the Gate-R placement decision (findings-02 §5).
5. **Prune debt is real but modest**: 5 kill rows (completed work sitting in outstanding tables: P0 restart, LRC P4.5/4.6, K-MEM, NUMA-private-weights CLOSED-NEGATIVE, G11/G10 scored) + ~170 lines of A9 chronology violating the routing index's own "live work only" rule.

## 2. Resurrection sweep (§3) — MI210 (T1) and evidence-plane-live (T2) triggers

### Revive (criterion verbatim-matched; honest caveats noted)

| Item | Reopen criterion (source) | Trigger | Caveat |
|---|---|---|---|
| Qwen3.5-hybrid spec-dec via DFlash/DDTree on GPU | "Activation trigger unchanged: acquisition of training-capable GPU… on GPU the recurrent state uses parallel scan — the verification bottleneck disappears" (`gpu-acceleration-path.md:16,76`) | T1 verbatim | Reference impls are CUDA-targeted (Lucebox sm_86+; vLLM DDTree planned for Blackwell); ROCm port unverified. Our own DFlash C++ forward pass is verified correct to <0.01 — the algorithm was never the problem |
| Slot-promotion dispatcher v1 with GPU-hosted drafter | 5th documented trigger: "Drafter on dedicated compute (GPU), removing DRAM BW contention" (`gpu-drafter-mi200-investigation.md:161-163`) | T1 | Sequence behind findings-02 M0/M4; code "stays in tree — re-eval requires no rebuild" |
| F3-W3 GPU fine-tunes (planner-distill QLoRA, drafter training, EV-9 judge) | "HW-GATED — do not start before the MI210 card" (`frontier-f3-data-flywheel.md:24`) | T1 | Data gate still binding: 0/100 reviewed triage labels; F7 already records planner-distill as economically justified ($410.75 vs $250 threshold) |
| delta-mem Gate 2/3 + M.3 sidecar training | "DEFERRED until GPU available OR a separate small-context eval" (`delta-mem-reproduction.md:156`) | T1 verbatim | Gate 3 already passed directionally at N=5 (1.65× vs paper 1.20×); flash-attn-on-gfx90a unverified |
| Embedder/classifier/reranker GPU host | findings-03(w1) MI210 use #3; HW arrival was the gate | T1 | Third card in the sequencing — after residency/eval; it is a migration (BGE servers live today), not new capability |
| CAP-REG W4 (restart-class levers to AutoPilot) | "W1–W4 wait for evidence-plane-ledger (findings-01 Phase 1)" (`capability-registry-and-promotion.md:85`) | T2 | Operator call whether Phase-1-certified requires W8 evidence first; scaffolding (W0–W3) already landed. **Recommend: also gate on findings-01(w2) R1+R4 — do not hand restart levers to an optimizer whose refutation loop is open** |
| Accept-path bundle (K-DIV-1 thresholds, H5/EV-4, K-SKILL-1, EV-8/9/10, J16-N2-conjunct, Q3-2 J11/BSV-2) | "restart bundle WITH findings-01 ledger/verdicts" (master-index:148) | T2 | Sequence after W8 tail; run per-item, flag-isolated as the campaign already specifies |
| GSA/KSA summary-token CPT — Gate C *scoping only* | "Gate C — GPU acquisition that lets us run our own CPT" (`summary-token-attention-readiness.md:72`) | T1 verbatim | The tracker itself limits revival to scoping; one 64 GB gfx90a as CPT budget is unassessed |

Plus portfolio-discovered revivals: **EAGLE-3→MI210** (mtp-refresh's own trigger "now due"); **ERNIE image GPU rebench** (gate clause fired verbatim); **doc-to-LoRA trigger re-evaluation** (GPU conjunct fired; REPL-need conjunct still unmet — formally re-evaluate, expect still-dead); **UniRL** (blocker "no training GPU" no longer literally true; fit vs one gfx90a unassessed); **AB-MCTS design→experiment** (stale blocker, finding #2 above); **H7 Ouro-2.6B** (transformers-on-ROCm removes CPU contention; now on H5's critical path).

### Stays dead (equally valuable — do not re-open)

| Item | Why still dead |
|---|---|
| TiDAR Variant B | Gate is *checkpoint existence*, not hardware; none exists. Premise (idle CPU FLOPS at BW-saturation) is CPU-roofline-specific and doesn't transfer to the GPU. (BF16-on-GPU rescope = new premise, operator call) |
| DAR-3/SPO+/Package I/LRC-Ph1.5+/Trinity TR-4/5/J14-beyond-kill | Conjunctive gate: regret ≥5% AND vectors. T2 satisfies only vectors; the 2026-06-12 replay measured **0.00% regret over 12,057 decisions**. Infrastructure cannot manufacture regret. Correct action: run the replay (R16), don't reopen the work |
| 08-doc-to-lora Phase B | AND-gate: GPU ✓, "demonstrated need REPL retrieval doesn't cover" ✗ (recorded as solved by REPL tooling) |
| Task-rate/goodput live flip (W3) | Triple conjunct; W5 core_v2 still no-go (see findings-01 R2 — the *path* to reopening runs through the ledger-derived core) and the task-rate frontier admits five quality-floor violations |
| DCP pre-assembly enablement | Held on *adverse measurement* (ON p50 32.6 s vs OFF 20.2 s), not missing instrumentation |
| SpecDiff-2 / Jacobi-Lookahead / CLLMs | CUDA/vLLM-custom impls, 7B+ PyTorch diffusion drafters, retraining required; dominated by the already-active DFlash/EAGLE-3 GPU plan |
| Ouroboros multi-model validation | Archived with explicit "write a fresh handoff, do not resume"; references a deprecated stack |
| Vulkan on gfx90a | Falsified on this exact hardware 2026-07-02 (no ICD); do not re-attempt |
| Dispatcher-v1 as-is on CPU (Qwen3.6+Qwen3-1.7B) | Net-negative stands; pair now also known tokenizer-incompatible |

**Appendix (best-effort)**: reasoning-compression enforce decision accrues n≥100 via the live ledger; F2 self-running-lab's gates (N1+N4, N2) are now largely live — its first real quiet-window outputs are runnable; `handoffs/blocked/` is empty (nothing tracked); v6-consolidation trigger yielded zero revivals (N13/N14 residuals are operator-owned clean-window items, not shelved work).

## 3. Index fitness verdicts (one line each)

- **master-handoff-index**: dispatch function works; N-rows carry chronology that belongs in progress logs; N13 is complete-in-substance and should archive; generated A-by table is the right pattern — extend it to gate-state so fired gates surface mechanically.
- **routing-and-optimization**: structurally conformant; violates its own live-work-only rule (~170 lines A9 chronology); 2 completed rows in outstanding tables; the AB-MCTS self-contradiction; zero MI210 awareness.
- **inference-acceleration**: 17-row flat landscape with no priority marking while its highest-leverage row (GPU/MI210) sits unranked; two of its own handoffs' triggers fired without re-triage.
- **cpu-inference-optimization**: not stale on the CPU1 ceiling (L3aaN correctly rejected); holds one CLOSED-NEGATIVE row in the active queue; needs an MI210 re-triage pass, not deletion — CPU remains the production substrate today.
- **research-evaluation**: top HIGH gate ("do not enable authority until readiness passes") executed and now inverted; four rows wait behind the released gate; duplicated rows across Queue/Packages tables invite drift.
- **hermes-agent / pipeline-integration**: structurally fine; pipeline's three fired GPU gates are the staleness hotspot.
- **bulk-inference-campaign**: the real problem doc — 581-line dispatch/runbook/archive hybrid; Queue 1 is 100% closed; header contradicts the master index on authority state; its "everything is in three queues" claim is falsified by J8/J14/J17/H4/G2-G4/K-DIV-1 living outside every queue; cost model pre-dates the GPU.

## 4. PROPOSED master queue rewrite (replacement for master-index §A/§B — delivered as proposal, not applied)

### A. NOW — this week

- [x] **G0 · α from live logs (zero inference, today)** — parse per-role MTP acceptance from production llama-server logs; publish per-role α_MTP with a loud zero-lines failure. *Owner: gpu-drafter-mi200-investigation.md (retitle its Gating Measurement).* [findings-02 M0] ✅ 2026-07-17 (`scripts/benchmark/mtp_alpha_from_logs.py` `aa3b35a7`; live: worker_general draft-mtp α=0.994, frontdoor 0.603, architect 0.629; loud-fails on zero evidence)
- [x] **G1 · Ratify P-GPU-1** (operator; measurement trust boundary — human-amendment-only). [findings-02 §5] ✅ 2026-10-29 (audit: MEASUREMENT.md:67 P-GPU-1 MI210 GPU canonical throughput "ratified 2026-07-19"; commit d0689d251 duty_cycle amendment RATIFY-PGPU1-DUTY-CYCLE-20260814) [no-belief: audit-reconciliation]
- [ ] **G2 · Canonical-tree HIP build + `qwen35moe`/`qwen3next` op-coverage smoke** (no window needed; LD_LIBRARY_PATH hazard documented). [findings-02 M1-prereq]
- [x] **G3 · Frontdoor residency bench under P-GPU-1 → Gate R decision** (≥1.8× → R12 plumbing; 1.3–1.8× → HIP-kernel track critical; <1.3× → residency demotes to eval-only hosting). [findings-02 M1] ✅ 2026-10-29 (audit: commit b34a1203c 2026-08-14 "frontdoor Gate R verdict ... GPU is 2.5x, clears gate"; wrap-up 2f13b3e8d) [no-belief: audit-reconciliation]
- [x] **I1 · `seq_refuted` learning exclusion + strategy-store quarantine parity** (code + tests, zero inference). [findings-01 R1] ✅ 2026-07-17 (code was already wired in aa20d029; parity locked by test_seq_refuted_learning_exclusion_parity.py `0492c07a`)
- [ ] **I2 · Ledger-derived core_v2 selection** (read-only rebuild; demote 2026-06-15 calibration lineage to prior; compare item sets). [findings-01 R2]
  - [x] Post-E8 read-only rebuild + comparison ✅ 2026-07-29 — `core_v2_select.py --source ledger --min-attempts 5` wrote the non-promoted artifact `/mnt/raid0/llm/tmp/mainc-core-v2-20260729/{core.jsonl,report.json}`. The active era fence (`1785004723.0`) retained 16 trusted rows / 50 observed items and excluded 1,317 pre-era rows, yielding only 2 eligible / selected items (shortfall 38); neither overlaps the prior 40-item `core_v2_ledger_20260703_min5` selection. `tests/unit/test_core_v2_select.py` passed 6/6. No era amendment or activation was attempted.
  - [ ] Accrue a current-era, trusted ledger that yields at least 40 eligible core items before preparing any new `autopilot_quality` era row or activating a replacement core; the present 2-item artifact is evidence of insufficiency, not a candidate for promotion.
- [x] **I3 · DAR-1 regret replay over live ledger** (offline; the routing-unfreeze gate IS this replay). [R16] ✅ 2026-10-29 (audit: DAR-1 current-traffic replay done 2026-06-12 (completed/decision-aware-routing-completed-through-2026-09-27.md:23); commits 6712dceea, 0bf5b520e "Close stale DAR-1 replay queue item" (2026-07-03)) [no-belief: audit-reconciliation]
- [ ] **N2-tail · W8 promotion-eval evidence** (unchanged owner: evidence-plane-ledger-and-sequential-verdicts.md).

### B. NEXT — gated on NOW outputs

- [ ] **R12 · Orchestrator GPU plumbing** (gate: G3 ≥1.8×): registry device/accel block → lean compile → launch args → runtime attestation (three-gates lesson). 
- [ ] **M2/M3/M4 · architect `-ncmoe` sweep · op-offload prefill probe · batch-K verify curve** (GPU lane; M4 wants a brief window).
- [ ] **I4 · 33-flip-item discriminating re-run** (conc 1 vs 3, error_detail on; 1–2 h window). [findings-01 R3]
- [x] **I5a · α-wealth budget across fingerprints + W6 monotone trigger/fence governance.** R4 closed in orchestrator `62b24aa8`; R5 closed in orchestrator `ef70f859`. [findings-01 R4/R5]
- [x] **I5b · `StrategyStore.store()` write-side provenance validation.** R6 closed in orchestrator `796119ec`: write-side evidence validation, provenance stamping, journal-aware filtering for non-operator provenance-less rows, and operator-seeded hypothesis preservation. [findings-01 R6]
- [ ] **C1 · Campaign re-plan post-Gate-R**: substrate field per manifest entry; quiesce window shrinks to CPU-topology probes (shape-keyed bracket, J2/J3, E1); eval-shaped items (J12/J15, G5 remainder, K-MEM slice, H7, K-EMB Phase B) move to the GPU lane. [R14]
- [ ] **C2 · Accept-path bundle, per-item, flag-isolated** (after W8): K-DIV-1 thresholds → EV-4/H5 (H7 first) → K-SKILL-1 → J11/BSV-2 → J16 premise re-verify.
- [ ] **HOLD-pending-Gate-R: E3 8×8 GEMM SIMD; MoE-Spec CPU Phase-0; sarathi-serve gate re-read.** [R15]

### C. Revived shelf (schedule opportunistically; owners above)

EAGLE-3/DFlash-on-MI210 (only after M0+M4 verdicts) · slot-promotion-with-GPU-drafter (same gate) · embedder/vision GPU host · F3-W3 (data gate first: 100 labels) · delta-mem Gate 2/3 · ERNIE GPU rebench · GSA Gate-C scoping · CAP-REG W4 (recommend additional gate: I1 plus I4/R5/R6 landed) · AB-MCTS experiment · UniRL fit assessment.

### Dependency graph

```
G1 ──► G3 ──► Gate R ──► R12 ──► C1 (GPU eval lane) ──► C2 scheduling eases
G2 ──►  ▲                   └──► M2/M3 same lane
G0 ──────┴─(drafter leg)─► M4 ──► EAGLE-3/DFlash/slot-promotion go|no-go
I1 ──► CAP-REG W4 (recommended gate)
I2 ──► core_v2 promotion ──► task-rate/goodput W3 conjunct #2 ──► (with I3≥5%) routing unfreeze
N2-tail(W8) ──► C2 accept-path bundle
I3 ──► routing unfreeze conjunct #1 (expect: stays frozen)
```

### Cross-cutting concerns

1. Any GPU role migration passes the stack-change three gates (pipeline green ≠ starts ≠ live==config) and adds a GPU witness surface to swap-CI.
2. GPU numbers gate nothing until P-GPU-1 exists (G1 blocks G3's *decision*, not its dry run).
3. The evaluator is a placement-problem citizen: eval-lane throughput changes every window-cost estimate — re-cost C1 before scheduling any >4 h window.
4. Era hygiene: I2's demotion appends to `instrument_eras.yaml`; W6 fence moves follow the R5 disposition rule.
5. Routing retrains (if I3 ever fires) must first wire read-time exclusion into training-data assembly (findings-01 G5).

### Reporting

On completing a row: delete it here, update owning handoff + domain index, append to `progress/YYYY-MM/`; numbers use the claim grammar; fired-gate sweeps (this window's finding #1) become part of the weekly freshness check — a gate whose condition names hardware/state that now exists is a staleness violation even if <14 days old.

### Key files

`/mnt/raid0/llm/llama.cpp` (HIP: `ggml/src/ggml-cuda/`, `common/arg.cpp` spec/device flags, `tools/server/server-context.cpp`) · `epyc-orchestrator/scripts/server/{orchestrator_stack,stack_manifest,stack_numa,stack_paths}.py` + `orchestration/model_registry.yaml` (master: epyc-inference-research) · evidence plane: `scripts/autopilot/{safety_gate,eval_tower,audit_block_report,restart_readiness_report}.py`, `src/autopilot_core/{sequential_verdict,learning_exclusions}.py`, `orchestration/repl_memory/strategy_store.py` · α: `epyc-inference-research/scripts/benchmark/n5_frontdoor_drafter_retest.sh` + `scripts/utils/check_draft_compatibility.py` · MI210 artifacts: `/mnt/raid0/llm/tmp/mi210-build/`, `progress/2026-07/2026-07-02-mi210.md`.

## Track: cpu-fused-decoder-blocks
<!-- gate: none -->

> Folded from `handoffs/active/cpu-fused-decoder-blocks.md` @ `0001c77da2e5` on 2026-11-02 (BRF-T1-F10, route 1a, operator D1/D5; retired row INF-67 → EVL-21). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### CPU Fused Decoder Blocks (batch-1 decode megakernel)

**Status**: **A-GATE FAILED 2026-09-02 — the plan below is the historical design record, not a live plan.** ~~**PLAN APPROVED by operator 2026-08-30** — bit-exactness prioritized (NMSE ≤1e-4 acceptable fallback); qwen4exp-first with the GDN family in mind; op-based execution model (direct fast-path acceptable if diligent); decode prioritized, pp desirable; plan persisted before work begins.~~ The approval stands as a historical fact; what it authorised did not pass its own gate — see *Viability gate result 2026-09-02* below (fused 961 ms/token vs graph 196.9 ms in the same process and window). The 2026-09-01 control arm reproduced the same direction (graph-1T 350 ms vs fused-1T 1350 ms): **the megakernel does not currently deliver, and the scratch churn is the liability.**
**Created**: 2026-08-30
**Priority**: ~~HIGH — the last identified path to 20-60 t/s batch-1 CPU decode~~ **STALE 2026-09-08 (INF-70 audit)** — the "last identified path to 20-60 t/s" framing predates A-GATE. Re-ranking this handoff's priority is an operator/owning-session decision and is deliberately NOT made here; note only that the operator directive of 2026-09-07 stops lever research until a fully consolidated champion exists.
**Categories**: hardware_optimization, inference_serving, local_inference, kernel_architecture
**Workstream**: Inference Acceleration
**Parent index**: [`inference-research-index.md`](inference-research-index.md) (row INF-67; the kernel-tree commit tags historically said INF-64)
**Related**:
- [`cpu-shape-specialized-gemv-decode.md`](../completed/cpu-shape-specialized-gemv-decode.md) (INF-10) — the direct predecessor: same diagnosis (barrier/op-count-bound, not BW), 4 fusion arms REFUTED, the +2.6% DeltaNet-native-fused-wqkv precedent this project scales up
- [`batched-decode-measurement.md`](batched-decode-measurement.md) — the NUMA×placement canonical recipe (interleave+no-mmap), the same family's reference numbers
- [`autokernel-research-loop.md`](autokernel-research-loop.md) — the GPU megakernel/persistent-kernel literature (L4 lever) this project is the CPU analogue of
- `handoffs/active/master-handoff-index.md` — the router

**Framing superseded 2026-09-02 (INF-70 audit)**: this file remains the fused decoder's design record
and phase checklist. The live viability task list (A1–A4, A-GATE), the corrected measurement ledger and
the program this work now belongs to are in [`cpu-decode-roofline-program.md`](cpu-decode-roofline-program.md)
(INF-70). The section below is the historical design premise: the 74 ms anchor does not reproduce
(INF-68 measured ~110 ms UD / ~95 ms uniform on a clean build), the 28/46 ms split and the 65 µs/9.4 ms
constants are in no committed profiler record, and the measured node count is 7,906 pre-fusion /
~6,890 on the baseline build, not ~5,850. Do not quote this section's numbers; quote INF-70's ledger.

**Viability gate result 2026-09-02 (INF-70 Axis A, branch `inf70/fused`)**: with the batched `mul_mat`
substitution (A1) and the scratch arena (A2) both in, a clean Release build at `-t 1` measures fused
961 ms/token vs graph 196.9 ms in the same process and window — gemv column 810 ms, other column 150.6 ms;
logit gate max_abs 1.311 / NMSE 6.07e-2. **A-GATE FAIL.** Three fused-path correctness bugs the campaign did
not have were found and fixed on the way (GDN state byte/float offset, repacked IQ4_NL hc loras read as
plain rows, F16 `ple_conv1d` read as F32), and the pre-A1 per-row path aborts with heap corruption on the
pristine tree in Release. Details: `/mnt/raid0/llm/tmp/inf70/agents/fused/REPORT.md` and INF-70 Axis A.

#### The measured problem (2026-08-29/30, qwen4exp IQ4_XS UD, interleave baseline)

Batch-1 decode = ~74 ms/token (~13.5 t/s, t48; t64 sweet spot ~14). Breakdown, all in situ:
- ~28 ms real gemv work (expert mul_mat_id ~9.4 ms at ~65 μs/call median; dense ~18 ms) — at the machine's real memory rate (~100-180 GB/s in situ)
- ~46 ms of non-gemv dispatch: ~5,850 nodes × ~5-8 μs each (barrier + dispatch + tiny elementwise compute)
- Four clean-room kernel experiments (fused hc_mix op, elementwise chain fusion ×3, gemv software pipelining) all measured NEUTRAL or NEGATIVE in situ despite clean-room wins up to +55%. The per-node machinery cost is irreducible per-node; the only way down is fewer, fatter nodes.

#### The idea

Collapse the ~6,800-node decode graph to ~100 nodes: **one fused op per layer** (GGML_OP_GATED_DELTA_NET_FUSED_LAYER ×36 + GGML_OP_FULL_ATTN_FUSED_LAYER ×12 + PLE/head tail). The layer's math runs as one sequential kernel — data flows in registers/L2, no graph barriers between the layer's micro-ops. The per-node machinery runs once per layer instead of once per micro-op.

**Target**: ~28 ms gemv + ~96×15 μs fused overhead (~1.5 ms) + state/attention (~5 ms) ≈ 35-45 ms → **22-28 t/s**, with gemv micro-tuning inside the fused kernels (where dispatch can no longer eat it) reaching 30-40.

#### Operator decisions (locked 2026-08-30)

1. **Numerics contract**: bit-exactness PRIORITIZED (mirror the decomposed op order internally); NMSE ≤1e-4 acceptable where bit-exactness costs too much freedom. The arch test's CPU-vs-GPU NMSE bar applies as the floor.
2. **Scope**: qwen4exp-first; the GDN family (qwen3.5/qwen3next/qwen35moe) served by the same fused ops if it isn't disproportionate — the layer structure is shared via `llm_build_delta_net_base`.
3. **Execution model**: op-based (new GGML ops, ~100-node graph, fits the scheduler/backends). A direct decode fast-path outside the graph is permitted if it becomes clearly better — diligence required (the blast radius is real).
4. **Priority**: decode first; pp acceleration via the same ops (batched) is desirable but secondary.

#### Phases

| Phase | Deliverable | Milestone / gate |
|---|---|---|
| **0** | Measurement infra: fix the logit-dump tool (was crashing), standard A/B harness at the interleave baseline, in-situ profiler runs (all present from prior rounds) | reproducible fused-vs-decomposed logit diff ≤1e-4 |
| **1** | Fused GDN-layer function (36 layers): hc_mix + qkvz + conv + GDN scan (the ggml_gated_delta_net kernel) + output proj + MoE (router/top-k/topk-norm weights/expert dots/shexp) + hc_combine; recurrent + conv state in/out | decode 74 → ~45 ms; logit diff + greedy generation + arch test |
| **2** | Fused full-attn layer function (12 layers): QSA indexer (top-k blocks) + attention + gate + MoE; KV cache + indexer cache interfaces | decode → ~38 ms |
| **3** | PLE + head + tail; the process_ubatch hook; full fused decode | full fused decode + logit-diff validation |
| **4** | Thread-pool integration + gemv/activation micro-opt INSIDE the fused kernels (safe now — no dispatch to lose it) | 30-40 t/s |

Checklist (the dashboard gate — flipped as the phases land):
- [x] Phase 0: logit-dump tool fixed and verified; A/B harness + in-situ profiler established
- [x] Phase 1: fused GDN-layer function committed (`e57e1d542`) — compiles clean, single-threaded
- [x] ~~Phase 1 gate: logit diff ≤1e-4 + greedy generation + arch test (needs the hook)~~ (closed 2026-10-29 audit: SUPERSEDED → handoff header line 3: A-GATE FAILED 2026-09-02, plan is "historical design record, not a live plan"; fused path retired to opt-in in champion C5 (c72ec82f5))
- [x] Phase 3 partial: fused_head + fused_decode_token skeleton committed (`2d699f02c`)
- [x] Phase 2: full-attn layer function committed (`95902fefa`) — QSA indexer + flash-kernel attention; rotations + long-context indexer rope marked for the validation pass
- [x] Phase 3 partial: fused_ple committed (`8fd4c7f15`); head + decode-loop skeleton already in; the process_ubatch hook committed (`99a1c111e`)
- [x] ~~Phase 1 gate: logit diff ≤1e-4 + greedy generation + arch test (needs the MoE fix)~~ (closed 2026-10-29 audit: SUPERSEDED → handoff header line 3: A-GATE FAILED 2026-09-02, plan is "historical design record, not a live plan"; fused path retired to opt-in in champion C5 (c72ec82f5))
- [x] ~~Phase 4: thread-pool integration + fused-kernel micro-opt~~ (closed 2026-10-29 audit: SUPERSEDED → handoff header line 3: A-GATE FAILED 2026-09-02, plan is "historical design record, not a live plan"; fused path retired to opt-in in champion C5 (c72ec82f5))
- [ ] **FD-OFF-PROD — declare `GGML_FUSED_DECODE_OFF=1` for production `architect_general` (:8074) so serving matches every measured Q38FN number (filed 2026-10-24, 3c4ca599).** Every Q38FN speed/correctness result (research recipe, AK q38fn campaigns, `optimal_cpu_serving` 43.28 t/s) used OFF=1, but the production launcher does not set it, so :8074 runs the default-ON fused path, which carries the open FD-DIV-1b defect (synthetic weight scales; the real UD model was byte-identical in FD-DIV-1a) and the CH-24 `/tmp` debug writes. A ratification package (one operator command, env-diff proof, no reload; the owning session reloads `architect_general` afterwards) is being prepared at `/mnt/raid0/llm/tmp/ratify-fused-off-20261024/PACKAGE.md`. Blocker after the package exists: operator signature. Follow-up once FD-DIV-1b is fixed: measure fused ON vs OFF on Q38FN and decide whether serving should re-enable it.
  - *(2026-10-24 (3c4ca599) operator direction: fix in the champion, not production. Resolved in champion fold C5 (`experimental/champion-c5-20261024` @ `c72ec82f5`: fused decode default-OFF in code, opt-in GGML_FUSED_DECODE_ON=1; plus 14c57cbe9/CH-24 gating); reaches production at the next kernel promotion. RATIFY-FUSED-OFF-ARCHGEN-20261024 is parked (not to be run). workspace-58's v10 test: production :8074 as launched is coherent with zero fused calls (MTP verify batches skip the single-token fused path), so the defect was latent there.)*
  - *(2026-10-25, workspace-58 CAS subagent.)* **Resolved in champion C5**: the champion ref `ak/champion/llama-cpp-ffc1bac82eec` is now `c72ec82f5` (CH-31 CAS 2026-10-25T08:24:10Z, fork pushed), carrying `4976a189f` (fused decode default-OFF, manifest V11-106) and `c72ec82f5` (layout contract, V11-107). Not ticked: production is still v10 (default-ON) until the next kernel promotion; the box closes when the promoted v11 candidate carries V11-106. [no-belief: champion CAS is a ref operation; gate evidence is in c4/c5-fold-prep]
- [ ] **FD-DIV-1 — the Flash-Next (`qwen4exp`) fused decode diverges from the graph at non-production weight scales,
  and double-frees at w=1.0.** (filed 2026-10-04, workspace-ec; **owner TBD, the Flash-Next owner**)
  - The repro is committed as `45d8f2937` on `experimental/fused-yarn-20261004`: `QFR_*` knobs, with the log at
    `artifacts/dca-yarn-kernel-20261004/fused-divergence-repro.log`.
  - Default synthetic weights: OK (logits 1.7e-11).
  - `w=0.05, norm N(1,0.1)`: logits nmse 1.84, K 1.08, indexer 1.06 on all three rope configs.
  - `w=1.0`: abort, "double free or corruption (out)".
  - The divergence starts before attention, in layer 0 (GDN + MoE + hyper-connections).
  - **Keep `GGML_FUSED_DECODE_OFF=1` in production** until this is root-caused.
  - Done when the divergence and the double free are root-caused and fixed (fused ≡ graph within tolerance at
    w ∈ {0.05, 0.3, 1.0}), or the fused path is retired.
  - *(2026-10-23: FD-DIV-1a PASS. The real-model double free is fixed by `14c57cbe9` (GSQ falls through to the graph; UD fused path unchanged). **Still open:** the synthetic-weight divergence at w=0.05 and the w=1.0 abort of the repro, now FD-DIV-1b; plus the fold of `14c57cbe9` via the champion route.)*
  - *(2026-10-22, workspace-58 subagent, from NEW-10's smoke abort; box stays open.)* **Double free
    root-caused on a real model.** The GSQ-RCO Q38FN IQ3_XXS GGUF aborted the production CPU `llama-completion`
    (fused path ON, i.e. without `GGML_FUSED_DECODE_OFF=1`) on the first decode token with the same "double free or
    corruption (out)". Chain:
    1. GSQ stores `blk.*.ffn_down_shexp` as IQ4_NL (40 layers incl. layer 0; UD-IQ4_XS stores Q8_0). IQ4_NL is not on
       the `GGML_IQK=1` repack exclusion list (`repack.cpp`), so CPU_REPACK interleaves it (`iq4_nl_8x8`). Fused
       `lora_mm`/FusedMM does a plain per-row `vec_dot` at `data + row*nb[1]`, reading interleaved bytes as block
       scales, so the shared-expert down goes NaN at layer 0.
    2. Layer 1's `fused_moe` gets all-NaN router logits; no prob beats -INF, `best` stays -1, and
       `probs[-1] = -INFINITY` overwrites the malloc chunk size (0xff800000); the vector's `free()` then aborts "(out)".
    3. Second, latent bug: GSQ's `blk.1.ple_conv1d` is F16 and `fused_ple` read it through a `float*` (twice the
       tensor's bytes, garbage values). The graph already casts it to F32 (`build_ple`).
    - Patch `14c57cbe9` on llama.cpp `experimental/new10-ple-type-fix-20261022` (worktree
      `/mnt/raid0/llm/worktrees/llama-new10-ple-fix-20261022`, `src/models/qwen4exp-fused.cpp` +101/-7, UNBUILT):
      `fused_weights_supported()` refuses the fused path (one `LLAMA_LOG_WARN`, falls through to the graph) if any
      row-gathered weight is repacked, except `fused_moe`'s IQ4_NL `ffn_down_exps` which has a repack-aware mirror, or
      any raw-`float*` tensor is not F32; `fused_ple` widens `ple_conv1d` to F32 via `to_float` (tap stride uses
      `kern`); `best < 0` now `GGML_ABORT`s with a diagnostic; the bring-up prints and per-token `/tmp/qwen4exp-builds`
      dumps are gated on `GGML_FUSED_DECODE_TRACE`. Graph path untouched; production keeps `GGML_FUSED_DECODE_OFF=1`.
    - Whether the synthetic-weight divergence at w=0.05 has the same cause is not yet shown (the repro's synthetic
      weights are not repacked IQ4_NL); the ASAN repro below answers it.
  - [x] **FD-DIV-1a — build `14c57cbe9` and run three smokes (correctness, one build-role grant).** (1) GSQ IQ3_XXS
    with the fused path ON under the patch is byte-identical to the same model with `GGML_FUSED_DECODE_OFF=1`
    (the refusal falls through to the graph); (2) UD-IQ4_XS, patched build vs the production v10 store build,
    byte-identical greedy output; (3) optional: the FD-DIV-1 repro (`45d8f2937` `QFR_*` knobs) under ASAN at
    w ∈ {0.05, 0.3, 1.0}. Experimental branch only; v10 stays frozen; a fold goes through the champion route with a
    v11 manifest row. (filed 2026-10-22, workspace-58)
    - *(2026-10-23 15:3xZ, workspace-58 wrap-up; box stays open.)* IN PROGRESS: a workspace-58 subagent is preparing the job (launcher and FILLERS row). The slot is booked on q2 tonight after s5-cs8l4ab, and it runs if armed (calendar REVISION 15:2xZ). Not landed at this checkpoint.
    - *(2026-10-23 16:43Z, workspace-58 wrap-up; **FD-DIV-1a PASS**, pass rule PREDECLARED.json sha256 `02251f47...`.)* Verdict `/mnt/raid0/llm/tmp/fd-div-1a-20261023/out/VERDICT.md`, receipt `/mnt/raid0/llm/tmp/fd-div-1a-20261023/out/fd_div_1a_receipt.json` (`epyc.fd_div_1a.smoke_receipt.v1`). Smoke 1 (GSQ IQ3_XXS, patched `14c57cbe9`, fused ON vs v10 `GGML_FUSED_DECODE_OFF=1`): byte-identical on 4 prompts; unpatched v10 fused ON still aborts (rc 134), defect reproduced. Smoke 2 (UD-IQ4_XS, patched vs v10): byte-identical. Smoke 3 (ASAN repro) SKIPPED: `tests/test-qwen4exp-fused-rope.cpp` exists only on `experimental/fused-yarn-20261004`; filed as FD-DIV-1b. Production keeps `GGML_FUSED_DECODE_OFF=1`; folding `14c57cbe9` goes through the champion route with a v11 manifest row.
    - *Observation, no speed claim:* on UD-IQ4_XS, v10 fused-ON decode is ~1500-2000 ms/token vs ~70-87 ms/token on the graph (fused-off) path (descriptive, single runs); warrants a look.
  - [x] **FD-DIV-1b — port the FD-DIV-1 repro and run it under ASAN (filed 2026-10-23, workspace-58 wrap-up from FD-DIV-1a smoke 3).** `tests/test-qwen4exp-fused-rope.cpp` (`QFR_*` knobs) lives only on `experimental/fused-yarn-20261004` (`5bfdcd18c`, `6c126e975`, `45d8f2937` on top of five commits not in v10); `6c126e975` gates the same per-token trace output `14c57cbe9` gates, so the port is a merge with a known textual overlap, plus a second (ASAN) build. Run at w in (0.05, 0.3, 1.0). Done when it answers whether the synthetic-weight divergence has the repacked-IQ4_NL cause or another. Experimental branch only; own build-role grant. ✅ 2026-10-24 — **ANOTHER_CAUSE** (ASAN build of 14c57cbe9 + test port `2a2a79bb6`, q1 08:20-08:22Z; PREDECLARED sha256 `293c89a2…`): ctl CLEAN; w=0.05 DIVERGE (logits nmse 1.84), w=0.3 DIVERGE (3.49), w=1.0 ABORT "fused_moe: non-finite router logits"; ASAN reported no memory error. The F32/F16 fixture excludes the repack chain, so a second fused-MoE defect exists. Verdict `/mnt/raid0/llm/tmp/fd-div-1b-20261024/out/VERDICT.md`.
  - [ ] **FD-DIV-2 — the fused qwen4exp decode is WRONG on the real served model (v10 production and C3), and ~20x slower; fix it or make it default-OFF in code (filed 2026-10-24, workspace-58).** Evidence: (1) FD-DIV-1a Informational, `/mnt/raid0/llm/tmp/fd-div-1a-20261023/out/VERDICT.md:22`: UD fused (v10) vs graph (v10) `fused_equals_graph=false` on all 4 prompts (first_diff_byte 2-7), decode 1485-2004 vs 69-87 ms/token; (2) q38fn-armP v1 coherence on C3 without `GGML_FUSED_DECODE_OFF=1`: UD greedy output garbage, coherent with the knob (`/mnt/raid0/llm/tmp/ws58-q38fn-armP-20261024/void-run1-20261024/`); (3) FD-DIV-1b ANOTHER_CAUSE above. Production architect_general (:8074) sets no OFF knob, so it serves wrong output whenever up (down since 10-11). UPDATE 2026-10-24 ~10:1xZ: the v10 production check (`/mnt/raid0/llm/tmp/ws58-v10-fused-coh-20261024/VERDICT.md`) reads NO-DEFECT AS LAUNCHED: with the exact production argv/env (MTP draft, fused nominally ON) both arms are coherent and 0 fused-path lines appear, because MTP verify batches never take the single-token fused path. The defect is LATENT for production. Per the operator rule (fix in the champion, not v10/production), RATIFY-FUSED-OFF-ARCHGEN-20261024 stays parked and :8074 is NOT held; the fix is the C5 fold (3c4ca599: fused decode default-OFF in code, opt-in GGML_FUSED_DECODE_ON=1, plus 14c57cbe9 + CH-24 gating). Done when the fused path matches the graph byte-for-byte on the UD Paris/short/long prompts at production flags, or the knob defaults OFF in a promoted kernel.
  - [x] **FD-DIV-1a decision-line CORRECTION (workspace-58, 2026-10-24).** ✅ 2026-10-24 — the 1a verdict line "production keeps GGML_FUSED_DECODE_OFF=1" was FALSE for the production launcher, and smoke-2 PASS compared patched-fused vs v10-fused (equally wrong), so it never tested correctness against the graph. The Informational fused-vs-graph result above (false on all prompts) was the real signal and was missed.
  - *(2026-10-24.)* The fold of `14c57cbe9` via the champion route is C5 (`c72ec82f5`, V11-107, CH-31). FD-DIV-1b stays open (INF-67); the fused path is opt-in from C5.
  - *(2026-10-28, workspace-58; **FD-DIV-1b re-run on C5: PERSISTS_ON_C5**.)* Champion C5 `c72ec82f5`, ASAN build 115 s on CPUs 78-95, actual rc0 at 02:24:41Z. Cells: ctl CLEAN, w=0.05 DIVERGE, w=0.3 DIVERGE, w=1.0 ABORT (nonfinite router guard); no AddressSanitizer ERROR in those four cells. Source seal `c58d6d80588287a384e05b08ed20b794ce4912d6f7ea4d338cfefce441d3d5fa`, declaration `a90f03cbee1c99884752b623dd37231032c075d2d349a6fea5e52cc35f5617ad`, audit `/mnt/raid0/llm/tmp/codex-ni-20261028-fddiv1b-audit/audit.log`, packet `/mnt/raid0/llm/tmp/codex-ni-20261028-fddiv1b-t1`. Scope: synthetic correctness finding only; not a global memory-safety proof, does not identify the fix site, says nothing about production. The parent fused-decode fix (FD-DIV-2) stays OPEN. [belief: cc]

#### Validation strategy (learned the hard way — the arch test is self-consistent and cannot see graph-math errors)

1. **Logit comparison** (the dump tool, fixed in Phase 0): fused vs decomposed per-token, ≤1e-4, per layer type, before any perf claim.
2. **Greedy generation test** (Paris-style) — the real gate; every change.
3. **test-llama-archs** — necessary, insufficient.
4. **In-situ profiler** (`GGML_CPU_PROF` + `[mm_prof]/[mmid_prof]`) — the ONLY trustworthy perf instrument; clean-room numbers have lied 4/4 times.

#### Risks

- **Numerics**: the fused op's internal order must mirror the decomposed (bit-exact) or stay within the NMSE — the hc_mix revert (the 2·sigmoid fold bug) is the standing warning: graph-math errors pass the arch test and show as garbage generation.
- **State machinery**: the recurrent/conv state + QSA indexer + PLE interfaces are the hardest correctness surface — Phase 1 deliberately picks the uniform layer type first.
- **The MoE routing** (dynamic expert selection) inside a fused kernel.
- Effort: 4-8 focused sessions; the branch `exp/cpu-fusion-qwen4exp-20260829` and the worktree `/mnt/raid0/llm/llama.cpp-cpu-fusion-20260829` are the workspace (champion `270b48ed6` + 4 qwen4exp backports + confirmed fusion ops mean_d1/moe_topk_norm + profiling tooling).

#### Phase 0 DONE (2026-08-30) — tooling + fast-path hook design

- Logit-dump tool fixed and verified: `/tmp/qwen4exp-builds/dump_logits2` — the `-1` text_len convention is gone in this API (caused `std::length_error` in `llama_vocab::tokenize`); the two-pass tokenize returns the negative buffer size; the tool now writes the full 248,320 logits to a file for the fused-vs-decomposed diff.
- A/B harness: `numactl --interleave=all` + `-mmp 0`, t48/t64, IQK=1, the in-situ profiler (`GGML_CPU_PROF` + `[mm_prof]/[mmid_prof]`) — all established from the prior rounds.
- **Fast-path hook design**: `llama_context::process_ubatch` (src/llama-context.cpp:1320) is the single hook point — after the mctx apply, a branch: `model.supports_fused_decode() && gtype == LLM_GRAPH_TYPE_DEFAULT && batch-1 decode && CPU backend` → the fused decode writes the logits into the `llm_graph_result` and returns; the graph machinery untouched otherwise. State access via the memory context (the hybrid-idx cast, like the graph does); weights via the model's layers. The user permitted the direct fast-path blast radius.

#### Phase 1 progress (2026-08-30) — foundation committed

- `src/models/qwen4exp-fused.cpp` committed (`6321806b3`): the kernel-mirror helpers (FusedMM, lora_mm, hc_rms_norm_gamma, hc_stream_mean, hc_mix) — each mirrors the graph's exact function/order for bit-exactness. Single-threaded for now (correctness first).
- `e57e1d542` committed the FULL fused GDN-layer function: hc_mix + qkvz + conv state + 4-tap causal conv + l2 norms + the ggml_gated_delta_net kernel (scratch ctx + 1-thread pool) + z-gated rms + ssm_out + fused_moe (softmax router, argsort top-k, topk-norm weights, expert dots, shared expert) + hc_combine x2. Every op mirrors the graph's function/order for bit-exactness. Single-threaded (correctness first). Compiles clean, tree green.
- Next: thread-pool integration (the mms + the GDN kernel at nth>1), then the full-attn layers + PLE + head, then the process_ubatch hook + logit-diff validation.

#### Current tree state (starting point)

- Branch `exp/cpu-fusion-qwen4exp-20260829` @ `7cdd7c97b` — clean, arch suite 0 FAILs, "Paris" verified.
- The measurement recipe: `numactl --interleave=all` + `-mmp 0`, t48/t64, IQK=1, the in-situ profiler.
- Decode baseline: ~12.4-14.9 t/s depending on the box state.

#### Validation round 1 (2026-08-31) — the hook is wired; five correctness fixes landed; MoE NaN open

- The `process_ubatch` fast-path hook (committed `99a1c111e`, env-gated `GGML_FUSED_DECODE_OFF`
  for A/B): single-token decode on a CPU-resident qwen4exp runs `fused_decode`; any failure or
  unsupported cache type falls through to the graph.
- **A/B harness** (`validation/dump_logits_seq`): one model, two contexts; both decode the prompt
  batch through the graph (sanity: bit-identical, and bit-reproduces the Aug-30 `logits-ref.bin`),
  then 8 single-token steps — the graph ctx (env OFF) drives the greedy token stream, the fused
  ctx runs the fast path; per-step max-abs-diff + NMSE. Graph-only control: clean (0.0 diffs).
- **Five fixes** (commit `9a915a823`, ASAN-verified, `build-asan`):
  1. GDN kernel `wdata` null → segfault; sized scratch `S_v + 16` floats.
  2. `qkv` span: `ssm_d_inner` (6144) is the v-span; `wqkv` writes 10240 → 16 KB heap overflow.
  3. Conv-state staging `rl->ne[0]*4` → the row is `(d_conv-1)*conv_channels == rl->ne[0]`; 4×
     copy-back overrun.
  4. z-gate one scalar per head vs the graph's elementwise `sigmoid(z)`.
  5. `ssm_norm` OOB: `znorm[h*S_v+i]` on a `{head_v_dim}` tensor → garbage → NaN `final_in` →
     NaN router logits → `fused_moe` wrote `probs[-1]`.
- **Full-attn wiring rewrite**: KV/indexer writes were going to local copies at `pos` (OOB and
  lost). The caller now derives the used/visible cells from the cells API (`get_cells` passthrough
  on `llama_kv_cache_context`); the layer writes into the cache views at the current cell
  (n_used-1) and masks the current cell out of the attention; the QSA block path scores the
  visible cells only.
- **FIXED — the MoE NaN (commit `2fcfc5bc1`)**: the IQ4_NL down-expert tensors live in the
  **CPU_REPACK** buffer (8x8-interleaved rows on AVX2; the repack compute handles that layout,
  the plain vec_dot cannot). The fused MoE detects `tensor->extra` and mirrors
  `ggml_gemv_iq4_nl_8x8_q8_0_generic`. Also fixed in the same pass: the conv kernels read
  transposed (tap-fast per `c[i0 + i1*nc]`), the GDN state copy-back froze the recurrence
  (must copy tgd's state region, not ts), the F16 attention/indexer caches (staged F32 view +
  cast-back writes), the IMROPE 4-position format, the rope/flash kernel wdata + threadpool,
  and the meta-only result ctx (logits into the previous graph's sched-known t_logits).
- ~~flash_attn_ext is NaN on this model's real activations~~ — **RETRACTED (2026-08-31
  external audit)**: the NaN was the repro's own staging bug — it staged Q as F16 while the
  CPU kernel reads Q as `const float*` unconditionally (4096 NaNs = 16 overflowed heads × 256).
  The graph never uses flash (flash_attn=false → manual MHA), but the flash staging with F32 Q
  was the better path and will be retried in the ATTN rewrite. The manual `fused_attn_qsa`
  used meanwhile is itself broken (see the rewrite section).
- **Current**: the complete fused decode runs all 8 validation steps without crashing or NaN;
  the per-step logit diff vs the graph is O(10). The same-position layer comparison
  (env-gated dumps) shows layer 0 differs by ~5.8 with identical inputs. The op-id mapping is
  corrected (aae8cae1d): the graph's layer-0 hc_mix runs the MANUAL build_hc_mix (no DSV4
  machinery — no hc_fn tensor), but its rms_norm passes the input through (norm ~1) and the
  gate is effectively 1 — the mixed = the input — while the fused's manual hc_mix (per-stream
  rms → lo/gate → mean) differs. **The first divergence is the hc_mix's rms_norm/gate
  behavior.**
- **The graph's step-1 rms_norm is identity-like** (b0edc7177): the batch decode's rms_norm
  output is properly normalized (-0.0309...), but the step-1's output equals the input exactly
  (norm ~1) — the fused's per-stream rms gives [0.965, 1.81, 1.54, 1.36]. The fused's hc_mix
  diverges at the very first rms_norm.
- **ROOT CAUSE found** (580e0e5ed): the graph's step-1 `hc_init` has DIFFERENT per-stream
  values (rms [0.451, 0.479, 0.153, 0.284]) — the graph's layer-0 input is NOT the embedding
  repeated 4× — while the fused path builds res_hc as 4 identical copies. The graph's rms_norm
  is identity on its input (gamma ≈ 1.05). The stream-dependent input is the root divergence.
- ~~ROOT CAUSE confirmed~~ (f36ea436c / 3fccd0ddf / ac4532bab / 2794abc7f) — **RETRACTED as a
  correctness bug by the 2026-08-31 external audit**: the gallocr mechanism is real (zero-size
  requests alias live free blocks without consuming them; input tensors are freed after last
  use; the gate scalar really overwrites the token's bytes — and the pre-fix allocator is
  byte-identical to upstream), but the graph's only consumer of inp_tokens is node 0 and the
  overwrite happens at node 144+ — nothing ever reads the corrupted bytes. The graph greedy was
  13 hours before the fix and 13 after; the fused path was the diverging side all along. The
  "evidence" was post-compute dumps of memory-reusing buffers (the instrumentation class the
  session had already declared unreliable). The patch changed the debugger's view, not the
  computation: NOT a correctness bug, do NOT upstream it as one; the graph-path validation
  stands. (The fused PLE n-gram predecessor-order fix in 2794abc7f was a genuine fused-side bug.)
- PLE component verification (a56a79cc0): token embed, rows, key, key_n, value are ALL
  graph==fused EXACT (verified via pre-compute eval-callback dumps; post-compute dumps
  read freed memory and were the source of the earlier phantom divergences).
- BREAKTHROUGH (e3ddf1583): the "query weight differs" theory (78922ed81) was IMPOSSIBLE and
  is RETRACTED — both paths dereference the same tensor object; the GGUF ground truth says
  blk.1.ple_norm_query.weight[0] = 0.8261719 (the fused value); the harness's "1.02417" was
  blk.0.hc_ffn_norm.weight[0] picked up by the pattern-matching eval callback latching onto the
  wrong MUL node. The fix in e3ddf1583 was right; the theory on the record was wrong. The
  real bugs — all fixed:
  1) conv windows (GDN ssm_conv + PLE dilated conv) are channel-major (tap k, channel i at
     i*ncs + k); the fused built them column-major (transposed state, wrong tap/channel pairing).
  2) the GDN q/k l2_norm normalizes per ne[0] column (per head); the fused normalized flat once.
  3) the PLE layer is ALSO recr: the graph runs the full GDN+ffn block after build_ple; the
     fused's else-if skipped it.
  Layers 0-2 now bit-exact (l_last 1.3e-7); greedy g=13 f=13 (was 89). Logit diff 7.2 starts
  at layer 3 = the first full-ATTN layer.
- ATTN REWRITE DONE (470730838): the ≥6 audit defects fixed — fused_rope now stages the
  graph's [n_embd_head, n_head] tensor (heads 6-23 were never roped); the q/k/v/wo lora
  scales restored (the pre-rope Q/K divergence); the attention replaced by the graph's OWN
  flash kernel staged with F32 Q (the earlier F16-Q staging was the NaN source — the audit
  was right; flash_attn defaults to AUTO in this tree, so the graph IS the flash path); the
  k/v stage builds AFTER the current-cell write (the pre-write stage read the stale cell —
  the actual source of the 1.2 attention diff); the current cell is attended; the indexer
  uses ratio[il] + the pooled/query ropes.
  Validation: attn_pregate/Qcur/Kcur/Vcur/gate/gated/wo EXACT (max_abs=0) at layers 3+7;
  layers 0-6 bit-exact (l_last 1.3e-7); greedy 13=13; logit diff 7.19 -> 0.684 (nmse 1.7e-2).
- Repack guard INVESTIGATED (79fceb05d): the expert types are all handled (up/gate IQ3_S
  plain, down IQ4_NL repacked-with-mirror or Q8_0 plain; verified via per-call dumps). The
  ~1.6e-4 routed diff at layer 7 traced to the layer-7 ffn-side hc_mixed (2.6e-4) — the
  input to moe2 — while the ffn-side xn is 6.7e-6 (the layer-7 res after the attn-combine;
  the inject/attn_out/res_in all exact). The amplification (6.7e-6 xn -> 2.6e-4 mixed -> 
  1.6e-4 routed -> 1.6e-4 l_last) is the remaining divergence chain — bisection continues
  (the res's 6.7e-6 source is the open question).
- CRASH FIXED (5c575e211): the deterministic crash was the "hc_mix w:" debug print (added
  during the repack investigation) — it evaluated ggml_type_name(w_inject->type)
  unconditionally, and the head's hc_mix is called with w_inject=nullptr — a NULL deref in
  the print, not in the compute. Isolated via the instrumentation-strip test (per the
  2026-08-31 audit follow-up): the gates→0 build passed, the bisect named the print. The
  user's ASAN-vacuity point is confirmed (GGML_SANITIZE_ADDRESS=OFF for libggml-cpu; both
  scratch overflows lived in that blind spot) — a sanitized ggml rebuild is queued before
  the next corruption hunt. Two genuine overflows were also fixed along the way: the flash
  staging's wdata (16 floats short of the kernel's 6976 need) and the GDN kernel's 3.2 MB
  state write past the ne-sized 24 KB scratch tensor. Current state: full-instrumentation
  runs exit 0, logit diff 0.684, greedy 13=13, layers 0-6 bit-exact, layer 7 at 1.6e-4.
- THE SEED FIXED (2c09c1e9e): the IQ4_NL repacked mirror must round PER-K, not per-block —
  the graph's ggml_gemv_iq4_nl_8x8_q8_0_generic accumulates sumf[j] += sumi_k * d * a per k;
  the mirror accumulated the whole sumi and did ONE product per block (~1e-8 rounding).
  With the per-k products: layers 0-11 are now EXACT (layer 7: 1.553e-4 -> 1.341e-7).
- Layer-12 bisection (b494e1599): the GDN body is exact; the ffn diverges via the same
  chain: the ffn-side xn 6.7e-6 (the norm's ~56x of the ~1.2e-7 res) -> the hc_mixed
  4.05e-4 (~60x) -> the up/gate dots 1.3e-3 -> the ffn_out 1.25e-4.
- Silu sites on the graph's SIMD kernels: the PLE conv silu (8f7bc6974 — logit 0.947 ->
  0.6335) and the GDN conv silu (96ec5827a, neutral) use ggml_vec_silu_f32 (the graph's
  ggml_v_silu/ggml_v_expf, 1.45-ulp). The ffn glu's SIMD-silu was NEGATIVE (reverted); the
  PLE gate's SIMD sigmoid was NEGATIVE (c9b0cc488, reverted).
- The ~1.2e-7 seed is still open — the PLE chain: the layer-0's l_last 1.49e-8 (the GDN)
  -> the PLE query_n 4.8e-7 (the norm ~32x) -> the gate dot 8.2e-8 -> the norm_conv 1.9e-6
  -> the padded 4.8e-6 -> the conv_out 1.34e-7 (unchanged by the SIMD silu) -> the l_last
  1.27e-7. Current: logit 0.660, greedy 13=13, layers 0-6 exact; the remaining candidates:
  the gate's dot (the key_n*query_n FMA vs the graph's mul+sum_rows), the query_n's norm,
  or the layer-0's GDN.
- Sequence: logit gate ≤1e-4 → Paris → arch suite stays; no perf claims before it passes.
  Then the honest baseline (uniform IQ4_XS requant control, ~12 min) + one symbol profile of
  the 46 ms non-gemv composition before Phase 4.
- SESSION-OWNED operational note (2026-09-01, operator-ruled, owned by this session):
  ~/.local/share/opencode/opencode.db is ~210 GB (the host's largest file, ~44% of the free
  space after yesterday's 435 GB reclaim; churning tens of GB, not a steady trend — three
  samples 186/224.9/210.3 GB). The plan, owned here: LEAVE ALONE while this session is live
  (held open by pid 433986, actively written). At a natural boundary — the INF-67 ≤1e-4
  gate or a /clear+close — run a maintenance window with the process stopped: back the DB
  up, then VACUUM (needs ~2× transient, only with the free space confirmed), and prune
  sessions only after the campaign's findings are committed, never mid-effort. The
  mechanism hypothesis (tool outputs stored verbatim per message — this campaign moved
  genuinely large artifacts) is worth knowing independently: every large tool output is
  paid for twice. No action taken; not deferred — operator-ruled, tracked here.
- **CLOSED 2026-09-02 — the premise no longer holds; no maintenance needed.** Ownership passed to
  the adhoc-audit session after the INF-67 session was closed. Measured on the live host:
  `/mnt/raid0/users/daniele/.local/share/opencode/opencode.db` is **315 MB**, not ~210 GB; the whole
  opencode tree is **403 MB** (`log` 73 MB, `snapshot` 5.8 MB, everything else under 1 MB). It is the
  ONLY `opencode.db` on the host, and no `.db` anywhere under `/mnt/raid0` exceeds 1 GB.
  - **A VACUUM would reclaim ~0.** `freelist_count = 0` and `auto_vacuum = 0` — the file is fully
    packed live data, no free pages. Occupancy: `event` 260 MB (82%), `part` 27 MB, `message` 21 MB.
  - **Therefore the shrink was not an in-place delete.** With `auto_vacuum` off, deleting rows leaves
    free pages behind; a zero freelist means the file was replaced or vacuumed, not merely pruned.
    Which of the two is NOT determined here — do not record a mechanism that was not observed.
  - **History survived**: 228 sessions spanning 2026-04-28 → 2026-09-02. The campaign-window days
    (08-29 → 08-31) hold no sessions, consistent with that data being what went; 09-01 (83) and
    09-02 (110) are present. The campaign's substance is in git regardless.
  - **Not acted on, deliberately**: a live `opencode` (pid 500205, a DIFFERENT devcontainer — the path
    resolves only via its mount namespace) holds the db/wal/shm open read-write. Nothing was killed,
    stopped or written; the DB was inspected via a throwaway copy. The operator's "no opencode
    sessions open" is true of THIS devcontainer, not of the host.
  - **Policy note for any future attempt**: that path is outside `/mnt/raid0/llm/`, so the filesystem
    containment guard blocks writes to it — real maintenance would need an explicit operator
    `EPYC_FS_ACK`, on top of stopping the holder.
  - **Residual risk: a watch item, not a task.** ~193 of the 228 sessions are from the last two days
    and the `event` table carries 82% of the bytes, so ordinary growth is ~100s of MB/day — immaterial
    against 736 GB free. The original 210 GB was real (three samples) and its mechanism was never
    confirmed, so if a single artifact ever again approaches tens of GB, re-measure before assuming
    the old hypothesis. Do not pre-build maintenance for it.
- SAFETY contract (audit item 3, before any serving exposure): the hook must become OPT-IN
  (today `GGML_FUSED_DECODE_OFF` is an opt-out with `supports_fused_decode()` unconditionally
  true and zero residency checks); all persistent state (PLE history, conv/ssm, KV cells)
  must commit atomically at end-of-token; the t_logits write relies on allocation-ordering
  luck; repack guards on tensor->extra + type; the debug I/O must be stripped before any
  perf measurement.

## Track: laguna-s21-cpu-port
<!-- gate: none -->

> Folded from `handoffs/active/laguna-s21-cpu-port.md` @ `0001c77da2e5` on 2026-11-02 (BRF-T1-F10, route 1a, operator D1/D5; retired row INF-28 → EVL-21). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Laguna S 2.1 CPU Port — Experimental Branch

**Status**: v8 PROMOTED AND FROZEN — `production-consolidated-v8` at `67a433bf45a8a091d83b4ea0b32ff0735fd51800` (version `10107`) carries the base Laguna arch + DFlash work. Required GPU IQ2 and CPU Q4 lanes are complete; terminal both-mode lineup passed `24/24` smoke and `6/6` API. CPU Q8 characterization retains a real arithmetic miss but is not a promotion lane under operator scope; DFlash enablement is a gate FAIL/no-go. L-7 is complete; L-8 and future Laguna architect evaluation remain open post-v8. (Was: stub, created via /research-intake Stage-2, operator-approved 2026-07-22)
**Created**: 2026-07-22
**Priority**: P2
**Effort**: Low-Medium (base arch ~350 LOC; DFlash spec path is included in the v8 carrying work, with enablement separately gated)
**Categories**: local_inference, moe_optimization, speculative_decoding, quantization, hardware_optimization
**Source**: intake-879 (poolside launch blog) + intake-880 (GGUF model card) + Stage-2 deep-dive 2026-07-22
**Parent index**: [`inference-research-index.md`](inference-research-index.md)
**Related**:
- [`iqk-iquant-enablement.md`](quantization-and-low-bit.md#track-iqk-iquant-enablement) — Laguna UD-IQ2_M IQ-quant acceleration (already-coded branch; add Laguna as 5th beneficiary)
- [`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md) — the DFlash draft-dflash spec path + accept-rate bench
- [`deepseek-v4-flash-cpu-port.md`](../completed/deepseek-v4-flash-cpu-port.md) — the reusable experimental-branch new-arch CPU-port precedent (pattern, not coupling)
- [`architect-model-selection-bench.md`](model-evaluation-queue.md) — Laguna as a candidate once served

---

#### Objective

Port the **Laguna** architecture (poolside/Laguna-S-2.1: 118B-total / 8B-active MoE — 256 routed experts top-10 + 1 shared; 48 layers mixed 12 full-attention + 36 sliding-window(512); **sigmoid**-routed MoE with score-correction bias; **softplus attention-output gate**; QK-norm; per-layer-type RoPE — YaRN on full layers, plain RoPE on SWA layers) onto an experimental llama.cpp branch on the EPYC 9655 CPU stack, validate quality + throughput vs the production kernel, and merge into a new production version **only** after both gates pass. The port is now frozen in v8; **NEVER modify `production-consolidated-v8`**. All residual work starts from a fresh v8 pull in `llama.cpp-experimental`, per the four-step workflow.

#### Why now

`/research-intake` ingested Laguna 2026-07-22; the operator is downloading Q4_K_M (poolside, 75GB) + UD-IQ2_M (unsloth, 37GB) + the DFlash-BF16 drafter (2.2GB). Laguna is a weight-class-leading agentic coding model whose 8B-active MoE shape is favorable for bandwidth-bound CPU decode, and it lands directly on the active spec-dec-mtp-refresh line. **Base arch support is already MERGED upstream** (ggml-org/llama.cpp PR #25165, 2026-07-22T01:54Z, approved), so the forward-port can pull from upstream rather than only poolside's fork.

#### Key facts (Stage-2 deep-dive, 2026-07-22)

- **PR #25165 is MERGED** (22 files, +1091/−1): base arch only in `src/models/laguna.cpp` (+332) + `conversion/laguna.py` (+207). The `conversion/` package is **already present** in the v7 tree → the converter applies clean. **DFlash spec path is NOT in the PR** — it lives only in poolside's fork branch `laguna` (`--spec-type draft-dflash`).
- **DFlash = z-lab block-diffusion** (arXiv:2602.06036, intake-158), SAME codebase (GGUF `dflash.target_layers` = HF `target_layer_ids` +1, matching z-lab `offset=1`). No timestep/denoise tensors → single-pass conditioned block drafter, not iterative diffusion. Draft cost is cheap; the open question is acceptance.
- **DFlash-on-CPU is still likely NO-GO for quantized targets.** The March NO-GO (`../completed/dflash-block-diffusion-speculation.md`, 27% accept, AR drafter won 36.5 vs 13.0 t/s) roots in TARGET-side quant noise in the conditioning hidden states — which poolside's BF16 drafter does NOT fix. Only a near-lossless target (Q8_0 / F16) plausibly reopens it. See `speculative-decoding-mtp-refresh.md`.
  - *2026-09-23 correction:* "roots in TARGET-side quant noise" is a hypothesis, not an established cause — see
    `speculative-decoding-mtp-refresh.md` (causal correction 2026-07-29: 17.2% Q4 → 19.0% Q8, BF16 untested) and intake-1505.
- **UD-IQ2_M iqk coverage**: 92.2% of bytes are IQ-quant (IQ2_XXS 51% + IQ3_XXS 37% + IQ2_S 1.4% + IQ4_XS 2.3%), stubbed on frozen v7; the code-complete `iqk-iquant-enablement` branch already covers 97.6% of the IQ bulk (all but the 2 IQ4_XS tensors). No new kernel needed — see that handoff.

#### Tasks

- [x] Forward-port base Laguna arch (merged PR #25165 commits, ~350 LOC: `src/models/laguna.cpp` +332, `models.h`, 1-3-line touches to `llama-arch`/`llama-model`/`llama-vocab`, `conversion/laguna.py` +207) onto a FRESH-pulled `llama.cpp-experimental` off `production-consolidated-v7`; validate S-2.1 Q4_K_M loads + coherence/garbage smoke ✅ 2026-07-25 — landed as `afa770382` on `experimental-v8-refresh-20260724` (superset: includes the DFlash spec path NOT in the PR). Required CPU Q4 evidence is at `epyc-inference-research/data/kernel-v8-candidate/laguna-cpu-dflash-exact-tip/run-20260725T112845Z-67a433bf4-noswap/` (nested `run-20260725T113030Z`): base median `7.078103` t/s, DFlash median `8.028143` t/s, but acceptance `17.2267%` fails the lineup floor. Final hardened GPU IQ2 artifact `epyc-inference-research/data/gpu-mi210/laguna-iq2-kv-sweep-exact-tip/run-20260725T125201Z` is post-identity, `15/15`, and observation-only: A q8/FA-on `33.992845`, B f16/FA-on `35.490117`, C f16/FA-off `33.782293`; B/A `+4.404668%`. `test-llama-archs`/`test-chat-auto-parser` pass in ctest; 2026-07-25 audit verified graph idioms match sibling archs (NEOX rope group, Qwen3-style QK-RMSNorm, per-layer YaRN/plain-RoPE split sound, softplus gate width-checked on both target and drafter sides)
- [x] Confirm the PR-author-flagged "GQA head-ratio backend dispatch" bug does not hit the CPU build ✅ 2026-07-25 — exact-tip CPU Q4 evidence completed all `5/5` base and `5/5` DFlash replicates on the real S.2 model at `data/kernel-v8-candidate/laguna-cpu-dflash-exact-tip/run-20260725T112845Z-67a433bf4-noswap/` (nested `run-20260725T113030Z`; `q4_k_m_base`/`q4_k_m_dflash` both `status=complete`). Source audit confirms `laguna.cpp` reads per-layer `n_head` (`48` full / `72` SWA) with `n_head_kv=8` and passes both values to the shared `build_qkv` graph; `afa770382` changes no `ggml/` backend code. This closes the target CPU concern with real-model execution evidence, not a claim about every hypothetical Laguna variant.

---

#### 2026-07-25 v8 audit (Claude session, operator-requested) — findings + new tasks

Deep review of `afa770382`/`6c44557bf` + the certification harness
(`laguna_pgpu1_dflash_runner.py`, `laguna_cpu_dflash_observation_runner.py`). Kernel-side
code is clean (conversion surface complete 1:1 vs `load_arch_tensors`; templates match
`test-chat-auto-parser` expectations; the thread-safety fix is a textbook atomic-exchange).
The harness relaxations were audited commit-by-commit and are **NOT vacuous**: RESULT_JSON
exact numeric equality, `finish_reason=stop`, completion floors, anti-garbage, and
`draft_n>0` all still hard-gate — and post-relaxation the harness caught a REAL deterministic
q8_0 model arithmetic error. Remaining items:

- [x] **L-1 (silent-wrong risk) — make the SWA contract explicit in conversion.** ✅ 2026-07-25 — landed in `89d55f161`.
  Before the fix, `conversion/laguna.py` never wrote `SLIDING_WINDOW_PATTERN` (only `add_sliding_window`,
  `laguna.py:86-89`) — the 4-dense-first layer pattern is an implicit code-side default
  (`laguna.cpp:39-41`); and `rope_freq_base_train_swa` silently defaults to the full-attn
  YaRN base (500000) when `ROPE_FREQ_BASE_SWA` is absent (`laguna.cpp:47-49`) though SWA
  layers intend θ=10000. The landed conversion writes both keys and makes the C++ fallback loud.
- [x] **L-2 (integration gap) — validate encoder input width explicitly.** ✅ 2026-07-25 — landed in `89d55f161`. DFlash encoder
  previously assumed draft `n_embd` == target hidden size (`dflash.cpp:15` vs `speculative.cpp:1325`);
  `LLM_KV_TARGET_HIDDEN_SIZE` existed in `llama-arch.h` but was never read; there was no
  divisibility assert on `n_feat = n_embd_inp_enc()/n_aux` (`dflash.cpp:128`). Mismatch
  previously failed only indirectly via `fc` shape at load. The landed change reads the key
  and checks explicitly.
- [x] **L-3 (masking risk) — bound the non-finite feature sanitize.** ✅ 2026-07-25 — landed in `89d55f161`. `speculative.cpp`
  (+1471-1490) previously unconditionally clamped target features to ±65504/NaN→0 on ALL backends
  (comment blames Metal f16), warning once per process — after the first warning it silently
  masks real target-model numerical bugs. The landed change bounds that sanitize behavior.
- [x] **L-4 (harness defect) — fix `summarize()` attribution
  ordering.** ✅ 2026-07-25 — landed in `978ca540`; the exact CPU final reports semantic failure status before schema completeness. The 23:47Z "warmup" failure was a MISATTRIBUTION: all 20 cells' warmups passed;
  the real failure was 5/5 `q8_0_base` cells with `incorrect prime sum: 361` (vs 311),
  deterministic at temp0/seed 424242. Mechanism: error-path result rows lack the `"warmup"`
  key and `summarize()` checks `row["warmup"]` before ever surfacing `primary_error`. The
  `dc61034a` partial-summary patch preserves evidence but the strict path STILL dies on the
  next field check (`non-numeric replicate prompt_tps`) instead of reporting the semantic
  error. Make summarize() status-first: surface `primary_error` before schema-completeness
  checks.
- [x] **L-5 (model finding, investigate before more prompt surgery) — the q8_0 base
  deterministic arithmetic miss.** Sum 361≠311 with the correct prime list, plausibly induced
  by the `e2ea1df7` prompt constraints (≤2-sentence rationale, no enumeration → no shown
  arithmetic). Decide: relax the no-enumeration cap for the CPU lane, or accept and rerun with
  a different seed sweep — but do NOT paper over it with a validator relaxation; it is exactly
  the class of failure the harness exists to catch. ✅ 2026-07-25 — disposition is to preserve
  the deterministic miss and strict validator, with no prompt/seed surgery. The operator scoped
  Laguna promotion evidence to Q4 on CPU and IQ2 on GPU; Q8 remains characterization only.
- [x] **L-6 (gate design) — add an acceptance/net-speed floor before any production DFlash
  enablement.** ✅ 2026-07-25 — gate implemented in `733c2cee`/`2bbd4109`; current DFlash result is FAIL/no-go, not an enablement. Measured: GPU IQ2 acceptance 21.6% pooled — dflash is +35% on primes but
  **−28%/−37% on the other two prompts**; CPU acceptance 17.2% (q4) / 19.0% (q8). This is
  consistent with the March block-diffusion NO-GO (27% accept) and the target-side quant-noise
  mechanism — the BF16 drafter does not fix it. The landed runner now surfaces per-prompt net
  decode ratios and fails closed unless pooled acceptance is at least 60% with no prompt-class
  net-negative. Q4 CPU improved aggregate decode by 13.42% but its 17.23% acceptance still
  fails; IQ2-target GPU remains a NO by the March precedent's own logic.
- [x] **L-7 (minor) — tighten the normalize prompt.** ✅ 2026-07-25 — research commit
  `daa4c926` removes the disclosed `must be 1.0` answer while retaining the independent exact
  normalized-vector and computed-sum validator; focused Laguna runner tests pass. Before the
  repair, `bed4a1d4` disclosed "JSON `sum` … must be 1.0", so that sub-check did not test
  computation even though the normalized values 0/0.2/0.3/0.5 remained independently checked.
- [x] **L-8 (hygiene) — promote the ad-hoc GPU smoke artifact to a script.** ✅ 2026-07-29 — research
  commit `5fd85268` makes the compatibility projection durable: `laguna_pgpu1_dflash_runner.py`
  deterministically emits `candidate_smoke_summary.json` with schema
  `epyc.laguna_iq2_dflash_candidate_smoke.v2` from formal-run results. It retains the historic
  smoke's per-cell prompt/semantic/completion/cleanup evidence and DFlash acceptance totals, but
  is explicitly `non_gating` and `observation_only`; it cannot create a promotion or performance
  verdict. Reproduced with `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/pytest -q
  scripts/benchmark/test_laguna_pgpu1_dflash_runner.py`: 52 passed. No GPU process, production
  server, or production-kernel tree was touched.
- [x] **L-9 (post-v8 candidate bench) — Laguna Q4_K_M CPU quant-axis screen** ✅ 2026-07-27.
  The operator decoupled this arm from E8 and authorized a paired quality shortcut instead
  of an expensive full-suite discovery. Harness readiness remained complete:
  `laguna_q4_cpu_bench_runner.py` now uses a full `taskset 0-95` /
  `numactl --interleave=all` model prewarm before each suite, the sealed arm-neutral v4
  capture/converter contract, free ports `18094/18095`, and semantic validation of the
  frozen-v8 24-port both-mode stack. Concurrent HIP work is allowed only when every
  sidecar thread is disjoint from benchmark cores; exact argv/model/executable/listener
  identity and all thread affinities are sampled every five seconds. GPU-coexistent
  throughput is explicitly observation-only and forbidden as a role-decision input.
  Focused validation: `35 passed`. The completed SWE40 generation was deterministically
  replayed through the sealed v4 converter and official evaluator: Q4 `19/40` versus IQ2
  `17/40`, zero harness errors, paired discordants `6:4`, exact two-sided `p=.75390625`.
  This `n=40` screen does not resolve a quant-axis difference and is not equivalence
  evidence. The queued LCB53 arm is stopped under the operator's shortcut because the
  quant axis no longer changes the current architect decision. Reproducible evidence:
  `epyc-inference-research/artifacts/laguna-q4-cpu-v8-20260726/laguna-q4-swe-v4-tail-replay-20260727T165223Z/`
  (research `f7ab3ec4`).
- [ ] **L-9P — conditional CPU throughput/config discovery.** The prepared
  `laguna_q4_cpu_config_discovery.py` remains unexecuted. Trigger its bounded four-cell
  selector only if a concrete CPU-resident Laguna role decision needs the performance
  surface; the current screen authorizes no lineup or registry action.

#### Notes

Laguna evidence includes both poolside self-reported observations and the local exact-tip GPU KV artifact above; neither is decision-grade or a production-enable gate under MEASUREMENT.md. The iqk (Laguna UD-IQ2_M beneficiary), DFlash (accept-rate bench + draft-dflash port), and architect-bench rows live in the linked handoffs and are cross-indexed under the "Laguna S 2.1 experimental-kernel cluster" in [`inference-research-index.md`](inference-research-index.md) so the whole cluster can be tackled in one session.

## Track: moe-spec-cpu-spec-dec-integration
<!-- gate: none -->

> Folded from `handoffs/active/moe-spec-cpu-spec-dec-integration.md` @ `0001c77da2e5` on 2026-11-02 (BRF-T1-F10, route 1a, operator D1/D5; retired row INF-40 → EVL-21). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### MoE-Spec — CPU Speculative-Decoding Verification with Budgeted Expert Selection

> **HISTORICAL STATE (2026-07-04 refresh after v6 self-draft audit; superseded by the 2026-07-18 assessment below)**: **proven mechanism, NO MoE-Spec consumer** — the "gate released / integration can proceed" framing below is historical. The REAP role had been removed from the production stack (its B=40 deployable verdict had no consumer), the Coder B=64 result was not robust across builds/cache states, and frontdoor/architect had moved to v6 embedded MTP self-draft without same-file `-md`; at that point there was nowhere to deploy `moe_spec_budget` until a live MoE verifier path needed expert budgeting. The reopen chain required measuring the current CPU self-draft/spec-dec path in live verification batches; the 2026-07-18 assessment below closes that zero-inference check and reopens only the live-MTP B-sweep, not registry integration.

> **2026-07-18 zero-inference assessment**: reopen to a **current live-MTP MoE verifier B-sweep**, not to registry integration. The 2026-07-03 live acceptance report (`mtp_acceptance_report_20260703T114323Z`) proves current verification-batch consumers exist: frontdoor α=0.6582 (`26,787/40,700`), worker_general α=0.8256 (`54,378/65,861`), architect_general α=0.6854 (`3,745/5,464`), failed MTP roles `[]`. Missing artifact: a current `moe_spec_budget` B-sweep on those live verification batches with speed, acceptance, and quality/bit-exact guard. ✅ 2026-07-18

> **PRE-PRODUCTION REGISTRY-INTEGRATION GATE (2026-04-28; FULLY RELEASED 2026-04-29 — HISTORICAL, superseded by the 2026-06-12 note above)**: The Phase 3 follow-up "production registry integration with per-role binary_path + per-role moe_spec_budget" (REAP=40 confirmed deployable per v5 PGO; Coder=NOT deployable per consolidated v5 verdict) is now UNBLOCKED. Both gating conditions resolved:
>
> - ✅ Condition (a) [`completed/mab-tree-shape-selector.md`](../completed/mab-tree-shape-selector.md) — **CLOSED 2026-04-29 with NO-GO**. Original Phase 0'' "Coder -3.97% p=0.012" was poisoned by broken OMP baseline; Remediation Phase C (2026-04-29 evening) re-tested under canonical at n=180 Coder + n=90 REAP: **Coder -1.34% NS, REAP -8.20% p<0.001**. Disposition unchanged (no-go), framing revised. MAB selector mechanism falsified; Phase 1 not justified.
> - ✅ Condition (b) [`completed/hybrid-ssm-slot-promotion-spec-dec.md`](../completed/hybrid-ssm-slot-promotion-spec-dec.md) — RELEASED 2026-04-28; subsequently CLOSED 2026-04-30 with mechanism net-negative on Qwen3.6-35B+1.7B; dispatcher v1 in tree disabled-by-default.
>
> Both reopener tracks confirm MoE-Spec ceiling is unchanged — neither alternative mechanism delivers gain on this drafter/target/workload class. Production registry integration can proceed when scheduled. Other Phase 3 follow-ups (BOLT-libggml v5 redo, Coder-30B 10-rep alternated re-measurement, Q8 frontdoor + dense, [`moe-dynamic-expert-selection.md`](../completed/moe-dynamic-expert-selection.md) reopen triggers) remain on their own schedules.

**Status**: Phase 1 + Phase 2 + v5 PGO + BOLT-Coder all measured 2026-04-28 evening. **Final verdict: REAP-246B B=40 deployable (+13-16% pp32 / +3% end-to-end, robust across all builds); Coder-30B B=64 NOT deployable (result varies wildly across builds + cache states + system noise — gcc +7.3%, PGO single-B −43%, PGO mixed-B parity-to-+84% depending on cold/warm and noise); BOLT-libggml on v5 PGO Coder NOT deployable this attempt (perf record too short, 4% function coverage, BOLT pessimized mask branch − reopen with morning's recipe of 60s × 4 model classes).** Full consolidated decision at `data/cpu_optimization/2026-04-28-moe-spec-phase-1/decision_v5_FINAL.md`. Phase 1 implementation on `feature/cpu-ep-inter-process` HEAD `0c8d05597`. v5 PGO build at `/mnt/raid0/llm/llama.cpp-experimental/build_v5_pgo_use/`. Phase 0 verdict (queue Phase 1) preserved below.

---

#### Phase 1 — RESULTS (DONE 2026-04-28)

##### Implementation

~30 LOC mask-construction in `src/llama-graph.cpp::build_moe_ffn` between softmax (line 1398) and argsort_top_k (line 1492 post-edit), pattern mirrors existing DeepSeek-V3 expert-groups mask. Plus ~8 LOC param plumbing across `src/llama-cparams.h`, `src/llama-context.cpp`, `include/llama.h`, `common/common.h`, `common/common.cpp`, `common/arg.cpp`, and `tools/llama-bench/llama-bench.cpp` (env var fallback for llama-bench's separate arg parser).

CLI: `--moe-spec-budget N` / env: `LLAMA_ARG_MOE_SPEC_BUDGET=N`. Default 0 (off). Min-batch threshold: `LLAMA_ARG_MOE_SPEC_MIN_BATCH=4`.

Mechanism (matches paper algorithm but with batch-aggregation instead of tree-aggregation):
1. Aggregate routing softmax across n_tokens: `expert_scores = Σ_t probs[i, t]` per expert i.
2. Top-B select on aggregated scores → shortlist S.
3. Mask `selection_probs` to -INFINITY for experts ∉ S (additive mask, broadcast across n_tokens).
4. Existing argsort_top_k naturally selects only in-S experts per token.

##### Headline results (5-rep proper canonical: `taskset -c 0-95 -t 96 -fa 1 --mmap 0` + `numactl --interleave=all`)

**Coder-30B Q4_K_M (n_expert=128, n_expert_used=8):**

| Prompt | B | Throughput (mean ± std) | Δ vs B=0 | PPL chunk 3 | Notes |
|---|---|---|---|---|---|
| pp32 | 0 | 321.35 t/s (avg of 2 runs) | reference | 9.86 | baseline |
| pp32 | 128 | n/a (gate-skip) | bit-exact | 9.86 (byte-identical) | gate-disabled (B≥n_expert) confirms baseline |
| pp32 | 96 | 317.59 t/s | -1.2% (noise) | 9.75 (~baseline) | no-win at 75% budget |
| pp32 | 64 | 344.70 t/s | **+7.3%** | 10.52 (+6.7%) | **PHASE 1 GATE MET — quality cost moderate** |
| pp32 | 32 | 393.17 ± 2.72 | +22.3% | not measured | quality cost severe (B=64 already +6.7% PPL) |
| pp64 | 0 | 402.28 ± 8.04 | reference | — | |
| pp64 | 64 | 429.25 ± 2.69 | **+6.7%** | — | gain holds at larger batch |
| pp64 | 32 | 461.13 ± 2.80 | +14.6% | — | |

**REAP-246B Q4_K_M (n_expert=80, n_expert_used=8):**

| B | Throughput (mean ± std) | Δ vs B=0 | PPL chunk 3 | Notes |
|---|---|---|---|---|
| 0 (run 2) | 45.23 ± 0.99 | reference | 9.30 | baseline (run 1 was noisy outlier 35.64 ± 5.77) |
| 80 | 44.89 ± 1.06 | bit-exact (-0.8% noise) | gate-skip | confirms B≥n_expert disables |
| 60 | 42.19 ± 2.02 | -6.7% (1.4σ; likely noise) | 9.36 (~baseline) | no-win at 75% |
| 40 | 52.11 ± 0.58 | **+15.2%** | 11.44 (+23%) | **PHASE 1 GATE MET — quality cost meaningful** |
| 20 | 62.49 ± 0.07 | +38.2% | 15.79 (+70%) | quality unusable |

##### Phase 1 binding gates (from handoff above)

1. **Throughput gate ≥2% on at least one of Coder-30B / REAP-246B**: **MET** — Coder +7.3% at B=64, REAP +15.2% at B=40, both 3.5σ+ above baseline noise band.
2. **Quality (PPL bit-exact OR governed by spec-dec verifier rejection)**: **STRUCTURALLY OK for spec-dec** — forward-pass PPL drifts measurably at B<n_expert, but spec-dec verifier rejects mismatched draft tokens making end-to-end output bit-exact. Acceptance-rate impact (paper claims 1.4% average reduction) NOT measured here (Phase 2 deliverable).
3. **Stability**: 5-min sustained runs implicit in 5-rep × multi-config sweeps; no crash/deadlock.
4. **Compatibility**: code path is compatible by construction (operates pre-argsort_top_k, downstream `mul_mat_id` unmodified). Existing `moe_n_expert_override` interaction NOT measured.

##### Why measured gain exceeded Phase 0's 3-8% upper-bound estimate

Phase 0 estimate assumed strong overlap with existing `moe_n_expert_override` mechanism. Actual measured gain on REAP-246B (+15.2% at B=40) substantially exceeded estimate because:

- REAP-246B is heavier (~5× slower per token) and therefore more memory-stalled per CPU24 attribution
- Reducing distinct experts loaded directly cuts DRAM expert-weight bandwidth pressure
- Larger model has more headroom for the union-shrinkage mechanism than smaller Coder

Phase 0's "GPU HBM-loading mechanism doesn't translate to CPU" framing was partially correct (no equivalent loading cost) but missed the compounding factor: CPU's L3 cache (~32MB per CCD × 12 CCDs = 384MB) is far below total expert weight footprint (Coder 17GB / REAP 138GB), so each unique expert load IS a DRAM read. Reducing unique-expert-count directly reduces DRAM traffic, same mechanism as GPU HBM, just on a different memory tier.

##### Sweet spots for Phase 2

- Coder-30B: B=64 (50% of n_expert)
- REAP-246B: B=40-50 (need finer sweep; B=60 was noise band, B=40 has +23% PPL drift)

##### Phase 2 deliverables (queued)

1. **End-to-end spec-dec measurement** — actual `--draft-max 32 --p-split 0` config with draft model, measure tokens/s end-to-end and acceptance rate impact
2. **Production registry integration** — if Phase 2 confirms ≥2% end-to-end gain, add `moe_spec_budget` per-role config to `model_registry.yaml` (Coder-30B → 64, REAP-246B → 40 likely)
3. **Interaction with `cparams.moe_n_expert_override`** — production sometimes uses `--override-kv qwen3moe.expert_used_count=int:4`; measure whether MoE-Spec compounds or partially substitutes
4. **PGO+BOLT rebuild revalidation** — current build is gcc+libgomp; v5 production binary will be clang+libomp+znver5+PGO; mechanism gain may compound or shrink under PGO
5. **Full WikiText-2 32-chunk PPL gate** — 3-chunk diagnostic suffices for Phase 1 mechanism validation; full PPL needed for production routing decisions
6. **Tree spec-dec interaction** — paper's native algorithm operates on trees; if Phase 2 production benefit motivates re-enabling tree spec-dec on Coder/REAP (currently `p_split: 0` in registry due to historical sweep finding tree harmful at 48t), test whether tree+MoE-Spec reverses the historical tree finding



1. The paper's GPU mechanism (HBM expert-weight loading reduction during tree spec-dec verification) does NOT directly translate, BUT the underlying "reduce distinct experts touched per verification batch → reduce DRAM expert-weight reads" mechanism DOES translate to CPU. CPU expert weights are mmap'd in DRAM and the verification's `mul_mat_id` op reuses each expert across all matching tokens in the batch.
2. **Production runs Coder-30B and REAP-246B with `p_split=0` (linear spec-dec only)** — tree spec-dec was empirically tested and harmful (`registry:378 — Coder-30B tree net-negative at 48t`; `registry:447 — REAP-246B tree harmful at all ps values`). The paper is tree-only by mechanism (aggregates routing scores across 63-token EAGLE-3 trees), but the algorithm trivially extends to linear K=32 batched verification: aggregate routing scores across the K verification tokens, top-B select, mask out-of-S experts.
3. **Existing `cparams.moe_n_expert_override` already captures partial compute reduction** — `--moe-n-expert N` reduces per-token K from 8 to N. Production already uses this (e.g., `--override-kv qwen3moe.expert_used_count=int:4` for some Coder-30B configs). MoE-Spec's contribution would be tree/batch-level union shrinkage on top of per-token K reduction; the available delta is narrower than the GPU case where no equivalent mechanism existed.
4. Expected CPU gain on linear K=32 spec-dec: 3-8% upper bound (much less than paper's GPU 10-30% on tree). Below the original handoff's 5-15% framing but still potentially deployable.

Re-flagged 2026-04-27 after peer-review pass #2 noted that "all software paths exhausted" framing in upstream indices was incompatible with this stub's existence. Created 2026-04-27 evening as Phase 4 of closure-inflation remediation plan; previously a research note buried in `cpu-shape-specialized-gemv-decode.md`. Phase 0 completed same evening.
**Priority**: MEDIUM (algorithmic; competes with future hardware-acceleration work for engineer-time, NOT with closed CPU kernel/runtime tracks)
**Categories**: moe_optimization, speculative_decoding, inference_serving, hardware_optimization
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`inference-research-index.md`](inference-research-index.md), [`inference-research-index.md`](inference-research-index.md)
**Related**:
- [`cpu-shape-specialized-gemv-decode.md`](../completed/cpu-shape-specialized-gemv-decode.md) — research note that surfaced this technique (Session 2026-04-27)
- [`large-moe-expert-parallelism.md`](sarathi-serve-cpu-evaluation.md#track-large-moe-expert-parallelism) (CPU15) — compacted disposition gate; MoE-Spec only needs CPU15 coordination if `GGML_EP_*` is explicitly re-enabled after CPU15-REVAL
- [`research/intake_index.yaml`](../../research/intake_index.yaml) — intake entry to be added (forthcoming)

#### Background

MoE-Spec ([arxiv:2602.16052](https://arxiv.org/html/2602.16052v1), Feb 2026) is a training-free expert-budgeting technique that integrates with speculative decoding's verification step. The draft model proposes K candidate tokens; instead of running all experts during verification, MoE-Spec selects a budgeted subset of top-scoring experts per token for the verification pass. Reports **10-30% throughput improvement over EAGLE-3** at comparable quality on GPU benchmarks.

Adjacent prior art (also surfaced in the 2026-04-27 research check):
- **OD-MoE shadow networks** — ~84-91% expert-prediction accuracy with single-layer lookahead; >99% with separate shadow networks. More complex (requires training a small auxiliary model).
- **MoE Pathfinder** ([arxiv:2512.18425](https://arxiv.org/abs/2512.18425), Dec 2025) — Trajectory-driven expert pruning; treats expert selection as global path-planning across the layer graph.
- **REAP (Router-weighted Expert Activation Pruning)** ([arxiv:2510.13999](https://arxiv.org/abs/2510.13999)) — ALREADY DEPLOYED as the technique behind our REAP-246B model (Cerebras-pruned 480B → 246B). MoE-Spec is the inference-time analog.
- **Dynamic Skipping** — per-token, layer-calibrated `β` threshold for expert ratio comparison.

#### Why this exists

Most published MoE-Spec / OD-MoE / Pathfinder work is GPU-focused. CPU adaptation requires a llama-server scheduler change at the spec-dec verification step, NOT a kernel change. We already run spec-dec on Coder-30B and REAP-246B in production. If MoE-Spec ports cleanly, the expected gain is **5-15% on Coder-30B and REAP-246B decode** per the original research-check estimate.

This is independent of CPU2 (SIMD kernels), CPU15 (EP sharding), CPU22 (work-stealing). It operates at a different layer of the stack (scheduler vs kernel vs sharding).

#### Conflict / overlap analysis

| Track | Interaction with MoE-Spec |
|---|---|
| CPU2 SIMD kernels (Q8_0/Q6_K/Q4_K AVX-512BW) | Neutral — MoE-Spec changes which experts run, kernels are the same |
| CPU15 EP inter-process | CONFLICT POTENTIAL — both modify the verification-step expert dispatch path; need to either pick one or design integration carefully |
| CPU22 work-stealing | Neutral — work-stealing operates at the load-balancing layer below MoE-Spec's expert-selection layer |
| Existing spec-dec stack (`--draft-max`, `--p-split`, tree decoding) | Direct interaction — MoE-Spec adds a budgeted-expert dimension on top of K-token spec-dec |

#### Phase 0 — falsification probe spec (detailed)

**Goal**: cheaply confirm or refute that MoE-Spec's expert budgeting at the verification step delivers measurable throughput on our CPU spec-dec path before committing to a full integration.

##### Step 0.1 — Reference implementation review (1-2 hours)

- Read the upstream MoE-Spec arXiv:2602.16052 paper end-to-end. Pay special attention to: section 3 (algorithm details), section 4 (experimental setup — what was the baseline they compared against?), section 5 (results — distinguish absolute throughput gains from relative-vs-EAGLE-3 framing).
- Search GitHub for the reference code release. As of 2026-04-27 the paper says "code coming soon". If unreleased, work from the algorithmic description.
- Capture in a design note: (a) the exact expert-selection function (likely a top-K over routing scores at verification step), (b) the budget parameter B (= number of experts kept; default in paper TBD), (c) the integration point (where in the spec-dec verifier loop the budgeting fires).

##### Step 0.2 — Trace our existing spec-dec verifier path (1-2 hours)

- Read `tools/server/server.cpp` spec-dec path: where the draft tokens are verified against the target model, where the target model's MoE expert dispatch is invoked.
- Read `ggml/src/ggml-cpu/ggml-cpu.c` `ggml_compute_forward_mul_mat_id` (the MoE expert dispatch op). Identify where the routing scores are computed and where the expert subset is selected.
- Output: a numbered list of insertion points where MoE-Spec's budgeted-expert selection logic could attach.

##### Step 0.3 — Compatibility check vs CPU15 EP and CPU22 (1-2 hours)

- CPU15 EP master/worker drone path: workers receive the full src1+ids broadcast and run `ggml_compute_forward_mul_mat_id` independently. If MoE-Spec budgets at the routing-score selection step, each worker would need to apply the same budget — straightforward but requires the budget signal to flow through the IPC ring.
- CPU22 work-stealing (Phase 3 of remediation): operates at the expert-tile load-balancing layer below MoE-Spec's expert-selection layer. Should be orthogonal — MoE-Spec selects WHICH experts run, work-stealing balances HOW the selected experts' tiles are distributed across threads. No conflict; potentially compounding.
- Existing spec-dec stack (`--draft-max N`, `--p-split` for tree, etc.): MoE-Spec adds a budgeted-expert dimension on top. Tree spec-dec branches won't compound naively — each branch's verification step independently budgets. Linear spec-dec is simpler — single verification path, single budget.

##### Step 0.4 — Phase 1 prototype scope estimate (1-2 hours)

Output an explicit estimate:
- LOC estimate (target: <500 lines for the budgeting logic + env-flag wiring)
- Files to modify (likely: `ggml/src/ggml-cpu/ggml-cpu.c` mul_mat_id, a new `ggml_moe_spec.{h,cpp}` for the budget logic, optional `tools/server/server.cpp` for spec-dec wiring if budget needs to flow through HTTP request)
- Risk classification (LOW: pure scheduler change, no kernel rewrite. MEDIUM: needs to coordinate with CPU15 EP if production frontdoor uses both. HIGH: needs custom kernel — flagged for handoff escalation).
- Falsification budget: total 4-8 hours for Steps 0.1-0.4.

##### Phase 0 gate

- If integration surface looks LOW risk + ≤500 LOC + ≤1-2 days prototype → queue Phase 1 immediately.
- If MEDIUM risk + 1-2 weeks prototype → escalate priority decision (compete with CPU22 work-stealing for engineer time).
- If HIGH risk OR >2 weeks prototype → defer; prefer CPU22 work-stealing first.

#### Phase 0 — RESULTS (DONE 2026-04-27 evening)

##### Step 0.1 — paper read (arXiv:2602.16052)

Authors: McDanel, Li, Surineni, Khaitan (Feb 2026). Pseudocode (Appendix B):
```
For draft tree of M tokens, hidden states {h_t}:
  for each expert i: s_i = Σ_t g_i(h_t)         # aggregate routing-prob across tree
  S = top-B experts by score s_i                  # tree-level shortlist
  for each token t: expert subset = top_k(h_t) ∩ S  (truncate)
                              OR    top-B(h_t restricted to S) (substitute)
```

Key facts:
- **Mechanism targets memory bandwidth on GPU** ("expert explosion": 63-token EAGLE-3 tree on OLMoE-1B-7B activates 54 of 64 experts per layer; HBM must load the union)
- **Tree-only on EAGLE-3 trees**; not evaluated on linear spec-dec
- Budget B is **fixed per deployment**, searched empirically ({8, 16, 24, 32, 40, 48, 56} for OLMoE; {16, 24, 32, 48, 64} for Qwen3)
- B can be < per-token top-K (k=8 with B=32 means tokens whose natural top-K falls outside S receive fewer than k experts)
- Quality impact: **1.4% acceptance-rate reduction average**; task-dependent (code tolerates tight budgets, reasoning degrades steeper)
- vs EAGLE-3 baseline: **10-30% throughput** on A100 GPU
- **No code release** found; paper says "extends EAGLE-3 codebase"
- Hardware: A100 80GB (single-GPU OLMoE/Qwen3, dual-GPU Mixtral). No CPU mention.

##### Step 0.2 — CPU spec-dec verifier path traced

**Verification call site**: `tools/server/server-context.cpp:3030-3081` (slot decode path).
Spec-dec drafts are produced via `common_speculative_draft()` (common/speculative.cpp); the target verification is the standard `llama_decode(ctx_tgt, batch)` with batch_size=K (linear) or batch_size=tree.n_nodes (tree).

**Tree mechanism EXISTS in our fork**: `common/speculative.cpp:1137-1300` (DySpec heap-based dynamic tree construction). Triggers when `params.p_split > 0.0f` (line 1381). Production registry: tree DISABLED on Coder-30B + REAP-246B (`p_split: 0`); tree ENABLED on some other models with `p_split: 0.05`.

**Routing-score location (the real insertion point)**: `src/llama-graph.cpp:1395-1458` (`build_moe_ffn` function).
- Line 1398: `probs = ggml_soft_max(ctx0, logits)` → `[n_expert, n_tokens]`
- Lines 1413-1454: existing **DeepSeek-V3 expert-groups mask** uses exactly the structure MoE-Spec needs — masks `selection_probs` to -infinity for out-of-group experts before `argsort_top_k`
- Line 1458: `selected_experts = ggml_argsort_top_k(ctx0, selection_probs, n_expert_used)` → `[n_expert_used, n_tokens]`

**Original handoff's "ggml_compute_forward_mul_mat_id is the insertion point" was wrong**. mul_mat_id sees only already-selected expert ids; the budgeting must fire before argsort_top_k at the graph-build layer.

**Existing related infrastructure** (already in fork): `cparams.moe_n_expert_override` (`src/llama-cparams.h:46`) reduces per-token K from `n_expert_used` to override value. Wired through `--moe-n-expert N` CLI / `LLAMA_ARG_MOE_N_EXPERT` env. Implementation at `llama-graph.cpp:1477-1499`. **MoE-Spec is a different mechanism (per-batch top-B union shrinkage) — orthogonal to per-token K reduction.**

##### Step 0.3 — Compatibility analysis

| Surface | Interaction | Verdict |
|---|---|---|
| Linear spec-dec (Coder-30B + REAP-246B production) | Aggregate routing scores across K=32 verification tokens; mask out-of-S experts | COMPATIBLE — algorithm trivially extends from tree-aggregation to batch-aggregation |
| Tree spec-dec (DySpec, p_split>0) | Direct match for paper's algorithm | COMPATIBLE but production stack disables tree on the two target models |
| `cparams.moe_n_expert_override` (per-token K reduction) | Both mask `selection_probs` before argsort; orderings: MoE-Spec mask first (per-batch), then existing override (per-token K) | COMPATIBLE — orthogonal masking; possibly compounding |
| CPU15 EP (inter-process expert parallelism) | Master broadcasts src1+ids to workers; if budget masking happens at master before broadcast, workers see smaller `ids` array | COMPATIBLE if EP is explicitly enabled, but currently theoretical. CPU15 is default-off infrastructure after the 2026-05-28 compaction/canonical-baseline correction; no production role should assume `GGML_EP_*` is active without CPU15-REVAL. |
| CPU22 work-stealing | Closed via test, default-OFF; if reopened, operates at tile-distribution layer below MoE-Spec's expert-selection layer | ORTHOGONAL |
| `--draft-max=32 --p-split=0` (production Coder/REAP linear K=32) | Verification batch_size=32; MoE-Spec aggregates across the 32 tokens | COMPATIBLE |
| PPL preservation | spec-dec produces bit-exact output by construction (verifier rejects mismatched draft tokens regardless of target's expert subset); MoE-Spec changes target's expert dispatch but not the acceptance rule | bit-exact PPL EXPECTED |

**REAP-246B has a draft model** (`Qwen3-Coder-Instruct-DRAFT-0.75B-32k-Q4_0.gguf`, registry line ~441). MoE-Spec applies to the target's verification step, not the draft. The draft model has its own architecture (dense at 0.75B, no MoE) so MoE-Spec is moot for the draft side. REAP-246B's MoE target is what MoE-Spec acts on.

##### Step 0.4 — Phase 1 prototype scope estimate

| Item | Estimate |
|---|---|
| LOC | ~100-150 in `src/llama-graph.cpp` + ~20 in `src/llama-cparams.h` + `src/llama-context.cpp` + `common/common.cpp`/`.h` for `--moe-spec-budget` flag + env var |
| New ggml ops | NONE — reuses existing `ggml_sum_rows` + `ggml_argsort_top_k` + `ggml_set_rows` + `ggml_fill` (all already used by DeepSeek-V3 expert-groups path; pattern at lines 1437-1454) |
| Risk class | **LOW** — pure scheduler change, no kernel rewrite; bit-exact PPL is structural property of spec-dec (verifier rejects mismatches) |
| Build/test cycle | 1-2 days prototype + 1 day measurement |
| Falsification budget | Phase 1 MAX 3 days; if no signal, close honestly via test (not via inference) |

##### Phase 0 GATE VERDICT: **QUEUE PHASE 1**

Per handoff Phase 0 gate criteria: "LOW risk + ≤500 LOC + ≤1-2 days prototype → queue Phase 1 immediately". All three met.

**Prototype Phase 1 implementation sketch**:
1. Add `cparams.moe_spec_budget` (default 0 = off), `--moe-spec-budget N` CLI flag, `GGML_MOE_SPEC_BUDGET=N` env var (mirrors existing `moe_n_expert_override` plumbing).
2. In `src/llama-graph.cpp::build_moe_ffn` after line 1398 softmax, when `cparams.moe_spec_budget > 0 && cparams.moe_spec_budget < n_expert && n_tokens >= cparams.moe_spec_min_batch (default 8)`:
   - Aggregate: `expert_scores = ggml_sum_rows(probs)` → `[1, n_expert]` (sum across n_tokens)
   - Top-B select: `top_b = ggml_argsort_top_k(expert_scores, cparams.moe_spec_budget)` → `[B, 1]`
   - Build mask following existing expert-groups pattern (lines 1437-1454): set selection_probs to -INFINITY for experts NOT in top-B
   - Existing argsort_top_k at line 1458 naturally selects only in-S experts per token
3. Quality validation: PPL bit-exact at 12 chunks WikiText-2 on Coder-30B Q4_K_M and REAP-246B Q4_K_M (will pass by construction).
4. Throughput measurement: 5-rep proper canonical on:
   - Coder-30B Q4_K_M with `--draft-max 32 -p-split 0` (production config), B sweep over {n_expert/2, n_expert*3/4, n_expert} where n_expert=128 (B=128 is off; B=64 mid; B=96 light)
   - REAP-246B Q4_K_M with `--draft-max 32 -p-split 0`, B sweep matching n_expert (likely 80 for REAP-246B post-pruning; sweep {40, 60, 80})
5. Success gate: ≥5% on at least one of the two models OR explicit closure via test.

Phase 1 prototype branches from `feature/cpu-ep-inter-process` (current HEAD `0bc793637`).



Likely env-gated `GGML_MOE_SPEC_BUDGET=N` (default 0 = off; 0 < N < expert_count = budget the verification-step expert selection to top-N by routing score) controlling the budgeted-expert count at verification.

Implementation sketch (subject to Phase 0 refinement):
1. Add an `extra` field to ggml_tensor for `mul_mat_id` ops carrying the budget B. (Or use a thread-local global like `ggml_moe_spec_budget` set per request.)
2. In `ggml_compute_forward_mul_mat_id`, when B > 0 and B < n_experts, after the routing scores are computed but BEFORE the selected-expert loop runs, sort the routing scores and pick top-B. Replace the current "use all selected experts" with "use only the top-B by score".
3. Quality validation: ensure the spec-dec verifier still rejects mismatched draft tokens correctly. Since MoE-Spec changes the target's expert subset at verification, the target's logits will differ from a no-budget baseline — but spec-dec already tolerates this kind of variation (it accepts/rejects based on the target's distribution, whatever that is).
4. Throughput measurement: per-token decode rate at `--draft-max 16 --draft-min 4` with B sweep over {0 (off), n_experts/4, n_experts/2, n_experts*3/4}.

#### Measurement gates (Phase 1 binding)

1. Throughput: ≥5% on at least one of Coder-30B or REAP-246B decode (relaxed from 10-15% literature claim because GPU→CPU port typically halves expected gains).
2. Quality: PPL bit-exact OR ≤1e-3 drift vs no-MoE-Spec baseline. Spec-dec already produces bit-exact output by construction (verifier rejects mismatched draft tokens), so MoE-Spec quality should be governed by the same property.
3. Stability: 5-min sustained run, no crash/deadlock.
4. Compatibility: works alongside existing tree/linear spec-dec config without conflict.

#### Risk areas

- MoE-Spec's expert-budget selection might trigger different MoE expert activation patterns, potentially reducing the spec-dec acceptance rate. Need to measure acceptance-rate impact alongside throughput.
- CPU15 EP partial overlap: if both are enabled simultaneously, the verification-step expert dispatch is double-modified. Phase 0 must clarify the integration story.
- Reference implementation may be GPU-specific in non-trivial ways (CUDA kernels for the scoring step). Falsification probe must check this.

#### Integration effort estimate

- Phase 0 falsification: 4-8 hours (read paper, identify port surface, design note)
- Phase 1 prototype (if Phase 0 says feasible): 1-2 weeks
- Validation: 2-3 days

Multi-week effort overall. Prioritize against CPU22 work-stealing during Phase 4 of the remediation plan.

#### Sources

- [MoE-Spec arXiv 2602.16052](https://arxiv.org/html/2602.16052v1) — primary technique
- [MoE Pathfinder arXiv 2512.18425](https://arxiv.org/abs/2512.18425) — trajectory-driven pruning (alternative)
- [REAP arXiv 2510.13999](https://arxiv.org/abs/2510.13999) — already deployed (REAP-246B)
- [Awesome MoE Inference](https://github.com/MoE-Inf/awesome-moe-inference/) — collection
- [Discovering Important Experts NeurIPS 2025](https://neurips.cc/virtual/2025/poster/119676)
- Surfaced in: `cpu-shape-specialized-gemv-decode.md` (Session 2026-04-27 research check)

#### Research Intake Update — 2026-04-28

##### New Related Research

- **[intake-487] "Adaptive hybrid speculative decoding for accelerating large language model inference"** (Yang Yong et al., Neurocomputing 2026, peer-reviewed, paywalled)
  - Relevance: Same problem space as Phase 1's verification-batch mechanism — adaptive draft length + hybrid drafting. Mechanism unverifiable (no preprint, no abstract accessible).
  - Delta: catalog only; revisit if a preprint or open code surfaces. No action — Phase 1 gate already met by our heap-spec mechanism on Coder-30B + REAP-246B.

- **[intake-491] "Mamba Drafters for Speculative Decoding"** (arxiv:2506.01206; Findings of EMNLP 2025) — verdict: **worth_investigating**
  - Relevance: SSM-drafter-for-Transformer-target principle is directly applicable to our 30B-A3B + REAP-246B verification stack. Constant-memory drafter avoids the draft-path DRAM-bandwidth competition that limits speedup at large target sizes on EPYC.
  - Key technique: Mamba-130M external drafter + MAB-optimized tree-shape selector.
  - Reported results: GSM-8K 149.46 tok/s vs Pythia-410M 119.67 (Pythia-6.9B target); MT-Bench accept length 3.91 vs EAGLE 3.85.
  - Delta from current approach: (a) MAB tree-shape selector is a drop-in upgrade for our heap-spec tree shape independent of the SSM piece — investigate first; (b) SSM drafter for Coder-30B target requires hand-rolled Mamba inference in our llama.cpp fork, with no off-the-shelf small Mamba model tuned for our target's vocabulary — investigation, not adoption.
  - Caveats (Tier 2b): hidden-state backtracking limitation, tree verification incompatibility with sequential SSM, hyperparameter sensitivity. Competing approach (arxiv:2512.20573 diffusion-LLM drafting, Dec 2025) raises directional question whether SSM drafting is the long-term winner.

#### Phase 2 — IN PROGRESS as of 2026-04-28 evening (wrap-up snapshot)

##### v5 PGO build with MoE-Spec patch baked in

**Build dirs** (at `/mnt/raid0/llm/llama.cpp-experimental/`):
- `build_v5_pgo_gen/` — PGO instrumented (clang-20 + libomp + -march=znver5 + `-fprofile-instr-generate`)
- `build_v5_pgo_gen/merged.profdata` (2 MB) — merged from coder + q8 + reap profile runs (B=0 + B=64 Coder + B=40 REAP for mixed coverage; dense killed at 22 min wall)
- `build_v5_pgo_use/` — PGO-use rebuilt with `-fprofile-instr-use=...` from mixed merged.profdata; `--emit-relocs` linker flag for downstream BOLT

**Key insight from PGO single-B vs mixed-B**: under single-B (B=0 only) profile, the v5 build pessimized the MoE-Spec mask branch — Coder-30B B=64 dropped to **−43%** vs B=0 (mask overhead unprofiled, branch slow). After adding B=64 Coder + B=40 REAP profile runs to merged.profdata and rebuilding, Coder-30B B=64 returns to **parity (−2.6%)**. REAP-246B B=40 unaffected by either build (consistent +15% in both single-B and mixed-B PGO) because REAP's mask-overhead/total-compute ratio is small.

**Lesson for future PGO builds with MoE-Spec deployed**: profile workload MUST exercise B>0 path or PGO will pessimize it.

##### Phase 1 mechanism re-validation under v5 PGO mixed-B (5-rep proper canonical)

Megasync at 100% on 1 core during measurement window depressed absolute numbers ~50% (clean Coder pp32 B=0 ~379 t/s; under noise ~198 t/s). Relative deltas within sweep are noise-tolerant.

**Coder-30B Q4_K_M pp32:**
| B | mean ± std | Δ vs B=0 |
|---|---|---|
| 0 | 198.57 ± 5.55 | reference |
| 96 | 144.79 ± 6.54 | −27.0% (mask overhead at light budget exceeds savings) |
| 64 | 193.34 ± 10.64 | **−2.6% (parity)** |
| 32 | 249.60 ± 3.24 | +25.7% (severe quality cost — see Phase 1 PPL data) |

**REAP-246B Q4_K_M pp32:**
| B | mean ± std | Δ vs B=0 |
|---|---|---|
| 0 | 51.14 ± 1.11 | reference |
| 60 | 52.05 ± 0.99 | +1.8% (within noise) |
| 40 | 58.06 ± 0.59 | **+13.5% (clean signal)** |
| 20 | 74.45 ± 0.08 | +45.6% (quality unusable per Phase 1 PPL) |

##### Phase 2 end-to-end spec-dec via llama-server (IN PROGRESS)

Background task `b4bk8cu9g` running. Per-config: 3 prompts × n_predict=256 × spec-dec config matching production (`--draft-max 32 --p-split 0` linear). Captures `predicted_per_second` + `draft_n_accepted/draft_n` from /completion timing.

REAP-246B partial:
- B=0 (3 reps): rep0 server-not-ready JSON empty; rep1=7.27 t/s 59.9%; rep2=7.90 t/s 56.2%
- B=60 in progress at wrap-up
- B=40 + Coder B=0/64/32 queued (~25 min remaining)

Production registry reference: REAP-246B = 8.0 t/s spec-dec, 74-82% accept on coding workloads (we're testing on general prompts so accept rate is lower).

##### Phase 2 deferred items (post-end-to-end completion)

1. **BOLT-libggml on v5 PGO for Coder-30B role**: morning's `libggml-cpu.so.0.coder.fdata` likely incompatible with v5 binary layout; needs fresh perf-record + perf2bolt + llvm-bolt cycle.
2. **Production registry integration** (`/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml`):
   - Per-role binary_path: REAP-246B + Q8 frontdoor + dense → universal v5 PGO binary; Coder-30B → v5 PGO + BOLT-libggml binary
   - Per-role moe_spec_budget config: REAP-246B → 40; Coder-30B → 0 (skip; quality+throughput tradeoff doesn't pencil out under v5 PGO for B=64 parity); other models → 0
3. **Orchestrator launch path** (`orchestrator_stack.py`): read per-role binary_path + env-pass MoE-Spec budget
4. **production-consolidated-v5 branch** in `/mnt/raid0/llm/llama.cpp`: git history paperwork — cherry-pick from `feature/cpu-ep-inter-process` HEAD `0c8d05597` onto `production-consolidated-v4`. Optional; the binary built from experimental HEAD is functionally equivalent.
5. **Full 32-chunk PPL gate on v5 PGO build**: 3-chunk diagnostic suffices for Phase 1; production routing decisions need full PPL.

---

#### Research Intake Update — 2026-05-27

Companion `/research-intake` run for `gpu-drafter-mi200-investigation.md` surfaced one paper directly relevant to this handoff.

##### New Related Research

- **[intake-620] "SpecDec++: Boosting Speculative Decoding via Adaptive Candidate Lengths"** (arxiv:2405.19715, COLM 2025, Princeton + Tsinghua)
  - Relevance: SpecDec++ formalizes adaptive γ as an MDP and trains a per-token acceptance-prediction head on the drafter — the principled replacement for the current MoE-Spec verification-budget heuristic. Where MoE-Spec adjusts the *verification* budget (expert union reduction), SpecDec++ adjusts the *drafting* budget — orthogonal but composable.
  - Key technique: binary classifier on draft hidden state; stop drafting when cumulative rejection probability crosses learned threshold.
  - Reported results: 2.04× Alpaca / 2.26× GSM8K / 2.23× HumanEval (7-11pp over fixed γ).
  - Delta: layered onto MoE-Spec's +15.2% forward-pass / +3% e2e on REAP-246B, SpecDec++ would close the drafter side of the same loop. Lower priority than the current MoE-Spec rollout but a natural follow-on.

- **[intake-621] "DeepSeek-V3 Technical Report" (MTP section)** (arxiv:2412.19437) — cross-link only; main entry lives with the GPU-drafter handoff. DeepSeek-V3 MoE + MTP is the closest published reference architecture for "MoE target with MTP-style spec-dec head" — relevant for prior-art comparisons in the wiki page.

See `gpu-drafter-mi200-investigation.md` § Research Intake Update for the full 9-entry intake batch.

#### Research Intake Update — 2026-05-28

##### New Related Research

- **[intake-637] "DeepSeek-V4-Flash GGUF (antirez)"** (huggingface.co/antirez/deepseek-v4-gguf) — verdict: **worth_investigating** — **SUPERSEDED 2026-08-09; local testing closed 2026-08-26**: the antirez Q4-mixed GGUF and successor 0731 weights were deleted. The completed [`deepseek-v4-flash-0731-dspark.md`](../completed/deepseek-v4-flash-0731-dspark.md) Phase 2 remains historical production-implementation evidence for `COMMON_SPECULATIVE_TYPE_DRAFT_DSPARK` alongside `DRAFT_MTP`/`DRAFT_DFLASH`/`DRAFT_EAGLE3`; no DeepSeek rerun is implied, while the generic mechanism remains reusable.
  - Relevance: Ships an optional MTP-only side-file (3.6 GiB) packaging V4's multi-token-prediction head as a spec-dec drafter — same MTP-as-drafter pattern as our gemma4 / DSv3.2 deployments.
  - Key technique: Standalone MTP head GGUF, intended to drive a self-drafting MoE target (V4 verifier + V4-MTP drafter).
  - Reported results: MTP sidecar 3.6 GiB; no acceptance-rate measurement on card.
  - Delta from current approach: If `deepseek4` arch lands in llama.cpp/ik_llama.cpp, this becomes a candidate for a new MoE-spec target/drafter pair. Recipe directly extends the gemma4 MTP integration (see `project_gemma4_mtp_launch_recipe`). Pre-flight: verify (a) llama.cpp deepseek4 support, (b) MTP sidecar load API parity with gemma4 path, (c) acceptance-rate on representative workload (defer to user per `feedback_speed_verify_via_llama_bench`).

#### Research Intake Update — 2026-07-02

##### New Related Research

- **[intake-738] DSpark** (semi-autoregressive drafter + hardware-aware adaptive verification-depth; DeepSeek) — verdict: **adopt_patterns** (catalog).
  - Relevance: DSpark's confidence head + scheduler set per-request **verification depth** from live GPU utilization — the batch-serving successor to this file's fixed budget-B verification-step mechanism. Composes with intake-620 SpecDec++ (adaptive drafting-γ) as the drafting-vs-verification pair.
  - CPU verdict: the utilization-keyed adaptive-verification-depth controller is **GPU-high-concurrency-specific and largely inert on our concurrency-1, bandwidth-bound CPU decode**; the transferable core is the semi-AR draft head, which needs training (DeepSpec pipeline) + a GGUF port.
  - Numbers: +26.7-30.9% acceptance length over EAGLE-3, 57-85% production speedup — **all vendor-reported, GPU, unreproduced**; observations only (no protocol-id), **NOT a reopen trigger** against the catalog-only gate in the top CURRENT-STATE note.
- **[intake-742] Graft** ("Draft Less, Retrieve More: Hybrid Tree Construction", arXiv 2605.20104) — verdict: **adopt_patterns** (catalog).
  - Relevance: training-free, drafter-agnostic **prune-then-graft** — confidence-pruned draft-tree branches are refilled from a top-k successor adjacency structure. MoE-Spec is tree-native (aggregates routing scores across EAGLE-3 trees), so this is on-topic; conceptually pairs with a **CPU-resident n-gram / prompt-lookup refill** (chapter 03 lineage) of pruned branches.
  - Caveat: base drafter is EAGLE-3 (GGUF-incompatible in our fork) + a GPU-resident adjacency matrix; all numbers GPU. Catalog-only until a CPU-refill variant is measured on bandwidth-bound EPYC.
- **[intake-741] DFlare** ("Scaling Up Draft Capacity for Block Diffusion Speculative Decoding", arXiv 2606.02091; PKU + Tencent AngelSlim) — verdict: **worth_investigating** (GPU-track).
  - Relevance: layer-wise fusion lifts DFlash draft capacity (+5-11% over DFlash on GPU); ships in Tencent/AngelSlim, the toolkit `angelslim-techniques-evaluation.md` already mines.
  - **DISAMBIGUATION**: DFlare ≠ our closed **DFlash-on-Q4_K_M** (a different technique; our `dflash-block-diffusion-speculation.md` already concluded block-diffusion drafting NET-NEGATIVE on CPU at 0.3-1.4% acceptance). DSpark's "+16-18% over DFlash" is a GPU acceptance-length claim, not our CPU-throughput axis. Track for the MI210 GPU path only; cf. the diffusion-LLM-drafting competing-approach note in §Phase 2.

#### Progress checklist

- [x] **Former no-consumer blocker reassessed ✅ 2026-07-18**: the 2026-07-03 live MTP acceptance report proves current verification-batch consumers exist (`frontdoor` α=0.6582, `worker_general` α=0.8256, `architect_general` α=0.6854, failed MTP roles `[]`). Registry integration remains blocked until current sweep evidence exists.
- [x] **REOPEN-ASSESS zero-inference decision ✅ 2026-07-18**: reopen to a current live-MTP MoE verifier B-sweep, not to registry integration.
- [x] **Current live-MTP MoE verifier B-sweep**: run on actual frontdoor/worker/architect verification batches with speed, acceptance, and quality/bit-exact guard before any registry integration. ✅ 2026-08-27 — **GATE MET (architect +10.7% at B=n_expert/2)**, decision-grade record at `epyc-inference-research/data/moe-spec-bsweep-2026-08-25/` (findings.md + summary.json + summary_receipt.json). Canonical run (region lock q0-q3, binary v10126 `c7c37a0d9` = MoE-Spec `6b2cbf539` on v9 `0db32c06e`, MTP posture, greedy, 3 reps/cell):
  | role | B | t/s mean±std | Δ vs B=0 | α | α Δ |
  |---|---|---|---|---|---|
  | architect (122B Q4_K_M, n_expert=256) | 0 | 10.84±0.39 | ref | 0.487 | — |
  | | 128 | 12.00±0.41 | **+10.7%** | 0.463 | −2.4pp |
  | | 192 | 11.53±0.22 | +6.4% | 0.462 | −2.5pp |
  | frontdoor (35B-A3B Q8, 256) | 0 | 36.19±2.19 | ref | 0.577 | — |
  | | 128 | 32.05±2.98 | −11.4% | 0.517 | −6.0pp |
  | | 192 | 33.09±0.55 | −8.6% | 0.533 | −4.4pp |
  | worker (gemma4-26B Q4, 128) | 0 | 57.25±4.09 | ref | 0.570 | — |
  | | 64 | 55.77±19.16 | −2.6% | 0.548 | −2.2pp |
  | | 96 | 51.24±13.58 | −10.5% | 0.461 | −10.9pp |
  | | 128 (gate-skip) | 58.54±4.75 | +2.3% (noise) | 0.570 | 0 |

  **Verdict + caveats**: Phase-1 shape reproduces (heaviest DRAM-bound role wins; lighter roles negative). (1) n=3/cell — architect Δ≈2.9σ; operator declined the 5-rep confirm. (2) α −2.4pp on the winner; budgeted arms' outputs differ from B=0 by construction — mechanism-fire control passed (worker B=n_expert bit-exact to B=0, 3/3). (3) Cross-run MTP non-determinism: same-seed B=0 reps differ across runs on every role → strict bit-exact guard enforceable only via the gate-skip control. **Registry implication (PROPOSED, NOT applied — E8-reseed/OP-19 gate)**: `architect_critic` (122B Q4_K_M, :8074 — the measured "architect" role since the 2026-07-31 swap; architect_general is now GPU 27B) → `moe_spec_budget: 128`; frontdoor/worker stay 0; launcher must env-pass `LLAMA_ARG_MOE_SPEC_BUDGET=128`; patch text: `data/moe-spec-bsweep-2026-08-25/registry_patch_proposal.yaml`.
  *Note 2026-09-16: the "E8-reseed/OP-19 gate" above is resolved by operator ruling [`ruling_op19_e8_chain_20260827.json`](../../artifacts/operator/ruling_op19_e8_chain_20260827.json) (root `1ee8bd7c`). The ruling retires the E8 chain and re-anchors the reseed gate to the current eras; the gate binds only at promotion.*

- [ ] **Registry integration — now UNBLOCKED, and NOT yet done.** The prior gate was "registry
      integration remains blocked until current sweep evidence exists"; that evidence now exists
      (B-sweep ✅ 2026-08-27, gate met). This has no checkbox of its own, so it was invisible to the
      dashboard and screened as a prune candidate on 2026-08-28 — filed here rather than archived.
      **Do not integrate on the +10.7% alone: see the countervailing surface below.**
- [ ] **Refresh `wiki/INDEX.md`'s uninformative-`tg128` framing**, which repeats the "paired `tg128` row is
      uninformative by construction" line without the `pp512` half and goes stale now that the four downstream
      corrections have landed (`wiki/INDEX.md:3`) (found 2026-09-14, noninf sweep).
- [ ] **PREPARE the belief-kernel write-side wiring for the two MoE-Spec record sets** — neither carries a
      protocol-id, so no MoE-Spec number is a claim under `MEASUREMENT.md`, and neither
      `data/moe-spec-bsweep-2026-08-25/` nor `artifacts-df25/champion_anchor_*/` has a write-side hook:
      draft a source row for `scripts/vidya/adapters/README.md` plus a task for
      `handoffs/active/vidya-belief-substrate-program.md` (preparation only; the owning session applies)
      (found 2026-09-14, noninf sweep).
- [ ] **Carry the reconstructed-substitute caveat onto every downstream quotation of the +10.7%**, including
      this handoff's own table: `plan.json` records that the "live verification batches" were reconstructed
      substitutes because the 2026-07-03 prompts were never persisted — documented honestly in the artifact
      and absent everywhere else (`data/moe-spec-bsweep-2026-08-25/plan.json`) (found 2026-09-14, noninf
      sweep).
- [x] **Operator decision RULED 2026-09-17 — Option A (confirm first). The reconciliation is done and the GPU row is
      void.** ✅ 2026-09-17 Reconciled 2026-09-14 (INF-40, zero-inference, structural): the **−2.92%** row was
      measured on **Qwen3.8-27B-Q8_0, a DENSE model** — `general.architecture qwen35`, **0 of 866**
      tensors match `*exps*`/`ffn_gate_inp`, and the GGUF carries **no `*.expert_count` key**
      (`model_registry.yaml:1596,1707` also say "dense"). `--moe-spec-budget` masks inside
      `build_moe_ffn` (`src/llama-graph.cpp:1985`, champion `c7c37a0d9`), which a dense graph never
      builds, so **both** GPU arms ran identical code. `tg128` was already flagged uninformative by
      construction (batch-1 misses `min_batch 4`); `pp512` fails the stronger model-class
      precondition. It is also not significant on its own samples: medians 768.83 → 746.38 (−2.92%)
      but means 758.63 ± 27.80 → 745.37 ± 25.07 (**−1.75%, Welch t = −0.87**, n=6, ranges overlap).
      **There is no countervailing surface.** The one live objection to the CPU **+10.7%** is its own
      thinness: n=3/cell, Δ ≈ 2.9σ, below `MEASUREMENT_POLICY.md`'s ≥5 reps for a ≥5% claim, 5-rep
      confirm declined; both numbers are OBSERVATIONS (no protocol-id). Decision package below.

      | surface | posture | result | what it is evidence of |
      |---|---|---|---|
      | architect (122B Q4_K_M, n_expert=256), live MTP verification batches, B=128 | CPU verifier, n=3, era E9 | **+10.7%** (10.84 → 12.00 t/s, α −2.4pp) | MoE-Spec on a 256-expert MoE CPU verifier at B=n_expert/2 — thin (n=3), OBSERVATION |
      | Qwen3.8-27B-Q8_0 pp512, `budget=32` | GPU `llama-bench`, n=6, 2026-08-28 CH-4 | **−2.92%** median / −1.75% mean, NS | **nothing about MoE-Spec** — dense model, flag's subgraph absent; usable only as a ±3.7% noise reading for that GPU surface |

      **OPERATOR DECISION — INF-40: enable `moe_spec_budget: 128` on `architect_critic`?**

      **Context.** The prepared registry patch (`data/moe-spec-bsweep-2026-08-25/registry_patch_proposal.yaml`)
      adds `moe_spec_budget: 128` to `architect_critic` (122B Q4_K_M, CPU :8074) on a single E9 run:
      +10.7% end-to-end t/s (10.84 → 12.00, n=3, Δ ≈ 2.9σ), acceptance 0.487 → 0.463 (−2.4pp). The
      GPU counter-row is void (dense model, see above), so the fork is purely evidence-weight vs
      compute: registry writes are gated by the standing E8-reseed / OP-19 ruling, and a ≥5% claim
      needs ≥5 reps (`MEASUREMENT_POLICY.md`) — the offered 5-rep confirm was declined on 2026-08-27.

      **Option A — Confirm first, then apply (5-rep A/B/A/B, ~1 inference window).** Re-run B ∈ {0,128}
      on the same model/binary/posture, ≥5 reps alternated, declared noise floor in t/s *and* % of
      mean, gate-skip mechanism-fire control retained, protocol-id registered so the result is a claim.
      Cost: one region-locked window on the 122B (a slow model: ~1.5–2 h). Risk: lowest. Reversibility:
      n/a. Buys: a decision-grade number plus the α re-measure the quality question actually needs.
      **Option B — Apply now on the n=3 observation, with a declared revert trigger.** Patch the
      registry + launcher env-pass, and revert if the role's live speed telemetry does not show the
      gain or if acceptance drops below a named floor. Cost: ~0 compute. Risk: deploying a 2.9σ effect
      whose α cost (−2.4pp) is measured and whose end-to-end quality cost is not; the verifier keeps
      target-greedy, so the failure mode is speed/acceptance, not corruption. Reversibility: high
      (delete one key → default 0). Violates the ≥5-rep claim bar for a ≥5% deploy decision.
      **Option C — Leave at 0 and close the integration line.** Keep MoE-Spec as a capability enabled
      nowhere; retire the proposal, keep the mechanism documented. Cost: 0. Risk: discards the only
      positive MoE-Spec result ever measured on a live production serving path. Reversibility: the
      patch text stays in the artifact dir.

      **Recommendation: Option A.** The blocker was never the GPU row; it is that a +10.7% deploy
      decision rests on n=3 while the project's own claim grammar demands ≥5. One window converts the
      project's single live-path MoE-Spec win from an observation into a claim — and if it holds,
      Option B's risk disappears rather than being accepted. Tie-breaker fact, if compute is the
      binding constraint: the 5-rep confirm is the *same* run that re-measures α, so Option B would
      have to buy that window anyway to monitor its own revert trigger.

      **Default if no ruling: status quo — `moe_spec_budget` stays 0 everywhere**, the patch stays
      prepared-not-applied, and INF-40 stays open on this box. No autonomous registry write.

      **OPERATOR RULING 2026-09-17: Option A.** Run the 5-rep alternating A/B/A/B confirm of
      `moe_spec_budget` ∈ {0,128} on `architect_critic` (122B Q4_K_M, CPU), **queued until the AutoKernel
      quiet window ends; the operator must say go before it runs.** `moe_spec_budget` stays 0 until the
      confirm reports. Registry writes stay gated as above.

      **Fact the package missed (verified 2026-09-17):** frozen production v9 (`0db32c06e`) contains **no
      MoE-Spec code** (`git grep moe_spec 0db32c06e` is empty). The +10.7% ran on
      `/mnt/raid0/llm/tmp/inf40-build` = v9 + MoE-Spec `c7c37a0d9` (`plan.json` `binary_commit`), and the
      champion `ef81196d5` carries it (`src/llama-graph.cpp:1985`). A registry key therefore takes effect
      only on a serving binary that contains MoE-Spec (the champion, or a future production version) —
      on the v9 binary `--moe-spec-budget` does not exist. The confirm must run on the binary the role
      would actually serve from.

      **Operator question (2026-09-17): could the confirm run on Qwen3.8-Flash-Next (qwen4exp) instead,
      since it should be faster? Answer: not as a substitute.** Checked against
      [`cpu-decode-roofline-program.md`](cpu-decode-roofline-program.md) and this handoff; two of the
      three reasons first drafted were wrong and are corrected here.
      1. **The deploy decision is per model.** The ruling is about a key on `architect_critic`; a
         qwen4exp result does not license it. The budget scale does not transfer either: B=128 is
         n_expert/2 on the 122B (256 experts) but n_expert/4 on qwen4exp (512 experts × 10 used), and
         the frontdoor/worker rows above already show the sign flipping across models.
      2. ~~qwen4exp has no speculative verification path, so the mask never fires~~ — **corrected: it
         does have one, on the experimental champion.** Axis E ran E1–E3 early (E2 ported the qwen4exp
         MTP path 2026-09-02; E3 measured α), and champion `ef81196d5` serves MTP at 82.1% acceptance
         with `--spec-draft-n-max` 3 (fleet) / 4 (coding). A verification batch is therefore 4–5 tokens,
         which meets `moe_spec_min_batch` = 4 (`common/common.h:475`, `src/llama-context.cpp:272` in
         `ef81196d5`), so the `build_moe_ffn` mask **would** fire there. Only plain batch-1 decode
         (1 token < 4) never triggers it. Frozen production v9 has neither the qwen4exp arch nor MoE-Spec.
      3. ~~qwen4exp is ~95 ms/token (≈10.5 t/s), no faster than the 122B~~ — **corrected: the ~95 ms
         token is the 2026-09-02 audit-day baseline, which the roofline header marks as not the current
         state.** The consolidated champion measures **27.893 t/s plain / 43.281 t/s MTP** (18-launch
         close-out, hot harness, 24-prompt mix), i.e. ~2.6–4× the 122B's 10.84 t/s. It **would** be a
         faster run, but speed does not answer reason 1. It is also a CPU inference run on the champion,
         so it needs the same quiet window.
      **OPERATOR PLAN 2026-09-17 (retargets the confirm; nothing acted on here).** The plan is to promote
      the AutoKernel champion (`ef81196d5`) to production and to promote Qwen3.8-Flash-Next (qwen4exp) to
      `architect_critic`. That resolves both blockers above: the role's future model is qwen4exp (reason 1),
      and its future serving binary contains MoE-Spec (the v9 fact). So the confirm runs **directly on
      qwen4exp + the champion binary** when a CPU window opens, not on the 122B, which is leaving the role.
      The E9 122B +10.7% stays on record as the motivating observation only. No stack, registry or
      launcher change is made by this ruling; the registry key waits for the promotion AND the confirm.
- [ ] **INF-40 confirm run (operator Option A, retargeted 2026-09-17) — GATED: waits for the end of the
      AutoKernel quiet window AND an explicit operator go.** On qwen4exp (Qwen3.8-Flash-Next) served by
      champion `ef81196d5`, with MTP on at `--spec-draft-n-max` ≥ 3 so verification batches meet
      `moe_spec_min_batch` = 4. Sweep `moe_spec_budget` for 512 experts × 10 used (e.g. {0, 64, 128, 256};
      pre-register the grid and the pass rule before running). 5-rep alternating A/B/A/B per arm against 0,
      same-window, with the champion's production recipe. Declare the noise floor in t/s and % of mean, keep the gate-skip
      mechanism-fire control, re-measure α, and register a protocol-id so the result is a claim. Then
      apply or retire `registry_patch_proposal.yaml` on the result.
- **(Folded 2026-09-17 into the retargeted confirm above; kept for the record.)** Former optional
      follow-up — qwen4exp MoE-Spec measurement. Not a substitute for the confirm above. The
      qwen4exp MTP path exists only on the experimental champion, so a production-meaningful measurement
      needs that drafter path to reach a serving binary (INF-70 Axis E). It needs its own B sweep
      (512 experts), at `--spec-draft-n-max` ≥ 3 so the verification batch meets `min_batch` 4.

## Track: v9-kernel-per-request-speculative-params
<!-- gate: none -->

> Folded from `handoffs/active/v9-kernel-per-request-speculative-params.md` @ `0001c77da2e5` on 2026-11-02 (BRF-T1-F10, route 1a, operator D1/D5; retired row INF-58 → EVL-21). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### v9 kernel candidate — expose per-request speculative parameters

**Filed** 2026-07-31 · **Owner** operator (kernel promotion) · **Status** PROMOTED AND FROZEN as production v9 on 2026-08-11; resident fast-path follow-up remains open
**Production** `production-consolidated-v9` @ `0db32c06e3e550065b78311a6031ef3dd2c4f27c` (binary 10125), exact v8 base/rollback `67a433bf45a8a091d83b4ea0b32ff0735fd51800`

---

#### 0. What this is, in one paragraph

Frozen v8 accepts no per-request speculative parameters. Experimental v9 now exposes exactly one:
`speculative.n_max`. It is a request-local cap bounded by the launch-time maximum; `0` disables
speculation for that request, the effective value is returned in `generation_settings`, and slot
reuse does not leak a prior request's cap. The other speculative fields remain unavailable because
their request-local behavior is not wired or proven. This corrects the original proposal, which
treated deleting the whole `#if 0` block as sufficient.

#### 1. The finding, verified in source

`/mnt/raid0/llm/llama.cpp/tools/server/server-schema.cpp`, lines 204-233:

```cpp
    // TODO: to keep things simple, we disable speculative parameter adjustments for now
#if 0
    // TODO: for now, be able to adjust only the draft-model based speculative parameters
    add((new field_num("speculative.n_max", params.speculative.draft.n_max)) ...
    add((new field_num("speculative.n_min", params.speculative.draft.n_min)) ...
    add((new field_num("speculative.p_min", params.speculative.draft.p_min)) ...
    add((new field_str("speculative.type")) ...
    add((new field_num("speculative.ngram_size_n", ...)) ...
    add((new field_num("speculative.ngram_size_m", ...)) ...
    add((new field_num("speculative.ngram_min_hits", ...)) ...
#endif
```

**Everything speculative is inside the `#if 0`.** Including `speculative.type`,
which would have allowed per-request selection between `ngram-mod` and
`draft-mtp` — exactly the selective control we wanted.

##### The trap that produced a confident wrong answer

This was first reported (by me) as "these ARE per-request fields", because:
1. `grep` finds the `add((new field_num("speculative.n_max" ...` registrations and
   they look live; the `#if 0` is 4 lines above and does not appear in the match.
2. `tools/server/README.md` shows `speculative.n_max` in its JSON examples — but
   those are **`generation_settings` echoes of launch defaults**, not accepted
   request fields.

Source registration plus a README example reads as corroboration from two
independent places, when neither is evidence. **Lesson: when a grep hit decides a
capability question, read the enclosing preprocessor context before answering.**

#### 2. Why it matters now

Production launches `--spec-type ngram-mod,draft-mtp` (composed). That recipe
costs a measured **−1.6 % mean** on ordinary prose/code and is carried
deliberately for the repetitive-context upside. With no runtime control:

- That ~1.6 % is paid on **every drafted request**, forever, with no way to skip it
  on traffic known to be non-repetitive.
- Autopilot cannot raise the draft budget on repetitive workloads where the
  composed drafter would actually pay off.
- `n_max: 0` — the natural "just turn speculation off for this call" escape hatch —
  does not exist either.

#### 3. Tasks

- [x] **V9-1. Expose only functional `speculative.n_max`** on an experimental branch; preserve the
  frozen production tree ✅ 2026-08-10
- [x] **V9-2. Prove request-local plumbing:** `0` disables, positive values cap the launch maximum,
  over-large values clamp, omission restores the launch default, and reused slots remain isolated
  ✅ 2026-08-10
- [x] **V9-3. Report the effective value** in every completion's `generation_settings`, so a harness
  can attribute results to the actual draft cap ✅ 2026-08-10
- [x] **V9-4. Keep unwired controls unavailable.** `n_min`, `p_min`, type selection, and ngram fields
  were deliberately not exposed; source presence is not runtime wiring ✅ 2026-08-10
- [x] **V9-5. Regression-check ordinary speculative requests.** Focused server tests pass on the
  final candidate (`2 passed in 56.14s`), and the real DSpark smoke reports effective caps 0 and 3
  independently on one reused slot ✅ 2026-08-10
- [x] **V9-6. Complete the kernel-promotion qualification procedure** against frozen v8: rebuild CPU
  and HIP from the repaired final tip, validate linkage/functionality, and run every incumbent-role,
  correctness, quality, topology, rollback, and measurement gate ✅ 2026-08-11
- [x] **V9-7. Execute the authorized `production-consolidated-v9` cutover** and production-named
  GPU/DFlash/DSpark certification ✅ 2026-08-11. GPU roles and `-np 1` Q8 DSpark exact parity pass.
  Qwen3.6-27B Q8 DFlash is capability-certified but lineup-ineligible under P-DFLASH-LINEUP-1:
  acceptance 35.954% < 60%, despite a 2.458× aggregate decode gain; the lane remains disabled.
- [ ] **V9-8. Implement and prospectively ratify the resident promotion fast path** described in
  [`kernel-promotion-resident-fast-path.md`](https://github.com/pestopoppa/epyc-inference-research/blob/main/docs/design/kernel-promotion-resident-fast-path.md): sealed candidate hot stack, exact-parity pack, resident per-request speculation schedule, and automatic fallback to the existing fresh-server instrument.

#### 3.1 Evidence

- Candidate commit: `84c84fafe36c7e5deab7ff5301b1a7a1cde9b920` (feature), included in final
  candidate `2ac4b32a01a6d97af1c85889443472fbd4a1e12e`.
- Final bounded Q8 smoke: vanilla and DSpark produced identical 16-token arrays; DSpark drafted 18
  and accepted 7 tokens at effective `n_max=3`.
- Durable receipt: [`artifacts/audit/v9-dspark-autokernel-base-20260810.json`](../../artifacts/audit/v9-dspark-autokernel-base-20260810.json).
- Qualified final candidate and production tip: `0db32c06e3e550065b78311a6031ef3dd2c4f27c`
  (version 10125; CPU SHA-256 `8ebb1355…`, HIP `21cfb750…`).
- Final freeze: [`ratify_v9_final_freeze_20260811.json`](../../artifacts/operator/ratify_v9_final_freeze_20260811.json).
- Production certification evidence is pinned in
  [`v9-kernel-promotion-attestation.json`](v9-kernel-promotion-attestation.json), including the
  region-locked GPU role pass, region-locked DSpark parity pass, and DFlash lane-specific no-go.

#### 3.2 Promotion boundary (completed)

The complete qualification repaired the starting candidate to `0db32c06e…`, rebuilt and re-ran the
full gate set, cut over the versioned production tree, certified the production-named GPU and
speculation paths, and froze v9. v8 remains the tested rollback anchor. AutoKernel initialization and
its hypothesis queue were explicitly outside this promotion goal.

#### 4. NOT in scope here — draft-max tuning is a TODAY task

`--spec-draft-n-max` is a **launch flag on the current kernel**. It needs no kernel
change and must not wait for v9. It is being swept now; see
`handoffs/active/draft-max-sweep-20260731.md`. Recorded here only so nobody files
it against this handoff by association.

#### 5. Do not do this

- **Do not patch the frozen production tree** (`/mnt/raid0/llm/llama.cpp`,
  `production-consolidated-v8` @ `67a433bf4`). All kernel work happens on
  `llama.cpp-experimental`, per the four-step workflow in `CLAUDE.md`.
- **Do not treat this as a prerequisite for the speech or vision work.** Qwen3-ASR
  and qwentts.cpp need no kernel change at all; this is orthogonal.

#### 6. Cross-references

- Master index row **N28**; tasks SW-1..SW-4.
- `speculative-decoding-mtp-refresh.md` — carries the ngram retraction banner and
  the T1 draft_max evidence.
- Design decision to carry composed ngram, with its measured −1.6 % cost:
  artifact §01 "Design decision — the recipe carries `ngram-mod`".
