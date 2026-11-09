# EVL-47 staleness audit (vidya-belief-substrate-program.md), 2026-11-09, read-only

Classes: SV = STILL-VALID (trigger unmet, text accurate); STALE = STALE-PREMISE; DONE = ALREADY-DONE (code proves it); UNDER = UNDERSPECIFIED; NAR = NEEDS-AUTOPILOT-RUN (truly waits on the hold); DOABLE = DOABLE-DURING-HOLD.
Extra tag WPR = waits on a NON-Autopilot producer run (inference row / AK hold / live API); the hold does not block it, the missing run does. Many WPR boxes are "write side before the run": where the writer is code, that part is DOABLE.
Line numbers are handoff lines (hint only; task text is identity). 89 open boxes (grep of `- [ ]`).

## A. Autopilot / planner tie-in boxes

Call path VERIFIED (code): orchestrator `scripts/autopilot/autopilot.py:9513` `_loop_beliefs.prepare()` (runs before every planner turn, mandatory) -> `loop_beliefs_bridge.prepare` (subprocess of ROOT `scripts/vidya/loop_beliefs.py`, default root `/mnt/raid0/llm/views/epyc-root-main`, which is at current HEAD a69312d5b) -> `planner_coordinator.plan_with_providers(belief_context=...)` (requires sealed ReadyBeliefs, :338-346) -> prompt block autopilot.py:6404; `vidya_planner_bridge` settled-ground/kvq blocks at autopilot.py:9913/9953. Targets come from compiled priors (`role_targets` -> `stack_priors.live_stack_role_records`), not the running stack, so they resolve with the stack down.
Live evidence of use: canonical `/mnt/raid0/llm/state/vidya/reads.jsonl` = 28 reads, 0 with consumer `autopilot.planner` (17 AK empty-target, 10 AK non-empty, 1 ws58 verify). So the AutoPilot read path has never run live. Journal `orchestration/autopilot_journal_1.jsonl`: 507 rows, last 2026-08-09T19:29:35Z, 0 `measurement_tuple`, 0 rows after fence 2026-08-10T16:23Z.

