# Inference-Batch Operator Bundle

Batched escalations + operator gate grants for the inference-batch loop. The loop appends `HELD_AMBIGUOUS` / `HELD_OP_GATE` decision blocks here and NEVER stalls waiting on them. The operator records grants in the **Grants** section; the loop reads grants at each session-init.

## Canonical operator-gate registry

This registry is the SINGLE source of truth for every `preconditions.operator_gates` value any entry may cite. A 2026-07-17 adversarial audit found the earlier Grants list was out of sync in BOTH directions (≈16 gates cited by entries were absent here → ungrantable; 3 grants here were wired to no entry). This section reconciles it: every distinct gate below is a real citation target, and every gate an entry cites appears here. The loop reads this at each session-init; nothing an entry gates can start until its gate row is `GRANTED`/`SATISFIED`.

Format for operator action: change `[ ]` → `[x]` and append `GRANTED <date> — <note>` (or `DENIED <date> — <note>`).

### A. Operator-decision gates (require a human choice — the loop can NEVER self-satisfy these)

- [ ] **OP-5a — P-REV-1 MEASUREMENT amendment**: signs the reviewer-calibration protocol (draft text in `handoffs/active/reviewer-calibration-accounting.md` RC-6). Until granted, every reviewer FA/FR/CR number stays an observation; unlocks the decision-grade P6 entries (P6-RC8, P6-LB7, P6-RM4). Cited by: P6-RC8, P6-LB7, P6-RM4, P6-RM2-A3.
- [ ] **OP-5b — LB-6 budget-gate threshold**: pick the quality-gain-per-throughput-cost value that unlocks enforce-mode (candidates in `handoffs/active/reviewer-latency-and-sampling-budget.md` LB-6). Gates any enforce-mode flip + the advisory→canary rollout entry. Cited by: semantics-advisory-rollout, P6 decision-grade set.
- [x] **OP-6a — kernel timing**: SATISFIED 2026-07-20 — v7 cutover is complete; run the P0 RCP prologue on the production v7 reference lineup, era-stamped to `production-consolidated-v7`, and do not revive the old v6-now vs hold-for-v7 branch unless a rollback occurs. Cited by: RCP-W1/W2/W3. ✅ 2026-07-20
- [ ] **OP-6b — reference-lineup relaunch window approval**: the ~1.5-2h quiesced window (relaunch + flag-propagation preflight + RD-12 paired replay + RC-8 smoke). Gates the P0 RCP prologue. Cited by: RCP-W1/W2/W3.
- [x] **OP-quiet-window — heavy-run window authorization**: GRANTED 2026-07-20 — operator authorized proceeding to the inference-batch loop after v7 promotion; loop may consume a window only when `inference_load_check.py --json` reports `quiet: true` immediately before execution. Cited by: the eval-fanout + bench entries (8). ✅ 2026-07-20
- [ ] **OP-stack-restart-approval — reference-lineup relaunch mechanism**: **[MECHANISM RESOLVED 2026-07-17 — ESC-1]** RCP-W1 needs the reference lineup brought up, but `orchestrator_stack.py` has NO `restart`/`--lineup` verb (audit finding). Operator decides the real relaunch path (stop+start, `reload` with a profile, or a lineup selected outside the CLI) AND authorizes it. Cited by: RCP-W1. See Escalations → RCP-W1. The relaunch command is now fully specified (env ORCHESTRATOR_FEATURE_REVIEW_DECISION_SHADOW=1 orchestrator_stack.py start --numa-mode full); only the OP-6b window approval + sole-host-occupancy confirmation remain operator-owned.
- [ ] **OP-POST-REBOOT — post-reboot clean-throughput attestation window**: the formal post-reboot bench gate for kernel-throughput numbers (host reboots are operator-only). Cited by: KOP2-v6iqk-canonical-verify.
- [x] **EV-11b-ece-binning-decision-recorded — EV-11b ECE binning decision**: SATISFIED 2026-07-20 — operator selected the `stat_tests.expected_calibration_error` closed-top-bin definition; eval_tower `_aggregate` now emits `ece_binning=closed_top_bin_stat_tests` and `ece_instrument_era=ev11b_closed_bin_2026_07_20`. This is a soft operator gate, not a structural `depends_on` edge; EV-11c still waits on EV-CONF/logprob and scorer-era prerequisites before decision-grade math rebaseline. Gates EV-11-math-rebaseline. Cited by: EV-11. ✅ 2026-07-20
- [ ] **OP-eval-suite-routing — eval-tower suite/verifier routing**: **[RESOLVED 2026-07-17 — ESC-2: NO run_benchmark route; EV-4/EV-11 require BUILD-evalbatch-verifier-mode]** the tier-based `eval_batch_serving_evaltower_window.py` cannot express `--suite/--split/--verifier/--diversity/--roles`. Decide: route these via `run_benchmark.py --suite <name>` (loses per-role/ECE/HE-R+ granularity) OR extend the window runner. Cited by: none (EV-4/EV-11 now cite BUILD-evalbatch-verifier-mode instead). See Escalations → eval-suite-routing.
- [ ] **OP-bench-recipe-abstraction — bench_canonical invocation form**: **[RESOLVED 2026-07-17 — ESC-3: use -m <gguf> form; BULK-A7 fully resolved, BULK-DS-E1/K-ROPE keep a build-gate for their non-throughput harness]** `bench_canonical.sh` has NO `--recipe` flag and `canonical_recipe.py` has no named-recipe registry (all 6 recipe IDs were fabricated). Decide: re-pin each kernel/bulk bench to the real `-m <model.gguf> -n N` form individually, OR build a recipe registry / route through `run_batch_entry.py` (B2 bridge). Cited by: BULK-DS-E1, BULK-K-ROPE, BULK-A7 (and the two KOP2 benches, re-pinned to `-m` form directly). See Escalations → bench-recipe-abstraction.

