# Handoff content review — 2026-11-03

**Scope**: every open `- [ ]` box in the 31 non-index active handoffs, read and judged one handoff at a time in priority order (HIGHEST/HIGH, then MEDIUM, then LOW) by one reviewer (ws58, Fable 5.1), applied by one sonnet subagent per handoff in a temp worktree on origin/main, pushed through `push_fold_branch.sh`. Criterion (operator): a task earns its place only if it contributes to an improved UNDERSTANDING or PERFORMANCE of the inference and orchestration stack. The 2026-11 backlog refactor moved boxes verbatim and judged none; the 2026-11-03 model audit (`bc18f2e94`) judged model-naming boxes only. This review judged everything else.

**Conventions applied** (the ones `scripts/handoffs/belief_capture_check.py` accepts): a retired or merged-away box becomes a non-checkbox line `- **[declined: ws58 2026-11-03 content-review: <reason>]** <original text>` (its sub-bullets stay); the model audit's `- [x] … [declined: operator 2026-11-03 model-audit …]` ticks were normalized to the same non-checkbox form (a decline is never a tick); REFINE/NARROW keep the box's original opening so the D1 identity check still matches; CHECK appends `[check: <question>]`. Every commit passed `index_state.py --check` (rc 0) and `belief_capture_check.py --strict` (0 D1/T3) except where noted.

## Per-handoff tally

| Handoff | Priority | Open before → after | Retire | Merge-away | Refine | Narrow | Check | Normalized | Commit |
|---|---|---|---|---|---|---|---|---|---|
| mi210-serving-program | HIGHEST (kept) | 64 → 48 | 8 | 8 | 12 | 1 | 1 | 0 | `2407ac77b` |
| thesis-experiment-orchestrator-vs-strongest-model | HIGH (kept) | 9 → 7 | 2 | 0 | 1 | 1 | 0 | 0 | `1e078238d` |
| model-architecture-readiness | HIGH → **MEDIUM** | 17 → 6 | 11 | 0 | 1 | 0 | 0 | 0 | `59c0a9bf8` |
| stack-lifecycle-program | HIGH (kept) | 40 → 30 | 8 | 2 | 4 | 2 | 0 | 0 | `4ed468720` |
| speculative-decoding | HIGH (kept) | 50 → 35 | 9 | 6 | 7 | 2 | 0 | 0 | `4b1d5c4e6` |
| memory-program | HIGH (kept) | 55 → 40 | 5 | 10 | 9 | 0 | 0 | 0 | `3e65a3c21` |
| cpu-decode-roofline-program | HIGH → **MEDIUM** | 70 → 32 | 23 | 15 | 9 | 4 | 1 | 0 | `948657be0` |
| context-and-token-economy | HIGH (kept) | 72 → 41 | 16 | 15 | 9 | 1 | 4 | 1 | `6d262650b` |
| eval-tower-program | HIGH (kept) | 72 → 43 | 18 | 11 | 9 | 1 | 4 | 0 | `c12e5344d` |
| coordination-and-churn-pipeline | HIGH → **MEDIUM** | 112 → 48 | 56 | 8 | 7 | 0 | 1 | 0 | `0d0bb7646` |
| routing-program | HIGH (kept) | 116 → 63 | 23 | 30 | 13 | 1 | 0 | 0 | `5b4e7ac39` |
| harness-program | HIGH (kept) | 126 → 94 | 15 | 17 | 13 | 0 | 1 | 0 | `aed56064f` |
| kernel-champion-and-promotion | HIGH (kept) | 129 → 102 | 19 | 8 | 6 | 0 | 2 | 0 | `fada782c0` |
| kv-cache-program | HIGH (kept) | 131 → 92 | 7 | 32 | 10 | 0 | 0 | 0 | `8ad674af2` |
| vidya-belief-substrate-program | HIGH → **MEDIUM** | 419 → 384 | 35 | 0 | 1 | 0 | 0 | 0 | `582eea7ce` |
| quantization-and-low-bit | MEDIUM (kept) | 40 → 28 | 11 | 1 | 1 | 0 | 1 | 3 | `4c3cd3378` |
| long-context-program | MEDIUM (kept) | 57 → 33 | 16 | 8 | 4 | 0 | 0 | 0 | `0434fabee` |
| knowledge-pipelines | MEDIUM (kept) | 68 → 22 | 27 | 19 | 4 | 0 | 0 | 8 | `2d2b34691` |
| benchmark-suites | MEDIUM (kept) | 68 → 30 | 11 | 27 | 7 | 1 | 0 | 1 | `4782d36d5` |
| speech-and-multimodal | MEDIUM (kept) | 84 → 70 | 6 | 8 | 5 | 0 | 0 | 0 | `d289aaf0b` |
| model-evaluation-queue | MEDIUM (kept) | 96 → 34 | 37 | 25 | 4 | 1 | 1 | 11 | `08bc958bf` |
| rocm-kernel-authoring | MEDIUM (kept) | 99 → 75 | 18 | 6 | 3 | 0 | 0 | 2 | `86d29d0e7` |
| autopilot-program | MEDIUM (kept) | 112 → 74 | 25 | 13 | 1 | 0 | 0 | 0 | `d6962b8f8` |
| engineering-hygiene-backlog | MEDIUM (kept) | 125 → 93 | 23 | 9 | 0 | 0 | 0 | 0 | `86de40f1d` |
| deepseek-v41-flash-evaluation | MEDIUM (kept) | 136 → 121 | 13 | 2 | 0 | 0 | 0 | 0 | `a17b52e27` |
| numa-placement-and-contention | LOW (kept) | 99 → 44 | 33 | 22 | 7 | 0 | 0 | 0 | `9b5c8daad` |
| reviewer-control-plane | LOW (kept) | 37 → 26 | 7 | 4 | 1 | 0 | 0 | 0 | `6e61ad7d9` |
| frontier-lab-automation | LOW (kept) | 28 → 6 | 21 | 1 | 1 | 0 | 0 | 0 | `a33f51fcd` |
| autokernel-loop | MEDIUM (kept) | 222 → 131 | 60 | 31 | 3 | 0 | 0 | 0 | `5dfa1ce1c` |
| **Total (29 handoffs)** | 4 priority changes | **2,753 → 1,852** | **563** | **338** | **152** | **15** | **16** | **26** | 29 commits |

