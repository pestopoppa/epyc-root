# 2026-10-01 — workspace-8d (per-task wrap-up: RI-16 and TD-29.K2)

## The pause lane

workspace-76 announced a DS41 pause at 2026-10-01 02:58Z (`/mnt/raid0/llm/tmp/sequencer-8d/DS41_PAUSE_ANNOUNCED.json`,
expected end ~10:45Z). DS41 was stopped with its watchdog held while their 27B harness replays ran on :8083.
Conditions: :8083 is not stopped; RI-18 sends at most one concurrent request to :8083; TD-29 stays on cores
`48-71,80-87` and off `72-79`, where the 27B's host threads decode. This session's CPU work ran in the lane
`sequencer-8d/run_cpu_lane_pause.sh`, admitted through `window_gate.py --allow-announced-pause`, and serialized by
`ws8d-jobs.lock`.

## RI-16: routing-decision latency on live `/chat` (complete)

- Code: orch `78847544`, deployed 2026-09-30 04:52Z.
- Data: 30 live `/chat` requests from ~03:06Z. Request set `/mnt/raid0/llm/tmp/ri16/ri16_load.py`; results
  `/mnt/raid0/llm/tmp/ri16/load-20260930/results.jsonl`.
- Reader, re-run for this wrap-up:
  `python3 scripts/analysis/routing_stage_latency.py --since 2026-10-01T03:00:00Z --path all` (orchestrator).

| stage | p50 ms | p95 ms |
|---|---|---|
| priors | 156 | 275 |
| route | 197 | 529 |
| xmas | 26 | 96 |
| factual_risk | 0.06 | 85 |
| route_total | 542 | 1027 |
| mode | 58 | 69 |
| review_gate | 69 | 105 |
| total | 622 | 1159 |

n=30; all chat path. Routing costs ~0.6 s at p50 and ~1.2 s at p95 before generation starts. That is comparable to
typed routing's 590 ms median.

Caveats:
- n=30, from one session.
- The GPU was busy with the replays.
- The CPU was quiet with DS41 paused, but production frontdoor shares cores 0-95.

Derived actionables:
- `priors` is the MemRL `ClassificationRetriever` path, and RI-19 found it has 0 memories. RI-19 gains a measured
  value (~156 ms p50) and a concrete next step: set `use_memrl: false`, re-run the set, then delete the branch.
- Filed RI-24: cut the `route` stage cost. Count the prompt embeddings per request, compute the embedding once, and
  re-measure.
- RI-17 (rules-only vs live routing) is unchanged. It decides whether the KNN layer stays at all.
- Belief kernel: the VB-ROUTE-LAT write side holds these 30 records. The adapter is still owed (existing task).

## TD-29.K2: native vs JSON vs free-form on the champion sidecar (complete)

Run `/mnt/raid0/llm/tmp/champion-sidecar/runs/td-20260930-p32/`, 03:08-03:15Z.
- Pause profile: cpuset `48-71,80-87`, 32 threads.
- Champion: `cpu-20260925-90c12df42`.
- Model: frontdoor Qwen3.6-35B-A3B Q8 with MTP.
- Cases: the 18 TD-4 cases.

| arm | exact | decode tokens | calls | wall | vs free-form |
|---|---|---|---|---|---|
| native id_only (K1 single-token keys) | 18/18 | 564 | 18 | 49.6 s | 1.45x |
| JSON | 18/18 | 9,870 | 18 | 265.3 s | 7.76x |
| free-form | 18/18 | 805 | 18 | 34.2 s | 1.0x |

- K1 lifted native from 12/18 to 18/18. `native_keys` is present on all six `file_ticket` cases.
- Native is 5.3x faster than JSON, with 17.5x fewer decode tokens.
- Free-form is 18/18 on frontdoor, against TD-4's 6/18 on the gemma worker. Closed-set accuracy gains depend on the
  model; on frontdoor the gain is robustness only.
- Native costs 1.45x free-form wall. Prefill dominates (native `prompt_ms` 24.96 s vs `gen_ms` 19.31 s), so TD-29.M4
  (prefix-cache reuse) is next.

Follow-ups:
- TD-29.M0 ticked: the instrumentation produced the per-call accounting. Gap found: `prompt_n`/`cache_n` are `None` in
  every arm, and the streamed arms report `prompt_ms` 0.0. Prompt-token fields are set only when a `chat_payload` is
  present (`inference.py:1359-1367`), and frontdoor runs on raw `/completion`. Filed as TD-29.M0a, a prerequisite of
  M4.
- M2/M3 decision note (in the handoff): both stay. Free-form passing on frontdoor makes validate-first more
  attractive, since the typed call is pure overhead on the passing share. M2's first input becomes a per-role
  free-form failure rate from shadow receipts.