| Box (line) | Exists today | Planner calls it? | Canary | Remaining | Class |
|---|---|---|---|---|---|
| VB-AP-FIRST-CYCLE (203) | `adapters/autopilot_journal.py` + `cli ingest autopilot-journal`; mhs_guard adapters | yes (via bridge, untested live) | none for AP-live | Steps 1-4 need first post-restart cycle. Step 3 premise STALE: `sub/gate-frontier-20260916` producer is on orchestrator main (commit af7ee295 is ancestor of origin/main) as `scripts/autopilot/eval_leakage_monitor.py` (LEDGER_EVENT_TYPE `eval_leakage_guard`); the file named `eval_leakage_guard.py` never exists. `mhs_guard.HOOK_SINCE` still unset. | NAR + STALE (step 3) |
| VB-AP-SPINUP-AP3-SCOPED (3707) | scoped value pinned `start_authority_daemon.py:133`, required at `autopilot.py:524` | n/a | n/a | Daemon start. Prechecks stale: clone now 3 behind origin/main (94af001d) with dirty `orchestration/model_registry.yaml` (+24/-10), not the 50be5797/instrument_eras.yaml state the box cites; embedders :8090-8095 down. Read-only strategy-store/drift checks are DOABLE now. | NAR (prechecks DOABLE) |
| VB-CANARY-B-FRONTIER (4016) | canary_b.py (frontier section assembled, T1 count 0, no per-trial assertion) | canary replays the pre-planner path by hand (calls `lb.prepare`, not `plan_with_providers`); its cited autopilot.py anchors (8797-8806, 9083-9136, 9138-9195) have rotted (belief block now ~9513) | B = UNKNOWN by design (hash embedder); live-embedder row `vb-canary-b-r2-20261107` published, NO filing exists after 11-04 | Trigger needs a real journal row ts>2026-08-10T16:23Z with `pareto_status=frontier` AND non-excluded `keep_revert_decision`. That means a full AutoPilot trial incl. eval inference, plus the stack/embedder up. | NAR (assertion + control DOABLE) |
| SC14-B (634) | `gate.evaluate` exists | not verified | none | Blocked on FIRST-CYCLE; needs first CANDIDATE->BASELINE promotion. | NAR |
| VB-AP70-ROTATION-READ (1562) | strict reader `read_rotation_study`/`emit_rotation` autopilot_journal.py:682/864 (3c4cf1050 verified) | no cli ingest entry (grep `rotation` in cli.py/ingest_sources.py = 0), no README row | none | Observer must write first rotation set; cli entry + README row + canary after. Offline: could add cli/README now. | NAR (cli/README slice DOABLE) |
| VB-REFOCUS-NONEMPTY-READ-PROOF (3703) | AK one-shot 2026-11-08 `/mnt/raid0/llm/tmp/ak-planner-proof-20261108` (read non-empty, usable 16, planner abstained; tracked as AK-PLANNER-RELIANCE-PROOF in autokernel-loop.md:5743, not mentioned here) | AP side never run | n/a | Needs a planner turn that CITES claims. AP half needs a live planner turn = operator exception to the hold (dry-run turn) or hold lift. | NAR (AK half retryable) |
| VB-LOOP-TEXT (3704) | device-scope group implemented (a39e3140e verified); `p1_acceptance` PASS per b2d3c598c (AC9 amended, option B) | n/a | AC1-AC9 | Box text still says AC9 FAIL / AC7 needs --before: STALE. Remaining: two-CPU-model smoke. The 10-21 smoke ran `prepare` without a daemon, so this does NOT need Autopilot running; handoff P1-PHASE2/LAND notes saying it waits on stack restart look wrong. | STALE + DOABLE |
| VB-REFOCUS-TRIAL-REMINDER (3717) | script + run-loop.sh exist | n/a | n/a | No reminder process is running (ps) and the log's last write is 2026-10-26; it died (reboot). Trial premise (both loops live 7 days by 2026-11-23, eval 11-30) conflicts with Autopilot hold and OP-AK-HOLD (reconfirmed 11-09); critical daily nags start 11-23. Needs an operator decision on the trial date (single named decision). | STALE |
| P1-PHASE2 (3747) | built per box | n/a | n/a | Open on (1) `autopilot_journal` applicability live proof (needs a post-AP-55 journal trial) and (2) DS41 floor (VB-DSV41). | NAR |
| VB-PARK-AUTOPILOT-DIAG (215) | members: VB-MHS-GATES, JUDGE-EXPOSURE-WIRE (README row l.159 exists), RRR-READOUT, AP66-TABLE-REPLAY-WIRE | n/a | n/a | Trigger "autopilot-safety merges" is already met (af7ee295 + 753343f5 on main). Re-triage members. | STALE |
| USAGE-PROV-1 (157) | writer+reader published | no loop reads cost | none | Needs a live API call site with non-null declaration (API, not Autopilot). | WPR (stack down) |
| VB-INF50-DRAFT-WIDTH (2241) | none | n/a | DONE-WHEN needs "AutoPilot canary for the frontdoor role" but canary B has no per-role mode | Clarify what canary variant proves a role-specific claim. | UNDER |
| VB-KVQ-V10-INGEST (1908) | AP planner kvq context wired 2026-09-25 (`_build_vidya_kvq_context` autopilot.py:9913) | yes | n/a | First complete post-hook 12-row sweep. | WPR |
| FROZEN TD-ADVICE (2308), SEL-LOADAB (2324), DISPATCH-S2 (2466) | none | n/a | n/a | Freeze text "v11 promoted / autopilot trained on swapped stack" is a future event; consistent with hold. | SV (frozen) |

