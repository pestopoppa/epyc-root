# RTG-08 staleness audit: handoffs/active/context-and-token-economy.md (read-only, 2026-11-09)

Orchestrator HEAD 98221350 (2026-11-08); llama tree ffc1bac82. Index state says open=47; raw count of `[ ]` is 49 (46 top-level + 3 indented children). Legend: SV=STILL-VALID, SP=STALE-PREMISE, AD=ALREADY-DONE, US=UNDERSPECIFIED, NA=NEEDS-AUTOPILOT-RUN, DH=DOABLE-DURING-HOLD. "INF" = needs inference/quiet host but NOT Autopilot (the hold does not gate it; a quiet-host window does).

| # | Line | Box | Class | Evidence / note |
|---|---|---|---|---|
| 1 | 23 | TOC-CMP-1 inverted miss detector | AD | Fixed in orchestrator 921f71d1 (2026-07-21); session_summary.py:355-366 uses `seg.granular_blocks` minus stub ids; tests test_session_summary.py:304 (destroyed fires), :322 (preserved does not). The handoff itself ticks the same fix at ~L167. Box is a re-filing. Tick/delete. |
| 2 | 24 | TOC-CMP-2 governance retention probe | SV, US, DH (build) / INF (run) | "5-8 EPYC rules" and "Appendix D v4 rubric" are not defined or linked in the file. Probe harness build is DH; arms are INF. |
| 3 | 25 | TOC-CMP-3 compaction artifact contract | SV, DH (code, flag) / INF (A/B) | No pinned-governance buffer or six-field brief in code (grep). "TOC A/B" arm names unmapped (see drift 3). |
| 4 | 26 | TOC-CMP-4 reproducible A/B pre-registration | SV, US, DH (pre-reg doc) | "blocked actions per step" is not a field in toc-mp-ab-design-20261031.md or trajectory_artifact; "FIFO" and "raw tail" arms are not in `context_arm_ab.ARMS`. |
| 5 | 27 | TOC-CMP-5 role-boundary regression test | SV (half-done), DH | ChatML half covered: test_control_token_assemblers.py:297 asserts `build_consolidation_prompt([INJ])` has no control tokens. `[User]:` literal appears nowhere in src; control_tokens.py neutralises ChatML-family tokens only, so the bracket-role case is untested and probably unhandled. "stays a prompt block" assertion absent. |
| 6 | 31 | CF-3c live quality-monitor validation | SV, US | Monitor now persisted via LangGraph projection (30aa952e) but gated off (see #8). Overlaps #7 and #8. "real traffic" has no named source. Not Autopilot-specific: any orchestrator traffic works. |
| 7 | 145 | CF-3c A/B (A0-A3 arms) | SV, INF | Arm letters A0-A3 here collide with CF-AB-1's A0-A7 frame (L116/117/240); implemented arms are different again (drift 3). Frontdoor = Qwen3.6-35B-A3B Q8 :8070 is current. |
| 8 | 173 | Enable decision: role_aware_compaction + helpfulness_scoring in SHADOW | SP | Premise "monitor-only, no behaviour change" is FALSE. session_summary.py:309-340: both flags gate `seg.consolidated = "[Compacted] <first sentence>"` (destroys segment text); the monitor is created only inside that branch. Also the whole branch sits behind `two_level_condensation` (session_summary.py:149-151 returns early); all three are default False/False, none in PRODUCTION_FEATURE_WAVE_OVERRIDES (orchestrator_stack.py:2564). A "shadow" mode needs new code or a three-flag flip that changes behaviour. Operator decision stays, but must be re-posed. |
| 9 | 188 | CF-AM-1 gist extraction compare | US, INF | "one held-out local document/search set" unnamed. |
| 10 | 195 | CF-EI-1 file tiered eviction index | SV, DH | Own [check] (L203): merge into TOC-MP-2 arms if an arm needs it. TOC-MP-2 is ticked; design doc toc-mp-ab-design-20261031.md has no eviction-index arm. By the box's own rule: retire as design-only or file. Pure doc decision. |
| 11 | 225 | Port per-operator context budgets to delegation | US, DH | Offline-first measure of current per-op context is doable; `_maybe_dcp_seed_context` budget not re-verified by me. Cross-link `autopilot-program.md` AP-ME-1 not checked. |
| 12 | 238 | CF-PB-1 plan-boundary trigger | SV, SP (anchor), INF | `len(state.context) > 12000` OR-trigger is now src/graph/compaction.py:223, not :130. |
| 13 | 250 | CF-AKV-0 old tool-result share screen | SV, US | Own 2026-11-01 note: no operational "long loop" definition, metrics unknown. trajectory_artifact writer exists (default off, no artifacts emitted) so no data source yet. |
| 14 | 308 | DCP-6 delegation pre-assembly eval | SV, INF | dcp_j7_ab.py real mode needs `--real --host-quiet-confirmed` and AutoPilot STOPPED (hold satisfies the latter). Prior live A/B: ON 32.6s vs OFF 20.2s, decision=hold. 11-01 telemetry prep (seed duration, top_up_observable=false) is design only: chat_delegation.py:253 has `_maybe_dcp_seed_context`, no duration timing. Telemetry prep is DH. Depends on DCP-12 first. `dcp_pre_assembly` default off. |
| 15 | 315 | DCP-9a Eq.-4 over Claude Code journals | SV, DH | Zero compute. But its sibling DCP-9b was declined as "agent-fleet bookkeeping, not stack question"; same rationale applies to 9a. Decide consistently. |
| 16 | 374 | (Gated) ColBERT KB as prior-decisions source in pre-assembly | SV, gated on DCP-6 | Flag exists (features.py:266). No gate owner named. |
| 17 | 379 | DCP-10 ContextBench zero-decode scoring | SV, DH | Anchor `context_discovery.py:87` is now :96. Scorer prep done (DCP-10-SCORE-PREP). Needs checkouts on raid; raid free 186G vs 150GiB floor. |
| 18 | 382 | DCP-10b Loc-Bench secondary | SV, DH | After #17. |
| 19 | 385 | DCP-12 power prerequisite | SV, INF; harness prep DH | dcp_j7_ab.py lacks correctness labels (11-02 note); no calibration run yet. |
| 20 | 387 | DCP-13 hand-off fidelity (parent) | SP (parent text), INF | Children 13a/13b ticked; the "Residual (open)" prose describes exactly 13a/13b and is stale. Remaining: inference arms (i)-(iii). `fetch_report` is still a real REPL tool (environment.py:543) so the turn-0 break claim at chat_delegation.py:203-220 still holds. |
| 21 | 393 | DCP-15 constraint propagation (report-only) | SV, DH | Evidence file exists: artifacts/noninf-memeval-20261021/dcp14_result.json. Zero inference. |
| 22 | 953 | Step 3 force </think> at budget=0 for hybrid SSM | SP, INF (one request) | Repro is Qwen3.5 2026-04-17. `thinking_budget_fields(0)` returns `{}` BY DESIGN (serving_params.py:511-514), so "budget=0" sends no field and cannot suppress thinking; the semantics, not a server bug, may be the whole story. Needs a one-request probe on :8070 (v10), no Autopilot. Step 4 declined/merged. |
| 23 | 955 | Thread thinking.budget_tokens through ChatRequest per role | SP / AD-in-part | Plumbing exists: ChatRequest.thinking_budget (api/models/requests.py:234), RoutingResult.reasoning_budget (chat_utils.py:92), request-local scope repl_thinking_budget.py, `repl_thinking_budget` flag (features.py:247, default off), per-role easy/hard fields config/models.py:1354. Server field is `thinking_budget_tokens`, not `thinking.budget_tokens`. Remaining is per-role values (needs TB/E curves) and enabling flag. |
| 24 | 1122 | PRB-T4 TALE-EP evaluation | SV, INF | "no server up as of 2026-08-21" stale; r1 failed 10-31 (native cwd); successor queued. Script exists: epyc-inference-research/scripts/benchmark/eval_tale_budget.py. |
| 25 | 1633 | EVL-34 natural-delegation rerun | SV, INF | v8 custody successor prepared 11-02; launcher refuses until "canonical engine and qualification are available" (unspecified). |
| 26 | 1637 | Operator decision: push/PR sub-decision taxonomy branch | AD | Merged to main as 602c44c5 (2026-05-20, "(#1)"), wired in orchestration/repl_memory/episodic_store.py + scripts/memory/backfill_sub_decision.py. Branch `rao-redel-subdecision-taxonomy` and commit 8bf985c no longer exist. Tick. |
| 27 | 1638 | Step 3 conditional substrate replacement | SV, gated on EVL-34 | Gate is "delegation-positive re-test", which EVL-34 has not yielded. |
| 28 | 1699 | Gate depth escalation on expected value | SV | Contract doc docs/design/conditional-depth-gate-contract.md exists; no implementation; threshold needs inference. Implementation behind default-off flag is DH. |
| 29 | 1706 | Evaluate OOLONG adapter | SV, DH (adapter) | Requirements already filed as OOL-1 (ticked [x]): duplicate framing. Readiness audit 11-02 lists missing depth bridge. |
| 30 | 2429 | RC-XLLM-PREFILL-1 native endpoint-prefill smoke | SV, INF/GPU; off-track | Unresolved [check: which production role or lever...] in its own text. Not a context-economy item. |
| 31 | 2505 | RC-CVEC-HOOKS | SV | Verified at ffc1bac82: qwen35.cpp:198, qwen35moe.cpp:221 call build_cvec; qwen4exp.cpp:391 comment only. Remaining: logit-change assertion on live server (INF); assertion code DH. |
| 32 | 2619 | TB-1 per-model budget curve | SV, INF | CAP-04 (11-03): 8k/16k derived cells invalid; fresh generation per budget required. |
| 33 | 2631 | TB-2 single-setting hypothesis | SV, INF | Uncovered until TB-1. |
| 34 | 2635 | TB-3 audit production ceilings | SP (anchor), partly DH | `reasoning_budget` is not a model_registry.yaml role field (only max_tokens_multiplier: 4 and one workaround note at :1583); budgets live in config/models.py:1354-1355. Knees absent so audit half blocked. |
| 35 | 2723 | TB-6-exec-followups (d) kv_bytes/token | SV, DH | GGUF-header computation is zero inference; :8083 Qwen3.8-27B Q8 + DFlash2 recipe. |
| 36 | 2724 | TB-6-exec (c) A2/CPU np x ctx | SP (title), INF | Title still says 122B-Q4 (deprecated, retargeted 10-28 to Qwen3.8-Flash-Next); handed to CPU lineage. |
| 37 | 2729 | TB-6 concurrency-aware admission | SV, US | Joint scheduler spec is prose; no code. |
| 38 | 2756 | TB-6-ROUTER | SP (gate) | "GATED on GPU joining orchestration" but E-4 text (L2864) says architect_critic = Qwen3.8-27B Q8 on :8083 (GPU). Gate premise looks already met; re-verify. |
| 39 | 2831 | RP-3 loop on architect workload | SP | Own [check]: loop is the deprecated 122B (RP-4/RP-5 closed OBSOLETE 10-29). Retire unless a served model is named. |
| 40 | 2846 | E-2 effort curve per model | SV, INF | Coverage list names gemma worker and Qwen3-Next-80B ingest; verify against current lineup. Absorbs E-3. |
| 41 | 2859 | E-4 per-role defaults | SV, blocked on E-2 | Stale 122B note already corrected inline. |
| 42 | 2905 | E-6b budget-cap retest on olympiad | SP (anchor), INF | `run_budget.sh` is not in git (only architect_bench_gpu_budget.sh); anchor rot. |
| 43 | 3398 | First-party verbatim-log A/B | SV, INF | Prereqs landed: context_arm_ab.py (arms summary_only/summary_pointer/pointer_only/prune_pointer/full_history), trajectory_artifact.py, flags default off. Overlaps #3, #4, #7, #47. |
| 44 | 3494 | TOC-SP-3 verified-quote receipt | SP (anchor) | `_spill_output` now environment.py:907, not :746-838. R7 screen (ticked 11-05): VQ 0.8204 >= control 0.7663; parent has no stated closing decision. |
| 45 | 3504 | TOC-SP-3-EXP09-R3 expand screen | AD (superseded) | R7-SCREEN (ticked, rc0, 24 logs x 4 arms = 96 cells) is exactly R3's design completed after R4-R6 disk stops. Tick or fold. |
| 46 | 3551 | TOC-SP-5 gates on per-turn corpus | SV, NA-ish | Waits on the first A/B run emitting trajectory artifacts (writer default off). Not Autopilot per se; needs any instrumented run. |
| 47 | 3584 | TOC-MP-4 needle screen | SV, INF; fixture DH | Prereqs TOC-MP-1/2/2i ticked. 20-task fixture build is DH. |
| 48 | 3592 | CTX-HO-1 amend A6 | SV, US, DH | See findings 1-3. |
| 49 | 3594 | CTX-HO-3 resume_state in /log envelope | SV, US, DH | scripts/coordination/worker_checkpoint.py: no `resume_state`; `_receipt_validation` (L483) already captures command/exit_code/evidence; bus payload built in `_bus_envelope` L579. "remaining uncertainty" and "rollback note" have no input flag. |

## Counts (a box may carry two tags; primary class)
AD 4 (TOC-CMP-1, taxonomy PR, R3, plus #23 partial) ; SP 10 ; SV with gaps ~29 ; NA (truly Autopilot) 0 ; US as secondary 10.
Primary: AD 3 (+1 partial), SP 9, UNDERSPECIFIED 4, STILL-VALID 33, NEEDS-AUTOPILOT-RUN 0.

## Drift not mentioned in the handoff
1. Fold broke ownership text: header says parent index lists two indices (routing-and-optimization + research-evaluation); only routing-and-optimization-index.md RTG-08 (and master) reference it. Header Status/Updated dates (2026-06-13/07-14) are stale; tool-output-compression.md now lives only in completed/ yet toc-mp-ab-design-20261031.md names `handoffs/active/tool-output-compression.md` as owner.
2. Arm taxonomy: CF-AB-1 A0-A7, CF-3c A/B A0-A3, TOC-MP-2 arms 1-5 and implemented `context_arm_ab.ARMS` are four different sets with no mapping table.
3. Index row NEXT ACTION CTX-HO-1/3 is the only P2 harness-intake work in this file; CTX-HO-2 lives in coordination-and-churn-pipeline.md (RI-12), fine.
4. Disk: raid 186G free against a 150GiB long-run floor; three EXP-09 resumes died on it; no disk-aware admission hold.
5. Duplicates: TOC-CMP-1 = ticked L167 fix; CF-3c validation (#6) = Enable decision (#8) = A/B (#7); A6 defined twice (L117 addendum and L240 CF-AB-2); OOLONG box = OOL-1; R3 = R7; Step 4 declined into Step 3.

## Autopilot dependencies
None of the 49 boxes needs an Autopilot run. dcp_j7_ab.py's only Autopilot coupling is that it refuses to run while Autopilot is up (autopilot_core, no change affecting it found; I did not read the A/B harness beyond its docstring and `_autopilot_pids`). L163 "validating telemetry moves requires agent traffic (autopilot)" is wrong in its own next clause: any orchestrator traffic suffices.

## Could not verify
Per-operator budget claim (#11); that TB-6-ROUTER gate is met; ingest/worker lineup in E-2; whether `[User]:` is unhandled in other sinks; Autopilot harness paths (autopilot_core) vs the handoff's assumptions; live flag state in the running API (runtime_flags.json is gitignored live state, not read).