### B. Operator approval / attestation gates (human authorizes a specific inference/kernel/OCR run)

- [ ] **OP-EXPERIMENTAL-KERNEL-BENCH** — authorize benching an experimental (non-production) kernel build (e.g. the frontdoor Q8 fusion build vs v6). Production kernels stay frozen; this approves the experimental-branch build+bench. Cited by: KOP2-frontdoor-q8-fusion-ab.
- [ ] **OP-STRAND-INFERENCE-APPROVAL** — the entry's own "USER APPROVAL REQUIRED" for the Strand/RustEvo^2 single-instance bench. Cited by: KOP2-strand-rustevo2-phaseB.
- [ ] **OP-VL-INFERENCE-APPROVAL** — authorize a vision-language inference run (PaddleOCR-VL). Cited by: ODLB-W3-03-paddleocr-vl.
- [ ] **OP-WORKER-MTP-REATTEST** — re-attest the gemma4 worker_general MTP head config before a long-context matrix run. Cited by: BULK-K-ROPE-cells.
- [ ] **OP-ODL-SOURCE-CORPUS** — provide/approve the source PDF corpus + ground-truth for the ODL structural benches (the real gap on the OCR entries — the command is valid, the corpus is missing). Cited by: ODLB-W3-01/02/03.
- [ ] **Ref-judge budget** — approve the metered frontier-API judge-of-judge (pinned model-id+date, ~100 sampled decisions) for the H5 Ref arm. Cited by: RM-6/reviewer-model-ablations Ref arm (prose today; wire into RM-6 operator_gates when that arm is scheduled).
- [ ] **EV-4-v7-contention-matrix-recert** — re-measure and commit the v7 contention matrix, including the post-v7 `vision_escalation` geometry, before any fanout eval-tower entry resumes. Cited by: EV-4, EV-8, EV-10a.

### C. Posture decisions that SHAPE (not hard-block) entries

