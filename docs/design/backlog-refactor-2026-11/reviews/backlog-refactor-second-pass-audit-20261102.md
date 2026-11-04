# Backlog refactor — second-pass audit and inference fusion recommendations

**Yes—there are substantial opportunities to combine inference work.** The revised v3 improves the migration mechanics, but it still organizes primarily around files and checkboxes. To minimize inference, it needs a separate **experiment-to-task mapping**: one qualified experiment can supply evidence to several tasks, while each task retains its own acceptance criterion.

I reviewed v3, its manifest, refinements, lint, dry-run report, and the source handoffs at **`3ac825873dfb`**, with parallel audits across the destination domains. No inference, scheduling, or repository changes were performed. The opportunities below are supported by task-level overlaps; the artifacts do **not** support a credible total GPU-hour or percentage-saving estimate yet.

**1. Fix these v3 issues before using its readiness classifications**

These are material defects, beyond the first-pass findings:

| Finding | Consequence | Required correction |
|---|---|---|
| **Nearby text is treated as task-specific evidence.** EvalPerf’s completion criterion is derived from nearby EffiBench preparation; T4’s quant/build field comes from Gemma prose. | Tasks become “executable” with the wrong instrument or model identity. | Require semantic equivalence for each derived field. A source citation proves location, not applicability. |
| **Inference classifications are demonstrably wrong.** Q38 floor calibration, TOC-SP-3’s model comparison, and EvalPerf are classified non-inference; scorer construction and TOC-SP-5’s explicitly zero-inference audit are classified inference. | The proposed publication gate both rejects valid preparation and misroutes real inference. | Keep regex lint advisory; validate explicit execution types against the actual deliverable. |
| **Existing authorizations become new operator requests.** TD-23 quotes an existing local-model ruling; CH-27 quotes an already-authorized bounded C5 window. Both are routed toward fresh approval. | Approved work is blocked again, and worker tasks may disappear into the decision queue. | Distinguish pending choices, historical rulings, standing constraints, and already-issued authorization. |
| **Task prerequisites are replaced with program dependencies.** The refinement generator copies `track_gate` when a prose prerequisite lacks an ID. | An unrelated program gate can replace the actual scientific prerequisite. | Resolve the prerequisite named in the task; retain program relationships separately. |
| **Splitting is numerical rather than semantic.** The manifest allocates anonymous children without disjoint deliverables, including parents that already have named children. | Duplicate work, inflated counts, and parent/child double dispatch become likely. | Define child outputs and acceptance criteria first; make roll-ups non-dispatchable. |
| **The lint does not implement v3’s “tags allowed” contract.** It rejects failed fields even with NEEDS tags; `NEEDS-OPERATOR` itself triggers a failure. | The proposed per-fold gate cannot behave as specified. | Implement separate reporting, migration-validation, and publication modes. |
| **Companions disagree.** Proposal: 8,130 source tasks. Manifest: 8,089. The plan companion still names `283e2be1de`, while v3/manifest name `3ac825873dfb`. | “Zero lost tasks” lacks a coherent baseline. | Regenerate all companions from one pinned inventory and reconcile every difference. |
| **The thesis routing is stale.** The companion retains PARKED, but the pinned handoff explicitly records ACTIVE/unparked on October 29. | An obsolete park can be propagated during consolidation. | Reconcile the old rationale with the latest recorded authorization before deriving gates. |

The problematic field derivation is visible in [task_audit.py](/mnt/raid0/llm/tmp/ws58-csh/task_audit.py:49); the lint implementation is in [task_lint.py](/mnt/raid0/llm/tmp/ws58-csh/task_lint.py). The thesis contradiction is in [its handoff](/workspace/handoffs/active/thesis-experiment-orchestrator-vs-strongest-model.md:3).

Also, **a prior measured runtime cannot be mandatory for every first experiment**. New workloads need a bounded pilot and a conservative, explicitly provisional estimate; otherwise the estimate rule creates a circular prerequisite.

**2. Highest-confidence inference fusions**

The following are the strongest candidates for one experiment with multiple consumers. Task references were checked at the pinned commit; linked working files may subsequently move.

