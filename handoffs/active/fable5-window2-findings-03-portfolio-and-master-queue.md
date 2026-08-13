# Window-2 findings 03 — Portfolio audit, resurrection sweep, and proposed master-queue rewrite (§3 + §8.4)

**Method**: index-driven per the brief — master index + 6 domain indices + `bulk-inference-campaign.md` read in full by dedicated agents; owning handoffs sampled only to confirm ambiguous lines (~20 sampled of ~349). **115 outstanding items triaged** (routing 26 + acceleration 23 + CPU 8 + research 26 + hermes 6 + pipeline 11 + campaign/queues 15). This is a **proposed** rewrite artifact — no live index was edited (CLAUDE.md rule).

Triage totals: **keep 72 · revive 15 · reorder 15 · merge 8 · kill 5**. Full per-item tables with deciding facts live in the evidence bundle (`/tmp/claude-1000/.../scratchpad/dives/portfolio-*.md` this session; deciding facts reproduced below only where they change the queue).

> **APPLIED 2026-07-03 (operator-directed).** The write-authority constraint that held this as a *proposal* was lifted by explicit operator request ("reprioritize all backlog work keeping your strategic recommendations front of mind"). The §4 rewrite + the DGX→MI210 un-stalings were applied to the live `master-handoff-index.md` (§F rewritten to an ordered GPU queue; §A0 strategic-priorities block added; §B2-F3 un-gated) and to 10 owning handoffs/indices. A parallel intake/deep-dive sweep (findings-05) added 22 missed-tasks + the kernel roofline analysis. See [completed findings-05](../completed/fable5-window2-findings-05-intake-sweep-and-roofline.md) §7 for the full list of files touched. Edits are uncommitted pending operator review.

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
- [ ] **G1 · Ratify P-GPU-1** (operator; measurement trust boundary — human-amendment-only). [findings-02 §5]
- [ ] **G2 · Canonical-tree HIP build + `qwen35moe`/`qwen3next` op-coverage smoke** (no window needed; LD_LIBRARY_PATH hazard documented). [findings-02 M1-prereq]
- [ ] **G3 · Frontdoor residency bench under P-GPU-1 → Gate R decision** (≥1.8× → R12 plumbing; 1.3–1.8× → HIP-kernel track critical; <1.3× → residency demotes to eval-only hosting). [findings-02 M1]
- [x] **I1 · `seq_refuted` learning exclusion + strategy-store quarantine parity** (code + tests, zero inference). [findings-01 R1] ✅ 2026-07-17 (code was already wired in aa20d029; parity locked by test_seq_refuted_learning_exclusion_parity.py `0492c07a`)
- [ ] **I2 · Ledger-derived core_v2 selection** (read-only rebuild; demote 2026-06-15 calibration lineage to prior; compare item sets). [findings-01 R2]
  - [x] Post-E8 read-only rebuild + comparison ✅ 2026-07-29 — `core_v2_select.py --source ledger --min-attempts 5` wrote the non-promoted artifact `/mnt/raid0/llm/tmp/mainc-core-v2-20260729/{core.jsonl,report.json}`. The active era fence (`1785004723.0`) retained 16 trusted rows / 50 observed items and excluded 1,317 pre-era rows, yielding only 2 eligible / selected items (shortfall 38); neither overlaps the prior 40-item `core_v2_ledger_20260703_min5` selection. `tests/unit/test_core_v2_select.py` passed 6/6. No era amendment or activation was attempted.
  - [ ] Accrue a current-era, trusted ledger that yields at least 40 eligible core items before preparing any new `autopilot_quality` era row or activating a replacement core; the present 2-item artifact is evidence of insufficiency, not a candidate for promotion.
- [ ] **I3 · DAR-1 regret replay over live ledger** (offline; the routing-unfreeze gate IS this replay). [R16]
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