The 2026-11-03 engineering-hygiene LOOP-50 line still matches `- [x] … [declined:` by grep; it is a genuine landed tick whose prose mentions the tag, not a decline, and was left as is.

## Priority changes (4, all HIGH → MEDIUM)

- **model-architecture-readiness** — the log-linear GDN port waits for a production-scale model (operator 2026-11-02); what survives is G16/G16b (feeds mi210 G15) and the unfunded Engram Track B bet.
- **cpu-decode-roofline-program** — campaign closed out 2026-09-08; 38 of 70 boxes were labelling and process residue; what survives is a handful of decisive CPU levers (SYNC-6, CLOSE-6, D6, XFER-4b, CAFE-5), the G2-CONC promotion gate, Q38P physics and the INF-72 routing tap.
- **coordination-and-churn-pipeline** — the coordinator-daemon / tmux delivery plane it was filed for is retired (loop-owned fleet, SendMessage + flag files, the compute-calendar grant protocol); what survives is the churn-pipeline defect list, FM-* fan-out measurement and a few bus/dashboard repairs.
- **vidya-belief-substrate-program** — the operator refocused the belief kernel on AutoKernel + autopilot consumers with a demand-driven schema (2026-10-21); the prospective-wiring backlog no longer ranks with inference programs. Only 35 of 419 boxes were retired here (retired producers and custody/conformance records); the remaining prospective wiring boxes were not adjudicated producer-by-producer and are the largest remaining body of unreviewed-in-depth tasks.