- TD-29 shadow mode remains open.

## RI-18 status (read-only; the run is live)

`/mnt/raid0/llm/tmp/ri18/run-v1/segments.jsonl`, first pass:
- `answer` hit its 5400 s budget at 366 of 453 S1 items.
- `verdict` hit its budget at 358 items.
- `noise-verdict` completed (32 items).
- `revise` has been running on CPU since 05:51Z (item 191 of 274 at ~06:12Z).

A resume pass, `sequencer-8d/run_ri18_resume_pause.sh`, then covers the remaining S1 items and S2 (155), followed by
verdict, revise, noise-revise and `gate`. `score` follows, run by the main session.

## GPU A/B

Pending. It waits for workspace-76's "done" after their replays and two orchestrator-REPL calls.

## Changes

| Repo | File | Change |
|---|---|---|
| epyc-root | `handoffs/active/routing-intelligence.md` | RI-16 ticked with the table; RI-19 measured value and next step; RI-24 filed; RI-18 run status |
| epyc-root | `handoffs/active/typed-decision-plane.md` | TD-29.K2 and TD-29.M0 ticked; TD-29.M0a filed; M2/M3 decision note; Start here refreshed |
| epyc-root | `progress/2026-10/2026-10-01-workspace-8d.md` | this note |

## UFH-12: context.search landed as an opt-in arm (handoff update)

- `context.search` is on orch main `b384cdbb` (series `d02942f7`..`b384cdbb`, golden field-off test `5cae6c6b`), reviewed
  by this session. Opt-in per request via `ChatRequest.context_search`; it returns pointers, its accounting is a separate
  `context_pulls.search` block, and with the field off the surfaces are byte-identical to `08edc054`.
- `repl-embedding-retrieval.md`: ticked REPL-EMB-1.1 (`4f534f95`, `cc808487`; hermetic tests `002b6fc4`, `1fe1d5f8`)
  and the minimal REPL-EMB-1.2/1.3. REPL-EMB-1.4 stays frozen, now carrying the post-cap G1 (0.921/0.918/0.862 < 0.95).
  REPL-EMB-4.1 stays open with a landing note. Filed REPL-EMB-4.4, the deploy step for DS41-C100's `orsv` arm.
- Defaults are unchanged: the REPL-EMB-2.1 kill rule governs any default, and 2.2 is still next.

## V6R-4d.1 / V6R-4d.2: champion HIP build validated on GPU, SW-9 exercised (PASS)

- Ran 2026-10-01 12:14 to 12:16:40Z in workspace-76's DS41 pause, on the production Qwen3.8-27B Q8_0 with its MTP draft.
  The MI210 device lock was held for the A/B only.
- Builds: P = v10 `kernels/production/gpu` (`gpu-20260921-ffc1bac82`, b10303); C = champion
  `kernels/builds/gpu-20260929-90c12df42` (b10308).
- Arms: P C P on :8197, `-t 8` on cores 72-79, membind 3. Every arm was checked for KFD VRAM residency, its own
  libggml-hip mapped, placement, and `/props` build_info.
- pp/tg tok/s: P 886.9/39.01, C 884.4/38.83, P 875.1/39.00.
- RESULT: `PASS=True; identity C==P True; P-self True; pp_tps_median +0.39% (floor 2.00%); tg_tps_median -0.46% (floor
  2.00%); sw9_C_all_probs=True; sw9_P_gap=True`.
- Restore: production :8083 relaunched on v10 (PID 1677674, slot dir `architect_critic`), /health ok.
- Evidence: `/mnt/raid0/llm/tmp/gpu-champion-ab/runs/w8083-20261001T121346Z/` (`result.json` sha256 `ef3b32b7…5821`);
  log `/mnt/raid0/llm/tmp/gpu-champion-ab/run_27b_ab_lockonly.log`.
- V6R-4d.1 (the vision-window variant) is ticked as covered: the production-27B A/B is a superset of it.
- The parent V6R-4d is ticked.
- What this means for v11: the champion's GPU side is no-regression with the SW-9 fix in. A candidate from a descendant
  tip, such as the DS41-C68 fold, reruns the A/B on its own full GPU build. This is recorded under V6R-4a.
- Derived actionable declined: "add the vision model (:8086) to a future GPU A/B".
  - The champion changes no ggml-hip source.
  - The mtmd/clip path does not use the changed loader.
  - The v11 promotion gate covers all serving roles on the full candidate.
  - A separate vision window would displace a production server and test nothing that is at risk.