### What VB-CANARY-B-FRONTIER waits for, precisely
Needs one journal row after 2026-08-10T16:23Z (epoch fence `pareto_exclude_before_ts`) with `pareto_status=frontier` and a `keep_revert_decision` other than `excluded`. Frontier is currently empty (T1 count 0), so the first admitted trial qualifies. That requires the daemon running trials with evaluation inference. Fixtures, the assertion code and a negative/positive control can proceed during the hold: build a scratch journal shard copy with one SYNTHETIC post-fence frontier keep (labelled control, in `CANARY_SCRATCH`, never in orchestrator journal or ledger), assert id+numbers appear in the assembled prompt, and make the assertion report "not exercised" (not FAIL) when no real qualifying row exists. Pre-hold journals: 0 rows carry a tuple; adapter skips tuple-less rows by design (autopilot_journal.py docstring), 1505 trials are pre-hook and ineligible as measurements; trial 1472 is `excluded`, pre-fence. Permitted: committed-conclusion observation (Judged/Located, `cli conclusion add` through the register, no run_id, no protocol), strategy-store/insight channels already read, offline tooling replays on scratch ledger copies recorded as tooling, not measurement. Not permitted: backfilling tuples, ingest of old trials as measurement.

## B. Box-by-box (all 89)
Format: line | ID | class | note