| Experiment package | Tasks that can consume it | Safe fusion and remaining boundary |
|---|---|---|
| **Trellis quantization comparison** | TQ3 STEP 2/3; IQK T2/T3 | Run the same IQ4_KT–Q4_K_M and IQ2_KT–IQ2_XXS comparisons once, retaining paired speed and task-quality outputs. Both handoffs consume the result and the conditional port decision. Preserve exact artifacts, reference instrument, and the stated ≥95% speed rule. [TQ3 source](/workspace/handoffs/active/tq3-quantization-evaluation.md:232) |
| **Q38FN floor package** | CH-27; AK-Q38FN-64K-FLOOR; matching AKX-AUTO-11 registry checks | One authorized **C5** calibration window can collect serving, 64K decode, and 64K prefill floors. Share each matching floor across consumers. These remain different measurement cells; neither serving nor bench floors substitute for the other. The authorization does not extend to generic search or a newer champion. [CH-27](/workspace/handoffs/active/autokernel-champion-aggregate.md:202) |
| **Speculative cross-slot parity** | DF2-12.1; CH-37 | One frozen parity campaign supplies both the exposure result and the defect-trigger evidence: solo/concurrent, slot-reuse/cold, speculation-off, low-entropy and planted-canary controls. **G2-CONC still requires the final promotion binary and its complete gate set.** [DF2 source](/workspace/handoffs/active/dflash2-block-drafter-experimental-build.md:827) |
| **CPU/GPU prefill crossover** | PF1; HSF prefill placement rule; NPD reopening trigger | One Q38FN CPU/GPU matrix across prompt lengths and GPU microbatch settings establishes the crossover and feeds both downstream decisions. It does not measure KV-transfer cost or authorize placement deployment. [PF1](/workspace/handoffs/active/mi210-big-model-and-acceleration-roadmap.md:235) |
| **Corrected placement matrix** | E5 rerun; T3; P1-2; S04/S05; matching HSF/capacity consumers | Reconcile the remaining cells, then execute one corrected-placement matrix with affinity, memory policy, cache-drop, and pages-by-node evidence. Do not rerun every historical cell or accept old “decision-grade” labels without their placement witnesses. [Existing reconciliation](/workspace/handoffs/active/batched-decode-measurement.md:847) |
| **Parser pipeline comparison** | PIP02 English Phase C; ODL rebaseline/real Paddle comparison; matching report/decision tasks | One approved **755-page English** ODL/Paddle output bank supports TEDS, structure, text, reading-order metrics and the shared comparison. Infer only eligible unexposed pages after custody reconciliation. The 1,651-page multilingual extension is separate. [Parser source](/workspace/handoffs/active/document-parser-table-bench.md:75) |
| **Public STT screen** | CS-8.STT5/8; matching STT3/LEX2 controls; CS-26.LID1 | Share frozen FLEURS audio/reference manifests and identical baseline transcripts; add candidate arms once. LID1 can reuse existing autodetect tags without inference. Cropped audio, VAD/prompt interventions, lexicon boosts, and private confirmation remain distinct inputs or arms. [Speech source](/workspace/handoffs/active/conversation-stack.md:679) |
| **BEAM memory experiment** | M-12b; UTM-B2/B3; BEAM cells referenced by UTM-V6 | One BEAM128K campaign with fixed ingest filtering, retrieval arms, and no-memory control. The umbrella matrix references those results instead of ordering another campaign. [Memory source](/workspace/handoffs/active/unified-trace-memory-service.md:393) |
| **Spill/evidence retention** | TOC-SP-3; REPL-EMB-3.1/3.2 | One frozen failing-log corpus with current-summary, verified-quote, deterministic-shape-header, and pointer-only arms. Reuse raw answers and evidence selections for downstream scoring. Resolve whether the nominal control actually exists before running. [TOC source](/workspace/handoffs/active/tool-output-compression.md:552) |
| **Reviewer anchors and vectors** | RC-8/RM-2 A1; LB-7 anchors; matching RM-3/4/11a; RC-10/SC43 analyses | Generate matched anchor responses once and capture full score vectors prospectively. Reuse them for calibration and confidence analyses. Independent problem-solving reviewers remain separate arms; the old scalar-only ledger cannot supply missing vectors. [Reviewer source](/workspace/handoffs/active/reviewer-calibration-accounting.md:63) |
| **Reviewer shadow prologue** | RCP-W2; RD-12; LB-1; TM-8 | The existing paired 50-question shadow-OFF/ON replay already serves these consumers. Execute and retain it once. RCP-W3’s near-miss calibration uses another corpus and verdict. [Campaign source](/workspace/handoffs/active/bulk-inference-campaign.md:644) |
| **Web retrieval package** | AR-3 Package D; SX-5/6; compatible ColBERT S5/S6 comparisons | Share frozen queries, fetched-page snapshots, search failures, and trajectories. SearxNG already explicitly folds its work into Package D. MindDR’s 20-item sentinel and the 50-query web sentinel are different cohorts; only identical cells transfer. [Search source](/workspace/handoffs/active/searxng-search-backend.md:208) |