| Repo | File | Change |
|---|---|---|
| epyc-root | `handoffs/active/autokernel-champion-aggregate.md` | V6R-4d, V6R-4d.1 and V6R-4d.2 ticked; Start-here row removed; v11 line under V6R-4a |
| epyc-root | `handoffs/active/speculative-decoding-mtp-refresh.md` | SW-9 exercised on GPU (header and SW-9 item) |
| epyc-root | `handoffs/active/thesis-experiment-orchestrator-vs-strongest-model.md` | ARCHSWAP-4: :8083 relaunched again 2026-10-01 12:16Z |

## INF-78 OAB-35: the `context.get(name, '')` HTTP 500 (fixed and deployed)

- Orch `2d97ade2` on main (parent `b384cdbb`). API-only reload ~13:10Z, PID 1767532.
- Root cause: models write the dict idiom `context.get('inbox', '')`. `ContextBundle.get(path, max_chars=None,
  offset=0)` read `''` as `max_chars`, and `_page_bounds` raised a ValueError from `int('')`. The model repeated the
  line for 6 turns, escalated to `coder_escalation` (same failure), retries ran out, and the API returned HTTP 500.
- Live since OAB-7 (`88e22777`). It hit workspace-76's DS41-C95 `orv`/`orsv` arms (`orch:architect_critic`,
  orchestrator-variable mode); evidence `/mnt/raid0/llm/tmp/repl_tap.log` 12:11-12:12Z.
- Fix: a dict-style default (`get(name, default)` or `default=`); paging unchanged for numeric `max_chars`; a
  TypeError naming the signature for a bad `max_chars`; `context.get('missing', None)` still raises a KeyError that
  lists the sections.
- Tests: a regression test that reproduces the crash on the old code; oab7 68/68; a targeted set of 785 passed. One
  CPU-starved timing witness failed in that set and passed 10/10 when rerun on its own.
- Derived actionable filed: OAB-36, document `context.get(name, default)` in the root block, landing between C95 arm
  pairs because it changes the prompt bytes.

## UFH-12 REPL-EMB-4.4: context.search deployed for `orsv` (complete)

- API-only reload at 12:22Z onto `b384cdbb` (PID 1690649), then a runtime `POST /config {"repl_embedding_pool": true}`,
  read back as true.
- The 13:10Z reload for OAB-35 reset the pool to OFF, its default. workspace-76 rescheduled `orv`/`orsv` for a later
  DS41 pause, and will ask workspace-8d to re-enable the pool at runtime first.
- Pin or reset is decided: the flag stays OFF by default per the REPL-EMB-2.1 kill rule, and is enabled at runtime only
  for the experiment arm.

## RI-18 status (not complete)

- All 608 answers, `verdict`, `noise-verdict`, `noise-revise` (pinned) and `gate` are done.
- The gate never fired on the 579 scored items. avg_q ≈ 1.0 against the 0.6 threshold, which matches the structural
  finding that the KNN cannot see Q < 0.3 failures.
- The 90 final revisions were VOIDED by the driver ("code_root commit drifted during the segment"). This session's
  12:22Z fast-forward of the shared orchestrator clone for UFH-12 caused it. The integrity check worked as designed.
  Incident: `INC-20261001-shared-clone-drift-voided-ri18-revise`.
- The redo runs with `--code-root` pinned to `/mnt/raid0/llm/worktrees/orch-ri18-pin-08edc054`, in normal DS41
  windows, and `score` runs automatically after it.
- INTERIM, not a verdict: a `score` attempt before the redo returned VOID (clause 0, revise missing 90). AUROC of Q
  against wrong answers 0.56 [0.51, 0.62]; π1 net per 100 −36.8 [−41.5, −32.3].
- Filed RI-18a (the driver's `--retriever` default `graph` does not mirror production's fallback to
  `TwoPhaseRetriever`; this gate ran with `--retriever two_phase`) and RI-18b (the wrappers must read segment
  `end`/`void` events rather than the process rc).

| Repo | File | Change |
|---|---|---|
| epyc-root | `handoffs/active/autokernel-orchestrator-actor-backend.md` | OAB-35 ticked (the `context.get` fix); OAB-36 filed; status line |
| epyc-root | `handoffs/active/repl-embedding-retrieval.md` | REPL-EMB-4.4 ticked; pin-or-reset decided (OFF by default) |
| epyc-root | `handoffs/active/routing-intelligence.md` | RI-18 status (void, pinned redo, interim score); RI-18a and RI-18b filed |
| epyc-root | `docs/reference/agent-config/INCIDENT_LOG.md` | `INC-20261001-shared-clone-drift-voided-ri18-revise` |
| epyc-root | `progress/2026-10/2026-10-01-workspace-8d.md` | these sections |