17 | VB-Q38P4-PARITY-WIRE | UNDER | no Q38P-4 producer exists; no pointer to the owning handoff
19 | VB-MI210-PAIRED-DIAG-WIRE | WPR | 11-05 outputs pre-hook; next NPD1/Q38P ABBA must emit sealed declaration (writer change DOABLE)
91 | VB-CH18-MERGE-TRIAL-WIRE | WPR | adapter `ch18_merge_trial.py` + `ingest ch18-merge-trial` verified registered; waits next merge trial (code part DONE)
93 | VB-EXP01-PROXY-WIRE | DOABLE | writer + refusal control before next EXP-01 run; no cli/ingest name yet
97 | VB-KVU19A2-WIRE | WPR | `kvu19a2_native` registered; needs its 20-launch sidecar
120 | VB-KVU-16A-LOAD | DOABLE | ingested 11-07 refused=0; remaining is canary ranking/scope fix (reader code, no run)
137 | VB-AK-R18D-AA-WIRE | STALE+DOABLE | box says row unpublished; `/mnt/raid0/llm/tmp/vb-r18d-aa-wire-20261104/out` has COMPLETE + capture jsonl (11-08 01:13) and pipeline-mgmt 11-08 says it finished; file result, register project.py, ingest
141 | VB-AK-R23-4-SWEEP-WIRE | WPR | row stopped rc=75 on 11-08, needs republish after reboot (not "ready for owner publish")
149 | VB-AK-R18-GFX-OBSERVATION | WPR | no GFX record on disk
152 | VB-P5-SCORER-CONTROLS-WIRE | DOABLE | writer must add completion_utc+grant (code); then next control
157 | USAGE-PROV-1 | WPR | see A
203 | VB-AP-FIRST-CYCLE | NAR+STALE | see A
205 | VB-AK-SEAT-FINISH | DOABLE | member code items (b2, b1w, b1x, METRICS-1, CTX-1, DS41-OPS) are code; then one fresh campaign file
206 | VB-PARK-HARNESS-EVAL | SV | parked, trigger unmet
207 | VB-PARK-INTAKE-SWEEPS | SV | parked
208 | VB-SR8-DRAFT-ACCEPTANCE-WIRE | WPR | nested under parked 207 but a live row (SR-8)
209 | VB-PARK-OCR | SV | parked
210 | VB-PARK-AK-DIAG | SV | parked; AK hold
212 | VB-PARK-SPEECH | SV | parked
213 | VB-PARK-SECURITY-DTAP | SV | parked; dtap-finance-pair adapter landed 616daaa7f
215 | VB-PARK-AUTOPILOT-DIAG | STALE | see A
305 | SC21 | SV | parked; last run 2026-08-24
385 | SC12 | WPR | first completed post-hook K35 run or next promotion package
634 | SC14-B | NAR | see A
679 | SC18 | WPR | needs RVP-C2-2 layer on llama.cpp-experimental
708 | elementwise UNSUPPORTED follow-up | STALE | compares against "current C5"; champion is C9 now; no owner id, no artifact path for old run
718 | VB-AK-GPU-CONTROLS | WPR | AK hold
1096 | VB-AK-LEGACY-SERVING-LIVE | WPR | owner-run loop; AK hold
1125 | VB-AK-UNIFIED | WPR | AK hold
1288 | SC81 | WPR | W5s successor run
1368 | VB-DSV41 | WPR | DS41 run
1386 | VB-AK-SERVING-PROFILE-WIRE | WPR | owner-run profile
1562 | VB-AP70-ROTATION-READ | NAR | see A
1675 | SC84a | SV | parked
1827 | SC88 | WPR | first opt-in receipt
1839 | VB-AK-HISTORY | WPR | AK-HR-3 campaign
1871 | VB-AK-HELDOUT | DOABLE | research `9eee67c1` (exists) writes plain JSON; producer self-hash is research code
1908 | VB-KVQ-V10-INGEST | WPR | see A
1987 | VB-ARCH-CPU-QUAL | STALE | "v7 quality-gate family" while production is v10, champion C9; needs a real gate run to fixture against; restate on current gate
2130 | VB-KVU-1 | WPR | next np-ctx-kvu producer
2241 | VB-INF50-DRAFT-WIDTH | UNDER | see A
2242 | CAFE-2 native cost capture | WPR | nested under 2241
2308 | VB-TD-ADVICE | SV | frozen
2324 | VB-SEL-LOADAB | SV | frozen
2333 | VB-SWAP-C | WPR | next HSF run
2372 | VB-INF70-XFER4B-WIRE | WPR | XFER-4b run
2399 | VB-PREFILL-XOVER | WPR | PF1 writer needed before first cell (research code)
2466 | VB-DISPATCH-S2 | SV | frozen
2525 | VB-SERVING-DF2 | WPR | next parity/acceptance run
2526 | SR-8 edit-source lookup capture | WPR | nested
2549 | VB-FA-MASKSKIP | WPR | `kvu19b_gap` landed; needs 27B-target claim
2591 | VB-KVU16H | WPR | VRAM probe
2607 | VB-CPU-FA-VKQ | WPR | RTG-57 run
2707 | VB-KQROUTE-1 | WPR | A/B run
2757 | VB-YARN-E1 | WPR | INF-59 E1 run
2962 | VB-AK-LONGCTX | WPR | INF-81 record
3642 | VB-Q38FN-SERVED-SWEEP-WIRE | WPR | needs driver.py sidecar writer (code DOABLE)
3699 | VB-REFOCUS-PUSH-CORRECTION-FIX | STALE+DOABLE | `2c0c7334b` is on no branch; local `f8/vidya-correction-fix` tip is 7f2df8f61 (1 commit ahead of origin/main, not merged), also pushed as `origin/salvage/root-vidya-correction-fix-20261102`; research/intake_index.yaml +3334 lines may conflict with main; operator Go given 11-02; run cite-check + pending-corrections=0 first
3703 | VB-REFOCUS-NONEMPTY-READ-PROOF | NAR | see A
3704 | VB-LOOP-TEXT | STALE+DOABLE | see A
3707 | VB-AP-SPINUP-AP3-SCOPED | NAR | see A
3717 | VB-REFOCUS-TRIAL-REMINDER | STALE | see A
3734 | VB-AKXALL8-PROCESS-WIRE | WPR | writer upgrade + next run
3747 | P1-PHASE2 | NAR | see A
3924 | VB-FOLDGATE-WRITE | WPR | writer on main (`champion_fold_gate` registered); next gate run
3956 | VB-M4-FOLD-SPEED-WRITE | WPR | `m4_cpu_speed` registered; M4/C5-era wording
3979 | Class-A pilot register fill | DOABLE | register has 24 rows vs 54 gold; confirmation work, no inference
3982 | GPU-prep findings capture | STALE+DOABLE | says no register/CLI exists; register+CLI landed 11-06 (b8a1d1383); checkpoint 42f1d1aac merged (8066bf575 ancestor of HEAD); register has 0 matching rows
3984 | CME-7T conclusion | DOABLE | doc exists; 0 register rows match
4016 | VB-CANARY-B-FRONTIER | NAR | see A
4058 | VB-HARVEST-1022.a | WPR | v11_gate_bench landed; remaining armP/P2, c5-gate-b, kvu19b-p3, hsf-5p (many are projections of existing outputs: partly DOABLE)
4062 | VB-HARVEST-1022.e | DOABLE | five source rows; record layouts not yet inspected
4096 | VB-MOE-RT10-CAPTURE-LINK | WPR | next DS41 routing tap
4115 | VB-UFH12-GS-FROZEN-QUERY | WPR | first frozen-query run
4212 | VB-AK-PM12-LESSON | DOABLE | producer `93c217ec5` exists (verified) but lacks evaluator/protocol + metric fields: research code change
4215 | VB-AK-R22-2-NATIVE-WIRE | WPR | R22-2 run
4217 | VB-AK-R24-9-REPEAT | WPR | adapter extension already done; needs live row (code DONE)
4314 | VB-AK-LOOP-PROCESS-ID-LIVE | WPR | next owner-run loop; AK hold
4335 | VB-G16-GREEDY-WIRE | WPR | next G16 run
4393 | LSA-EVIDENCE-1 | DOABLE | README source-row registration before first screen is documentation
4394 | LSA-BUILD-WIRE | WPR | nested
4395 | LSA-CAPACITY-WIRE | WPR | nested
4396 | S8-C-VALIDATION-WIRE | WPR | nested
4397 | LSA-GNX-VALIDATION-WIRE | WPR | nested
4399 | VB-EXP09-SPILL-WRITE | WPR | successor run
4401 | VB-AK-R23-1-EOF-WIRE | WPR | post-hook EOF run
4403 | VB-KPF50-COUNTERFACTUAL-WIRE | WPR | first RESULT.json; no adapter yet
4405 | VB-KPF17-ORACLE-WIRE | WPR | no adapter yet
4407 | VB-KPF17-MAP-REVALIDATION-WIRE | WPR | no adapter yet