## Ten most consequential retirements

1. **P3-4 native-MTP vs DFlash2 serving A/B** (mi210) — decided by the operator rule "27B ALWAYS DFlash2"; its instrument R23-3 (autokernel-loop) retired with it.
2. **The coordinator-daemon plane** (coordination-and-churn: M3/M3d/M4/M5/M5a/M5c, C20, C30, C36, AIR-6/7/9, WS-2/3, DP-2, FW-1/2 — 56 boxes) — superseded by the loop-owned fleet decision, SendMessage hand-offs and the calendar grant protocol.
3. **The INF-70 label sweeps and process lessons** (cpu-decode: STAT-1-SWEEP, SCALE-1, CLOSE-4, WRAP-1/9b/12/13, CLS-RECT-1 folded to one LABEL-SWEEP; C1-C4, MEAS-3/4/7, CLOSE-5/10/11/12, E4/E-GATE retired) — a closed campaign's residue, 38 boxes.
4. **Gate 4/Gate 5 and the HOLA/GDN-2 retrofit line** (model-architecture: Gate 4, Gate 5, G5, B4, B9) — readiness criteria and third-party-checkpoint training experiments with no path to a served-model decision.
5. **The hidden-state probe chain** (routing: P2.3-P2.6, P3.1-P3.3, P4.3, P4.4, P6.3.*) — conditional on a frozen P1.5 gate; /hidden-states is not in v10; the verifier gate is inert (LRC-2).
6. **tau-bench (CJ-4a-e)**, **Memento S2/S3 (S2-CGE-1, S3 rows, S2 smoke)**, **SLIDERS Phases 1-2**, **MinerU/GLM-OCR conditionals** — suites and programs with no execution path or whose premise the model audit declined.
7. **AK7/AK8 phases and the V27 restart checkpoint** (autokernel-loop) — superseded by the kernel-promotion skill, the v10 freeze and the AKU unified-loop slices; plus the Dream-RSI search-policy ports and harness spikes (CORAL, orx, OpenHyra).
8. **The eval-tower campaign index lines** (P0/P1/P2/P6, RE-4 pointer, D3/D4 sampling cert, Harbor/TB Core) and **lever-category rows** in model-evaluation-queue (EAGLE-3, GPU-draft/CPU-target, diffusion path, VL split, ASR…) — pointers and categories, not tasks.
9. **NUMA pre-reboot staging S-07..S-20 and July E5 notes** — stale since the 2026-08-13 reboot; E5 consolidated into one RE-MEASURE row.
10. **Watches with no trigger**: STQ1_0 PR #22836 (quantization, knowledge, model-eval), Loopie, J-space, Zunhai Su group, Hermes ingest, X-MAS telemetry, RI-JS-1/2, CT-4-class rules — and the standing-rule checkboxes (C1-C4, NG5, STANDING rows in stack-lifecycle, R-13, LOOP-26, CT-1a, "Rules for new tests").

## Ten most consequential refinements