These should move from “possible Phase 2 deduplication” into **explicit experiment packages**, with each original task pointing to the exact result slice it consumes.

**3. Extract more information from each run**

These packages offer broader reuse, but require deliberate capture design.

- **DS41 routing trace → RT-6 and RT-7.**
  RT-10 should capture expert selections, token order, phase, workload, and speculative-block labels once. NUMA placement replay, locality/skew, residency, and stationarity are then offline analyses. Preserve their distinct decision rules. The existing trunk-only trace cannot answer drafter timing or MTP questions.

- **Harness recordings → several HIL tasks.**
  One correctly instrumented collection can support HIL-13 scanning, HIL-15 dependency analyses, HIL-16a recording verification, and HIL-18a ranking. Capture model turns, tool events, outcomes, dependencies, CAS blobs, and session/task joins together. HIL-16b’s targeted/no-hint/placebo/wrong-step continuations still require new intervention arms. [HIL source](/workspace/handoffs/active/harness-improvement-loop.md:118)

- **Judge response bank → multiple judge analyses.**
  A frozen candidate-answer bank and qualified judge outputs can support CJ-13 agreement, EV-15 formulas, confidence/calibration, and compatible compact-judge comparisons. Capture required token probabilities at generation time. CJ-16’s cascade needs actual sequential latency; commit-first and biased-rubric variants require separate judge calls. Changing the judge generally requires rerating, **not regenerating candidate answers**.

- **Reasoning budget curve → several decisions.**
  TB-1 supplies TB-2/TB-3 analyses; TB-4 already connects effort–budget interactions to E-2/E-6, and E-3 can consume paired rescue outcomes. However, OlympiadBench and GPQA are different populations. Share controls only inside the same suite and identity. A long-budget answer truncated afterward is not a short-budget generation.

- **Frontdoor memory/routing experiment.**
  M-12k and RI-17 can share a frozen quality workload and a validated common control. CFI-1 injection and RI-20 prompt changes become separate arms. “Memory off,” “rules only,” and “prompt absent” must not be silently treated as the same intervention.

- **Turn-taking trace bank.**
  CS-45/47 and CS-22 detector/text tasks can share audio, labels, probability streams, interim transcripts, and timestamps. Threshold policies can replay offline when the saved timeline is sufficient. If a threshold changes segmentation, resets, or STT inputs, new generation is required. CS-49’s live cancellation/AEC behavior remains a live intervention.

- **Prefill-cost capture.**
  KVU-16g and PB-QCOST can share prospective iteration records containing prompt size, cached context, phase, allocation, and time. Fit existing samples offline first. Required n1/n4 validation and held-out residual tests remain additional cells. YARN-E1-MEM has duplicate consumers, but its different images/flags prevent automatically folding it into this campaign.

- **Coding-model response matrix.**
  Share acquisition, contamination filtering, sandbox/oracle infrastructure, and exact incumbent response cells across compatible tasks. Preserve C390, LCB, RustEvo2, SWE, EffiBench, EvalPerf, and GSO as distinct populations/instruments. Multiple deterministic analyses of one generated program are useful; pooling unlike benchmarks into one acceptance result is not.

**4. Several “open inference tasks” should first become replay or reconciliation work**

This is likely the cheapest immediate reduction in compute:

- **C6:** repair parser/completion consumers and replay retained evidence against unchanged predicates. Existing diagnostics cannot qualify a subsequently modified candidate.
- **NEMO-PROF-RESEG:** resegment retained profiling traces without another GPU run.
- **EXL3-6c5a:** convert retained October speed/quality outputs into the required records. Do not invent missing historical measurement warrant.
- **KPF:** reuse already-rejudged historical cells. Localize/fix the retained fork effect before repeating dependent groups.
- **KB G11/G13:** their collections are already filed. Perform disagreement analysis and reconciliation before another encode. PREFIX-3’s incorrect encoding path is a separate case requiring corrected generation.
- **STT:** fix scorers and replay banked hypotheses; preserve incomplete/empty predictions in the original denominator.
- **HIL-16a:** verify recordings offline.
- **Autopilot/coordination:** reuse immutable journals and transcript snapshots for compatible lineage, allocator, feedback, and usage analyses.
- **Vidya:** attach prospective capture and canary work to each producer’s next legitimate qualified run. Do not create extra inference merely to populate a capture hook.

