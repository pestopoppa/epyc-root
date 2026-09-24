# 2026-09-24 — main-ak-seat (DS41 run 7 halt, autokernel actor-seat repair, planner A/B)

Session window ~09:55–11:40 UTC. Monitoring handover of DS41 AutoKernel run 7 (owning handoff
`handoffs/active/deepseek-v41-flash-evaluation.md`, INF-77; the prior session's log is
`progress/2026-09/2026-09-24-main-dsv41.md`).

## Problem: run 7 lost a complete 27B proposal to two actor-seat defects

Run 7's first 27B planner proposal, `akm-q4k-q82x4-weight-prefetch` (`iqk_gemm_kquants.cpp ::
mul_mat_qX_K_q8_2_X4_T<DequantizerQ4K_AVX2,1>`, a Q4_K weight prefetch), landed in ~39 min (09:16→09:55).
It was thrown away:

1. opencode exited rc=1 after recovering from an error in its own bash tool (`(res.stderr || "").trim is
   not a function`, raised on the planner's `mkdir -p $HOME/...` scratch-dir probes). `_run_agent` discarded
   every rc≠0 reply unread and retried from zero.
2. The retry (10:09:49) returned EMPTY stdout. `_parse_reply` then ran the schema repair over the empty
   report, and the repair invented `replay-verification / src/verify/replay.ts :: replay`. The codex critic
   rejected it, correctly, at 10:10:23 (~30 s).

## Halt

The operator approved halting run 7 to fix the seat and ran `kill -TERM 1791442 2093139`. Neither
`serial_run` nor `run.py` exited, and `run.py` launched a new actor (2130164). The session TERM'd that actor,
then KILL'd 1791453/1791442. All were verified dead and `state-run7/STOPPED.txt` was written.

Root cause, from reading the code afterwards (now DS41-C22): SIGTERM is designed as a drain. Forming lanes
abandon at their next stage boundary. But a planner call IS the stage, and the retry inside the call never
checks `should_stop()`, so a signal-killed actor (rc −15) gets retried as a transient.

## Changes

| Repo | Path | Change |
|---|---|---|
| research (lane `lane/ak-actor-seat-20260924`, `e9495971`, pushed, NOT on main) | `scripts/kernel_rnd/autokernel/loop/actors.py` | rc>0-only salvage of schema-COMPLETE replies; no repair over an empty report (`REPAIR_MIN_REPORT_CHARS`); repaired `target_surface`/`target_symbol` must appear in the report; template-echo objects skipped and refused as abstentions; prompt on STDIN; stdout/stderr captured to files; prompt diet (`_dedupe_subtrees`, `_slim_shared_history`, 95.7k→75.9k chars); `ActorSeat`; `actor-calls.jsonl` |
| research | `loop/actor_opencode_config.py` (new) | per-run opencode config: `tool_output` cap, step cap, read-only scout fan-out; v2 puts guidance in an `instructions` file |
| research | `loop/actor_tools_mcp.py` (new) | output-capped MCP tools (outline, read_range, grep, code_search, profile_top, symbol_annotate); runs under the orchestrator venv, the only venv with `mcp` |
| research | `loop/run.py` | `--actor-seat {bounded,plain}` (default `bounded`), `--actor-fan-out`, `--actor-steps` |
| research | `loop/actor_lifecycle.py` | refuses stdin-prompt backends (the worker stage has no stdin) |
| research | `loop/test_actors.py`, `test_actor_opencode_config.py`, `test_actor_tools_mcp.py` | 167 actor tests; one fixture address is now built at runtime rather than written as a 16-digit literal (the PII pre-commit hook read it as an account number) |
| root | `handoffs/active/deepseek-v41-flash-evaluation.md` | C20 updated (later fixes, bounded-v1 result, lane commit); C20a/C20b ✅, C20c filed; C22, C23 filed; C18 and C10 notes |
| root (earlier, `312595b7`) | DS41 C18/C10/C20/C21, INF-78 `autokernel-orchestrator-actor-backend.md`, repl-turn-efficiency S4-T1/T2, TD-21.33, HS-4 P6/P7 | already landed on main |

Why the three late fixes were needed:
- **Prompt on stdin.** opencode 1.18 re-quotes any positional argument that contains a space. It escaped all
  2,982 quotes in the run-7 prompt, and a ~100 KB prompt also sat close to the 128 KiB `MAX_ARG_STRLEN` limit.
- **Capture to files.** opencode/Bun exits without draining a pipe. The same session export came back as
  65,536 or 98,304 bytes through a pipe and 328,871 bytes through a file. The reply JSON is at the tail, so a
  long run would lose it.
- **Template echo.** opencode's compaction summary quotes the prompt's `{"abstain":"<reason>"}` template.
  The bounded-v1 driver recorded that object as its hypothesis.

## Results

- **Tests:** 167 passed across the five actor suites (re-run at commit time). The full `autokernel/loop`
  suite shows the same 152 failures as the branch point `e485008a`, plus
  `test_gpu_runtime::test_gpu_calibration_actual_http_keeps_both_original_claims_and_device_trace`, which also
  fails intermittently on the baseline. No regression.
- **Planner A/B** (`/mnt/raid0/llm/tmp/ak-seat-ab/driver.py`: same un-escaped, dieted run-7 prompt, 27B on
  :8083, its own detached lane @ `ebb68dc55`):

| Arm | Steps | Tool calls | Decoded tokens | Wall | Compactions | Notes |
|---|---|---|---|---|---|---|
| plain (run-7 export, old prompt) | 71 | 70 (54 bash) | 63.8k | 40.3 min | 2 | 46k-token first context; tool outputs 275k chars total, max 58 KB |
| bounded v1 (agent `prompt` replaces the system prompt) | 12 (stopped) | — | median 1,626/step vs 266 | ~35 min (2180.5 s) | 1 (context full at 97.7k) | tool outputs 42k chars; 0 scouts; one step 19k tokens; no hypothesis (template echo) |
| plain (new prompt) | running since ~11:19 | | | | | PENDING |
| bounded v2 (`instructions` file) | queued | | | | | PENDING |

  What bounded v1 shows: the model's own deliberation fills the context, not tool output. Replacing
  opencode's terse default system prompt made each step ~6x longer. The A/B verdict is still PENDING.
- **Profile check (read-only, for DS41-C23):** the planner's `perf annotate` reported `measurement-record.data
  has no samples!`, but the profile is not empty: 25.7 MB, 114K `cycles:u` samples. The same session's
  `perf report` puts `mul_mat_qX_K_q8_2_X4_T<DequantizerQ4K_AVX2, 1>` at 19.28% of cycles. perf matches
  `--symbol` against the full demangled signature and prints "no samples" when the filter matches nothing.
  libgomp takes ~45% of cycles at unresolved addresses (40.83% + 2.88% + 1.36%). That is consistent with the
  DS41 finding that decode is flat from 24 to 96 threads. No new task was filed for it.

## Derived actionables

| Item | Disposition |
|---|---|
| (a) SIGTERM does not stop `serial_run`/`run.py`, and `run.py` re-launches the dead actor | **filed** DS41-C22 (root cause from the code: drain semantics plus a retry that never checks `should_stop`) |
| (b) planner `perf annotate` "has no samples!" | **filed** DS41-C23. The profile is fine; `symbol_annotate` should resolve short or templated names |
| (c) opencode bash-tool error `(res.stderr || "").trim is not a function` | **declined.** The rc>0 salvage for schema-complete replies (C20) already absorbs its cost. It is a defect in third-party opencode 1.18.31, and posting an upstream report is an external action nobody asked for |
| (d) the research venv lacks pytest | **declined.** `pyproject.toml` already declares a `test` extra pinning `pytest==9.1.1`, the same version system `python3` has. Every suite runs with system `python3` plus the venv's site-packages on `PYTHONPATH` (the command recorded in DS41-C20). Adding the extra to a shared venv would be an environment change on a shared host, not a code gap |
| Record the plain and bounded-v2 arms | **filed** DS41-C20c |
| Heavy-plan/fast-author split | not filed: the operator dropped it |

## Deferred, with named blocker

- **DS41-C20 promotion to research `main`.** Waiting on the A/B result (plain new-prompt arm running,
  bounded v2 queued). The lane commit `e9495971` defaults to `--actor-seat bounded`. If bounded loses,
  acceptance (ii) flips the default to `plain` before the merge.
- **Run 8.** Launches from the merged tree after C20, per C20(iii).

## Follow-ups executed (operator direction via coordinator, ~11:45–12:30 UTC)

The wrap-up's filed items were handed back to this lane to execute. All research code went into a NEW
worktree `/mnt/raid0/llm/tmp/ak-actor-seat-followups-20260924` on branch
`lane/ak-actor-seat-20260924-followups` (off `e9495971`). The A/B worktree was not touched, because the
queued bounded-v2 arm imports from it. The research commit is `1c7d0a2d`, pushed to its lane only; it rides
with the DS41-C20 seat merge and is not on research `main`.

| Item | Result |
|---|---|
| DS41-C22 stop path | ✅ `loop.ActorStopped` added. On stop, the actor's process group gets TERM, then KILL after 15 s. The stop is never retried and is recorded as `stopped_mid_formation`. rc<0 without a stop stays a retried transient (deliberate). 11 tests use real child and grandchild processes. |
| DS41-C23 `symbol_annotate` | ✅ Short or partial names now resolve against the DSO's `perf report --sort symbol` rows. An ambiguous name returns the candidate list. One read-only smoke (3.7 s) against the run-7 profile found perf 6.17's trailing `IPC` columns in those rows; fixed and pinned by a test (the smoke was not repeated). |
| VB-AK-SEAT | Split three ways. **-a ✅** (subagent): ROOT contract `autokernel_actor_seat_capture.py` plus strict reader `autokernel_actor_seat.py`, class `measurement`, no new ladder, every tuple capped at `Judged/Located`; 33 tests. **-b1 ✅**: `actors._record_call` writes `actor_call.v1` using ROOT's writer; end-to-end dry-run ingest gave projected=1, refused=0, rows=2. **-b2 [ ]**: the arm record, which lands with OAB-4's driver revision (the live driver must not be edited, and both of its arms predate `HOOK_SINCE`). |
| DS41 compaction | ✅ (subagent, operator-approved). Active file 783 → ~650 lines. C0–C19 (15 items) moved verbatim to `handoffs/completed/deepseek-v41-flash-evaluation-completed-through-2026-09-24.md`. The open `- [ ]` set is identical before and after (42); the Completed Scope table links the sibling. |

## Seat A/B verdict, merge, run 8 (12:40–13:10Z)

| Arm (27B :8083, same run-7 prompt) | Wall | Steps | Decoded | Compactions | Proposal |
|---|---|---|---|---|---|
| plain, pre-fix (run 7) | 40.3 min | 71 | 63.8k | 2 | valid (discarded by the old defects) |
| **plain, fixed prompt** | **31.9 min** | 23 | 57.7k | 1 | valid |
| bounded v1 (replaced system prompt) | stopped 35 min | 12 | 47.3k | 1 | none |
| bounded v2 (`instructions`) | 44.3 min | 34 | 60.2k | 1 | valid, better grounded |

- Operator chose "merge, default plain". Research main `21ca61b0` = seat `e9495971` + follow-ups `1c7d0a2d` +
  `--actor-seat` default `plain`; 217 actor/champion tests passed. Bounded's deficit is perf-tool time (DS41-C20d).
- No arm used a scout although `task` was offered and allowed; every arm compacted once (append-only context).
  Operator ruling: fan-out is the orchestrator's job, not the harness's → INF-78 OAB-8; REPL-held context → OAB-7.
- TD-21 session (workspace-8d) stacked TD-21.29/30 on `e9495971` (`td21/29-30-actors` @ `c0a00a8b`); told to
  rebase onto `21ca61b0` and land; run 8 does not carry it.
- **Run 8 launched 13:06:55Z** (`state-run8`, pid 3359620), floor 5.097 from the cache. `EPYC_ROOT_REPO` points at
  `/mnt/raid0/llm/worktrees/ak-seat-handoffs-20260924` — keep that worktree while run 8 runs.

## Operator-invoked wrap-up #2 (13:15–13:40Z)

This ran in a fresh lane worktree, `/mnt/raid0/llm/worktrees/ak-seat-wrapup-20260924b`. The ak-seat-handoffs
worktree is frozen because it is run 8's `EPYC_ROOT_REPO`. Run 8 was not touched.

- **Checklist sync.** The segment's ticks (C20, C20c, C21, OAB-0) had already landed in `44836aab`. Nothing was
  left to flip.
- **Derived actionables: 2 filed, 3 declined.**
  - Filed **DS41-C24**: release run 8's `EPYC_ROOT_REPO` pin on a lane worktree before run 9. Point it at a root
    checkout that follows main, then remove the lane worktree.
  - Filed **VB-AK-SEAT-b1v**: prove the producer on run 8's first real call. At 13:19Z no call line existed
    yet, because the first planner call had not returned.
  - Declined: TD-21.29/30 rebase. It belongs to the TD-21 session, which the coordinator has already told to
    rebase onto `21ca61b0`, and its rows live in `typed-decision-plane.md`.
  - Declined: replicating the n=1 A/B. OAB-4 already requires three ABAB pairs per arm, and C20d re-runs the
    bounded arm after caching.
  - Declined: "every arm compacted". This is OAB-7.
- **Index.** `index_state.py --check` reports 0 problems. The generated signal has **0 prune candidates** (165
  open-tasks, 2 no-checkboxes, 1 open-assertion, 1 undispatchable). Proposed for a human read only:
  - `design-backlog-triage-2026-07-23.md` (EVL-09): a dated triage document with no boxes.
  - `cpu-shape-specialized-gemv-decode.md` (INF-10): 0 open, carries a re-open trigger.
  - `model-stack-change-standardization-audit.md` (RTG-18): 0 open, 11 guarded boxes.
- **README freshness.** Passes.
- **Wiki.** Compiled the whole delta (8 sources, including the three TD-21 sources left out last time):
  - `autonomous-research.md`: the seat A/B verdict and run 8.
  - `agent-architecture.md`: TD-21 landed, and the lesson that the repair turn needs evidence.
  - `routing-intelligence.md`: OP-47 makes era E18 live.
- **Cleanup.** Removed four research worktrees with `git worktree remove` and no `--force`. Each was clean, had
  its HEAD on `origin/main`, and had no process using it:
  - `ak-seat-merge-20260924`
  - `ak-actor-seat-20260924-base`
  - `ak-actor-seat-20260924`
  - `ak-actor-seat-followups-20260924`

  Kept `/mnt/raid0/llm/tmp/ak-seat-ab` with its lane, the frozen ak-seat-handoffs worktree, and
  `/mnt/raid0/llm/tmp/ak-seat-vbseat-proof` (the evidence for b1).

### Learnings persisted to repo docs (operator request: visible to every agent, not only Claude memory)

Every claim was checked against research main `21ca61b0` and the audited opencode source at `350c726aa`
(`/mnt/raid0/llm/harness/opencode`).

| File | Section written |
|---|---|
| `docs/reference/harness-candidates/opencode-p03-audit-20260916.md` | New *Addendum 2026-09-24: `opencode run` as a headless actor — measured pitfalls*. A 7-row table (stdin re-quoting at `run.ts:288-290`; pipe truncation; agent `prompt` replacing the system prompt at `request.ts:60`; compaction echo; rc=1 with a complete reply; `hidden` is TUI-only; the unused `task` tool), plus the no-model-call config checks (`debug config`, `debug agent`, `mcp list`). |
| `handoffs/active/harness-selection-and-integration.md` | HS-4 P7: a pointer to that addendum. |
| `docs/guides/agent-workflows/agent-loop-design.md` | New *Launching and stopping a DS41-style serial run* (`PYTHONPATH`, `EPYC_ROOT_REPO`, the dry-run floor banner, no mid-run fast-forward, stop semantics before and after `21ca61b0`, the actor-seat default). New *Who owns fan-out and context: the orchestrator* (the operator ruling). The existing stop paragraph now points at the new section. |

No research-repo doc was edited. The research roster doc covers the owner-map contract, and the root loop guide
is where the `serial_run` CLI is operated.

### TD-21.29/30 and run 8

TD-21.29/30 landed on research main (`4915220f` + `34373dd8`). Run 8 does not carry them, by design: the shared
clone stays at `21ca61b0` while run 8 runs. Two edits to the DS41 handoff:
- a note under C10 on the semantics to expect when comparing run 9 with run 8;
- **DS41-C10a**: fast-forward the shared research clone to ≥ `34373dd8` only after run 8 stops, before run 9.

I did not tick TD-21.29/30 in `typed-decision-plane.md`. Those boxes belong to the TD-21 session, and on
origin/main they are still unticked.

## Stack-configuration window: unified KV, overflow handling, GPU matrices, CPU speech (13:40–18:00Z)

The operator opened a stack-configuration window. The running plan is `/mnt/raid0/llm/tmp/stack-window-plan-20260924.md`.
The live results page (database-backed, the working view, not the record) is https://claude.ai/artifact/Lr4Xd1jBwUW3ToDCQJCEjm.
All follow-up work now lives in the new handoff `handoffs/active/kv-unified-stack-rollout.md` (RTG-57).

### Problem: DS41 run 8 lost its first planner reply to a 98,304-token ceiling

Run 8's batch 0 planner call (13:12→13:32Z, 1235.7 s) returned an empty reply. The 27B hit `finish=length` at
:8083's per-slot limit, and the C20 fix refused the empty reply safely without fabricating anything. The registry
said :8083 serves a unified 196,608-token pool, so the cap should not have existed.

**Root cause: production was never unified.**
- The frozen v10 server turns on `kv_unified` only when `-np` is absent: auto becomes 4 slots plus unified
  (`tools/server/server.cpp:145-150`). Otherwise the default is `false` (`common/common.h:580`).
- The orchestrator always passes `-np`, and nothing in it mentions kv-unified. Every live llama-server logs
  `kv_unified = 'false'`.
- The "unified" registry text came from bench launches that had no `-np`, or passed `--kv-unified` by hand.
- :8083 (`-np 2 -c 196608`) therefore gives each request 98,304 tokens.

This rule and the output-divergence caveat below are now in `agents/shared/OPERATING_CONSTRAINTS.md` →
*Inference and Benchmarks* and in `wiki/kv-cache.md`.

### Run 8 stopped (15:32Z)

The operator stopped run 8 for the window.
- `run.py` held **every CPU region lock** through the full-target floor calibration, which timed out the
  production frontdoor's `/chat` on :8070.
- TERM only drained: calibration started its next launch. Ending the run took KILL on `run.py` (3508990),
  `serial_run` (3359620) and the calibration llama-server (3961920). All were verified dead, and the region locks
  were free afterwards.
- State at stop: iteration 0, 0 measurements. The partial full-target calibration (~2 h) was discarded; the
  half-screen floor stays cached. See `state-run8/STOPPED.txt`.
- The stop path's gap during calibration is filed as DS41-C26. The run-9 prerequisites, in order, are DS41-C25.

### What was built (all 2026-09-24)

| Item | Where | Notes |
|---|---|---|
| `-kvu` stack-change package for :8083 | root `artifacts/operator/stack-change-kvu-20260924/` (copied from `/mnt/raid0/llm/tmp/stack-change-kvu-20260924/`) | Patches 1–3 are the default; O-2 (`-ctkd/-ctvd q8_0`) is optional. It includes the capacity table (np2 kvu 0.18 GiB free, with O-2 0.53), the bring-up, a 7-point serving proof and the rollback. **Not signed yet (OP-54)** |
| Stack-wide `-kvu` inventory | root `artifacts/operator/kvu-stack-inventory-20260924.md` | Every live server runs split KV. Rollout order: :8083, then the embedders (per-slot 256 < bge 512), then :8070 only if long jobs go there, then :8086 only if `-np` rises |
| Serving-engine technique audit | root `artifacts/operator/serving-engine-technique-audit-20260924.md` | vLLM / SGLang / TGI / TRT-LLM vs llama-server v10 plus the orchestrator. Steal list T1–T14. T2, T3, T5, T6 and T7 went onto the overflow branch; #4, #6, #7 and #8 are filed as KVU-2, 5, 6 and 1c |
| Context-overflow handling | orchestrator `feat/context-overflow-handling-20260924` @ `8bbe2a3c` (pushed, not merged) | `fca70439`: detection on all four transports, limits from `/props`, FCFS token admission, retry → reroute → typed 413/503. `8bbe2a3c`: live `/slots` occupancy, adaptive decode reservation, bounded queue → 503, `max_tokens` clamp, `context_length` on `/v1/models`, the MTP sub-batch error classified as `pool_exhausted`, split truncation classified as `context_limit`. 80 tests. **Operator decisions pending (OP-55)**. Streamed chat truncation is still undetectable (KVU-3a) |
| Promotion-gate fix | orchestrator `fix/promotion-gate-red-20260924` @ `d7ab368e` (pushed, not merged) | 14 errors → 4 (`aa322456`). The operator then chose option A, and `9692c7f9` (general_suite_quality counts as per-axis evidence) was merged as `d7ab368e`, so **strict is green**. The only remaining failure is runtime attestation: `-ub 8192` live vs 2048 expected on :8070, :8074, :8080 and :8180. The owning session reloads those four after the speech test, then merges and re-runs the gate (KVU-4a). The critic-suite instrument is filed as SSU-F16 |
| GPU np × ctx study, 27B | research `artifacts/np_context_kvu_study_20260924/` (research main `21cf444c`) | Details below |
| CPU STT/TTS real-time study (C1) | research `artifacts/speech_cpu_realtime_20260924/` (`21cf444c`, the 17:14Z snapshot) | Details below. An SMT-sibling follow-up run was still writing at 17:53Z (KVU-11a) |

### GPU sweeps (production v10 GPU binary; :8083 stopped 15:36Z, :8086 stopped for the 35B run with operator approval)

Qwen3.8-27B Q8_0 with MTP draft, olympiad-style prompts, n=1 per cell. Numbers are verified against the committed
`summary.tsv` / `server.stderr`, and where they differ from the page, the files win.

- **v1 (15:37–15:45Z)** used `c = L·np`, which left no room for the prompt. Split silently truncated at the slot.
  Unified np2 hit a server exception under the full pool. v1 is kept as edge-behaviour evidence.
  - Long prompt: 124,174 tokens accepted under unified (399.9 tok/s prefill, 310.5 s). Split returns HTTP 400 at
    98,304.
- **v2 headroom matrix (15:49–16:51Z)**, `c = (L+1024)·np`:
  - Per-request decode, unified vs split: equal within 1.1% at np1, with byte-identical outputs; +0.3% to +5.7% at
    np2/np4.
  - Aggregate np4 is −8% (8k) and −16% (32k) under unified, but the two arms generated different answers there. The
    KV layout changes float summation order, and sampling diverges at temperature 0.6. **Verdict: unified KV does
    not cost throughput.** A fixed-length or multi-wave confirmation is still owed (KVU-8).
  - np8 does not fit in either arm (skipped at 63 GB in use for L2048; out of memory at load for 8k and 32k).
  - O-2 costs no per-request speed.
  - **Pool-full repro:** unified fails exactly one request with `speculative batch index 8 is not inside the current
    sub-batch [0, 8)` in 4/4 runs. Split never errors and silently truncates at the slot. This is a v11 kernel
    candidate (KVU-7, guarded), and the overflow branch already classifies it.
- **MTP depth (→17:07Z):**
  - depth 4 acceptance 0.63–0.66 vs 0.37–0.46 at depth 8;
  - per-request within ±2.5% except one +7.8% cell;
  - 1014 MiB less at production shape (`-np 2 -c 196608 -kvu`, whole-device VRAM, load-only).
  - Confirm on production traffic before changing the recipe (KVU-1b).
- **35B-A3B matrix (Qwen3.6-35B-A3B-MTP Q8_0, from ~17:12Z, driver pid 1224153)** was still running at wrap-up and
  is not committed (KVU-9). Preliminary page rows (unverified against files) cover 16 cells, np 1–8 × L 2k/8k,
  MTP depth 4. They are not a clean "unified is free" result yet:
  - per-request unified vs split is −0.6% to −5.3% in 7 of 8 pairs and +5.6% at np8 8k;
  - the −5.3% cell (np1 8k) tracks lower draft acceptance on different answer text.

  Read this after the run completes, with KVU-8's fixed-length method. :8083 and :8086 stay stopped until the
  run ends; the owning session restores them.

### CPU: C1 speech done, C2 skipped

- **C1 (16:05–17:10Z).** STT (whisper large-v3-turbo) runs 5–8× faster than real time at 24–32 threads. TTS
  (Qwen3-TTS 0.6B) runs ~1.7× real time, with a first packet in 75–113 ms. Both together stay real time.
  - Next to a generating frontdoor (`-t 96` on 0-95), both collapse: TTS RTF ~8, and the frontdoor drops from 43
    to 0.3 tok/s.
  - Whisper hangs on some core layouts (e.g. 32@0-31).
  - Recommendation: keep speech on the GPU. The residency decision is operator option A/B/C (OP-56, KVU-11).
- **C2 (Flash-Next CPU np × ctx) was skipped by the operator at 17:25Z.** The GPU matrix shows no unified-KV
  throughput cost, and the CPU's relative behaviour is not expected to differ. Reopen only if needed (KVU-12).

### TD-21 coordination (SW-9 spec-accept-probs fix, champion order)

- The TD-21 session's fix is `experimental/mtp-spec-probs-fix-20260924` @ `2b57340bf` (on `fork`), the champion
  `ak/champion/llama-cpp-ffc1bac82eec` @ `8df1b5cf2` + 1.
- The DS41 anchor `ebb68dc55` is a clean descendant of `8df1b5cf2` (+6).
- The operator gave the ADMIT. OP-52's CPU window was sequenced after C1 and the Flash-Next matrix; C1 is done and
  the matrix was skipped.
- Agreed order: **champion ff → main-ak-seat rebases the DS41 port onto the new tip → anchor rebuild → run 9**
  (DS41-C25). Floors are bound to the anchor, so the advance must precede run 9's first full-target calibration.
- `/mnt/raid0/llm/tmp/ak-loop-tree` is unused by this session.

### Derived actionables

**Filed:**
- DS41-C25 (run-9 order), DS41-C26 (stop during calibration).
- SSU-F16 (critic-suite instrument, text prepared by the gate-fix agent).
- RTG-57 KVU-1..KVU-13b (including KVU-3a streamed truncation, KVU-11a speech follow-up commit,
  KVU-13a ambient `LLAMA_ARG_*` env, KVU-13b stack-change skill source list).
- OAB-4a (pin :8083's KV mode per arm).
- VB-KVU-1, VB-SPEECH-CPU-1, VB-AK-SEAT-b1w.

**Explicit declines, recorded in the RTG-57 "Not filed here" section:**
- SSU-F3 capacity model (RTG-19);
- INF-41 aux VRAM (OP-48);
- package §10 items the overflow branch already fixes;
- a Stage-1 intake sweep of the audit's primary sources (no claim relies on them; intake runs only when the operator
  invokes it).
- The campaign holding every CPU region lock through calibration: not filed separately, because OP-41 owns
  admission control. DS41-C25 carries the scheduling constraint.

**Closed in this wrap-up:** VB-AK-SEAT-b1v. Run 8's one call line ingests with matched=1, projected=1, refused=0.

## Stack window, part 2: OP-54 applied, M-3/M-4, 35B matrix, CPU speech under load, DS41 run-9 prep (18:00–19:55Z)

The plan file `/mnt/raid0/llm/tmp/stack-window-plan-20260924.md` has the minute-by-minute record. This section records what landed.

### GPU residency applied (OP-54, signed ~18:40Z, applied 18:45–18:55Z)

The operator signed revision 3 of the package. Revision 3 replaced the np2 funding: it runs np 4, drops O-2, and
moves speech to CPU. The signed copy is now in root:
`artifacts/operator/stack-change-kvu-20260924/revision-3/` (PACKAGE.md, patches, argv, capacity).

| Service | Live now |
|---|---|
| :8083 architect_general (pid 2009477) | `-np 4 -c 196608 --kv-unified --spec-draft-n-max 4 -ub 2048 --cache-ram 65536`. The log reads `n_slots = 4, n_ctx_slot = 196608, kv_unified = 'true'` |
| STT :9000 | CPU `-t 24 -ng` on 0-23, 0 VRAM |
| TTS :9002 | CPU on 24-39, 16 threads via the `nprocs` shim, 0 VRAM |
| CPU roles | `--cache-ram 32768` on :8070/:8074 (+ halves); :8086 `--cache-ram 0` |

Serving proof:
- a 124k-token request served;
- jfk.wav RTF 0.20;
- TTS first packet 97 ms;
- `status` shows no attestation warnings;
- the promotion gate is green;
- 26 `created context checkpoint` lines since the launch, which closes KVU-1c.

| Repo | Commit | What |
|---|---|---|
| orchestrator | `0a564a1f` | the package, plus the contention-matrix re-bench (topology `4893e37e`; worst pair architect_critic+worker_vision 0.08) |
| orchestrator | `41ecf9fc` → merge `3a61c153` | bare `FINAL(OK)` NameError rescue on /v1 (`rescue_bare_name_final`). Found during the serving proof; the bug predates OP-54. API reloaded, repro fixed |
| orchestrator | `8a0c0944`, `ff67bbec` | overflow-branch merge and gate-fix merge (18:10–18:30Z). The CPU-role reloads on `-ub 2048` ran 18:16–18:18Z |
| research | `75ee1b8e` | registry: architect_general np4 + kv_unified + depth 4 + cache_ram; speech aux on CPU |

### Measurements (research `07060eaa`, `6afc7eed`)

**M-4: live np4 kvu, fixed-length 1024 tokens, 2 waves.**

| Concurrency | Aggregate tok/s (wave 1 / wave 2) |
|---|---|
| 1 | 40.2 / 39.9 |
| 2 | 71.4 / 67.8 |
| 4 | 95.3 / 93.1 |

These match the split-KV study cells. The single-wave "aggregate loss" was an answer-length artifact, so KVU-8
closes, with one substitution named in the box.

**M-3: production depth 4 vs 8. NOT confirmed.**
- Depth-8 production arm: n=240, median context 63.5k, mean accepted 4.86, acceptance 0.483, 38.2 tok/s.
- Depth-4 arm: 0 organic requests.
- Log projection (a model, not a measurement): depth 4 = 0.93× for the median request, 1.01× aggregate.
  Positions 5–8 carry 27.5% of accepted tokens.
- Filed as M-3b.

**35B-A3B kvu matrix (24 cells, 0 errors, depth 4):**
- Unified is within 2% of split in the fixed-length L 2048 cells.
- At 8k/32k the delta is −5.3..+5.6% with no consistent sign, because completions diverge even at np 1.
- np 8 fits.

**27B load-only (server MiB):**

| Shape | MiB |
|---|---|
| split d8 | 39,018 |
| np2/196k unified | 39,026 |
| np4/196k | 40,522 |
| np2/262k | 42,362 |
| np4/262k | 43,858 |

**CPU speech vs live CPU LLMs (addendum 3): not real time, and the collision is two-sided.**
- With :8074 or :8070 generating (`-t 96` on 0-95):
  - STT RTF ≥ 58;
  - TTS first packet 13.4–13.6 s, then a stall;
  - :8074 falls 31.2 → 0.59 tok/s and :8070 falls 36.8 → 1.05 tok/s.
- Partition test (`-t 56` on 40-95):
  - STT 0.22–0.44;
  - TTS marginal (first packet 0.24–1.0 s, RTF 0.93–1.40);
  - LLM −22..26%.
- No priority-pause mechanism exists.
- Findings persisted for future STT/TTS planning in
  `docs/reference/speech/cpu-speech-contention-20260924.md` (new).

### DS41 run-9 prep (C25)

- Champion ff to `2b57340bf`.
- Port merged onto it: anchor **`5a60152ae`** on `experimental/deepseek41-port-20260924`.
- `build-cpu` is version 10313, sha256 `763e1474…f8f7`. ggml linkage PASS. `test_speculative.py` 9/9, relayed
  to workspace-8d.
- Inputs re-resolved (r4, `ds41-5a60152ae-cpu-t48-dspark-b2`, verified). Backups are in `bak-20260924-run8/`.
- Dry run rc=0.
- Shared research clone fast-forwarded (C10a prep). `/workspace` carries the seat capture contract, and the old
  lane worktree was removed (C24 prep).
- Both floors recalibrate (~8.5 h, all CPU region locks).
- **Operator: run 9 OFF-HOURS, launched tonight by main-ak-seat after this wrap-up.** Not launched at wrap-up
  time. The pending API reload for orch `c347600e` (TD-21.33c) comes first.

### workspace-8d coordination

- It needed no CPU window: SSU-F14 is satisfied by `0a564a1f`'s matrix.
- It closed OP-48 on its side (root `baa0d036`, S-11a superseded). Its rows were not touched here.

## Operator-invoked wrap-up #4 (19:50–20:10Z)

**Checklist sync: 9 flips + 7 completed-this-session boxes added (16 `[x]` lines).**
- RTG-57 flips: KVU-1, 1c, 2, 3, 4a, 8, 9, 11, 11a.
- Added as `[x]`: KVU-0i, KVU-1e; DS41 C25.1–C25.4 and C25.6.

**Derived actionables: 6 filed (+2 extended), 5 declined** (RTG-57 "Not filed here" plus below).
- Filed:
  - M-3b (under KVU-1b);
  - KVU-11b (CPU speech contention decision; see the note below);
  - KVU-11c (qwentts thread flag, to retire the shim);
  - KVU-13c (capacity gate at `stack_manifest` import);
  - VB-KVU-1a;
  - VB-SPEECH-CPU-1a.
- Extended: KVU-13a (ambient `LD_PRELOAD`/`SHIM_NPROCS`) and KVU-13b (the skill source list).
- Declined:
  - a priority pause as its own task (it survives as option C);
  - the frontdoor-under-partition measurement (part of the layout decision's re-run);
  - pinning `megasync` (recorded in the reference doc);
  - the package §9 `worker_general` tests (already SSU-F13);
  - the opencode limit (KVU-1a stays open: the operator applies it outside containment, and
    `~/.config/opencode/opencode.jsonc` has no 196608 limit yet).

**Fixed in passing:**
- research `afbc6bea` (main `170c763c`): the addendum-3 side note said `HIP_VISIBLE_DEVICES` was unset.
  `/proc/<pid>/environ` shows `-1` on both speech services.
- The signed revision-3 package was only in scratch while orch `0a564a1f` cited the root path. It is now copied
  into root.

**Note on KVU-11b.** The coordinator relayed an operator choice for the speech layout mid-wrap-up. The permission
classifier refused to let this subagent write that relayed choice into the handoff, so KVU-11b is left as
filed. The owning session records the operator's decision.

## Reduced-scope planner build (evening, 20:30–21:45Z)

**Problem.** The operator directed a reduced-scope build on the opencode seat, run in parallel with DS41 run 9's
floor calibration. The goal was to learn what the final orchestrator wiring must copy; the operator called the
learnings "immensely important" to it. The builds were worktrees only: no inference, no `perf record`, tests
pinned to cores 72-79, and the shared research clone untouched (run 9 spawns from it).

**Built.** Three research lanes, all off research `origin/main` `170c763c`, pushed and unmerged, **none A/B'd**:

| Lane @ commit | What | Measured |
|---|---|---|
| `lane/ak-ctxvar-20260924` @ `ce5800cb` | `--actor-context-mode variable`: the bundle goes to files under `workers/actor-context/*/` with an index in the prompt (default inline, byte-identical). Manifest `epyc.autokernel.actor_context_bundle.v1`. 143 tests. | run-8 planner prompt 26,293 → 5,510 tokens (−79%); run 7 32,917 → 5,629 (−83%), 27B tokenizer |
| `lane/ak-turns-20260924` @ `0bf2d7c2` | `epyc.autokernel.actor_call_metrics.v1` row per actor call (before the v1 line), plus a summarizer | reproduced DS41-C20c exactly: 23 steps, 25 tools `{bash 11, glob 1, read 13}`, 1 compaction, 57,702 decoded |
| `lane/ak-perfcache-20260924` @ `f4a5d240` | perf report/annotate cache in `actor_tools_mcp` (DS41-C20d). 111 tests. | run-7 profile (25.7 MB): 1.283 s → 0.0012 s, byte-identical |

**Findings that change plans:**
- **The plain seat has no MCP server** and never called the perf tools. Context as FILES is the only
  "variable" it can use. Reads outside `--dir` work only via `--auto`, and the critic runs without it.
- **The DS41-C20d premise is likely wrong or partial.** At 1.3 s per call, perf-tool time cannot explain the
  bounded seat's ~12-minute loss. The A/B's per-call metrics will attribute it. opencode has no per-tool latency,
  so it is inferred from step timestamps or reported as unknown.
- **chars/3.5 undercounts this prompt by ~30%.** The target JSON runs at 2.46 chars/token and is 37% of prompt
  tokens.
- **About 13.2k tokens of every call is fixed.** The lane `AGENTS.md` alone is ~2.5-3k tokens of llama.cpp
  contributor guidance.
- **Three planner defects:**
  - `render_context` never printed `node_profile`;
  - the plain planner read the anchor build tree, not its lane;
  - it compiled `.o` files into `/tmp` despite "never build".
- **Pre-existing test failures on research `origin/main`:** the `oracle()` stand-ins lack `require_reference`
  after `37d326ac`, and there is a `test_shared_history` WAL `-shm` mtime failure. Being fixed on the integration
  lane.
- **The PII pre-commit hook redacted 7 perf sample-period cells** in `ce5800cb`'s fixture.

**Root documentation (this wrap-up):**

| File | Change |
|---|---|
| `handoffs/active/autokernel-orchestrator-actor-backend.md` (INF-78) | New section *Techniques learned in the opencode seat*, mapped to OAB-6/7/8, R4 and S4-T1. `[x]` OAB-7s, OAB-4m, R4c; `[ ]` OAB-9 (live A/B), OAB-10 (AGENTS.md trim), OAB-11 (anchor-tree reads, `/tmp` builds), OAB-12 (pull accounting). Baseline's perf-tool attribution marked doubted |
| `handoffs/active/deepseek-v41-flash-evaluation.md` (INF-77) | DS41-C20d progress: `[x]` C20d1 (cache built), `[ ]` C20d2 (re-run; premise doubtful). `[ ]` C20e (`node_profile`), C20f (anchor-tree reads), C20g (`/tmp` `.o` builds), C20h (merge the three lanes and relaunch). DS41-C24 acceptance-wording note |
| `handoffs/active/repl-turn-efficiency.md` | S4-T1: `actor_call_metrics.v1` named as the comparability target; the step vs REPL-turn unit warning |
| `docs/guides/agent-workflows/agent-loop-design.md` | New section *Context as files, per-call metrics, tool-output caching*, with the traps |
| `docs/reference/harness-candidates/opencode-p03-audit-20260916.md` | Addendum rows 8-10: no MCP in the plain seat; export observability limits; no parent/child sessions |
| `scripts/vidya/adapters/README.md` + `handoffs/active/vidya-belief-substrate-program.md` | Source rows plus `[ ]` VB-AK-METRICS-1 (`actor_call_metrics.v1`) and VB-AK-CTX-1 (`actor_context_bundle.v1`, joined on `prompt.sha256`) |
| `handoffs/active/tool-output-compression.md` | `[ ]` TOC-RD-1b: PII hook exemption for perf periods in markdown table cells (hook unchanged) |

**Next (operator-confirmed morning sequence, 21:40Z):**
1. When calibration ends (~04:45Z), stop run 9.
2. Merge `lane/ak-planner-integ-20260924`.
3. Run the ctx A/B: 3 pairs, or 2 if short on time.
4. Relaunch run 9 with the winner.
5. Per-task wrap-up.