1. **P2-5c/P2-5f (mi210)** — the P-SHED-1 shed-trade measurement now has a stop rule and the undefined complexity threshold became one operator decision package (duty cycle ≥ 15%, net ≥ +10% at both stress levels); the 122B gate is gone.
2. **P2-5j (mi210)** — host-thread placement sweep absorbed its protocol and the duplicate restore-to-git row; device-local node-1 candidates vs 184-191 with a measured-locality done-when; GPS-PIN-1 re-pointed on the winner.
3. **TB-6-ROUTER (context-and-token-economy)** — its "GPU joins the orchestration stack" precondition was met 2026-09-24; unblocked with a concrete done-when.
4. **REGIONLOCK-1 (cpu-decode)** — carries the operator's 2026-11-02 decision (serialize builds under the bench lock) and CLOSE-8's admission-control point; MEAS-1/MEAS-1-DECIDE/CLOSE-8 merged in.
5. **NOFOLD-1 (cpu-decode)** — the no-fold list (feature/tree-draft-v6; sync17-fix2/retest1-fix1 with GGML_SCALE_SPLIT/GGML_SOLO_YIELD_ROWCOL default ON) now has a home the fold checklist reads (kernel-manifests README).
6. **CF-3c A/B (context-and-token-economy)** — the seven-policy bake-off became one A/B with the mandatory masking anchor, the keep_k_latest_wo_reasoning arm, a non-termination counter on every arm and a decision rule.
7. **SR-8 (speculative-decoding)** — "speculative edits" hypothesis became a measurable three-arm test on the edit corpus with a ≥ 1.5× routing decision; XGRAMMAR-A2 ordered after SPEC-GRAM.3 (llguidance first).
8. **B1 (model-architecture)** — the #27442 HIP sweep re-specified exactly as the closed G1 CPU design with a 10/10 decision rule; **D-c1 (memory)** absorbed D-c/D-c2/D-e1 into one real-traffic measurement with a decision rule.
9. **AK-QL-7 (autokernel-loop)** — the whole sub-4-bpw family (H-QL-1/2/3, QL-2/3/5, S3-AKU-19) now hangs on the one IQ-residency tripwire (rocm-kernel-authoring TRIPWIRE, which itself absorbed the IQ2_XXS rows and INF37-IQ-2); **HSF-5.P-NEXT (kv-cache)** became the one decision on the host-KV mirror's fate.
10. **RI-10 / DAR-LAT-3 / TR-4.1 / TR-5.3 / DAR-4 / DAR-5 (routing)** — staged rollouts and pre-registered experiments collapsed from 20+ sub-boxes into single owned boxes with their stages and gates inside.

## Open CHECK questions (16, appended as `[check: …]`)

mi210 GPU-PLT-2 and model-eval GPU-PLT-1 (which lineup role would a PLT coder serve?); cpu-decode CLOSE-9 (does the calendar launcher expose a drain a halt reaches?); context-and-token-economy CF-EI-1, PRB Step 3 (does budget=0 still leak reasoning on v10?), RC-XLLM-PREFILL-1, RP-3 (which model loops?); eval-tower EV-8 (what decision does diversity feed?), P3 bulk-campaign (which entries still exist?), BUILD-semantics-serving-integration and CP3 delimiter (tracked in reviewer-control-plane?); coordination L2543 (does the dispatcher still key on file:line?); harness UFH14-A7 (finding or build?); kernel-champion CH-20.1 (name the two follow-ups) and MoE-Spec registry integration (is the patch in C5?); quantization EXL3-3 (which low-bit lane consumes the gfx90a EXL3 oracle?).

## Systemic patterns