## C. Drift the handoff does not mention
1. Canonical ledger is `/mnt/raid0/llm/state/vidya/ledger.jsonl` (41,109 lines, 11-09); `/workspace/.vidya/ledger.jsonl` (14.7 MB, 11-08) is a scratch copy (ledger_home.py). Handoff cites 30,813-frame era.
2. `state/vidya/reads.jsonl` shows 0 autopilot.planner reads ever.
3. 11-08 AK planner proof (abstained) is not referenced here.
4. Journal "last entry" is 2026-08-09T19:29Z in `autopilot_journal_1.jsonl`; the legacy `autopilot_journal.jsonl` mtime 06-27 is a different file; reminder log says Autopilot last ran 08-11 22:15Z.
5. Index row EVL-47 itself: "GNX-REINDEX-1 receipt" is declined/retired (handoff l.3936); "file r18d/r234 rows" is stale (r18d ran, r234 needs republish).
6. Champion is C9 / kernel work paused; C5/M4/v7/v11 wording in several boxes predates that.
7. Canary B anchors to autopilot.py line numbers that have rotted and re-implements the pre-planner path.
8. Handoff is 4,407 lines with extensive nested superseded text ("declined" bullets, history); a picker-up must read the REFINE 2026-11-03 and trackd 2026-11-07 notes, not the box head.

## D. Not verified
Did not run any CLI/tests (rules), so p1_acceptance PASS, pending-corrections=0, and ingest counts come from the handoff/commit text, not re-run. Did not verify most WPR trigger claims beyond adapter existence in cli/ingest_sources and the 11-07 trackd notes. `ps` showed no reminder or Autopilot process; I did not inspect row/queue state for `vb-canary-b-r2-20261107` beyond absence of a filing.
