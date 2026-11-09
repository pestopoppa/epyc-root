# RTG-02 staleness audit — /workspace/handoffs/active/autopilot-program.md (read-only, 2026-11-09)

Columns: # | line | box | CLASS | HOLD (RUN = needs autopilot/inference; DOABLE = code/no-compute work the hold does not block; OPER = operator-only decision/edit; its decision package is DOABLE) | evidence / note.
Line numbers are the handoff's own; the task text is the identity.

## True last-run date
`orchestration/autopilot_journal.jsonl` (shard 0): trials 0-999, 2026-05-26 .. 2026-06-27T23:57 (frozen shard).
`orchestration/autopilot_journal_1.jsonl` (live tail, shard 1): trials 1000-1505, 2026-06-28 .. **2026-08-09T19:29:35Z**. Last real trial = 1503 (seed_batch, q=1.787, 14:25Z); 1504 numeric_swarm skipped; 1505 "(killed)". optuna_study.db mtime 2026-08-09 14:26. So the true last run is **2026-08-09**, not 06-27. The handoff's own T0.1 note ("stopped since 2026-07-27") and CURRENT-CAMPAIGN are also off by ~2 weeks vs the journal (CURRENT-CAMPAIGN:261 correctly says 2026-08-09).

## Table
| # | line | box | CLASS | HOLD | evidence / note |
|---|---|---|---|---|---|
| 1 | 43 | AP-27 RLVR tiers | STILL-VALID | RUN | code slices exist: src/autopilot_core/rlvr_tiers.py, wired autopilot.py:77,11619 (journal payload). Remainder = Ouro integration (inference). |
| 2 | 56 | AP-ME-1 per-operator ctx budgets | STILL-VALID | DOABLE | offline census landed orch 95d663e5 (operator_context_baseline.py); budgets themselves still unimplemented; box does not mention the census. |
| 3 | 90 | BSV-2 differential testing | STILL-VALID | RUN | scaffolds bsv_paired_report.py / bsv_paired_runner.py exist; needs paired live evals. |
| 4 | 92 | BSV-3 conflict-aware acceptance | STILL-VALID | RUN | child BSV-3a ticked; parent waits on BSV-2 rollout evidence. |
| 5 | 117 | AP-19b supervised gepa run | STILL-VALID (premise aging) | RUN | cites esc8 landmine audit recipe + frontdoor.md; lineup/stack changed since; needs re-read of recipe vs v10 store. |
| 6 | 121 | AP-29 episodic-only control | STILL-VALID | RUN | primitive landed 2026-11-01 (APP 0162aa16, tripwire 015eb8e4); comparison needs authorized run. |
| 7 | 142 | AP-29b lexicographic vs scalarized replay | STILL-VALID | DOABLE | zero-inference; MUST read both shards via scripts/autopilot/journal_shards.py (JRN-5); name `chapter 08` and era (E17-E20) to rescore under. |
| 8 | 178 | lineup status worker_fast/eval_batch_frontdoor/embedder extra_recipes | STALE-PREMISE | DOABLE | launch_manifest.yaml:80-81 already marks worker_fast DEPRECATED (worker_pool); :300-312 still declares both; "none are running" unverified. Route via stack-change skill; not an autopilot item. |
| 9 | 186 | AP-58 reseed speed axis | STILL-VALID | DOABLE | safety_gate.py exists; design decision; eras since: E16 (08-10), E18, E20 (10-21). |
| 10 | 233 | memories.sub_decision no producer | STILL-VALID | DOABLE | only episodic_store.py-internal `sub_decision=` hits (:228,504,520,623,776); no external producer found. Same hole T3.1 needs. |
| 11 | 285 | ten zero-importer modules | UNDERSPECIFIED | DOABLE | the ten are not listed; src/mutation_ledger.py has no `import` hit in src/scripts (verified negative); re-audit needed. |
| 12 | 397 | routing not context-length aware | STILL-VALID (unverified) | DOABLE | only role-based INGEST_LONG_CONTEXT dispatch (chat.py:479, graph/nodes.py:639); no length check found. Not an autopilot item. |
| 13 | 420 | P1 contention matrix marker polarity | STALE-PREMISE (anchor rot) | DOABLE | contention_matrix.py:306-313 is now `_enumerate_full_pairs`; bug location not re-resolved. Re-grep before dispatch. |
| 14 | 474 | decision on 419 update-path rows | STILL-VALID | OPER | decision package; recommended option exists in the box. |
| 15 | 574 | dominates() positional axes | UNDERSPECIFIED | DOABLE | `safety_gate.py:2303` anchor rot (now quality-history code); afdd5d74 fix not re-checked. |
| 16 | 586 | AP-48 adaptive admission after E13 | STALE-PREMISE | RUN | E13 burst baseline predates v10 + lineup change; baseline must be re-collected on the v10 kernel. |
| 17 | 608 | AP-WM-1 shadow least-commitment | STILL-VALID | DOABLE | offline over archived proposals. |
| 18 | 626 | AP-WM-1b AutoKernel matched archive | UNDERSPECIFIED | RUN | depends on AutoKernel (not autopilot); champion C9 paused (memory) so premise may be dormant. Not read in depth. |
| 19 | 642 | AP-CH-2 reset-free vs episodic | STILL-VALID | RUN | needs proposer generation at equal budget. |
| 20 | 651 | P17.BT-5a feedback synthesizer | ALREADY-DONE (code) | DOABLE | scripts/autopilot/feedback_synthesizer.py (+test) orch 95d663e5 2026-11-02; unticked because the "shows signal" readout is not recorded. Run offline + record. |
| 21 | 660 | BT-5b feedback-conditioned pilot | STILL-VALID | RUN | gated on 5a signal. |
| 22 | 668 | BT-5c log pair CONTENT | UNDERSPECIFIED | DOABLE | write-side hook; no confirming code found (mutation_author_capture.py has no winner/loser text); borders on mutation_pair_features/CRM capture work (orch 70c5e831..a8a1e25b). |
| 23 | 737 | AP-54b wiki-fence A/B | STILL-VALID | RUN | compute-gated. |
| 24 | 746 | AP-56 determinism certification | STILL-VALID | RUN | must be re-run on kernel-store binary (v10), fixed seed. |
| 25 | 754 | AP-63 orx refill preconditions | ALREADY-DONE (part a) | DOABLE | experiment_journal.py:583-588 run_manifest field, :607 select_lineage_parent, autopilot.py:11411 call. Part (b) not verified; row text must be split. |
| 26 | 786 | AP-64 task_failed both producers | STILL-VALID (half done) | DOABLE | eval_tower side done (eval_tower.py:1255 task_failed_scores_zero_v1, E17 2026-09-23); seeding side and same-axis-0 test unverified. |
| 27 | 792 | AP-65 _proxy_check binds? | STILL-VALID | DOABLE | safety_gate.py:2936 still `warnings.extend`; :3002 returns warnings. |
| 28 | 828 | AP-67 planner numeric trials reach sampler | STILL-VALID | DOABLE | actions.py:905-927 explicit-params branch applies+evals with no suggest_trial/tell; study.tell only in species/numeric_swarm.py:259,292,315. |
| 29 | 834 | AP-68 planner arm vs sampler | STILL-VALID | DOABLE | journal analysis; read both shards. |
| 30 | 854 | AP-70 rotation-boundary drop | ALREADY-DONE (code, opt-in) | RUN | f0bbbad7 + fb034576 (2026-11-01); autopilot.py:5547 runs only with AUTOPILOT_CORE_ROTATION_STUDY_ID; data needs a run. |
| 31 | 864 | AP-71 PromptForge lineage audit | STILL-VALID | DOABLE | git+journal offline. |
| 32 | 870 | AP-72 physicality bound | STILL-VALID | DOABLE | safety_gate.py has only QUALITY_MAX/RELIABILITY_MAX (:90-97); no speed/TTFT bound. Roofline numbers must be v10/lineup-specific. |
| 33 | 879 | AP-DGM-PROV | UNDERSPECIFIED | RUN | freezer exists (root 37e74b28 scripts/research/selector_replay.py, historical-final=not_evaluable). No orchestrator write-side hook exists: grep `eligible_candidates`/`decoding_id` in orchestrator = 0 hits. See finding 1. |
| 34 | 882 | AP-DGM-SEL | UNDERSPECIFIED | RUN | same input; conformance only on fixtures. |
| 35 | 4682 | SEQ-SHINKA-1 | UNDERSPECIFIED | RUN | same input; "ALE trigger" never defined. |
| 36 | 928 | early-abort reliability decision (":1960") | UNDERSPECIFIED | OPER | file anchor `:1960` unnamed; cannot be resolved. |
| 37 | 934 | human_only_paths.yaml edit | STILL-VALID | OPER | trust boundary: human-amendment-only. |
| 38 | 945 | worktree-apply behaviour change | STILL-VALID | OPER | ratify-or-reverse. |
| 39 | 950 | AP-55-ARM | STILL-VALID | RUN | start_authority_daemon.py:117-125 pins AP55 gate "shadow", seed rerun "0". |
| 40 | 1268 | C1 fix #2 manifest writer | UNDERSPECIFIED | DOABLE | scripts/server/runtime_facts_manifest.py exists; other-agent ownership; dashboard track row. |
| 41 | 1284 | C1 fix #3 one env across --workers 6 | UNDERSPECIFIED | DOABLE | scripts/server/*; no owner. |
| 42 | 3543 | goodput vs raw rate (axis 1) | STILL-VALID | OPER | operator decision; era E18 rate/duration axis since. |
| 43 | 1904 | EV-CONF-2 salient-token confidence | STILL-VALID | DOABLE | code part DOABLE; re-baseline of math AUROC needs inference. |
| 44 | 2144 | BEP-2 CPU latency A/B | STILL-VALID | RUN | bench. |
| 45 | 2147 | BEP-5 sandbox-before-disk | STILL-VALID | DOABLE | design/code; safety-gated. |
| 46 | 2261 | DCP-6 deploy attestation | STALE-PREMISE | RUN | cites API git_sha 27e09a1 and "llama.cpp/build/bin/llama-server exists (rebuilt 08-10)": that is the v9 in-tree binary; I observed it fails to load (libcrypto OPENSSL_3.3.0 missing) and v10 serves from kernels/production/cpu. The "falsified caveat" is now moot. |
| 47 | 2391 | W3 rotation snapshots | UNDERSPECIFIED | DOABLE | substrate 5561f48 + chaining b7a61c02 (merged 753343f5) landed; remaining scope not stated. |
| 48 | 2412 | W6 strategy provenance | STILL-VALID | DOABLE | partial read-side guards 005e836, 0f07644; write-side evidence_trial_ids unverified. |
| 49 | 2597 | W5 designed core_v2 | ALREADY-DONE | DOABLE | benchmarks/prompts/core_v2.jsonl in main, eval_tower.py:4476 core_v2 metadata; branch/worktree path in box is gone (/mnt/raid0/llm/tmp/core-v2-current-refresh-20260614 missing). |
| 50 | 2598 | W6 rotating audit block | ALREADY-DONE (shadow) | DOABLE | daemon env AUTOPILOT_W6_AUDIT_BLOCK=1, SHADOW_ONLY=1 (start_authority_daemon.py:98-101); worktree gone. |
| 51 | 2600 | W8 promotion evals | STALE-PREMISE | RUN | superseded by AUTOPILOT_MULTITIER_PROMOTION=1 staged T1->T2->T3->fresh T1 (daemon env + CURRENT-CAMPAIGN:261). |
| 52 | 2637 | (Z) llama-server log retention | STILL-VALID | DOABLE | too-big; subsystem investigation; cites upstream #27442. |
| 53 | 2998 | W8b live candidate evidence | STALE-PREMISE | RUN | names `local_frontdoor`/`local_worker` canary, old lineup. |
| 54 | 3361 | real_suite_v1 discriminability | STILL-VALID | RUN | root-cause child ticked 2026-09-24 (RTG-16); re-run needs evals; corpus changed E20 (EV19). |
| 55 | 3571 | W3e retire tier-cost axis | UNDERSPECIFIED | DOABLE | blocker sentence truncated; positional axis reads (see #15) make it risky. |
| 56 | 3647 | W6d production-weighted mix | STILL-VALID | OPER | design decision. |
| 57 | 3656 | W6f re-establish T1 baseline | STALE-PREMISE | RUN | superseded by ratified clean v10 multi-tier baseline (artifacts/operator/ratify_multitier_baseline_v10_20260810.json + t1/t2/t3 clean); but E20 corpus (2026-10-21) postdates it -> reseat needed. |
| 58 | 3689 | W5 regime-profiled offered load | STILL-VALID | RUN | next instrument era; design part DOABLE. |
| 59 | 3935 | P0.1 run/pause decision | STILL-VALID | OPER | this is the hold-lift decision. |
| 60 | 3936 | P0.2 amendment bundle | STILL-VALID | OPER | rate-axis era-fence partly landed (orch b336f50b, 59934bfa 2026-11-01). |
| 61 | 3939 | P0.3 blacklist purge | STILL-VALID | OPER | token-gated; dry-run must be re-run (5 entries counted 2026-07-11). |
| 62 | 3986 | W1 runtime-facts consumption | STILL-VALID | DOABLE | box itself records HIGH gitnexus impact (22 upstream); proceed methodically per memory. |
| 63 | 4139 | T0.1 confirm AutoPilot stopped | STALE-PREMISE | DOABLE | "stopped since 2026-07-27" is wrong (journal to 08-09); proof is process/journal check, not coordination. |
| 64 | 4144 | T0.2 GPU reasoner service | STALE-PREMISE | DOABLE | path /mnt/raid0/llm/llama.cpp-mi210-hip does not exist; GPU kernel is kernels/production/gpu; `start_whisper():1836` now at orchestrator_stack.py:3298; Qwable registry entry at model_registry.yaml:754 is a note block. |
| 65 | 4147 | T1.1 composite executor | STILL-VALID | DOABLE | `eval_tower.py:1063` anchor unverified; depends on #64. |
| 66 | 4151 | T2.1 blended cost | STILL-VALID | DOABLE | |
| 67 | 4155 | T3.1 scaffold-eligibility in episodic | STILL-VALID | DOABLE | shares the sub_decision no-producer gap (#10). |
| 68 | 4159 | T4.1 offline replay | STILL-VALID | DOABLE | journal_snapshot_replay.py exists. |
| 69 | 4163 | T5.1 measurement protocol | STILL-VALID | OPER | protocol annex is human-amendment-only. |
| 70 | 4451 | SEQ-B1 keep joint gate? | STALE-PREMISE | OPER | numbers from E8/core_v1; E16..E20 since. |
| 71 | 4461 | SEQ-3 resume top candidate | STALE-PREMISE | RUN | box itself says era problem: 393 core_v1 trials, E8; current eras through E20 (instrument_eras.yaml:571). |
| 72 | 4516 | decide re-arm sequential gate | STALE-PREMISE | OPER | daemon env AUTOPILOT_SEQ_VERDICT=0, SEQ_P0_2_BRIDGE=1 (:96-97); "max E_quality 11.55 vs 20" is E8-era. |
| 73 | 4572 | SEQ-4 allocation replay | STILL-VALID | DOABLE | zero inference; 141 candidates/393 trials. |
| 74 | 4905 | MHS-8 apply gate | STILL-VALID | DOABLE | code. |
| 75 | 4990 | W3 reliability ladder (lab) | UNDERSPECIFIED | DOABLE | scripts/lab/promote_job.py exists; "ongoing", no exit criterion; not autopilot. |

## Drift the handoff does not mention
1. Live selector has no "menu": parent = `select_lineage_parent` rule `latest_committed_baseline_promotion_same_species` (experiment_journal.py:607) with latest-same-species heuristic (autopilot.py:11411-11430). DGM/Shinka/HGM comparisons assume a choice set; none exists in the loop, and the orchestrator has zero write-side fields for eligible menu, decoding_id or holdout. "Prospectively capture" therefore needs a design (where is the menu: candidate pool in sequential resume? planner proposals?) before any run.
2. JRN-5 regression risk: preflight_audit.py:52,797 JOURNAL_PATH and restart_readiness_report.py:28,769 default to base shard only (frozen at 2026-06-27). A restart-readiness report would analyze pre-rotation data and miss shard 1 (06-28..08-09). journal_shards.py exists and is not used there.
3. Kernel: stack_paths.py resolves via kernel store (_kernel_backend_dir("cpu")), so launchers are migrated; but model_registry.yaml:32 base_dir, :501-509 command templates, :3185/:3284 `binary:` (GPU, labelled production-consolidated-v9), model_registry_full.yaml:512,12386-12402 still hold literal llama.cpp/build/bin and build-hip/bin. Consumers of those templates not found in Python (unverified); the in-tree binary does not load (OPENSSL error).
4. ik_llama: orchestrator_stack.py:1078-1196,2421 and launch_manifest.yaml:334 still describe the worker_general gemma4 MTP path as requiring ik_llama PR #1744; ik_llama is deprecated as a serving path. model_descriptors.py:833 still branches on "ik_llama.cpp" binary_dir.
5. Eras: instrument_eras.yaml runs to E20 (2026-10-21) plus E10 cpu-candidate eras; handoff prose is E8/core_v1. Journal rows show core_id None for all 1372 trials at top level (core id may be nested; not chased).
6. Belief kernel: scripts/vidya/adapters/README.md:459 lists autopilot-journal ingest as wired 2026-09-16 and "parked since 2026-08-09 awaiting first post-hook trial"; no box says the first post-restart run must be checked against the canary. belief_scope field added to journal rows 2026-10-21 (experiment_journal.py:594).
7. Planner roster: start_authority_daemon.py:109-113 pins a temporary two-Codex roster "Claude weekly tokens exhausted"; stale-by-design, must be revisited at restart.
8. Multi-tier staged promotion is the promotion path (AUTOPILOT_MULTITIER_PROMOTION=1), ratified v10 baselines 2026-08-10 predate E17-E20; handoff mentions neither in the W8/W6f boxes.
9. Dashboards: no box covers autopilot dashboard registry/probe/freshness envelope; `/health` vs `/api/health` distinction not mentioned for restart verification.

## Restart preconditions (checklist)
- [ ] Operator explicitly lifts HOLD (P0.1) AFTER next production kernel promotion + stack reorg.
- [ ] `verify_llama_cpp.sh` + `verify_kernel_store.sh` pass; served binary proven by digest/ggml linkage (verify_ggml_linkage.sh), VRAM sampled during GPU roles.
- [ ] Registry/launch_manifest lineup final; resolve #8 (worker_fast, eval_batch_frontdoor, embedder extra_recipes); literal build/bin paths and ik_llama launcher text removed or proven unused.
- [ ] Journal readers shard-aware (preflight_audit, restart_readiness_report use journal_shards); restart_readiness_report, seq_readiness_report, archive_authority_report all clean.
- [ ] Current era fenced: baseline reseated under E20 corpus (EV19) and current kernel; multi-tier T1/T2/T3 baselines re-proved vs 2026-08-10 ratification.
- [ ] Decide SEQ gate (SEQ_VERDICT, SEQ_P0_2_BRIDGE) and AP-55 shadow->enforce plan; AP55 stays shadow for first run.
- [ ] Planner roster policy re-decided (temporary Codex-only roster).
- [ ] Start only via start_authority_daemon.py (env-gated); no bare `autopilot.py start`; no other llama-server/autopilot live (model_gate_report blockers).
- [ ] Belief ingest canary armed; first post-hook trial verified; any new write-side capture (menus, decoding_id, holdout) shipped before the first model-producing run, else AP-DGM-* stay not_evaluable.
- [ ] Orchestrator API reload ownership per CLAUDE.md; orchestrator at current main (a4963aa3+), loop-safety C1-C3 in.
- [ ] Stale journal tail row 1505 "(killed)" / trial counter state checked (autopilot_state.json) before first trial.

## Could not verify
Consumers of registry literal templates; box #12, #22, #40, #41 live status; AP-63(b) and AP-64 seeding half; contents of AP-WM-1b, 3543, 928; whether any process is currently running (not checked by design); core_id nesting in journal rows.