- **Standing rules filed as checkboxes** (C1-C4, NG5, STANDING-* rows, "Rules for new tests", R-13, CT-4, LOOP-26…): ~45 boxes that can never close and were inflating the dashboard. They were retired with the text kept visible; the rule belongs in prose or `agents/shared/`.
- **Duplicate owners across folded files**: the fold moved boxes verbatim, so the same task sat in two files (YARN-E1-MEM, KVU-6/KPF-22, KV-3/KPF-23, KVU-19c/KPF-30, KVU-22/KPF-41, AKX-1/2 vs AKX-P0/P2, CLOSE-12/VB-INF70-ARMS, R23-49/REGIONLOCK-1, 2b-agentic/P5-1, S-17/R1a…). One owner was kept each time.
- **Conditional chains filed box-by-box** (SLIDERS 0.1-2.1, CTC-1..8, T0.1-T5.2, RE-4.2-4.5, DAR-LAT-3a/3g/3b/3c, Phase 1b dashboard cutover, video-gen steps): 338 boxes merged into their gate or parent so a single box carries the stages.
- **Era-stale premises**: v7/v8/E8 references, the deprecated 122B (P2-5g, TB-6-exec-v8, item C, GPU-draft/CPU-target), Gate-R/OP-16/pre-reboot staging, "GPU is only a bench instrument" (TB-6-ROUTER) — each retired or re-pointed at v10 / the 2026-09-24 GPU serving cutover.
- **Launcher/custody residue in the vidya and codex-ni sections** (conformance, custody, continuation rows): retired where they recorded process rather than measurement; the remaining ~380 prospective-wiring boxes in vidya were not judged producer-by-producer and are the natural next review target under the 2026-10-21 demand-driven decision.
- **The outline tallies I wrote were often off by one or two** against the action lists; every applier reported the discrepancy and applied the list, so the per-file "before → after" above is the ground truth (verified by `grep -c '^\s*- \[ \]'` in each commit).
- Process notes: the push script refuses detached worktrees (rules updated to `git worktree add -b`); full-replacement refinements must keep the original opening or `belief_capture_check.py` reports D1 (one such advisory D1 landed in stack-lifecycle `4ed468720` for the L1990 narrow and was not re-fixed; thesis `1e078238d` recorded the TE-reopen → TE-pre-A2 rename with a `[moved:]` sub-bullet).

