# Backlog ROI Audit — 2026-07-14

**Status**: EXECUTED 2026-07-14 (updates applied same session). Residual items below are operator decisions or follow-through checkboxes.
**Owner**: operator-requested full-portfolio audit session (Fable 5, ultracode).
**Scope**: all 137 active/blocked handoffs + 7 indices, cross-referenced against all 1,632 research-intake entries (531 with actionable verdicts: `worth_investigating`/`new_opportunity`/`adopt_component`/`adopt_patterns`) and the 10 open 2026-07-08 literature recommendations.

## Method

97-agent three-phase workflow: (1) full-read extraction of every handoff/index + the whole intake index; (2) six domain gap analysts (cpu, gpu, specdec-models, routing/autopilot/evidence, agents/pipelines, research-eval) with mandatory grep-verification before claiming anything "missed"; (3) adversarial verification of each of the 25 missed-task candidates by skeptic agents whose default stance was "already tracked/done/rejected/gated". 20 of 25 candidates were killed on evidence; 5 survived. Kill verdicts are recorded below so the same candidates are not re-proposed by future intake sweeps.

## A. Verified missed ROI tasks (5) — now filed with owners

All five were confirmed absent from every handoff, index, progress note, and the master-index GATED/stays-dead lists before filing.

- [ ] **RE-1 · Math-Verify scoring flip + re-baseline** (S, med-ROI; intake-377/379) — the `math_verify` scorer is landed in orchestrator but **zero** pool questions use it (1,319 math `exact_match`, 500 `substring`, 0 `math_verify`). Flip math-suite scoring to `math_verify` and re-baseline affected suites. Label-quality lift for every downstream consumer (per-question ledger, McNemar/MDE power, A9 labels, promotion verdicts). Filed: [eval-tower-verification.md](eval-tower-verification.md) EV-11.
- [ ] **RE-2 · Execution-free patch verifier as gating signal** (M, med-ROI; intake-757) — Dockerless execution-free patch verdicts as a coder_escalation pre-gate / eval-tower verifier signal at zero inference cost. Was an unrouted queue line in findings-05 with no owner arrow. Filed: [eval-tower-verification.md](eval-tower-verification.md) EV-12.
- [ ] **RE-3 · Review-finding-F1 suite (EV-NEW formalized)** (M, med-ROI; intake-658) — local code-review benchmark from the Factory methodology deep-dive (Augment v1 145-bug golden set, ~80-LOC scorer, ≤2pp judge-swap as first EV-6 cross-family instance). Was prose-only at eval-tower L403; no checkbox, no index row. Feeds coder-pool composition + Strand Phase C. Filed: [eval-tower-verification.md](eval-tower-verification.md) EV-13.
- [ ] **RE-4 · LongCoT-Mini calibration run** (M, med-ROI; intake-386) — ~500-easy deterministic long-horizon reasoning suite on local models; adds a non-saturated suite exactly where EV-9 found production suites saturated, and tests the reasoning-compression premise (unbounded reasoning harmful) on our stack. One clean-window package. Filed: [bulk-inference-campaign.md](bulk-inference-campaign.md) standalone-window queue.
- [ ] **RE-5 · Simula double-critic fold into F1-DGM scoping** (S, med-ROI; intake-410 + rec-002) — Simula's double-critic rejection sampling + calibrated complexity scoring are the published quality-control mechanisms for exactly the F1-DGM-1/2 synthetic-eval-generation step that is open right now; zero-cost design input if folded during scoping. Filed: [frontier-f1-real-task-corpus.md](frontier-f1-real-task-corpus.md) F1-DGM.

## B. Kill list — 20 candidates rejected by adversarial verification

Do not re-propose these as "missed" from future intake sweeps without new evidence.

| Candidate | Verdict | Where it lives / why dead |
|---|---|---|
| MTP self-draft acceptance check under `-np 8` eval-batch lane | TRACKED | batched-decode-measurement.md E2 remainder |
| Concurrent 4×quarter+MTP aggregate bench | DONE | iqk-port.md Phase-3B complete; residual in v6-iqk-promotion |
| Clean `-np 8` paged-attn A/B redo + f1-paged-attn fold | TRACKED | llamacpp-v6-consolidation.md Stage-2 |
| CPU_REPACK auto-mbind upstream PR | REJECTED | cpu-shape-specialized-gemv-decode.md — deliberate no-PR decision |
| intake-750 bandwidth-tier snapshot harvest | GATED | intake-750 recommended_action gate |
| intake-796 fp64-reference kernel-correctness oracle | TRACKED | agentic-rocm-kernel-authoring.md AK-KB-1/2 |
| Consolidated v7 GPU-wins promotion bundle doc | GATED | master-index §F v7-candidate row (operator-gated promotion) |
| intake-119 llmfit residency pre-screen | REJECTED | gpu-acceleration-path intake-310 probes supersede |
| Hy3 architect-candidacy plain quality bench | GATED | speculative-decoding-mtp-refresh.md |
| v6 quality-gate baseline scheduling | GATED | gemma-challenge-kernel-techniques-v7.md K5 (operator) — elevated in this audit, see D |
| Ternary Bonsai-8B into tq3 watch | REJECTED | tq3-quantization-evaluation.md sub-2-bit watch owns the call |
| TabFM/TabICL as A9 verifier family | REJECTED | A9 `stop_current_verifier_family` decision stands |
| ≥100 compressed calls through run_bash_compressed | TRACKED | tool-output-compression.md P4e |
| Hermes trace-corpora snapshot/registration | GATED | frontier-f3-data-flywheel gates |
| Injection scanner extension to web_research | DONE | completed/frontier-f5-intake-injection-hardening |
| Rampart NER for PII-3 hybrid trigger | GATED | completed/privacy-hygiene-precommit-hooks reopen clause |
| Math-Verify integration (generic) | TRACKED | routing-index Concern 13 — the *unflipped scoring* piece is RE-1 above |
| Qwen-Scope SAE eval-redundancy probe | TRACKED | eval-tower-verification.md EV-8 candidate |
| AI-Scientist Automated-Reviewer pre-filter | TRACKED | research-evaluation-index rec-003 → eval-tower |
| AgentRxiv shared-preprint coordination | DONE | autopilot-continuous-optimization.md intake fold |

