# 2026-09-24 — non-inference Tier-2 tasks (ad-hoc, operator-spawned; no roster lane)

Operator asked for the seven remaining Tier-2 items from the 2026-09-23 survey, same mode: parallel
subagents on their own worktrees (smallest adequate model: Haiku for EVL-42, Sonnet otherwise), every
result reviewed and re-tested on the main thread before landing. No inference. Handoff/index edits from
a private landing worktree (`noninf/landing-20260924`), not the shared index.

| Item | Result | Evidence |
|---|---|---|
| EVL-42 1d | Research `test` extra pins `pytest==9.1.1`; README installs it into a gitignored `.venv-test`; 4 scorer suites, 52 pass | research `6cf4a076`..`cbb12fc7` |
| RTG-51 (e2e test) | Already fixed by `40034bf1` (2026-09-16) — test hard-coded the fixture day; box was never ticked. 14/14, 20/20 reruns | — |
| RTG-16 | Root cause: `real_suite_v1_eval_20260706T192007Z` was a total-outage run (50/50 errors: 12 circuit-open :8070, 38 no-progress nudges) pooled as wrong answers by `eval_suite_discriminability.py`. Fixed: errors leave flip/run-spread; re-score on the real pair clears `run_unstable`/`brittle`; MDE 0.267 unchanged (the de-saturation half needs inference) | orch `8a829233` |
| RTG-21 / MF-VBS-1 | Verification never happens in the BEP harness: 0/38 edited trajectories execute anything; 15/15 voluntary stops edit-without-verify. Caveats: one day/role, rider never asks, only t1 stops voluntarily. Verdict: build the gate → MF-VBS-2 filed | orch `86471b1f` |
| UFH-07 | Telemetry isn't broken — the tool has 0 calls in 1,092 transcripts (no agent file points at it). Write path verified end-to-end. Decision → OP-49 | — |
| INF-41 S-11/S-12/S-13 | Research master: `tts_server` (qwentts.cpp, pin `2c1b5182e` — `abab6b3b` in the task text is its pre-ratification parent; the task's GGUF pair was a Path-A leftover) and `voice_server` recording the GPU whisper.cpp service already live since 08-02. S-13 guard in `verify_speech_kernels.sh` + research `verify_qwentts_pin_isolation.sh`. Orch derived artifacts recompiled (provenance hash only) | research `53418b84`..`e485008a`; orch `f323fa01`; root (this landing) |
| INF-41 S-11a | Capacity-gate fold of the 4.68 GiB PREPARED only (`artifacts/operator/inf41-capacity-gate-aux-vram-20260924.patch`): needs a signature (margin 5.85→1.17 GiB) and a fresh contention matrix (stale since 08-23; blocks every `stack_manifest.py` commit; refresh = live bench) → OP-48 | — |
| RTG-09 | Duration axis implemented and wired at all 3 call sites, landed DEFAULT-OFF (live reward byte-identical) because a reward change is a `routing_reward` era boundary; ratification script flips 0.20/0.05 + era E18 → OP-47 | orch `b8035db9`, `88e24ef0`; root ratify script |
| Found in passing | 3 stale q_scorer tests + a real leak: the host-only alias `worker` surfaced as its own scoring role via stack priors → `_NON_SCORING_HOST_ALIASES`; `test_q_scorer.py` 78/78 | orch `42e304ac` |

## Corrections made in main-thread review
- EVL-42: README claimed the whole `scripts/benchmark/` glob runs — it has 4 collection errors; scoped to the 4 suites. Report's per-file counts were wrong (total right).
- RTG-09: first version flipped the live reward with no era boundary → reworked default-off + ratification.
- INF-41: a nested `fork` of the subagent committed unrequested registry work (see memory `feedback_fork_status_checks_can_go_rogue_and_write`); registry comments claimed the gate fix was "CLOSED"/live when it was only prepared → corrected in `e485008a`. Root guard walked the whole llama.cpp tree at every session init → direct existence tests.
- RTG-21: re-checked the "0 executions" claim against in-REPL verification (imports/asserts after the write): 0/14.

## Belief kernel
Source rows + tasks filed: VB-MFVBS-1 (verify-before-stop), VB-EVALDISC-1 (discriminability audit; pre-`8a829233` instability flags inadmissible where a run was error-dominated).

## Open, not blocked on this session
OP-47 (RTG-09 ratify), OP-48 (S-11a signature + contention-matrix bench), OP-49 (compressor telemetry path).
This session had no lane: all root edits went through the private landing worktree; shared clones were only fast-forwarded (a peer's staged `src/typed_decisions/native.py` in the orchestrator clone was left untouched).