Outlines and apply scripts: `/mnt/raid0/llm/tmp/ws58-review/` (scratch; the decisions themselves live in the handoffs' declined lines).

## Addendum — vidya-belief-substrate-program producer-by-producer pass (2026-11-03, ws58)

Second pass over the one handoff the first pass left unadjudicated. Every open box was read; the ~300 prospective "wiring" boxes were judged per producer against the 2026-10-21 refocus: the only ledger consumers are the AutoKernel planner (`loop_beliefs.py prepare` from research `loop/run.py`) and the AutoPilot bridge, so a producer feeds a live decision only when its claims land in a tier those readers assemble or gate kernel promotion. Liveness evidence: source kinds and dates in the canonical ledger (`/mnt/raid0/llm/state/vidya/ledger.jsonl`, 40,122 frames), the registered `ingest_sources.py` names, adapter files on main, and owner-row status after the first pass.

| Open before → after | Retire | Merge-away | Refine | Check | New boxes | Commits |
|---|---|---|---|---|---|---|
| 384 → 90 | 25 | 279 | 61 | 5 | 10 | `8ed0bea89`, `94c6ab191`, `eb67fdbbe` |

- **Kept LIVE (one survivor box per family, refined to a planning-context canary done-when):** AutoKernel loop producers (VB-AK-UNIFIED with its six slices and SC51, VB-AK-LEGACY-SERVING-LIVE, VB-AK-GPU-CONTROLS, VB-AK-HISTORY, VB-AK-HELDOUT, SC88, SC81 census/blast-radius, VB-AK-R18D/R22-2/R23-4/R24-9/PM12, VB-AK-R18-GFX, VB-AK-LONGCTX, VB-AK-SERVING-PROFILE (+NEMO, RVP-ATT, quantize-dispatch), VB-AK-SEAT-FINISH, VB-AK-NATIVE-WIRE-WRITE, VB-AK-RELIANCE-REVIEW, SC64 bug); AutoPilot (VB-AP-FIRST-CYCLE collapsing SC6-LIVE/SC7/PROMO-RULE-INGEST/MHS-OPS-HOOK, VB-AP-SPINUP-AP3-SCOPED collapsing the three spin-up steps, SC14-B, VB-AP70, VB-AP-JOURNAL-CARRY, VB-KVQ-V10-INGEST); serving/KV/kernel measurement families with recent ledger frames or active campaigns: VB-KVU-1 (np-ctx-kvu), VB-KVU-PF (kv-prefix-fork, 16 members), VB-KVU16H (VRAM/residency), VB-FA-MASKSKIP, VB-CPU-FA-VKQ, VB-SWAP-C (serving fabric/HSF, 12 members), VB-PREFILL-XOVER, VB-SERVING-DF2 (speculative serving, 8 members), VB-INF50-DRAFT-WIDTH, VB-YARN-E1 (long context, 10 members), VB-DSV41 (DS41, 10 members), VB-Q38FN-SERVED-SWEEP, VB-MOE-RT10 (moe-routing), VB-KQROUTE-1 (kernel A/B, 7 members), VB-FOLDGATE-WRITE, VB-M4-FOLD-SPEED-WRITE (13 members), VB-C6-Q4-MICROBENCH, VB-ARCH-CPU-QUAL (v7 quality gate, 5 members), SC18 kernel correctness (9 members), SC54 qwen4exp quality, SC12 K35/promotion receipts, VB-KVU19A2, VB-KVU-16A-LOAD, VB-R2364, VB-INF70-XFER4B, VB-G16-GREEDY, VB-V11-ORACLE, VB-HARVEST-1022.a/.e, USAGE-PROV-1, VB-CERT-1, LSA-EVIDENCE-1; the refocus core (PUSH-CORRECTION-FIX unblocked by the 11-02 Go, NONEMPTY-READ-PROOF, LOOP-TEXT decided, TRIAL-REMINDER, P1-LAND, P1-PHASE2, P1-AC9, VB-CC-PILOT and its three capture sub-boxes, VB-CANARY-GATE/-1, VB-TICK-CONTRACT).
- **Parked (one box per family, trigger named, members re-fileable from their declined lines):** VB-PARK-HARNESS-EVAL (harness, eval-suite, benchmark, REPL/retrieval, routing, thesis, TOC, HIL, PAW, XGrammar — ~70 producers), VB-PARK-SPEECH (15 CS-* producers), VB-PARK-INTAKE-SWEEPS (SC49/SC50/SC65), VB-PARK-OCR (ODL, PIP-02/03/05, ODL-011), VB-PARK-SECURITY-DTAP (4), VB-PARK-AUTOPILOT-DIAG (VB-MHS-GATES, judge exposure, RRR, AP66), VB-PARK-AK-DIAG (CH-17, lineage, INF-58, INF-26 CL3/NEW8, CL3 quarter), SC84a (operator-parked), SC21 contention matrix.
- **Retired (25):** producer retired/declined — R23-3 (VB-AK-R23-3), SC41 V27 GPU discovery, SC89 AK-plateau, HRM-1, SR-7, VB-AK-BELIEF-1 (superseded by the landed consumer), SC66 (moe-routing already wired, 618 frames), VB-INF70-ARMS + VB-SC75-CLS (INF-70 closed, capture wired), VB-GPU-RUNNER and SC82 (superseded by the floor registry), CH26 perf-mmap ABI; custody/verification records, not measurements — SC12-ARTIFACT, canonical-host attest, SC81 IQ4XS/quantizer-build, linkage guard, GNX caller audit, B2 producer-E, NIB98 FD verifier, SSU-F11, GPU-ZOS 2.2, QUAL-HARD, AK-CUSTODY, LOOP-5 operational counters.
- **Open CHECK questions (5):** SC54 (60 qwen4exp-quality frames already in the ledger — real run?), VB-UFH12-PARITY (6 repl-embedder-parity frames 10-27 — real G-P1/G-P2?), VB-NEMOTRON-BOLT-FOLD-WIRE (30 frames 10-24 — done?), P1-LAND (DP-1 decided? backfill ran 10-22 but none of the three P1 branches is merged), VB-TICK-CONTRACT (SESSION_LIFECYCLE line landed?).
- **Priority re-check:** stays **MEDIUM**. What survives is the refocus trial (consumers landed, trial clock 2026-11-30, one push blocked only on the operator Go already given) plus ~25 live-family canary tasks; none ranks with an inference program.