- [ ] **GC-4 — GLM-5.2 RAM-residency posture** (co-resident 239GB vs swap-on-demand vs review-windows): decides whether A4 is an interactive reviewer or a batch judicial gate; shapes the P5 GLM entries. Cited by (prose→wire on schedule): P5-GC1/GC2/GC3. NOTE: the P5 entries hard-gate on `COORD-glm52-admission` (parallel-session handshake); GC-4 shapes HOW they run once admitted.
- [ ] **GPU-bet-2 — 122B-IQ2 residency sequencing**: gates the H5 A3 same-family GPU reviewer arm (needs the residency lane; NO stack change until the parallel session's feature tests complete). Cited by (prose→wire on schedule): P6-RM2-A3-arm-122b-iq2-gpu. Also tracked as `COORD-axa-teleport` (that COORD row is the hard dependency; GPU-bet-2 is the operator posture behind it).

### D. Model-download gates (SATISFIED automatically when the artifact lands on disk — not operator decisions, but download is operator-initiated)

- [ ] **MODEL-DOWNLOAD-thinkprm-1.5b-q4km-gguf** — not on disk (verified 2026-07-17). Cited by: EV-5-thinkprm-t2-verifier.
- [ ] **MODEL-DOWNLOAD-ouro-2.6b-thinking** — not on disk. Cited by: EV-7-ouro-t0-sentinel.
- [ ] **MODEL-DOWNLOAD-sae-res-qwen35-27b-single-layer** — not on disk. Cited by: EV-8-diversity-redundancy.

### E. Code/data-prereq gates (auto-checkable landing conditions — the loop verifies these at session-init, no operator action unless they regress)

- [x] **math-verify-importable-attested** — SATISFIED ✅ 2026-07-17 (`import math_verify` OK under orchestrator venv). Cited by: EV-11.
- [x] **H4-nearmiss-corpus-v1-present** — SATISFIED ✅ 2026-07-17 (`/mnt/raid0/llm/datasets/nearmiss-corpus-v1/rows.jsonl`, 49MB, content_sha256 1c50c025). Cited by: RCP-W3, RC-8, RM-3/RM-4 screening.
- [x] **screening-tier-runner-landed** — SATISFIED ✅ 2026-07-17 (`scripts/autopilot/screening_tier_runner.py` exists, 26 tests green). Cited by: H5-RM3, P6-RM4.
- [ ] **RM-1-pool-gen-output-present** — PENDING: no `reviewer_pool_gen.json` output on disk yet (the generator `scripts/analysis/reviewer_pool_gen.py` exists; needs one run to produce the pool). Cited by: H5-RM3, ROUTE screening entries.
- [ ] **XMAS-enforce-window-ab-root-present** — PENDING: no concrete enforce-window A/B root has been named for the passive post-enable telemetry monitor. Cited by: BULK-XMAS-telemetry.
- [ ] **EV-11a-boxed-fix-landed** — UNCONFIRMED (verify at session-init): `debug_scorer._score_math_verify` native-`math_verify.parse()` boxed-extraction fix. BLOCKS EV-11. Owner: debug_scorer (research + orchestrator copies).

### F. Build-backlog gates (a runner/mode/adapter must be BUILT before the entry can run — these are NOT satisfiable by the loop; they need a build session)

Surfaced by the 2026-07-17 command audit: the fabricated `execution.command` strings hid genuinely-missing tools. The Wave-3 build pass built 8 of them (run_paired_ab, skill_efficacy_paired_ab, run_task_lg_parity, autowiki_writer, run_hermes_smokes, score_longcot_run, reviewer_corpus_ledger_run, reviewer_events_to_ledger). The gates below are the ones NOT built — they are inference-coupled, download-gated, GLM-gated, or serving-integration (stack-frozen), so they can't be built+validated without a window/model/unfreeze. Each blocks its entries until built.

- [x] **BUILD-mechanism-a-ledger-producer** — SATISFIED ✅ 2026-07-17 (workaround). The events→ledger materializer is built + tested (`reviewer_events_to_ledger.py`, 11 tests), and `data/trace/events.sqlite` already holds **32 historical REVIEW_DECISION events** — the shadow plane has fired, so this is NOT hypothetical. RCP-W2 + RD-12 are unblocked (materialize existing events → ledger → report; ECE/AUC/FA/FR compute after the `--corpus` gold-join). Runtime caveat (ESC-4, not a blocker): a scoped run may find 0 events. The durable alternative (review_service writes ledger rows inline) remains a stack-frozen serving-path change, deferred. NOTE: LB-4 (needs `BUILD-policy-arm-wiring`), LB-7 (needs OP-5a), and P6-RM2-A3 (needs COORD-axa-teleport) stay blocked on those OTHER gates — this gate no longer blocks them.
- [ ] **BUILD-semantics-serving-integration** — CP1/CP2/CP3 semantics layer landed as MODULES but is not wired into the live serving path (stack-frozen). Cited by: semantics-shadow-rollout, semantics-advisory-rollout.
- [x] **BUILD-tm8-coverage-counter** — SATISFIED ✅ 2026-07-17 (built + fixture-tested): thin coverage counter over `events.sqlite` (query.decision_chain); buildable but contingent on the plane firing. Cited by: TM-8.
- [x] **BUILD-lb1-offline-attribution** — SATISFIED ✅ 2026-07-17 (built + fixture-tested): offline OFF/ON throughput-attribution analyzer (does not exist; `task_rate_goodput_replay.py` does journal-Pareto replay, not this). Downstream of a working Mechanism-A run. Cited by: LB-1.
- [x] **BUILD-policy-arm-wiring** — SATISFIED ✅ 2026-07-17 (built + fixture-tested): per-policy arm wiring for the sampling-policy A/B. Cited by: LB-4.
- [x] **BUILD-field-order-arm-config** — SATISFIED ✅ 2026-07-17 (built + fixture-tested): RA-8 field-order A/B: two arms with different rubric field ordering — a config lever the reviewer-corpus bridge does not expose. Cited by: RM-6.
- [x] **BUILD-evalbatch-verifier-mode** — SATISFIED ✅ 2026-07-17 (mode built; EV-4/EV-11 runnable, EV-5/7/8 remain MODEL-DOWNLOAD-gated for validation): cross-family verifier / diversity-baseline mode on `eval_batch_serving_evaltower_window.py` (tier-based today; no `--verifier/--diversity`). Cited by: EV-4, EV-5, EV-7, EV-8, EV-11 (also MODEL-DOWNLOAD-gated).
- [x] **BUILD-embedder-recall-harness** — SATISFIED ✅ 2026-07-17 (built + fixture-tested): retrieval recall@k harness (bench_canonical is tg/pp only). Cited by: BULK-K-EMB-1.
- [ ] **BUILD-paddleocr-vl-adapter** — `_extract_with_paddleocr` VL backend in `pdf_router.py` (adapter accepts the engine string but has no backend). Cited by: ODLB-W3-03 (also OP-VL-INFERENCE-APPROVAL).
- [x] **BUILD-shapekeyed-step2-driver** — SATISFIED ✅ 2026-07-17 (built + fixture-tested): shape-keyed Step-2 live-smoke + vision re-bench harness (screening_tier_runner has no such mode). Cited by: ROUTE-A1.
- [x] **BUILD-migration-probe-driver** — SATISFIED ✅ 2026-07-17 (built + fixture-tested): J2/J3 live under-traffic migration-probe harness (screening_tier_runner has no `--migration-probe/--oscillate-load`). Cited by: ROUTE-A3.
- [x] **BUILD-glm-reviewer-capability-probe** — SATISFIED ✅ 2026-07-17 (built + fixture-tested): GLM-5.2 single-model reviewer-capability probe runner + authored command (screening_tier_runner does reviewer PAIRING, not single-model capability). Cited by: P5-GC1/GC2/GC3 (also COORD-glm52-admission).

## Standing pre-work blockers (code, not operator decisions — tracked for the loop's precondition awareness)

- **EV-11a** — see gate E above (debug_scorer boxed-extraction fix; status unconfirmed as of 2026-07-17 — confirm before trusting any EV-11 math number).
- **health_check.sh exit-1** — pre-existing security-audit step fails under `set -e`; B4 attestations conservatively FAIL until fixed.
- **CandidatePackage sanitizer gaps** (CP3 findings, xfail'd) — control/data separation, path allowlist/secret redaction, silent truncation of buried critical outputs; harden before enforce-mode.

## Escalations (loop appends; operator resolves)

Four pre-formed decision blocks were seeded by the 2026-07-17 command audit (the loop appends more as it hits HELD_AMBIGUOUS/HELD_OP_GATE entries). The operator can resolve these BEFORE starting the loop — each unblocks a cluster of entries.

### ESC-1 — OP-stack-restart-approval: reference-lineup relaunch mechanism (blocks RCP-W1 → whole P0 prologue)
- **Gate**: RCP-W1's first command clause was `orchestrator_stack.py restart --lineup reference`, but that CLI has NO `restart` verb and NO `--lineup` (audit-confirmed). The reference lineup must be brought up some other way.
- **Evidence**: `orchestrator_stack.py` subcommands are `start / stop / reload / status` only.
- **Options**: (A) stop + start with the reference lineup selected via the stack config; (B) `reload` with a reference profile if one exists; (C) the lineup is selected outside this CLI (launch env / manifest). Operator picks the real relaunch path + authorizes the ~1.5-2h quiesced window (this is also OP-6b).
- **RESOLVED 2026-07-17:** command = env ORCHESTRATOR_FEATURE_REVIEW_DECISION_SHADOW=1 orchestrator_stack.py start --numa-mode full (start's default HOT tier IS the reference lineup; no restart verb). Residual: OP-6b window + sole-host occupancy.

### ESC-2 — OP-eval-suite-routing: eval-tower suite/verifier selection (blocks EV-4, EV-11)
- **Gate**: `eval_batch_serving_evaltower_window.py` is tier-based (`--tier{1,2,3} --n --seed`) and is actually a current-vs-eval_batch ENDPOINT A/B — it cannot express `--suite/--split/--verifier/--diversity/--roles/--record-metrics`.
- **Evidence**: `parse_args` has no such flags; `scoring_verifiers` IS a real suite reachable via `run_benchmark.py --suite scoring_verifiers` but that loses per-role/ECE/HE-R+ granularity.
- **Options**: (A) route EV-4/EV-11 via `run_benchmark.py --suite …` (accept coarser granularity); (B) extend the window runner with suite/split/roles selection (a build); (C) split — cheap suites via run_benchmark, per-role/ECE via a new mode. Operator picks.
- **RESOLVED 2026-07-17:** run_benchmark route rejected (raw generations, no per-role/ECE). EV-4/EV-11 -> BUILD-evalbatch-verifier-mode.

### ESC-3 — OP-bench-recipe-abstraction: bench_canonical invocation (blocks BULK-DS-E1, BULK-K-ROPE, BULK-A7)
- **Gate**: all 6 `bench_canonical.sh --recipe <id>` commands were fabricated — there is no `--recipe` flag and no named-recipe registry.
- **Evidence**: real interface is `bench_canonical.sh -m <model.gguf> [-n N][-p N][-r REPS][--perf][--dry-run]`; `canonical_recipe.py` has no recipe map. (KOP2-frontdoor/v6iqk already re-pinned to `-m` form.)
- **Options**: (A) re-pin each remaining bench to the explicit `-m <model> -n N` form (fast, no code); (B) build a named-recipe registry so the manifest can stay symbolic; (C) route through `run_batch_entry.py` (the B2 bridge that resolves canonical commands). NOTE: BULK-K-ROPE (long-context accuracy) and BULK-DS-E1 (KV-per-slot footprint) additionally need a NON-bench_canonical harness — bench_canonical only does tg/pp throughput.
- **RESOLVED 2026-07-17:** -m /mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf -n 128 for both; A7 = real throughput, DS-E1 = smoke (KV-footprint harness still build-gated).

### ESC-4 — Mechanism-A firing contingency (RCP-W2, RD-12, LB-1, LB-4, LB-7)
- **Gate/Note (not a decision — a standing caveat)**: the events→ledger materializer (`reviewer_events_to_ledger.py`) is built and tested, but it only produces rows if the reviewer shadow plane actually EMITTED REVIEW_DECISION events during the eval workload. The plane fires on the delegation path; EvalTower's rubric-judge hard-disables delegation. So the FIRST live RCP-W2 run may materialize ZERO rows — that is an expected diagnostic outcome, not a failure. If zero: the durable fix (review_service writes ledger rows inline) is a serving-path change, deferred until the stack unfreezes. Record the zero-row result as evidence and hold RD-12/LB-4/LB-7 (they share the dependency).
- **RESOLVED 2026-07-17 (validated non-inference):** 32/32 historical events -> 32 ledger rows, report clean; FA/FR null (event candidate_ids not nearmiss row_ids). RCP-W2 command correct as-is; non-null FA/FR = RCP-W3's bridge. Firing-contingency discharged for the 32 existing events.

### ESC-5 — EV-4-v7-contention-matrix-recert: v7 matrix re-measure (blocks EV-4 fanout)
- **Gate**: EV-4 and other fanout entries need a v7 contention matrix whose measured geometry matches the current production-v7 stack, including the one-instance `vision_escalation` layout. Reusing or hash-bumping the v6 matrix would certify the wrong shape.
- **Evidence**: live matrix fingerprint for the current measured role subset is `8c8cfcbb13d2611d`; the committed global matrix still carries `df373c79cc4af06f`. The 2026-07-20 EV-4 attempt was stopped before a decision-grade summary because the loop/matrix state had already diverged and then exposed additional robustness defects.
- **Options**: (A) run the A3/A5 re-measure and commit the regenerated v7 matrix, then append a READY requeue row for EV-4; (B) defer all fanout eval-tower entries; (C) run serial only as diagnostic, never as the EV-4 decision-grade baseline.