Conversely, **AP-DGM/SEQ-SHINKA is not currently an executable historical causal replay**: original menus, identities, and counterfactual outcomes are missing. That needs prospective capture, not a more permissive replay interpretation.

**5. Campaigns that should share setup but retain separate experiments**

These are important limits on fusion:

- **KPF residual campaign:** historical-image/layout controls, group3 localization, final-image qualification, and performance tails are different stages. The earlier S1 fusion attempt already exposed missing controls and unavailable mechanisms.
- **GDN:** numerical fidelity first; timing only after clearance; short-prompt fallback regression afterward. Prove the chunked path actually dispatched.
- **Final kernel promotion:** historical C6, diagnostic parity, and final-candidate production-optimal qualification are not interchangeable.
- **Long context:** methods may share corpus custody, but retain original denominators, matched A0/A1 exposure, model identities, and distinct approximation mechanisms.
- **Speech versus vision:** S-18/S-19 do not share FLEURS generation. A common multimodal handoff or resident-model window is only logistical overlap.
- **Cross-harness evaluation:** REPL/OpenCode can share fixtures and oracles, but need separate harness baselines and executed-tool evidence.
- **Image/video:** retained images support extra deterministic audits; changed generation paths require new images. Video scope and harness requirements remain separate.
- **Training:** MindDR RL, AW environment generation, fine-tuning, and inference evaluation need distinct execution classes and budgets.

Heavy instrumentation also needs care: **a profiling run is not automatically an uncontaminated timing run**. Capture cheap provenance everywhere; isolate expensive tracing unless its overhead has been qualified.

**6. Change the plan’s unit of work**

I recommend adding an experiment manifest before splitting the 626 “oversized” boxes. Each package should contain:

| Field | Purpose |
|---|---|
| `consumers` | Task IDs and the exact acceptance clauses each result can satisfy |
| `identity` | Model/artifact/build, rendered prompts, decoding, harness, runtime placement, instrument class |
| `cohort` | Item hashes, split, exposure history, exclusions, original denominator |
| `arms` | Shared controls, distinct interventions, independent sampling unit, order |
| `capture` | Raw outputs, token IDs/probabilities where needed, timings, failures, provenance |
| `analyses` | Deterministic consumers, metrics/directions, protocols, decision rules |
| `reuse_conditions` | Exact conditions under which another task may consume a cell |
| `stopping_rule` | Final decision table and when additional inference cannot change the action |
| `remaining_cells` | Only missing, invalid, or genuinely new generation—not every unchecked parent |

This permits **many tasks → one experiment → several independent verdicts**. It also prevents the reverse mistake: ticking every consumer merely because the shared run finished.

For shared controls, retain the dependence in the analysis. Multiple comparisons against one control do not create independent baseline observations. Predeclare primary decisions and exploratory readouts; do not claim a win by selecting the best of many post-hoc metrics.

**7. Recommended execution order**

1. **Repair the audit baseline and semantic classifications.** Reconcile companion SHAs/counts, existing authorizations, task identities, and incorrect field derivations.
2. **Inventory reusable evidence.** Mark each cell as retained-and-valid, retained-needing-replay, invalid-generation, missing, or unexposed.
3. **Build experiment packages for the strongest overlaps above.** Keep task verdicts separate; replace duplicate run instructions with result-consumer links.
4. **Complete deterministic tails first.** They may resolve prerequisites or eliminate proposed reruns.
5. **Run bounded discrimination pilots where needed.** Establish instrument validity, fired controls, variance, and realistic duration before committing large campaigns.
6. **Schedule only the remaining qualified cells**, grouped by compatible model residency and setup.
7. **Perform file consolidation around this structure.** Readiness-neutral folds can proceed, but task splitting should follow experimental decomposition.

My recommendation is to retain v3’s atomic migration approach while **replacing “split first, deduplicate later” with “identify experiments first, then split implementation and analysis around them.”** The largest defensible savings come from exact duplicate campaigns, shared qualified controls, complete prospective capture, and deterministic replay—not from reducing the number of handoffs or checkboxes.