## C. Reprioritizations applied (headline moves)

**Operator decision bundles surfaced to the top of the master index (§A00):**
1. **OP-1 — P0.1–P0.3 sign-off bundle** (orchestration-robustness + loops-and-dashboards Phase-2 MEASUREMENT amendment): promotion is unreachable **by construction** until the rate-axis era-fence amendment is signed; AutoPilot burns ~16-min trials into a dead gate (348 trials promotion-stale). Escalated above further W8 evidence accrual.
2. **OP-2 — one consolidated quiet-window measurement bundle**: v6-iqk live throughput+garbage verification & clean post-reboot canonical bench (the kernel has been LIVE since 2026-06-26 with verification still pending — an inverted gate) · K5 v6 MMLU-Pro/GPQA-Diamond baselines (sole remaining gate on the banked v7 GPU-win bundle: HIP graphs +25% spec-dec, MMVQ→MMQ +17–32%, bf16 state +16–21%) · frontdoor Q8_0 barrier-fusion A/B (#1 CPU decode lever, est +10–15%) · N5 drafter-α retest · Strand RustEvo2 Phase B (~half-day; unblocks the entire blocked swarm-dataset-distillation program).
3. **OP-3 — zero-inference decision batch**: E3 go/no-go + E4 CPU17/CPU18 doc re-promotions (all gating data exists since 2026-07-07) · `dispatch_swarm_fanout` ownership decision (**OVERDUE**, watch lapsed 2026-07-12) · agent-file-compression Phase 5 rollout (LOW→MED; decision-only, 30–50% token reduction compounds everywhere) · context-folding α-promotion (gate MET 2026-06-19, unactioned 4 weeks) · MoE-spec reopen assessment vs the 2026-07-03 live-α report · MathSmith S2 free artifact scan (2.5 months stale purely for want of a free check) · Wilson/McNemar stdlib port consolidation (one module, owner loops-and-dashboards, consumer eval-benchmark-cost-reduction — de-duplicates two open items).

**Elevated**: gfx90a training-viability smoke → standalone MI210 probe (single shared unblock for F3 fine-tunes, drafter training intake-624/737-738, EV-9 judge, MFMA reopen) · tool-use-eval-contract "journal nonzero tool calls" (upstream of tool-output-compression P4e telemetry starvation; REPL extraction repaired 2026-07-11, evidence journaling still open) · rao-redel fund-or-close (8 weeks stale; the unblocking A/B is 10–60 min).

**Downgraded / parked**: DFlash/DDTree → fund-or-close decision row (every production target now ships a native MTP head; tree-draft Phase-1b shelved 2026-07-06 for the same reason) · qwen36-27b-cpu-feasibility → monitor with explicit role-candidacy reopen trigger (premise weakened; ~7.5–9 t/s projection below role thresholds) · K-MEM-1 HIGH→MED (baseline scored; only the 120-row follow-up slice remains) · MoE-Spec index row P1→gated (owning handoff: proven mechanism, no consumer).

## D. Index fixes applied (7 files)

- **master-handoff-index.md**: new §A00 operator bundle; N15 row deleted (resolved, handoff archived); ODL quiet-window row corrected (hybrid sidecar IS live on :5002, 27/27 parses — remaining gap is the benchmark-backed routing-policy decision); archived-file links repointed; LOW/MED row hygiene (N12 tail removed, agent-file-compression → MED).
- **cpu-inference-optimization-index.md**: P0 row added for the clean post-reboot canonical bench (its own highest gate lived only in master N13); GEMV row re-pointed at the barrier-fusion A/B (SIMD follow-ons explicitly deprioritized); MoE-Spec row re-tagged gated with the real reopen chain; batched-decode row gains E3 go/no-go + E4 doc-decisions; DSA row gains the refresh-snapshot precondition (P0→MED aligned with master); N12/md-double-load closed rows relocated; header bumped.
- **inference-acceleration-index.md**: v6-consolidation row rewritten to cutover-complete reality (links v6-iqk-promotion.md + iqk-port.md); gemma-challenge row updated (K3 done, onegraph DEFERRED, next = K4/K5 + K10/K11); checklist rows added for T4/T5/P6b/K4/K5/v6-iqk-verification (checkbox-discipline visibility); header bumped.
- **routing-and-optimization-index.md**: stale copied AutoPilot runtime prose replaced by delegation to the owning handoff (code_stale=false, trial 1346 as of 2026-07-14); dispatch_swarm_fanout decision marked OVERDUE and queued; env-synthesis row refreshed to AW-6/7 reality; AB-MCTS gate rationale corrected (W4 live, W6 evidence-complete); loops-and-dashboards P0.1–P0.3 named as the binding constraint on the P0 evidence-plane row; completed rows pruned; A9 row next-action rewritten to the 2026-07-07 rebuild/scoring step.
- **pipeline-integration-index.md**: completed P0 vision row retired + checklist flipped; malformed completed PDF-probe row removed; DS-E1 gated row re-triaged (gate fired, decision recorded); K11 FTS5 + AutoWiki-writer + retrieval-weight-promotion dispatch entries added to the KB-RAG row; header bumped.
- **hermes-agent-index.md**: tool-use-eval-contract row rewritten to post-2026-07-11 state (repaired REPL extraction; open = journal nonzero tool calls + usefulness evidence) and promoted to an explicit MED queue row; tool-output-compression remaining-scope reworded (P4e ≥100-call telemetry + P3d A/B); x_max_escalation + live-Hermes-smoke items surfaced; header bumped.
- **research-evaluation-index.md**: F1 row updated (W3 ledger run completed 2026-07-07; next = AP-16 token-bloat investigation + ledger→promotion wiring); gpu-cot-scaffold rows retargeted at the successor DESIGN handoff; rao-redel gate text corrected; K-MEM-1 dedup (HIGH row deleted); eval-tower row refreshed to EV-4/5/8 gated + EV-7 landed + EV-10a pending; Wilson/McNemar surfaced as independent non-inference item; EV-11/12/13 + LongCoT-Mini rows added (§A above); header bumped.

## E. Archived this session (13 handoffs → completed/, 1 → archived/)

All were verified complete/superseded by full-document reads + reference-map checks; inbound links repointed. Findings were already extracted into owning docs/indices before the move (verified per-file).

`md-double-load-mtp-fix-brief` · `halo-trace-loop-spike` (not_actionable 2026-07-14) · `post-reboot-autopilot-restart-runbook` (executed 2026-07-02) · `fable5-window2-mi210-focus-injection` (consumed by findings-05b) · `launcher-numa-mode-gating` · `contention-matrix-v6-quarter-refresh` (N15 resolved) · `mi210-batch1-latency-wall-greenfield` (all 3 levers resolved) · `fable5-window2-findings-04-negative-space-and-self-critique` · `gpu-cot-scaffold-sidecar` (study complete 2026-07-06; live successor = scaffold-autopilot-cost-lever-deployment.md) · `numa-private-weights-quarter-roles` (N12 closed negative; reopen clause preserved in-file) · `iqk-port` (sole open item duplicated in v6-iqk-promotion.md) · `autopilot-restart-2026-07-09` (superseded by 2026-07-14 restart; unresolved Jul-8 silent-death root-cause folded into autopilot-continuous-optimization.md as a task) · `fable5-architecture-review-3` → **archived/** (byte-identical duplicate of review-2 except its own de-dup note).

## F. Checkbox-discipline repairs

~40 done-in-prose-but-unchecked items flipped (`- [x] … ✅ date`) across 19 handoffs: learned-routing-controller (P6.1.1-3), evidence-plane-event-sourcing (W1, W4), cpu-shape-specialized-gemv (4), opendataloader (4), colbert-reranker (1), findings-05c lever matrix (L3/L4/L5/L20), internal-interaction-lifecycle (P3-1), tool-output-compression (P3d), within-role-placement (WP-5/J2/J3), llamacpp-v6-consolidation (F1/F2/F5/F6 + Hadamard), frontier-f1 (W2), multimodal-pipeline (DD2 ×2), model-stack-change-standardization (3), frontier-f2 (W2), frontier-f3 (W1), delegation-context-preassembly (DCP-1/2/3), batched-edit-parallel-apply (BEP-1/BEP-4), agent-file-prose-compression (operating points), glm51-reap (WAIT-DSA disposition).

## Reporting

- On completing any §A task: flip its checkbox here AND in the owning handoff + domain index; delete the master-index row if one was added.
- The kill list (§B) is authoritative negative evidence for future intake sweeps — cite it before re-proposing.
- Next audit of this kind: re-run after the OP-2 measurement window lands, or when the intake index grows by ≥100 actionable entries.
