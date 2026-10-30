# Agentic serving harness fixes — demonstrate on the 27B, generalize, then audit

**Status**: active. Phase A: A1 (F12 run) done and graded 2026-10-03; A2 running inside the INF-80 X0 window; A3/A4 implemented and offline-tested, GPU test pending. Phase B: B2, B3, B5 live; B6, B4 (API part) and DIAG deployed 2026-10-03 ~14:50Z, live proofs pending the :8083 restore.
**Created**: 2026-10-03, by operator directive in session ak-ds41-main:

> "yes, i want all the harness bugs we identified to be fixed. The fixes shoudl be as general as possible (not limited solely to the 27B model) as I'm sure they would affect the usage of any of the models in the orchestrator stack. A full review/audit of how fixes should holistically be folded into the orchestrator's mgmt shoudl be performed after they are demonstrated on the 27B model."

**Categories**: agent_architecture, inference_serving, context_management, tool_implementation
**Parent index**: [`user-facing-harness-index.md`](user-facing-harness-index.md), row UFH-14.
**Owners**:
- Phase A and the client-side harness pieces: ak-ds41-main.
- Phase B orchestrator and stack pieces: workspace-ec, the stack owner (formerly workspace-8d).
- Phase C: the operator's choice of auditor (Fable, per the auditor convention).

**Related**:
- [`harness-selection-and-integration.md`](harness-selection-and-integration.md) (UFH-01, HS-4: harness features live inside the orchestrator).
- [`harness-improvement-loop.md`](harness-improvement-loop.md) (UFH-08).
- [`deepseek-v41-flash-evaluation.md`](deepseek-v41-flash-evaluation.md) (INF-77, where the defects were found: DS41-C95).

## Evidence (the defects this handoff fixes)

1. **The 27B harness experiment (DS41-C95)** was graded blind by claude-opus-5-5. P(keep): DeepSeek as-ran 0.75, 27B×codex 0.50, 27B×Hermes 0.33, 27B×opencode 0.25, 27B as-ran 0. Orchestrator arms orv and orsv went 0/4.
   - **Diagnosis:** `/mnt/raid0/llm/tmp/ds41-c95/diagnosis-27b-report.md`. Most 27B failures were harness and serving defects, not model capability. In 6 of 8 no-reply calls, a keep-class candidate already sat in the transcript.
2. **The prefill/decode share analysis** covers 09-24→10-01 and was parsed from llama-server logs: [`docs/reviews/prefill-share-20261003.md`](../../docs/reviews/prefill-share-20261003.md).
   - On :8083, 74% of prefill time was cold ≥8k prefills where no slot held the prefix.
   - 21k s was duplicate concurrent prefill of the same context.
   - There were 929 prompt-cache evictions and 456 "failed to find a memory slot" warnings.
   - Neighbour prefill dropped decode from 28.6 to 7.8 tok/s, costing about 60k s.
3. **Decode-vs-context probe** (solo, production shape): `/mnt/raid0/llm/tmp/ds41-c95/probe-decode-vs-context.md`. On MTP, prefill fell from 850 to 487 tok/s between 2k and 80k, and time to first token at 80k is 165 s.

| # | Defect | Layer | Generic? |
|---|---|---|---|
| D1 | Client stream idle timeout (codex ~300 s) shorter than a long silent prefill. The abandoned request keeps prefilling, which doubles the load. | client harness | yes: any model with long prompts |
| D2 | Compaction requests change the prompt prefix (codex sends `tools=[]`), forcing a full cold re-prefill of 79–94k tokens. | client harness | yes |
| D3 | Compaction drops the task prompt (opencode). | client harness | yes |
| D4 | No answer protocol: the model explores past its budget with a candidate in hand, and the final answer is never emitted. | harness prompt and loop | yes |
| D5 | Parallel arms start at the same moment on the same context, so each prefills cold. No prefix warming. | harness scheduling | yes |
| D6 | The `--kv-unified` pool (`-c 196608` shared by 4 slots) overflows under concurrent long contexts, causing evictions and context-exceeded errors. | server config | yes: per-model sizing |
| D7 | Concurrent long prefills stall decode in the other slots. | server admission | yes |
| D8 | Serving telemetry gaps: no wall-clock time, no record of which role or client sent each request, `prompt_eval_ms`=0, cancels untimed, queue wait unlogged. | orchestrator and stack logging | yes |

## Phase A — demonstrate on the 27B (production Qwen3.8-27B Q8_0, DFlash2, :8083)

- [x] **UFH14-A1.** ✅ 2026-10-03 — F12 run: the cxf1 arm (F1: solo, 1 h idle timeout, compaction at 150k) and the cxf12 arm (F1 plus F2: JSON-first answer, forced answer at 65% of budget, refine turn, 8k thinking cap). 8 solo calls on C2 and C4, graded blind against all C95 arms. Covers D1 and D4, partly D2.
  - Launcher: `/mnt/raid0/llm/tmp/ds41-c95/f12_launch2.sh`. Log: `logs/f12_launch2.log`.
  - **Result** (blind Opus grades, `/mnt/raid0/llm/tmp/ds41-c95/grading/report.md`; per-call `results/C{2,4}/cxf{1,12}/r{1,2}/result.json`). n = 4 calls per arm, so OBSERVATION grade only:

    | arm | answered | keep exact / partial | P(keep) | mean factual errors | median wall s |
    |---|---|---|---|---|---|
    | DeepSeek as-ran (calibration) | 3/4 + 1 abstain | 3 / 0 | 0.75 | 0.0 | — |
    | cx (unfixed codex inline) | 2/4 | 0 / 2 | 0.50 | 2.0 | 5401 |
    | **cxf1** (F1) | 4/4 | 0 / 2 | 0.50 | 1.75 | 4640 |
    | **cxf12** (F1+F2) | 4/4 | 0 / 3 | 0.75 | 2.25 | 3880 |

  - **What F1 fixed:** no client timeouts, aborts or cold re-prefills; prompt-cache hit rate 90–96% per call. F1 alone still needed salvage (answer rebuilt from the transcript) on 2 of 4 calls.
  - **What F2 fixed:** cxf12 answered within its own turns on all 4 calls, with a ~16% shorter median wall than cxf1. It did not reduce factual errors (2.25 vs 1.75) and found no exact keep.
  - **DFlash2 on agentic traffic:** draft acceptance 29–34% on temperature-1.0 planner traffic, decode 25–30 tok/s at 57–152k context (well below the 91.7 tok/s single-stream short-context figure).
  - **Contamination:** C2/cxf1/r2 browsed the live campaign store (`anchor-gen-007`), so it saw post-anchor state; the grader flagged it. The harness had no filesystem isolation.
  - **Fixed offline (not yet GPU-tested):** a Landlock filesystem sandbox (`/mnt/raid0/llm/tmp/ds41-c95/sandbox3.py`; mount and user namespaces are unavailable in this container, Landlock ABI 6 needs no privilege) plus the A3 and A4 implementations in `run3.py`/`proxy3.py`. They close A3/A4 only after a GPU run.
  - The separate DFlash2 decode probe crashed on fresh slots (`KeyError 'params'`); fixed in `probe_decode.py` and folded into the INF-80 X0 window (A2).
- [x] **UFH14-A2.** DFlash2 decode-vs-context probe on the production shape, to compare against the MTP probe and to separate drafter speed from harness effects.
  - ✅ 2026-10-03 — ran folded into the INF-80 EXL3-X0 window: one launch of the production :8083 argv (np4, `-c 393216 --kv-unified`, q8_0 KV, DFlash2 n_max 7), Q8_0, solo, real DS41 planner context (C2+C4), thinking on, 1500 generated tokens, 2 reps. Table: `/mnt/raid0/llm/tmp/x0-27b-quants/results/probe/probe-decode-vs-context.md` (JSON beside it).

    | context | DFlash2 drafted tok/s | acceptance | no-draft tok/s | MTP drafted tok/s (2026-10-01 probe) |
    |---|---|---|---|---|
    | ~2k | 41.6 | 0.33 | 29.6 | 36.8 |
    | ~16k | 40.4 | 0.35 | 25.8 | 40.8 |
    | ~50k | 36.9 | 0.39 | 21.6 | 38.8 |
    | ~80k | 32.1 | 0.39 | 18.5 | 30.0 |

    - **Answer to the A2 question:** DFlash2 decode at the production shape is about the MTP probe's (`/mnt/raid0/llm/tmp/ds41-c95/probe-decode-vs-context.md`), with roughly half MTP's acceptance (0.33–0.39 vs 0.43–0.74). The drafter is not why agentic decode sits at 25–30 tok/s: no-draft decode itself falls from 29.6 to 18.5 tok/s between 2k and 80k, and the drafted/no-draft ratio grows with context (×1.41 → ×1.74). The other named suspect, the unified-KV neighbour tax, is now measured (KVU-18: −58/−60% at three parked ~100k neighbours).
    - The MTP probe ran on 2026-10-01 against the then-live :8083 shape (pre-KVU-16), so the comparison is across server shapes as well as drafters; n = 2 reps per cell.
    - *Observation, not a conclusion:* the canonical-recipe np1 figure (76.4 tok/s, acceptance 0.73; EXL3-X0 shape a) is ~1.8× the production-shape np1 figure (~41 tok/s, acceptance ~0.37). The two shapes differ in prompt content (benchmark vs real planner context), KV type (f16 vs q8_0), unified KV, pool size, n_max (8 vs 7) and thinking, so the gap is confounded; no single cause is claimed. Declined as a task for now: splitting it needs a one-factor-at-a-time grid on :8083, and nothing in UFH-14 waits on the answer.
    - Agentic-traffic acceptance from A1 (29–34%) remains context, not a substitute.
  - *F12 production-traffic numbers, 2026-10-03.* These are not the probe, so the box stays open. Re-derived from `wire_timing` in `/mnt/raid0/llm/tmp/ds41-c95/results/C{2,4}/cxf{1,12}/r{1,2}/result.json`, 8 calls. Server: :8083 PID 3793153, `-np 4 -c 196608 --kv-unified`, `--spec-draft-n-max 8` clamped to 7. This is the pre-KVU-16 shape.
    - DFlash2 draft acceptance: 0.290–0.343.
    - Median decode on turns of ≥1k tokens: 24.6–30.2 tok/s.
    - Prompt-cache hit: 0.882–0.959. Two calls sit below 0.90 (C2/cxf1/r2 0.882 and C4/cxf1/r1 0.896); both contain a compaction (A4).
    - Context: 49.8–56.9k at the first request, 109.5–151.5k at the peak.
  - Read the acceptance against the production prior, not the benchmark one. AngelSpec replayed temperature-1 production traffic and measured a block-8 DFlash-family drafter at a mean accepted length of about 2.5 tokens per step, roughly half its benchmark figure (`intake-1848#01`, `intake-1848#02`). Our 29–34% at n_max 7 is in that range and is not by itself a drafter defect. The unified-KV decode tax is a separate, unmeasured suspect (`intake-1849#02`; KVU-18 in [`kv-unified-stack-rollout.md`](kv-unified-stack-rollout.md)).
- [x] **UFH14-A3.** ✅ 2026-10-04 (GPU run 2026-10-03) Prefix warming plus staggered starts for parallel arms. Issue one warm request for the shared context, then start the arms so they hit the prompt cache. Measure the cold-prefill share and decode stall against an unstaggered A/B. Covers D5.
  - 2026-10-03: implemented in `/mnt/raid0/llm/tmp/ds41-c95/run3.py` + `proxy3.py`, offline-tested only. Close after the GPU A/B.
  - **Measured 2026-10-03 (run 3, C2, codex inline, 2 parallel arms, Landlock sandbox; `/mnt/raid0/llm/tmp/ds41-c95/logs/a3-group-report.log`, `results/C2/cxa+a3cold|a3warm/`).** n = 1 group per leg.
    - *Cold, unstaggered (15:44Z):* first requests `cache_n` 0 / 6,447, prefill 137.7 s / 281.5 s, TTFT after release 140.1 s / 281.6 s; 107,151 cold-prefill tokens in 419.2 s; decode with a neighbour prefilling 14.04 tok/s (n=1) vs clean 18.3 (n=11), estimated stall 93.9 s.
    - *Warm + 3 s stagger (16:05Z):* the warm requests each prefilled 56,794 tokens (104.2 s, 106.6 s) while the arms were held 246.5 s / 240.4 s; the arms' first requests then hit the cache — `cache_n` 54,751 / 56,794, prefill 8.4 s / 0.2 s, TTFT after release 9.0 s / 0.3 s. 115,641 cold-prefill tokens in 219.4 s (**−48% cold-prefill seconds**); decode with a neighbour prefilling 17.15 vs clean 20.7, estimated stall 137.9 s.
    - *Verdict:* warming moves the cold prefill off the arms' critical path (TTFT 140–282 s → 0.3–9 s) and halves cold-prefill seconds. The decode-stall comparison is NOT resolved: the warm leg overlapped workspace-ec's subagent GPU tests 16:17–16:50Z (INC-20261003-subagent-gpu-tests-in-peer-window), and the two warm requests prefilled concurrently instead of once. → UFH14-A3a.
  - [x] ~~**UFH14-A3a — re-measure the warm leg unperturbed, with ONE warm request.** (filed 2026-10-04) The 10-03 warm leg issued two warm requests (one per arm; 2 × 56.8k tokens) and overlapped foreign GPU work. Issue a single warm request for the shared prefix, then stagger; re-measure decode stall vs the cold leg in a coordinated GPU slot.~~ (closed 2026-10-29 audit: SUPERSEDED → split into UFH14-A3A-F1 (line 103) and F2 (line 104); r11 single-warm run done per 87 sub-bullet (A3A-DIAGNOSTIC-R2 [x] 2026-10-29))
    - [x] **UFH14-A3A-DIAGNOSTIC-R2 — run the prepared descriptive capture.** ✅ 2026-10-29 (run `ufh14-a3a-single-warm-r11-20261028`, successor of the r2 plan) The private
      `/mnt/raid0/llm/tmp/codex-ufh14-repair-20261028` successor passed a 78-second canonical tiny-model
      launcher smoke and a forced rc75 partial/cleanup smoke; its validated
      `/mnt/raid0/llm/tmp/compute-flags/ready/ufh14-a3a-single-warm-r2-20261028.json` remains held until
      the scheduler's full q3 admission is verified. Run the actual cold and one-warm Qwen/DFlash
      capture after admission; the tiny-model smoke is plumbing evidence, not the A3a measurement or
      a performance verdict. [belief: cc]
      - 2026-10-29 result (diagnostic observation, rc0 `complete`, 23:41Z to 00:00Z; no predeclared threshold,
        so no keep/reject verdict and no tick of UFH14-A3a). Frozen v10 GPU kernel, 4 slots, `kv_unified=true`,
        fixed historical member0/member1 (56,799 prompt tokens each), one cold leg then one warm leg (n = 1 each,
        NOT alternated, so no timing claim). Raw: `/mnt/raid0/llm/tmp/codex-ufh14-r11-successor-20261028/attempts/run-17932308737*/{cold,warm}/group/{native-group,timing-bindings}.json`.
        - Cold, unstaggered: member0 `cache_n` 0, prefill 108.8 s, 15.3 tok/s decode; member1 `cache_n` 0, prefill 256.3 s, 23.6 tok/s. Cold prefill 365.1 s total.
        - Warm, ONE warm request (56,794 tokens, `cache_n` 0, 94.0 s) then member0 at once and member1 at +3 s: member0 `cache_n` 56,794, 5 prompt tokens, prefill 0.17 s, first event 0.3 s, 12.7 tok/s decode. member1 got **`cache_n` 0, prefill 170.3 s, first event 170.5 s** (slot 3 "by LRU", because slot 0 holding the warmed cache was busy decoding member0). Cold prefill 264.5 s vs 365.1 s (-28%, vs -48% in the two-warm 10-03 leg).
        - Meaning: a single warm request in a 4-slot `kv_unified` server warms only the slot it ran on. Only the arm that lands on that slot benefits; a concurrent second arm re-prefills cold. This is the opposite of the 10-03 two-warm result (both arms hit cache), so the 10-03 "-48%" does not transfer to a one-warm design. Decode tok/s differs between legs but overlaps neighbour prefill windows differently, so no decode-stall conclusion is drawn.
        - Not verified here: q3 quiet during the legs (row claim only; no foreign-GPU sampling read by this filer).
    - [ ] **UFH14-A3A-F1 — warm all slots or share the prefix across slots.** (filed 2026-10-29) member1's miss is slot-local. Probe (a) one warm request per distinct slot, (b) `--cache-reuse`/slot-save restore of the warmed prefix onto the second slot, or (c) delaying the second arm until member0 releases slot 0 (LCP reuse). Re-measure first-request TTFT and cold-prefill seconds for both arms. Descriptive probe first; predeclare the threshold before any keep claim. [no-belief: unrun]
    - [ ] **UFH14-A3A-F2 — decode-stall comparison, alternated.** (filed 2026-10-29) The original A3a question (decode stall warm vs cold) is still open: r11 is n = 1 per leg, cold then warm, not ABA. Run it only after F1 picks a warmup that warms both arms, with q3 and the GPU quiet verified by sampling during the legs. [no-belief: unrun]
- [x] **UFH14-A4.** ✅ 2026-10-04 (GPU run 2026-10-03) Compaction that keeps the prefix. Make compaction requests carry the same tools and system prefix, or compact through a separate summarization call that leaves the live prefix intact. Measure re-prefill tokens per compaction. Covers D2. Also cover opencode's task-prompt drop (D3).
  - 2026-10-03: implemented in `run3.py` + `proxy3.py`, offline-tested only. Close after a GPU run measures re-prefill tokens per compaction.
  - *Baseline from F12, 2026-10-03, wire logs.* 5 codex compactions across the 8 calls, each a cold pair at `cache_n` = 0:
    - The `tools=[]` compaction request: 147.6–157.1k tokens, 416.7–461.2 s.
    - The post-compaction request: 38.3–39.7k tokens, 58.1–60.1 s.
    - Total: 2,459 s of prefill, 8.9% of the 27,731 s summed call wall time. This is 3.5× the hybrid re-prefill cost in A7.
  - **Measured 2026-10-03 (run 3, C4, codex inline, `--compact-limit 64000`, Landlock; `logs/a4-base.log`, `logs/a4-fix.log`, `results/C4/cxa+a4base|a4fix/r1/result.json` → `compactions`).** n = 1 call per arm, 2 compactions each (1 completed, 1 cut by the budget).
    - *Base (16:25Z):* the compaction request went cold — `cache_n` 0, **65,779 re-prefill tokens, 172.3 s**.
    - *Keep-prefix fix (17:10Z):* the rewritten compaction request shared 19 prefix items — `cache_n` 65,331, **8,912 re-prefill tokens, 40.1 s** (−86% tokens, −77% seconds per compaction).
    - Unchanged in both arms: the request *after* the compaction re-prefills ~32k tokens at `cache_n` 6,447 (31,858 / 32,594 tokens, 174.9 s / 147.2 s). → UFH14-A4a.
    - Neither call answered (both `no_answer` at the 2,700 s budget), so A4 says nothing about P(keep); that is A5's question.
  - [ ] **UFH14-A4a — the post-compaction request still re-prefills ~32k tokens.** (filed 2026-10-04) In both arms the first request after the compaction matched only 6,447 tokens of cache. Diff that request's rendered prompt against the compaction request's to find where they diverge after the system prefix (tool list, task-prompt re-insertion, summary placement), and make the post-compaction prompt extend the compaction prompt.
- [ ] **UFH14-A6.** Run every later harness experiment under the Landlock sandbox (`sandbox3.py`) and verify isolation on a real call before relying on it: a planted read of the live campaign store must fail, while the call's own workspace, result dir and wire proxy stay reachable. Origin: C2/cxf1/r2 contamination (A1).
  - 2026-10-03 evidence (run 3, all four A3/A4 calls under Landlock ABI 6, ~2,476 rules, `/tmp` denied; `sandbox-report.json` per call): the sandbox applied and refused real accesses — 19 denials in each A4 call (writes to `/tmp/sgemm*.o`, opening `llama.cpp-experimental-fastload-ds41-20260925/.git`). But the contamination scanner still fired: C2/cxa+a3warm/r1 shows 15 live-campaign-path hits and **101 hits of the post-anchor keep commit `053c3bd82`** with **0** sandbox denials, and C4/cxa+a4fix 21 campaign-path hits. The scanner counts needle mentions, not successful reads, so it cannot tell a denied attempt from a leak; but 101 future-commit hits with no denial means some allowed path exposes post-anchor state. The planted-read probe has not been run. Not flipped.
  - [x] **UFH14-A6a — find the a3warm `053c3bd82` leak path and run the planted-read probe.** ✅ 2026-10-30 [belief: cc] (filed 2026-10-04) Locate where the 101 hits enter the transcript (scratch clone refs, a bundle file, an allowed binary/log path), close it in `sandbox3.py`'s policy, and make `scan_contamination` cross-check each hit against the denial log. Then the planted read of the live campaign store must fail on a real call.
    - Source closure: research `276d75fab38b5c541624daba29affb7bc8dbbd4b` adopts the fixed policy/driver at `scripts/harness/ds41_c95/`. Historical event22 proves a successful read of relocated future anchor007; C2 now grants only its own006 and two input records. A real native Gemma1B proxy call in that policy denied both planted reads and retained own read/writes; six source tests plus lint/CLI portability checks pass. Raw101-hit history is retained. Future source emits exclusive pre-exposure provenance and refuses reused output directories. The former rc75 control was post-request drain, not in-flight cutoff; its compute packet is held DRAFT. No full27B efficacy or parentA6 standing-condition completion is claimed. [Evidence](../../artifacts/compute/refactor-a6-source-build-ready-20261030.json).
- [ ] **UFH14-A5.** Phase A verdict: which fixes measurably change P(keep), wall time and prefill seconds on the 27B. Wire the results to the belief kernel; VB-DS41-C95 already exists, so extend it rather than adding a new ladder.
- [ ] **UFH14-A7 (intake P7). Hybrid re-prefill when the next turn's history diverges inside the previous output.** Code read of frozen v10 `ffc1bac82` plus the F12 wire logs. Report and scripts: `/mnt/raid0/llm/tmp/p6p7-20261003/`.
  - **Mechanism.**
    - Context checkpoints are created at only one call site, in the prompt-processing loop (`tools/server/server-context.cpp:3725`).
    - They are taken at user-message starts and at 4+n_ubatch and 4 tokens before the prompt end (`:3640-3666`, `:3696-3726`).
    - None is taken during or at the end of generation. `--ctx-checkpoints` (default 32) and `--checkpoint-min-step` (default 8192; `common/common.h:633-634`, `common/arg.cpp:1520-1535`) govern prefill only.
    - The intake guess that every turn recomputes the previous output (intake-1827#record notes) is **refuted for the common case**. When the next prompt extends the cached tokens exactly, the live recurrent state is already at the end of the previous output and is used as is. On 179 of 230 follow-on F12 turns, `cache_n` = previous prompt + previous output, with zero re-prefill.
    - The checkpoint matters only when the re-rendered history differs from the generated tokens. The hybrid `pos_min` test (`:3397-3399`, `:3450-3464`; recurrent `seq_rm` rolls back at most `n_rs_seq` tokens, `src/llama-memory-recurrent.cpp:191-200`) then forces a restore, and the newest usable checkpoint is the previous prompt end minus 4.
  - **Measured.**
    - 41 of 230 turns (17.8%) show `cache_n` = previous prompt − 4 exactly, with re-prefill = previous output + 4.
    - Cost: 224,863 tokens and 705 s over 8 calls, 14.8% of all prefill time and 2.5% of wall time.
    - Divergence points come from `selected slot by LCP similarity` in the server-window logs (35 turns). 13 diverge in the first third of the previous output (reasoning), 10 in the middle, and 12 in the last 10% (message or tool-call tail).
    - An end-of-generation checkpoint would save **0** tokens, because every divergence precedes the end.
  - **Next steps, in order.**
    1. *Root cause, no code.* Set `LLAMA_SERVER_SLOTS_DEBUG=1` on the next :8083 relaunch. It prints the old and new tokens at the mismatch (`server-context.cpp:3407-3447`). Then classify each case: template re-render (fix in `epyc-qwen3x-v1-terse.jinja` or the Responses-to-chat conversion) or non-canonical re-tokenization of sampled text. A render-side fix recovers up to the full 705 s per 8 calls.
       - *Infra ready, 2026-10-03 (workspace-ec; a note only, the step stays workspace-89's).* No hand edit at relaunch
         is needed. Orch main aa1d6894 adds `orchestrator_stack.py reload architect_critic --diag-env-override
         LLAMA_SERVER_SLOTS_DEBUG=1 --experiment-id <ID> --override-ttl-s <N>` (N ≤ 14400). The override is recorded
         in `logs/env_overrides/<component>.json` and attested as a declared, time-bound warning (an ERROR after
         expiry). `python -m scripts.server.env_override readback --port 8083 --expect-declared` proves it, and a
         plain `reload` undoes it. Agreed scope: the A3/A4 multi-turn GPU window only, TTL ≤ 4 h (re-apply if longer).
         With debug ON, every `/slots` GET detokenizes the full slot prompts in the server loop, so it is not for heavy
         traffic. Applying it is UFH14-DIAG-EC-a below.
    2. *Only if the cause cannot be removed: experimental-tree code on `llama.cpp-experimental`.* Add generation-time checkpoints every N generated tokens for RS/hybrid slots, in the decode path beside the existing per-round speculative checkpoint (`server-context.cpp:3146-3184`). Each is about 144 MB of 27B linear state (`intake-1847#01`). Restore then lands at the last checkpoint at or before the divergence point. Replayed savings on the 35 located turns: N=1024 saves 92k tokens and 270 s (38% of the class); N=2048 saves 82k and 237 s; an ideal checkpoint exactly at the divergence point saves 105k and 309 s. No flag change in v10 achieves this.

## Phase B — generalize, model-agnostic

Client and harness side (ak-ds41-main):

- [ ] **UFH14-B1.** Move the demonstrated client fixes (D1–D5) out of the C95 experiment drivers (`/mnt/raid0/llm/tmp/ds41-c95/run2.py`, `proxy2.py`) into shared, model-independent harness settings. Targets:
  - the AutoKernel actor launch (`epyc-inference-research` actors.py);
  - the opencode and codex provider configs used with local models;
  - the orchestrator's own agent-loop compaction (HS-4).

  Each parameter is derived from the serving server's measured prefill rate and slot context, never hardcoded for one model.
  - [x] **UFH14-B1a — research side: F1/F2 in the AutoKernel actor seats.** ✅ 2026-10-03 — research `70f6b9f4` on main: `actor_serving.py` (F1: window from the server's `/props`, prefill rate from the orchestrator's serving-call records, idle timeout = 2 full-window prefills × 1.25 clamped [600 s, 4 h], compaction ≤ 0.76 of the window) for opencode seats on a LOCAL llama-server; F2 (`answer_protocol="f2"`, JSON-first, forced answer at 0.65 of the planner budget) planner only. Hosted providers and the codex/claude CLIs are untouched; `codex_config_overrides()` is the extension point.
  - [x] **UFH14-B1b — orchestrator side (HS-4 agent-loop compaction) — on workspace-ec's branch.** Flip when it lands on orch main with a live call. ✅ 2026-10-04 (workspace-ec)
    - Landed on orch main `ff92a580` (3a326a7c F1 as proposed, 1d03d9b4 F1 review fixes, cd5d7d97 compaction,
      63855968 F2, ff92a580 fixes). API-only reload → PID 3858207 (`ps` lstart 02:06:46Z;
      `/mnt/raid0/llm/tmp/ufh14-b1-ec-review/reload.out`). Live calls: the four 02:49–02:51Z :8083 passthrough records
      in `logs/serving_calls/serving_calls.jsonl` carry the new `serving_params` block.
    - Review fixes against workspace-89's proposal: `doomed` was overstated ~2.5x and is now judged against one
      prefill of the UNCACHED tokens; a sample-cache eviction bug was fixed; the design note's clamp claim was wrong
      (with any deadline the clamp returns the remaining budget, so F1 can only RECORD `doomed` under a deadline); the
      passthrough derivation now runs before the gate and the body stays verbatim.
    - Compaction finding confirmed: `TaskState.context` never reaches a turn prompt. Fixed always-on: a
      deterministic compaction index, and the overflow path no longer force-compacts; a test proves turn prompts are
      byte-identical.
    - Flags, all OFF (attested by the drift check, `t-drift.log`): `derived_prefill_timeout`, `repl_answer_force`,
      `session_compaction_llm_index`. Always-on: the deterministic index, the overflow path, the `serving_params`
      record block, the cache fix.
    - Tests: 45 new, 921 related, drift check, all rc 0 (`/mnt/raid0/llm/tmp/ufh14-b1-ec-review/t-*.log`). The first
      run had 5 failures: 4 from a fake backend `infer` signature in the test, 1 a real 7-char cap overrun (the
      separator), fixed in ff92a580.
    - Observed on the live records: `prefill_source: "unmeasured"` and `allowance_s: 0`, so no long call has been
      priced yet; the corrected-`doomed` window (B1d) starts only once records show a measured source.
  - [ ] **UFH14-B1c — opencode/codex provider configs used with local models outside the actor seats.** Apply the same derived parameters.
    - *(Annotation, workspace-ec, 2026-10-04.)* opencode half APPLIED with the operator's explicit OK
      (AskUserQuestion, 2026-10-04): `/home/node/.config/opencode/opencode.jsonc` `headerTimeout`/`chunkTimeout` =
      14,400,000 ms for `qwen-local` and `qwen-gpu`; backup `/mnt/raid0/llm/tmp/ufh14-b1-20261003/opencode.jsonc.bak-20261004`.
      Codex half: the template `/mnt/raid0/llm/tmp/ufh14-b1-20261003/codex-local-provider-template.toml` was handed to
      workspace-89 for their CODEX_HOME. Not ticked until the codex half is applied.
  - [ ] **UFH14-B1d — STACKCHANGE: per-role request timeouts cannot cover a full-context prefill.** (filed 2026-10-04,
    workspace-ec, from the B1 review) Item: [`docs/design/ufh14-b1-timeout-stackchange-item-20261003.md`](../../docs/design/ufh14-b1-timeout-stackchange-item-20261003.md)
    (durable copy of `/mnt/raid0/llm/tmp/ufh14-b1-20261003/orch/STACKCHANGE-ITEM.md`). Recommendation: **Option A** —
    the role value becomes the decode SLA (values unchanged, registry COMMENT-only changes) and `resolve_timeout` adds
    the derived prefill allowance, which is also what lets `derived_prefill_timeout` survive the dispatch clamp. Check
    `ingest_long_context` first (300 s; doomed above ~77k tokens on :8083, yet it is the long-document overflow
    target). **Reject Option C** (raise constants: hand-picked, wrong after the next relaunch). Gate: HELD until one
    window of CORRECTED `serving_params.doomed` counts per role exists (records with a measured `prefill_source`, after
    1d03d9b4). Then one stack-change package, operator signature.
  - [ ] **UFH14-B1e — port the `PROVISIONAL(answer)` REPL primitive behind its own flag, default off.** (filed
    2026-10-04, workspace-ec; not ported in B1b) Design: `/mnt/raid0/llm/tmp/ufh14-b1-20261003/orch/DESIGN-NOTE.md`
    "JSON-first and last-complete": a non-terminal primitive storing `state.provisional_answers`; at max turns
    (`repl_executor.py:771`) the answer is the last provisional that validates against `output_schema`. Done when it
    lands flagged off with tests, and an A/B task for enabling it is filed.
  - [ ] **UFH14-B1f — wire the per-turn thinking budget behind its own flag, default off.** (filed 2026-10-04,
    workspace-ec; not ported in B1b) `serving_params.thinking_budget_fields()` is on orch main but unused. Thread
    `ChatRequest.thinking_budget` per turn (RI-23 override pattern, `llama_server.py:150-170`) and merge the fields
    into the chat-lane body after `chat_template_kwargs`; chat lane only. Done when it lands flagged off with a test
    that the body carries `thinking_budget_tokens` only when the flag is on.
  - [ ] **UFH14-B1g — enable decision for `repl_answer_force` (F2).** (filed 2026-10-04, workspace-ec; the
    enable task for a fix that landed OFF) A/B on the eval tower: forced-answer turn at 0.65 of the request budget vs
    off; rescue rate and accuracy per suite. `derived_prefill_timeout`'s enable rides B1d (Option A). Declined, not
    filed: enabling `session_compaction_llm_index` — OFF is the intended posture, because the compacted field is
    never rendered into a turn prompt.
  - [x] **UFH14-B1h — retire `DEFAULT_PREFILL_FLOOR_TPS = 250` (`kv_pool_admission.py:169`) for the measured rate.** ✅ 2026-10-29 [belief: cc]
    (filed 2026-10-04, workspace-ec, from the B1 design note's "other constant to retire next") The long-prefill lease
    expiry should read `serving_params.rate_at(samples, prompt)`, keeping 250 as the floor. Done when the lease
    expiry uses the measured rate with a test, and the env override still wins.
    Landed on orchestrator main as `a446ae62c4ff718acab7eb6070f6818db63908e8`: current-launch
    per-port samples select the rate at whole-context depth; lease duration uses the uncached suffix,
    retains the 250 tok/s fallback/floor, and honors valid explicit environment overrides (including zero).
    Sample resolution runs outside the admission condition lock; expiry starts at actual acquisition.
    Validation: 117 relevant tests passed, Ruff and diff checks passed. Source closure only; no API reload
    or deployed throughput claim.

Orchestrator and stack side (workspace-ec; items are linked here as they land):

- [x] **UFH14-B2.** ✅ 2026-10-03 (workspace-ec) — orch 2586a7bb on main, API reload: scouts reserve prompt+max_tokens on the token gate; one long prefill (≥16384 est. tokens, env ORCHESTRATOR_KV_POOL_LONG_PREFILL_TOKENS, 0=off) per server, lease ends at first chunk or prompt/250 tok/s; /slots observation holds long requests behind any slot prefilling ≥4096 (covers other uvicorn workers + direct clients like C95); per-request cap = min(slot ctx, model ctx_max). 32 new tests; 4126 related pass. Live alias call via gate ok. Remaining limits: per-worker gate (cross-worker via /slots only), whole-prompt size even when mostly cached; ungated paths documented in /mnt/raid0/llm/tmp/kv-gate-8083-ec/BYPASS.md (action_repair_completer if pointed at :8083; prewarmer only :8074). Was: Token-aware pool gate, keyed per server: one long prefill at a time, with all orchestrator traffic, scouts included, going through it. Covers D7. Operator-approved 2026-10-03; deployed as an API-only change. In progress (workspace-ec): orch branch `feat/kv-pool-gate-8083-ec`; tracked as KVU-15 in `kv-unified-stack-rollout.md`.
- [x] **UFH14-B3.** ✅ 2026-10-03 (workspace-ec) — LIVE: :8083 relaunched 13:14:35Z (PID 4052768) with `-c 393216` unified, per-slot cap 262144 (server log `n_ctx_slot = 262144, kv_unified = 'true'`), draft n-max 7; API reload (PID 4054223) reads per_request 262144 / shared_pool / pool_tokens 393216; load peak 50.78 GiB; alias completion via :8000 correct; pipeline `check --run-promotion-gate` all ok. Receipt RATIFY-STACKCHG-KVPOOL-20261003; research 412e8fc1, orch 09e91e1e + 841935ea, root 64d70d17; evidence `/mnt/raid0/llm/tmp/stack-change-kvpool-20261003/`. Detail is KVU-16 in `kv-unified-stack-rollout.md`. Was: KV-pool sizing as a per-model stack rule: slots × expected context, plus a per-request cap. The :8083 instance is a relaunch with `-c 393216` unified and a 262144 per-request cap (stack change, operator signature). Covers D6.
  - [x] **Open sub-task: the full-pool concurrent-residency proof.** The 4 × 90k probe held (all 200, zero memory-slot ✅ 2026-10-29 (audit: kv-unified-stack-rollout.md:220 KVU-16b [x] PASS 2026-10-26 324673 resident cells all 4 decoding (>=300k gate), KFD 48.57 GiB; KVU-16c also [x] (:415)) [no-belief: audit-reconciliation]
    lines, KFD peak 51.73 GiB) but peaked at 92,343 cells in flight, under its 300k criterion, so residency is UNPROVEN,
    not disproven. Tracked as KVU-16b (corrected probe) / KVU-16c (cite workspace-89's P3 run).
    2026-10-03: KVU-16c resolved as NOT citable (P3 A1 ran `--no-cache-idle-slots`, and `/slots` showed 156,971 resident
    tokens), so KVU-16b's corrected probe is the proof.
- [ ] **UFH14-B4.** Prefix-cache and `--cache-ram` policy per server. Covers D5 and D6 on the server side.
  **API part DEPLOYED 2026-10-03 ~14:50Z (UFH14-DEPLOY-EC: orch main, API PID 1628390); policy not applied.**
  The first post-reload serving records carry `request.prefix_fp`; they are the 3 refused passthrough calls at
  14:51-14:58Z, so no dispatched call has been fingerprinted yet. The `missed_prefill_share` window (B4a) starts when
  :8083 is restored (KVU-16e). Earlier state: **DESIGNED + API part BUILT 2026-10-03** (workspace-ec): design
  `docs/design/ufh14-b4-prefix-cache-policy-20261003.md`; orch commits 61873d75, acb5a816, 1c3f8e77, c14a098d, 8f354ac3
  (integrated on `integ/api-reload-2-ec` 10bc5681). Key fix: router `id_slot` pinning hashed the prompt's first 256
  characters, so every call of a role went to ONE slot and v10 deferred it while other slots were free; pinning is now
  opt-in (`ORCHESTRATOR_PREFIX_ROUTER_PIN_SLOTS=1`). Instrument: `missed_prefill_share` (lower = better) from
  `scripts/analysis/prefix_cache_report.py`. Not ticked until PFX-SEL-1 lands; the sub-tasks below are the remainder.
  **2026-10-03 ~15:40Z — `prefix_fp` PROVEN on dispatched calls (passthrough lane).** After the :8083 restore, the three
  dispatched passthrough calls to :8083 at 15:39:37-15:39:39Z (`outcome=ok`, orch_commit aa1d6894) carry
  `request.prefix_fp`, with `timings.cache_n` 0 / 155 / 155 (`logs/serving_calls/serving_calls.jsonl`, read-only). The
  primitives lane has no post-deploy dispatched record yet: the only primitives records since the deploy are two
  `/chat` sub-calls that timed out at placement (15:39-15:41Z) and carry no `request` block. So the primitives-lane
  half of the B4 proof waits for one dispatched primitives call (UFH14-DEPLOY-EC-2). Records after 15:43:08Z are from
  the SLOTS_DEBUG window (DIAG-EC-a); they are fine for `missed_prefill_share` but are tagged `UFH14-A7`.
  - [ ] **UFH14-B4a — PFX-SEL-1 stack-change package, after a metric window.** Design §3.8 / §4.4: master
    `prefix_cache` per model, topology `prefix_cache_selection`, compiler + launcher + drift checker. No launch flag
    changes today (derived values equal today's). Prepare it after ≥ 1 window of ≥ 200 post-deploy calls gives a
    `missed_prefill_share` baseline; one package, operator signature. Raise :8083 `--cache-ram` 65536 → 102400 only if
    §4.3's decision rule fires (> 5% across two windows, with evictions logged).
  - [ ] **UFH14-B4b — A/B: the stable head as a system message (design R2, §4.2 item 1).** Split the prompt at a
    builder-emitted marker into `[system, user]` on the chat lane behind a flag; A/B on the eval tower (quality) and
    `missed_prefill_share` / `hit_tok` for REPL roles. Largest expected win on hybrids.
    - *(2026-10-05, workspace-ec)* Runbook (flags, arms, windows, report invocation, rollback):
      `/mnt/raid0/llm/tmp/ufh14-b4-20261005/B4bcd-RUNBOOK.md`. Needs code: a builder marker after `## Rules` and a new flag (proposed `stable_head_system_message`).
  - [ ] **UFH14-B4c — A/B: `prefix_stable_order` on in production (design R1, §4.2 item 2).** `src/features.py:236`;
    composes with B4b, same A/B protocol.
    - *(2026-10-05, workspace-ec)* Runbook (flags, arms, windows, report invocation, rollback):
      `/mnt/raid0/llm/tmp/ufh14-b4-20261005/B4bcd-RUNBOOK.md`. Flag exists (`prefix_stable_order`). Flips live with `POST :8000/config`, no reload. Persists in `runtime_flags.json` across reloads.
  - [ ] **UFH14-B4d — A/B: move CoT prefixes and worker RAG snippets to the tail (design R6, §4.2 item 3).**
    `graph/helpers.py:936-940` (CoT before the system prompt), `corpus_retrieval.py:739-780` (`## Reference Code`
    before `## Task`).
    - *(2026-10-05, workspace-ec)* Runbook (flags, arms, windows, report invocation, rollback):
      `/mnt/raid0/llm/tmp/ufh14-b4-20261005/B4bcd-RUNBOOK.md`. Needs code and a new flag (proposed `per_query_material_at_tail`). Design missed two CoT-prefix sites: `api/routes/chat.py:1642-1644`, `chat_pipeline/stream_adapter.py:365-367`. RAG half disabled (`rag_enabled` ABANDONED).
  - [x] **UFH14-B4e — delete `escalation_prewarmer` (design §4.2 item 5, delete-lens 4).** It warms
    `ARCHITECT_SYSTEM_PREFIX`, a string no real architect request contains (`escalation_prewarmer.py:61-65`); A3's
    client-side warm + stagger is where warming belongs. Review, not A/B: it changes no model input.
    - *(2026-10-05, workspace-ec; DEPLOYED.)* Deleted on orch `feat/ufh14-b4-cleanup-ec` @ `621791f0` (merged as fe07865f).
      Removed the turn-1 launch site `graph/helpers.py::_maybe_prewarm_architect` and the two `record_prewarm_hit` attributions
      in `graph/nodes.py` / `graph/langgraph/nodes.py::_record_escalation_role`. Blast radius (LOW, 3 importers); every call
      site was fire-and-forget or inside `try/except`. OAB-3 quiescence acceptance test now injects CPU burn behind MemRL
      q-scoring launch instead. API reloaded 08:02Z; 757 combined tests pass.
  - [ ] **UFH14-B4f — belief-kernel write side for the per-port prefix-cache report.** Add the report's per-port rows as
    a projection under B5's `serving_calls` adapter row in `scripts/vidya/adapters/README.md`. Row text PREPARED for the
    owning session in `/mnt/raid0/llm/tmp/wrapup-ec-kvu16/INDEX_ROWS.md`; read side rides VB-SERVE-TIMING-1.
  - [ ] **UFH14-B4g — re-measure the 27B DFlash2 prompt-cache entry cost (design §4.4).** It was to ride B3's relaunch
    (`-lv 4` lines `prompt_save … total state size … (draft: …)` and `created context checkpoint … size`). If those lines
    are not in the 13:14Z bring-up log, capture them at the post-X0 restore (KVU-16e); feeds PFX-SEL-1's entry cost.
    - 2026-10-03 (workspace-ec, read-only log read): the lines are logged at default verbosity, so `-lv 4` is not
      needed, but they appear only when a long prompt is saved. None exist yet on the 393216 / n-max-7 instances
      (`logs/llama-server-8083.log` from line 223777: the 13:14Z, 15:35Z and 15:43Z launches; only short calls since).
      The previous shape (np 4 / 196608, spec `n_max=4`, lines 130227-130857) gives a prior: 1631.2 MiB at 39,875 tokens
      (draft 156.7 MiB) and 3306.0 MiB at 84,951 tokens (draft 333.8 MiB), ≈ 40-42 KiB per token. Still open: read the
      first `prompt_save` line on the current shape once a long call lands.
    - 2026-10-03 (workspace-ec): runner prepared, dry-run OK: `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/b4g_entry_cost.py` (RUNBOOK step 5, :8083
      serving with its roles parked). It parses the log window and triggers one long call only if no `prompt_save`
      line exists yet; it reports MiB per 1k tokens, fixed MiB and R². Runs in the coordinated GPU block after ~18:15Z.
    - **2026-10-04 (workspace-ec): ran 03:53-03:59Z, INCONCLUSIVE.** The log window (bytes 27334737-27542756 of
      `llama-server-8083.log`, the current 393216 / n-max-7 launch) holds **zero `prompt_save` lines**, even after the
      runner's four long calls (8k / 24k / 48k / 72k tokens, all HTTP 200). One `cache_ram` eviction of 1532.4 MiB was
      logged. Output: `artifacts/gpu-block-27b-20261004/results/b4g/` (with `step5-b4g.out`). The prior from the old
      shape stands (37.155 MiB/1k, fixed 149.6 MiB). B4g-1 (2026-10-05): TRACE-level lines, so re-run on a scratch relaunch with `-lv 4` (recipe in B4g-1).
    - [x] **UFH14-B4g-1 — find out why no `prompt_save` lines appear on the current shape, before re-running B4g.**
      ✅ 2026-10-05 (workspace-ec): the cause is **log verbosity**, not a save path that stopped running. In v10
      (`ffc1bac82`; identical in v9) `prompt_save`'s "saving prompt with length" (`server-context.cpp:280`),
      "saving idle slot" (`:2472`), "created context checkpoint" (`:2408`) and "cache state" (`server-task.cpp:1858`)
      are `SRV_TRC`/`SLT_TRC` = TRACE (level 4) (`common/log.h:115`, `server-common.h:19,26`). The default threshold
      is 3 (`common/log.cpp:29`). `common/log.cpp:441-447` also maps every ggml/libllama INFO line to TRACE, which
      explains KVU-16b's missing startup memory/KV lines. The eviction lines ("making room for prompt cache entry",
      `server-task.cpp:1719`) are WARN, so they print at 3, which is why the 1532.4 MiB eviction appeared. The 489
      old lines came from exactly two launches started with `LLAMA_ARG_LOG_VERBOSITY=4` (log lines 21434 and 35063:
      266 + 223). All 22 other launches, including the current one and both B4i scratch launches, run at 3 with
      zero such lines. No launcher sets verbosity. The 2026-10-03 note "logged at default verbosity" was wrong:
      upstream moved these lines to TRACE in #23021 / #25078.
      **B4g re-run recipe:** a scratch relaunch with the production argv plus `-lv 4` (or env
      `LLAMA_ARG_LOG_VERBOSITY=4`; not `-v`, which floods DEBUG). Fallback at 3: the WARN eviction lines' entry size
      plus `/slots` `n_tokens` (`/metrics` has no prompt-cache gauge). Note:
      `/mnt/raid0/llm/tmp/ufh14-b4-20261005/B4g-1.md`. Suggested follow-up (not filed): record `LLAMA_ARG_*` env in
      `logs/server_launches/launches.jsonl` so an env-set verbosity is auditable.
  - [x] **UFH14-B4i — evaluate `--no-cache-idle-slots` per server (filed 2026-10-03, from workspace-89's P3 code read).**
    ✅ 2026-10-04 (workspace-ec) — OFF wins on :8083's shape; the stack change is UFH14-B4j.
    v10 defaults `cache_idle_slots` ON: with `--cache-ram` + `--kv-unified`, every idle slot is saved to RAM and cleared
    from the KV pool as soon as any new task starts (server-context.cpp:2469-2483). So on :8083 a paused agent context
    never stays resident in VRAM, and its next turn pays a RAM restore (or a cold prefill after one of the 929 evictions).
    A/B per server, both arms read with `prefix_cache_report.py`: per-turn agent latency, `hit_tok`, `missed_prefill_share`,
    `cache_ram` evictions, and VRAM headroom. Default ON against OFF. OFF keeps idle contexts resident, but the pool then
    fills with idle cells. Whatever wins becomes a PFX-SEL-1 field.
    - 2026-10-03 correction (P3 report): the purge is a code read. P3 A0, at the exact production flags, did NOT
      reproduce it (the neighbour slot held 0 tokens, so the path never ran). Arm ON of this A/B must first show that the
      purge happens on organic traffic (`saving idle slot` lines plus `/slots` `n_tokens` dropping on a busy neighbour),
      or the A/B has nothing to compare. This replaces a separate A0 re-run, which is not filed.
    - **2026-10-03 second correction (workspace-ec, read-only log read): the purge is real on organic traffic.**
      `logs/llama-server-8083.log` holds 211 idle-slot purges of non-empty slots (lines 35430-130878, 11.5 M tokens;
      latest line 130621, `id 2 | clearing prompt with 84951 tokens`), all at the previous np 4 / 196608 kv-unified
      shape. So the A/B has something to compare. Arm ON still has to show the purge at the current 393216 shape,
      which is a smaller precondition than proving it at all.
    - Runner prepared, dry-run OK: `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/b4i_idle_slots_ab.py` (RUNBOOK step 6). It runs on a scratch :18083 with
      :8083 STOPPED for VRAM: the production argv with `--no-cache-idle-slots` for arm OFF, captured-PID launch and
      kill scripts, and a linkage plus KFD proof at launch. Runs in the coordinated GPU block after ~18:15Z.
    - **2026-10-04 (workspace-ec): A/B DONE on scratch :18083 (:8083 stopped), production argv ± the flag.** Each arm
      ran 3 conversations × 6 turns, a ~20k-token base plus ~1.5k per turn, 200 generated tokens, 18 turns, 0 errors.
      Evidence: `artifacts/gpu-block-27b-20261004/results/b4i/` (ON `ON-r1-20261004T040819Z`, OFF
      `OFF-r1-20261004T042211Z`, launch scripts and scratch logs).

      | metric | ON (default) | OFF (`--no-cache-idle-slots`) |
      |---|---|---|
      | turn-2+ TTFT median | 66.4 s | **16.3 s** |
      | turn-2+ TTFT p90 | 81.0 s | **19.2 s** |
      | `hit_tok` | 0.81 | 0.81 |
      | KFD peak | 51.71 GiB | 51.71 GiB |
      | decode mean | 18.8 tok/s | 20.8 tok/s |
      | idle-slot drops seen on `/slots` | 9 (20–29k tokens each) | 0 |

      - The precondition holds: arm ON purged idle slots at the current shape (9 drops on `/slots`). No `saving idle
        slot` log lines appeared at verbosity 3; see B4g-1.
      - The cached-token share is the same in both arms; ON pays a RAM restore on every resumed turn, at ~4× the
        TTFT. VRAM headroom is unchanged at this load.
      - Caveat: one rep per arm, and only 3 conversations, so the pool never filled with idle cells. The pool-full
        side of OFF is bounded by KVU-15's admission and by the B4j package's capacity check, not by this A/B.
  - [ ] **UFH14-B4j — stack change: `--no-cache-idle-slots` on :8083, as a PFX-SEL-1 field.** (filed 2026-10-04,
    workspace-ec, from B4i) Make `cache_idle_slots: false` a `prefix_cache_selection` field for :8083 (design §3.8),
    and ship it in ONE package together with KVU-16f's `-b 512 -ub 512` once that A/B is done
    (`kv-unified-stack-rollout.md`). The package must state the pool-full behaviour with idle contexts resident:
    which admission path refuses or evicts when 4 idle agents hold the pool. One operator signature. Done when :8083's
    live argv carries the flag, `check --run-promotion-gate` is green, and the first post-change `missed_prefill_share`
    window is recorded under B4a.
    - *(2026-10-04 ~08:00Z, workspace-ec; not ticked until signed and serving.)* Packaged with KVU-16f as
      `STACKCHG-8083BATCH-20261004` (`/mnt/raid0/llm/tmp/stack-change-8083-batch-20261004/PACKAGE.md`, part A here,
      part B `-b 512 -ub 512`): `--validate-only` VALID, **greenlit by workspace-ec, awaiting the operator's terminal
      signature** (`ratify_stackchg_8083batch_20261004.sh`, token `RATIFY-STACKCHG-8083BATCH-20261004`, TTY-gated). It
      applies at the :8083 restore after YaRN E1 (one relaunch). Detail: `kv-unified-stack-rollout.md` KVU-16f.
    - *(2026-10-23, workspace-f8, code reading at 49550eda5 from the LB7 prep; check before the amendment quotes it.)* (1) Explicit `id_slot` on a slot cleared by cache-idle-slots skips the RAM restore: `f_keep` = 0/0 = NaN (server-context.cpp ~:1718), the `< 0.5` test (~:1726) is false, so `prompt_load` never runs and the turn re-prefills from zero; only `id_slot=-1` LRU (~:1752) restores. (2) The task-text claim "explicit id_slot reuse overwrites the victim without saving it" is WRONG at default `slot_prompt_similarity 0.1` (the victim is saved first); it holds only with `--slot-prompt-similarity 0`. (3) Pool full with idle contexts resident (OFF arm): `try_clear_idle_slots` (~:1787, called ~:4252) purges idle slots with NO RAM save (WARN `purging slot N with M tokens`), so the dropped conversation's next turn is a cold prefill.
    - [x] UFH14-B4j.1 — fold the three code-reading findings above into the B4j package amendment (correct the id_slot overwrite claim; account for the NaN f_keep restore skip and the OFF-arm purge-without-save) once UFH14-LB7 attributes the stall. ✅ 2026-10-24
      - *(2026-10-23 15:45Z, f8 late-afternoon wrap-up.)* UFH14-LB7 ended UNATTRIBUTED, not with an attribution, so this box's trigger has not fired; next stage UFH14-LB7.1. The three code-reading facts above do not depend on the attribution. Report-only from LB7: the ON penalty is mostly prompt-cache restore copies (OWN + OTHER median f 0.79, at 0.117 GiB/s); neighbour idle saves are about 0.2 of it.
      - *(2026-10-24, workspace-f8 sweep.)* **Amendment written:** `/mnt/raid0/llm/tmp/stack-change-8083-batch-20261004/AMENDMENT-B4j1-20261024.md`. It is informational and needs no new signature: the package was signed 2026-10-05 (receipt `receipts/RATIFY-STACKCHG-8083BATCH-20261004.json`) and part A is applied (`cache_idle_slots: false`), and nothing applied changes.
        - The three code facts were re-verified by source read at `49550eda5`; `server-context.cpp` is byte-identical at the current champion `dcc853b55`, and `get_available_slot`/`try_clear_idle_slots` are byte-identical in production v10 `ffc1bac82` (v10 lines :1647/:1655/:1679/:1716/:3798).
        - Correction kept: at the default similarity 0.1 an explicit-`id_slot` victim IS saved. It is overwritten unsaved only with `--slot-prompt-similarity 0`, or when the new prompt keeps ≥ 50 % of the victim's tokens (`f_keep ≥ 0.5`: its tail is lost).
        - Pool-full statement the package owed (4 idle contexts resident, OFF): the decode-time `try_clear_idle_slots` evicts idle slots one per retry in slot order (not LRU), with no RAM save, then halves `n_batch`. Nothing refuses at this layer.
        - The trigger resolved as **no rule attribution**: UFH14-LB7.1 ended `NOT_REPRODUCED`. Per its A1.7 ("in every case"), this box receives the verdict, the target/draft split and the three facts. Report-only, 98.7-100 % of ΔW is target-state restore transfers, TRANSFER_COUNT_BOUND, and draft bytes are 4.0 %. That restore cost is the only measured lever, and it is already applied.
  - [x] **UFH14-B4h — remove the dead slot-save warming path (delete-lens 2 and 6).** `--slot-save-path` /
    `save_hot_prefixes` / `restore_hot_prefixes` have no production caller and lose hybrid checkpoints;
    `canonicalize_prompt` is dead weight with pinning off. One cleanup commit with an upstream gitnexus impact first.
    - *(2026-10-05, workspace-ec; DEPLOYED.)* Deleted on orch `feat/ufh14-b4-cleanup-ec` @ `621791f0` (merged as fe07865f).
      Hot-prefix slot-save warming path removed. `--slot-save-path` KEPT (KV migration and kv_compress.py use it).
      `canonicalize_prompt` KEPT (does not run with pinning off; KPF-23 owns its fate). gitnexus impact: 0 callers (LOW).
      API reloaded 08:02Z; 757 combined tests pass.
  - Declined, not filed: adding `cache_prompt` to the direct callers that omit it (`worker_pool.py:855-867`,
    `tools/web/research.py:709-716`, design §4.2 item 6) — the server default is `true`, so the edit changes nothing;
    the design says add it when next touched. Declined: `--cache-reuse` as a generic knob (design §3.6, unsound on
    every model we run).
- [x] **UFH14-B5.** ✅ 2026-10-03 (workspace-ec) — orch c6225e8b/f7fad574/9a0d38e0 on main, API reload 04:59Z: per-call records in `logs/serving_calls/serving_calls.jsonl` (role, request_id, queue wait, llama `timings`, outcome incl. cancelled), chat-stream `prompt_eval_ms` fixed (live :8083 call: 2368 ms), progress rows flushed durably, launch/stop banners + `logs/server_launches/<port>.json` at each server's next stack launch; era ST1 (orch 4e23e553); write-side adapter row in `scripts/vidya/adapters/README.md` (root 999954ca), read side = VB-SERVE-TIMING-1 (open). Was: Serving telemetry: a launch banner with ISO-UTC, pid, role and argv; per-call role, request_id and llama `timings`; `prompt_eval_ms` filled in; cancel summaries; queue wait. Plus the belief-kernel write-side adapter, owned by workspace-ec. Covers D8.
- [x] **UFH14-B6.** ✅ 2026-10-03 (workspace-ec) — LIVE and proven on :8083, see the proof below. An OpenAI-compatible passthrough on :8000 for a named role (chat/completions and responses, streaming, tools, timings echoed), so harness experiments can go through the gate instead of hitting servers directly. The gap list is pending from workspace-ec. Gap analysis in progress (workspace-ec): `/mnt/raid0/llm/tmp/kv-gate-8083-ec/BYPASS.md`.
  **BUILT 2026-10-03, NOT LIVE** (workspace-ec): orch 3edfdff3 — `POST /v1/passthrough/{role}/chat/completions` and
  `/responses`, `GET …/models`; raw body forwarded, true SSE streamed unbuffered, server `timings` on the wire, behind the
  full admission gate (KV-pool tokens, one long prefill, host-wide lease after KVU-15a, per-request cap → 413), one
  `serving_call.v1` record per call (`caller.source="passthrough"`), localhost only, `ORCHESTRATOR_PASSTHROUGH=0` kill
  switch. Integrated on `integ/api-reload-2-ec` 10bc5681. The purpose (harness experiments go through the gate) needs
  it live on :8000, so not ticked until UFH14-DEPLOY-EC lands and a live call proves it.
  - **DEPLOYED 2026-10-03 ~14:50Z, pending live verification.** Merged to orch main (10bc5681, now aa1d6894) and
    deployed by an API-only reload (PID 1628390). Live so far: `GET /v1/passthrough/architect_general/models` answers.
    Three completion calls to :8074 (14:51, 14:54, 14:58Z; one streamed) were refused with 503 `lock_unavailable`
    after the 180 s region-admission timeout, blockers `['autokernel-cpu']`. That is by design: DS41 holds every CPU
    region in its build_and_measure window. Evidence: `/mnt/raid0/llm/tmp/integ2-ec/stream-smoke.txt` and
    `logs/serving_calls/serving_calls.jsonl`. :8083 is stopped for workspace-89's X0 window, so the end-to-end proof
    (one streamed call with timings) waits for the restore (KVU-16e). Not ticked until then.
  - **PROVEN 2026-10-03 15:39Z on :8083** (after the KVU-16e restore; `architect_critic`, production flags, before
    the 15:43Z SLOTS_DEBUG relaunch):
    - non-stream chat/completions: correct answer ("56"), with timings;
    - streamed chat/completions: 33 SSE chunks, timings on the last;
    - streamed `/v1/responses`: 27 events ending in `response.completed`, with timings.
    - Each call wrote one `serving_call.v1` record with `caller.source=passthrough`, orch_commit aa1d6894,
      `passthrough.http_status` 200, `sse_events` 0 / 33 / 27 and `request.prefix_fp` (`logs/serving_calls/serving_calls.jsonl`).
    - Gap found: `caller.port` is absent (null) on every passthrough record. Filed as UFH14-B6b.
  - [x] **UFH14-B6b — passthrough records must carry `caller.port`.** ✅ 2026-10-03 (filed 2026-10-03, workspace-ec, from the B6
    proof) Primitives records set `caller.port` (8083, 8070); passthrough records do not. Cause: `write_serving_record`
    replaces the `caller` block that `serving_calls.build_record` built with its own dict, which has `backend_url`
    but no `port` (`src/api/routes/passthrough.py:757-764`). `server.port` is present, so per-port joins work today
    only by reading the other field. Add `port` (parsed from `base_url`, the same value as `server.port`) to the
    passthrough `caller` block, with a test. Done when a passthrough record carries `caller.port` equal to `server.port`.
    - ✅ 2026-10-03 (workspace-ec): orch 0d8455a2 on main, deployed by the API-only reload that shipped 0f0bfa19.
      `write_serving_record` now stages the same `port` and `backend_url` the primitives lanes do. Tests: a served and
      a refused passthrough record both carry `caller.port` (`tests/unit/test_passthrough_route.py`). No live
      passthrough record exists since the reload (`serving_calls.jsonl` last written 15:41Z); the next passthrough
      call, e.g. the GPU-block runner's step 1, shows it live.
  - [x] **UFH14-B6a — passthrough refusal records must name the refusing gate in structured fields.** ✅ 2026-10-03 (filed
    2026-10-03, workspace-ec, from the 14:51-14:58Z refusals) Today a refusal record has `outcome=refused`,
    `dispatched=false` and free-text `error.message`, plus `error.type` (`lock_unavailable`). It has no structured
    field naming the gate: region lock, KV pool, per-request cap or backend semaphore. The blockers
    (`['autokernel-cpu']`) exist only inside the message string, and `passthrough.http_status` is `null` although
    the client received 503. Add `refusal: {gate, blockers, wait_ms}` and the returned status, set on every refusal
    path in `src/api/routes/passthrough.py`, with one test per gate. Done when each gate's refusal record carries
    its gate name and the client's status code.
    - ✅ 2026-10-03 (workspace-ec): orch 52fa84d8 on main, API-only reload. Every passthrough refusal goes through
      `_Refused`, which now builds `refusal = {gate, http_status, retry_after_s}` and puts it in both the HTTP body and
      the serving record (gates: `backend_unavailable`, `admission_queue_full`, `client_closed`, `lock_unavailable`,
      `upstream_unreachable`, `passthrough_error`, `role_parked`; an undispatched `ContextOverflowError` records
      `context_overflow`). Tests: `test_passthrough_refusals_carry_structured_gate` and
      `test_passthrough_returns_503_role_parked_with_refusal_gate` (`tests/unit/test_gpu_window_parked_role.py`).
      The done-when (gate name + client status on every refusal record) holds by construction. Two parts of the
      original spec did not land; they are filed as B6a-1.
    - [ ] **UFH14-B6a-1 — structured `blockers` and `wait_ms` on refusal records, and a test per gate.** (filed
      2026-10-03, workspace-ec, from the B6a landing) The B6a spec asked for `refusal: {gate, blockers, wait_ms}`.
      52fa84d8 ships `gate`, `http_status` and `retry_after_s` only. For `lock_unavailable` the blockers (e.g.
      `['autokernel-cpu']`) are still only inside `detail`, and the wait before refusal is not recorded. Thread the
      region-lock blockers and the measured wait into `_Refused(refusal=...)` at `passthrough.py` `lock_unavailable`
      and `admission_queue_full`. Add one test per gate: today one generic `_Refused` test plus `role_parked` cover
      them. Done when a `lock_unavailable` record carries `refusal.blockers` as a list and `refusal.wait_ms`.
  - [x] **UFH14-B6c — parked-role support for one-off GPU windows (`src/runtime/gpu_window.py`).** ✅ 2026-10-03
    (workspace-ec; built and deployed this session, recorded here so the checklist is complete) orch fa7075f8 +
    52fa84d8 on main, API-only reload.
    - An MI210 window file (`/mnt/raid0/llm/tmp/gpu-window/mi210.json`) parks roles or ports with a holder and an
      expected end. CLI: `python -m src.runtime.gpu_window park|status|restore`.
    - A request that resolves to a parked role or port fails in microseconds with 503 `role_parked` (Retry-After from
      the expected end, holder in the body), instead of connection-refused or a slow timeout. It is checked at every
      choke point: primitives `_real_call` (before the contention gate, role semaphore and region locks),
      `/v1/chat/completions`, the passthrough (models listing too), and a backstop by port in
      `LlamaServerBackend.infer` / `infer_stream_text`.
    - A real request writes `preempt_requested_at` (preempt-on-request), so the window holder can decide to yield.
    - Refusals are recorded as `outcome=refused`, `dispatched=false` with `refusal.gate=role_parked`.
    - Tests: `tests/unit/test_gpu_window_parked_role.py` (345 lines). First live use: the GPU-block runner's step 2
      (`/mnt/raid0/llm/tmp/gpu-block-27b-20261003/RUNBOOK.md`).
    - Stance (operator, 2026-10-03): the upcoming AutoKernel campaign is **CPU-only**, so the standing
      GPU-lending pattern this was built for is moot. Parked-role stays as infrastructure for one-off GPU windows
      (X0-style measurement blocks, KVU-19 P3 re-runs).
  - [ ] **UFH14-B6d — route escalations around a parked target.** (filed 2026-10-03, workspace-ec, the part of
    B6c that was not built) Today a request whose role is parked gets a fast 503 `role_parked`; nothing re-routes
    it. An escalation chain whose next hop is parked (for example `coder_escalation` or `architect_critic` on :8083)
    fails instead of trying the next eligible role. In the routing/escalation layer, treat a parked target like an
    unavailable one: skip to the next role in the chain when one exists, record the skip on the serving record, and
    return `role_parked` only when no alternative remains. Direct role calls and the passthrough keep the 503: a
    named-role caller asked for that role. Done when a test with :8083's roles parked shows an escalation served by
    the next eligible role, with the skip recorded.
  - Declined, not filed: passthrough for multi-endpoint fleets such as frontdoor. Frontdoor returns 422 by design
    (`passthrough.py:236-243`; the KV-pool gate is per URL). No harness experiment targets frontdoor: C95, the
    AutoKernel actor and the opencode/codex local-model configs all address single-endpoint roles. Supporting it
    would mean re-implementing the fleet's endpoint balancing inside the passthrough. The 422 fails loud, so a future
    need surfaces at once. Whether harnesses should ever reach frontdoor is a scope question for UFH14-C1, which
    already covers frontdoor; it is added to C1's scope below rather than filed as a separate task.
  - Noted, not filed: CPU-role passthrough calls cannot run while an AutoKernel window holds all CPU regions. That is
    the region-claim contract working as designed (the orchestrator takes CPU regions per call and waits behind an
    AutoKernel claim), not a defect.
  - Declined, not filed: timings on a NON-streamed `/v1/responses` body. llama-server v10 does not emit them
    (`server-task.cpp:558`) and the kernel is frozen; streamed `/responses` and chat/completions carry them.
- [ ] **UFH14-DEPLOY-EC — deploy orch `integ/api-reload-2-ec` (B6, B4 API part, KVU-15a, RI-18c, test fixes).**
  (filed 2026-10-03, workspace-ec) HEAD 10bc5681, worktree `/mnt/raid0/llm/worktrees/orch-integ2-ec`. Gate: the full
  unit run (`/mnt/raid0/llm/tmp/integ2-ec/full_unit3.log`, in progress at wrap-up) ends 0 failed apart from the known
  order-dependent test (SCG-TEST-ORDER). Then merge to orch main and `orchestrator_stack.py reload orchestrator`
  (API only) once :8083 is restored (KVU-16e). Proofs after the reload: one live passthrough streamed call with
  timings (B6); RI-16 reader shows `review_gate`/`review_verdict` null on live `/chat` (RI-18c); a 2-worker replay
  with peak 1 long prefill and a cached-prefix request not held (KVU-15a); serving records carry `prefix_fp` (B4).
  - [x] **UFH14-DEPLOY-EC-1 — gate, merge and API-only reload.** ✅ 2026-10-03 (workspace-ec). Full `tests/unit` on
    the integration branch: 15979 passed, 0 failed, 57 skipped (`/mnt/raid0/llm/tmp/integ2-ec/full_unit3.log`; main
    had 19 failing before). That run includes conftest fix ac33e623 and the 19 stale-fixture fixes d97004f6 /
    9d40c30b. Merged to orch main as 10bc5681 (now aa1d6894). `orchestrator_stack.py reload orchestrator` →
    API PID 1628390 at ~14:50Z (`/mnt/raid0/llm/tmp/integ2-ec/reload-api.out`). It shipped ahead of the :8083
    restore, so the parent stays open for its live proofs.
  - [ ] **UFH14-DEPLOY-EC-2 — the live proofs, after the :8083 restore (KVU-16e).** Status at 15:00Z:
    - B6: `…/models` OK; the streamed completion with timings is still pending.
    - RI-18c: `review_gate` null on live `/chat` is pending.
    - KVU-15a: the 2-worker replay is pending. Its cached-prefix half cannot pass in production until KVU-15c (see
      `kv-unified-stack-rollout.md`).
    - B4: `prefix_fp` is present on refusal records but not yet on a dispatched call.

    **Status at ~15:45Z, after the :8083 restore (KVU-16e done 15:35Z):**
    - B6: **PROVEN.** Non-stream, streamed chat and streamed `/v1/responses` through the passthrough to :8083, all with
      timings (15:39Z). UFH14-B6 ticked. Gap: `caller.port` null, filed as B6b.
    - B4: **PROVEN for the passthrough lane** (3 dispatched records with `request.prefix_fp`). Still open: one
      dispatched primitives-lane record carrying `prefix_fp`.
    - RI-18c: **suggestive, not proof.** A live `/chat` (~15:39-15:41Z) showed `routing_stage_ms.review_gate` and
      `review_verdict` null, but the call failed with "placement timeout role=frontdoor", because DS41 holds the CPU
      regions. The matching serving records (parent `api-ac5d8649777e`, matched by time and role only) are two :8070
      sub-calls that timed out undispatched. The gate only runs after an answer exists, so null here proves nothing.
      Still open: one COMPLETED `/chat` in a DS41 open window.
    - KVU-15a: **nothing new proven.** The post-restore calls are all short, so the lease was never exercised. The
      2-worker replay is still open. Its cached-prefix half waits for KVU-15c, and must not be read from the SLOTS_DEBUG
      window that started at 15:43:08Z.

    **~17:15Z (workspace-ec): the remaining proofs have a runner.** KVU-15c is now deployed (orch 0f0bfa19), so the
    cached-prefix half can pass in production. The GPU-block runner
    (`/mnt/raid0/llm/tmp/gpu-block-27b-20261003/RUNBOOK.md`, 5 scripts, dry-run OK) proves the lease and the KVU-15c
    credit with `deploy_ec2_lease.py` (step 1: :8083 serving and not parked, right after a plain reload that ends the
    SLOTS_DEBUG window). It also reports whether a primitives-lane record carries `request.prefix_fp`. Primitives
    records have no `long_prefill` field (KVU-15d). RI-18c still needs one completed `/chat` in a DS41 open window.
    Scheduled for the coordinated GPU block after ~18:15Z.

    **2026-10-04 02:48–02:52Z (workspace-ec): lease and credit PROVEN** in the GPU block (it started 01:59Z, not
    18:15Z on 10-03, because of missed notices). Evidence `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/ec2_lease/`;
    :8083 at production flags (`slots_debug_env: null`, server PID 1703677). The parent stays open for the two parts
    below that are still unproven.
    - [x] **UFH14-DEPLOY-EC-2a — KVU-15a lease, live.** ✅ 2026-10-04 (run `20261004T025039Z`, PASS) Two concurrent
      ~24k-token passthrough prompts (architect_critic, coder_escalation). The flock lease was held by 2 different API
      worker PIDs (3858210, 3858214), never at once (max holders 1 over 1042 samples); :8083 had at most 1 slot
      prefilling; B waited 48.9 s for A's prefill (`queue_wait_ms` 48870.97). The first attempt (`20261004T024825Z`)
      failed only because the runner's lane B used /v1 client mode without the required `x_session_id` (HTTP 422).
    - [x] **UFH14-DEPLOY-EC-2b — KVU-15c cached-prefix credit, live.** ✅ 2026-10-04 (run `20261004T024825Z`, credit
      PASS) Call 2 (26,026-token prompt extending call 1) was credited 18,829 tokens from `fp_history` vs server
      `cache_n` 22,178 (ratio 0.849, inside 0.5–1.5). It was judged a 7,197-token prefill, so `long_prefill: false`,
      and it was NOT held (`queue_wait_ms` 5.3).
    - [ ] **UFH14-DEPLOY-EC-2c — RI-18c: one COMPLETED live `/chat` with `review_gate`/`review_verdict` null.** Needs
      a DS41 open window (CPU regions free).
    - [ ] **UFH14-DEPLOY-EC-2d — B4: one dispatched primitives-lane record carrying `request.prefix_fp`.** No
      primitives call ran in the block (`primitives-lane prefix_fp present: []`). The record's `long_prefill` field is
      KVU-15d.
    - [x] **UFH14-DEPLOY-EC-2e — `deploy_ec2_lease.py`: the default lane B must send `x_session_id`.** ✅ 2026-10-30
      (filed 2026-10-04, workspace-ec) The durable runner is `epyc-orchestrator/scripts/research/deploy_ec2_lease.py`
      at commit `a75f030c062530dae0e1f0f18f39ce25486b211a`; lane B client requests carry a fresh valid ID, the
      runner preserves lane-A passthrough behavior, and its streaming lease order overlaps lane A with lane B before
      the credit call. Default dry-run and opt-in input-file execution are covered by four tests, including the real
      guard's missing-ID 422 and an overlapping mock-stream regression. No live lease, inference, or performance
      measurement was performed. [no-belief: implementation/tooling; no new measurement]
- [x] **UFH14-DIAG-EC — a recorded, TTL-bound diagnostic env override for one llama-server component.** ✅ 2026-10-03
  (workspace-ec) Orch main aa1d6894 (branch `feat/diag-env-override-ec`, ada71720 rebased). It is CLI-only, so no
  reload was needed.
  - Command: `orchestrator_stack.py reload <component> --diag-env-override KEY=VAL --experiment-id ID
    --override-ttl-s N`. The key must be on an allowlist (`LLAMA_SERVER_SLOTS_DEBUG`), and N ≤ 14400 s.
  - Record: `logs/env_overrides/<component>.json`. `declared_env_attestation` shows a live override as a declared,
    time-bound warning, and as an ERROR after expiry.
  - Readback: `python -m scripts.server.env_override readback --port <p> --expect-declared`. A plain `reload`
    restores the declared environment.
  - Tests: 51 new (`tests/unit/test_diag_env_override.py`).
  - Purpose: UFH14-A7 step 1.
  - [x] **UFH14-DIAG-EC-a — apply it for workspace-89's A3/A4 multi-turn GPU window, then restore.** ✅ 2026-10-04 (filed
    2026-10-03) At the start of the window, the session that owns that window's :8083 reloads runs it with
    `--experiment-id ufh14-a7-slotsdebug-<date>` and a TTL ≤ 14400 s (re-apply if the window runs longer). Prove it
    with the readback, then restore with a plain `reload architect_critic` at the window's end. Two side effects
    while it is on:
    - The KV-pool gate's `/slots` polls make the server detokenize every slot prompt.
    - `/slots` now returns `prompt`, so KVU-15a's cached-prefix credit becomes live for that window only.

    So serving records from the window are not a KVU-15b/15c baseline; tag them by the experiment id. Done when the
    readback shows the declared deviation during the window and `declared_env_attestation` is clean after the
    restore.
    - *(Annotation, workspace-ec, 2026-10-03; this item belongs to the window owner.)* APPLIED 15:43:08Z: the launch
      banner (`logs/server_launches/launches.jsonl`) shows `reload architect_critic --diag-env-override
      LLAMA_SERVER_SLOTS_DEBUG=1 --experiment-id UFH14-A7 --override-ttl-s 14400` → PID 1083497, the same argv as
      production. The id is `UFH14-A7`, not the `ufh14-a7-slotsdebug-<date>` form above; records can still be tagged by
      it, so this is not filed. Readback and the plain-reload restore are still pending (TTL ends ~19:43Z).
    - **RESTORED 2026-10-04T01:58:23Z (workspace-ec, which applied it):** a plain `reload architect_critic` → PID
      3843823; the record is archived (`epyc-orchestrator/logs/env_overrides/architect_critic.history.jsonl`) and
      `env_override readback --expect-declared` is ok. **Gap:** the TTL expired at 19:44Z on 10-03 and nothing
      restored it, because the A3/A4-done notice was missed, so `declared_env_attestation` sat in its post-expiry ERROR
      state for ~6 h (19:44Z → 01:58Z). The same missed notices delayed the GPU block from 18:15Z to 01:59Z.
      Follow-up: UFH14-DIAG-EC-b.
  - [x] **UFH14-DIAG-EC-b — an expired diagnostic override must reach its owner, not only the attestation.** ✅ 2026-10-29 [belief: cc]
    (filed 2026-10-04, workspace-ec, from DIAG-EC-a's ~6 h expired ERROR) The expiry is already an ERROR in
    `declared_env_attestation`, but nothing routed it to a session. At expiry, post a bus nudge to the session that
    applied the override (recorded in `logs/env_overrides/<component>.json`) and raise it on the hub's health fold.
    Do not auto-restore: a reload is the window owner's call. Done when a test with an expired record emits exactly
    one nudge naming the component and the restore command.
    Implemented in root `1ce4056f2` and orchestrator `7b7f6217`: diagnostic reloads record the restoring
    session; existing coordinator polling routes expiry with durable dedupe and crash recovery; a registered
    hub health probe exposes expired/malformed records without falsifying freshness. No automatic restore.
    Validation: 15 root and 64 orchestrator focused tests passed, including malformed inbox payload,
    missing/unregistered owner retry, concurrent polling, restart/rotation and health recovery; Ruff passed.
    Full make gates stopped at missing shellcheck. No live reload or notification was performed.

## Phase C — holistic audit (starts only after A5)

- [ ] **UFH14-C1.** A full review of how the A and B fixes fold into orchestrator management across every model in the stack: CPU and GPU roles, frontdoor, architect, workers and embedders. Covers routing, admission, compaction, caching, telemetry and per-model parameters.
  - Output: a decision package for the operator (options, tradeoffs, recommendation), plus follow-up tasks filed in their owning handoffs.
  - Delete-lens included: name the fixes that should NOT become generic.
  - Scope question added 2026-10-03: should harnesses ever reach a multi-endpoint fleet such as frontdoor through
    the passthrough? Today it returns 422 by design. See the declined note under UFH14-B6.

## Notes

- The C95 harness calls :8083 directly through its own proxy, because it needs raw streams with per-request timings on the wire. It runs at concurrency 1, so it cannot exhaust the pool. Once B6 exists, later harness experiments should go through the gate.
- **The 16-token verify block is a copy-workload profile, not an agentic one.** HyperQwen's DFLASH_TOKENS=15 gains come from greedy runs where the model reproduces its own context. Its author puts it about 2:1 behind MTP elsewhere, it costs recurrent-state pages per slot, and the source keeps k=7 for agentic clients (`intake-1827#01`, `intake-1827#06`, `intake-1830#record`). Do not tune temperature-1.0 agentic traffic toward it. Bole prices each extra verify position on Qwen3.8-27B at a ~144 MB recurrent snapshot per sequence (`intake-1847#record`). The production prior for block-8 acceptance at temperature 1 is AngelSpec's ~2.5 tokens per step (`intake-1848#01`).
- Since 2026-09-30 DS41's planner and critic are external models (gpt-6.1-sol, claude-opus-5-5). Whether the 27B returns to the planner seat is an operator decision after A5. It competes for :8083 with the INF-80 X0 window (`/mnt/raid0/llm/tmp/x0-27b-quants/PLAN.md`).

### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [x] **UFH14-LB1 — Close the llguidance-prefix abort: in the frozen production build any request whose grammar starts with %llguidance hits GGML_ABORT and kills the whole llama-server (common/sampling.cpp:211); carry an abort-to-error fix with a request-level test on the next experimental line and record which role ports accept raw grammar from clients other than the orchestrator (intake-2401).** ✅ 2026-10-22
  - *(2026-10-22, f8 locals-d, code done, NOT built, box stays open.)* Fix on `experimental/locals-kernel-fixes-20261022` (worktree `/mnt/raid0/llm/worktrees/llama-locals-kernel-fixes-20261022`, cut from the champion `ak/champion/llama-cpp-ffc1bac82eec` = `dd3d9721c`; local, not pushed) commit `0daa3ca8d`: `common/sampling.cpp` throws `std::runtime_error` instead of `GGML_ABORT` for a `%llguidance` grammar in a build without LLAMA_LLGUIDANCE; the server's existing `launch_slot` catch answers 400 `invalid_request_error` ("Failed to initialize samplers: ...") and keeps serving (draft samplers carry no grammar). Test `tools/server/tests/unit/test_chat_completion.py::test_llguidance_grammar_without_llguidance_is_request_error` on `/chat/completions` and `/completion` (400 with "llguidance" in the message, then `/health` 200 and a normal 4-token completion; skipped on an llguidance build). **Build+test spec:** recipe native-openmp-gcc15-cpu-v1 (the cmake line of `/mnt/raid0/llm/tmp/f8-fillers-20261022/rng/job.sh`, own build dir in the worktree, build-role claim; peak ~12 GiB private, ~40 min cold at filler width), target `llama-server`; (1) `strings libllama-common.so` contains `llguidance grammar ("%llguidance" prefix) requested`; (2) `cd tools/server/tests && LLAMA_SERVER_BIN_PATH=<build>/bin/llama-server <pytest-py> -m pytest -rA unit/test_chat_completion.py -k "llguidance or invalid_grammar"`, tinyllama2 preset (stories260K, < 1 GiB, ~2 min): expect 2 new PASSED + `test_completion_with_invalid_grammar` PASSED. **Role-port reachability (recorded):** every role `llama-server` binds `127.0.0.1` (`orchestrator_stack.py` launch argv, `gpu_shadow_lane.py`, `model_registry.yaml` `server_start`; the four live listeners seen 2026-10-22 are all loopback), so a raw `%llguidance` grammar reaches a role port only from processes on this host (other sessions, benchmark and AK harnesses, direct curl), all of which bypass the orchestrator guard `1e707b8d`; none is network-reachable. Tick when the build and both tests pass.
  - *(2026-10-22, workspace-f8.)* ✅ 2026-10-22 Build+test PASSED on `experimental/locals-kernel-fixes-20261022` @ `452887155` (12:33:58Z; recipe native-openmp-gcc15-cpu-v1, `build-cpu-off`): `strings libllama-common.so` carries the new request-error text; server pytest 3/3 (`%llguidance` grammar -> request error on `/chat/completions` and `/completion`, server keeps serving; `test_completion_with_invalid_grammar` PASSED). Evidence `/mnt/raid0/llm/tmp/f8-fillers-20261022/locals-d/off/out/steps.txt`. Production stays frozen; the orchestrator guard `1e707b8d` protects it until the fold.
  - [ ] UFH14-LB1.1 — fold `0daa3ca8d` (with `452887155`) into the next champion through the fold ledger (FOLD.md + trial merge on the champion tip, recorded in `autokernel-champion-aggregate.md`); production picks it up only with that champion's promotion.
    - *(2026-10-23, workspace-f8 midday wrap-up: the champion tip moved.)* The champion advanced `dd3d9721c` -> `49550eda5` (~07:20Z). `0daa3ca8d` and `452887155` are NOT ancestors of `49550eda5` (`git merge-base --is-ancestor`) and are not on the iqk-port re-cut `experimental/locals-kernel-fixes-20261023` @ `540578f55`. They live on `experimental/locals-kernel-fixes-20261022` (pushed to `fork`, cut from `dd3d9721c`). So the trial merge is onto `49550eda5` (or its successor), and the server pytest re-runs on that build.
    - *(2026-10-24, workspace-f8 sweep.)* **The fold is PREPARED and pushed, not built, not CAS'd.** Branch `experimental/ufh14-lb1-1-fold-20261024` is on the fork and is cut from the current champion `dcc853b55` (CH-29).
      - Commit 1, `344773a81`, is this fix: a clean cherry-pick of `0daa3ca8d` (`common/sampling.cpp` + the server test). The owner can CAS it alone.
      - Commit 2, `679257217`, is optional: CH-LB1.1's `5f1eee195`+`452887155`, squashed. It had two both-sides conflicts, in `tests/CMakeLists.txt` and `tests/test-backend-ops.cpp`.
      - Trial merges:
        - The branch fast-forwards onto `dcc853b55`.
        - It merges clean with the pending C4 candidate `experimental/champion-c4-20261024` @ `cdb4d8c77`.
        - **Hazard:** a merge with `experimental/locals-kernel-fixes-20261023` @ `540578f55` has no textual conflict but defines `test_backend_ops_extra_case_set` twice (its `51dfed7af`). Whichever lands second must drop its copy.
      - Build+test launcher: `/mnt/raid0/llm/tmp/f8-launchers-20261024/ufh14-lb1-1-fold/`. It holds FOLD.md with the draft ledger paragraph, plus a FILLERS row `ufh14-lb1-1-fold` drafted as BACKLOG (block-correctness, cpu build role, about 40 min cold, 12 GiB).
        - Its `--dry` run exited 0. The negative control holds: the champion C3 image lacks both gate strings.
      - Waiting on: a CPU build-role grant, then the champion owner's CAS and ledger entry.
    - *(2026-10-24 14:14Z, workspace-f8.)* **Build+test PASSED on the fold** `679257217` (`RUN_RECORD.json` all_pass=true, 8/8 steps; `BUILD_OK`+`PASSED` in `/mnt/raid0/llm/tmp/f8-launchers-20261024/ufh14-lb1-1-fold/`): request-error text in `libllama-common.so`, server pytest `-k "llguidance or invalid_grammar"` 3 passed / 0 failed / 0 skipped. The fold CAS waits on C4's CAS; box stays OPEN.
- [ ] **UFH14-LB2 — Persist finish_reason, n_tokens, max_tokens and call site with every structured-output, tool-call repair and review parse event (today the repair counters are in-process only and no event records finish_reason), then after 14 days classify parse failures as length-truncated vs malformed per site (intake-2388).**
  - *(2026-10-22, workspace-f8 / locals-a.)* Persist half landed on branch `f8/locals-a-orch-20261022` (unmerged, not pushed) (landed on orchestrator main; verified 2026-10-22) (commit `365b20c6`): `src/structured_output/parse_events.py` writes `epyc.orchestrator.parse_event.v1` JSONL (`logs/parse_events/parse_events.jsonl`, follows the serving_calls kill switch) for every `parse_with_repair`/async outcome, every tool-call JSON repair and every `parse_review_decision`, each with `finish_reason`, `n_tokens`, `max_tokens`, call `site` and `truncated_by_length` (True / False / null=unknown, never folded into "malformed"). The finish_reason is the PARSED generation's, frozen at parse start (`begin_parse`) so the repair turn's own recorded call cannot overwrite it; source is `explicit` (`generation_context`), `last_call_in_context` (new `serving_calls.last_call()`), or `absent`. A repair turn's own stop signal rides in `repair_turn`. Classifier: `python -m src.structured_output.parse_events [path]` (per kind:site: parsed / length_truncated / malformed / unknown_stop / repaired_after_*). 13 tests pass. NOT live: needs the branch merged and an API reload. The 14-day classification is the open child below.
  - [ ] UFH14-LB2.1 — after the branch is merged AND the API reloaded, let events accrue 14 days, then run `python -m src.structured_output.parse_events` and file per-site length_truncated vs malformed (count `unknown_stop` separately; if `absent`/unknown exceeds 20% of failures, wire `generation_context` at the owning call sites instead of relying on last-call-in-context). Trigger: reload + 14 days.
    - *(2026-10-23 15:45Z, f8 late-afternoon wrap-up.)* The clock started 2026-10-23T14:59:25Z: the API reload runs this code as orchestrator main `cbe542ca`, the landed form of `365b20c6`. 14 days puts the earliest classification at 2026-11-06T15:00Z.
    - *(2026-10-24 08:46Z, workspace-f8 sweep; read-only.)* **No events have accrued yet.** `logs/parse_events/parse_events.jsonl` was last written 2026-10-23T13:22Z, before the reload. The production model stack has been DOWN since at least then (no listener on :8070/:8080/:8083 at 08:46Z 10-24). The API (pid 3663075, restarted 16:19:44Z 10-23 on orch main `fd1a8941`, which contains `cbe542ca`) has served only `/health` since 16:19Z. So the 14 days count from the FIRST post-reload `parse_event`, not from the reload, and the 2026-11-06 date does not hold. Trigger: production stack up + 14 days of traffic.
- [x] **UFH14-LB3 — Replay logged turn-1 grammar_enforced REPL outputs, classify them tool-call / final-call / code-line, and either tighten the turn-1 GBNF to the CALL( shape or remove it (today its code-line rule admits any line) (intake-2388).** ✅ 2026-10-29 (audit: own criterion (tighten or remove turn-1 GBNF) met: 4-arm result 2026-10-23 off 66.67% vs legacy 40%, operator decision default off, live since 14:59Z reload (handoff:617-626); remaining LB3.4 live-watch is its own box...) [no-belief: audit-reconciliation]
  - [x] UFH14-LB3.2 — turn-1 grammar silently disabled by UFH14-LB3 itself, fixed ✅ 2026-10-23: a conditional function-local `import os` in `_execute_turn` (since 2026-03-03) made `os` a local, so the LB3 `os.environ.get` (orch 517e24d4, 2026-10-22 12:04Z) raised UnboundLocalError on every first turn and the blanket `except` hid it; no turn-1 GBNF applied on code at or after 517e24d4 (legacy default included). Found by the 4-arm mock run; fixed alone on orch main a498ffba (local import dropped + AST regression test `tests/unit/test_execute_turn_no_local_import_os.py`). No production exposure: the live API was not running a post-517e24d4 build (no :8000 listener at 2026-10-23T00:10Z), so the next reload starts on the fixed code. Follow-up: replace that blanket `except Exception: pass` with a logged warning (UFH14-LB3.3).
  - [x] UFH14-LB3.3 — make the turn-1 grammar block's `except Exception: pass` log a warning (and count it in parse_events / diagnostics) so a broken grammar path can never fail silently again. ✅ 2026-10-23
    - *(2026-10-23.)* Orchestrator main f3ab78b2: the turn-1 grammar block's blanket `except` now warns once per exception type, bumps `state.diag_counters["turn1_grammar_error"]` and writes a `turn1_grammar` parse_event; fallback unchanged; block is opt-in only (default `off`, 93055064). Tests `tests/unit/test_graph_helpers_lb3_3_lb11_1.py`.
  - *(2026-10-22, workspace-f8 / locals-a.)* PROPOSAL, flag-gated, default unchanged (branch `f8/locals-a-orch-20261022` (unmerged, not pushed) (landed on orchestrator main; verified 2026-10-22), commit `658513a4`). The retained evidence is ambiguous: no raw turn-1 text survives for the grammar-enforced runs (`seeding_diagnostics.jsonl` rows carry only a tap offset into a long-rotated tap; `repl_tap.log` is a 55 KB rolling file). What the 81 grammar-enforced frontdoor `repl` rows (March 2026) DO show: 4/81 (4.9%) called any tool vs 26/685 (3.8%) for the same-mode non-enforced rows, so the grammar's `TOOL(` branch is almost never taken and the any-line `code-line` branch absorbs the turn; pass 27/81 (33%) vs 311/685 (45%), confounded by suite mix. Also a structural defect: the grammar's tool-call shape is `TOOL("name", ...)` while the REPL's stop regex, prompts and `_call_tool` path are `CALL("name", ...)`. Change: `ToolRegistry.generate_gbnf_grammar(role, shape="legacy"|"call")` (legacy byte-identical; `call` = optional `x = CALL("tool", k=v)` or `FINAL(...)`, no any-line escape) and `ORCHESTRATOR_TURN1_GRAMMAR=legacy|call|off` in `graph/helpers.py` (default `legacy`). Replay classifier: `scripts/analysis/ufh14_lb3_turn1_grammar_replay.py`. 3 tests pass. RECOMMENDATION: set `off` first (the grammar has no measured benefit and the evidence it costs accuracy is only confounded), pending the A/B below; do not ship `call` without it.
  - [x] UFH14-LB3.1 — log the raw turn-1 output text (hash + first 400 chars, plus the grammar shape) next to `grammar_enforced` so the replay has a corpus; then A/B `off` vs `legacy` vs `call` on a pinned tool-required suite (frontdoor:repl, same questions, report tool-call share, turns, pass). Inference-gated: needs a CPU window on the frontdoor server, ~60 min; no GPU. ✅ 2026-10-23
    - *(2026-10-22, f8.)* Logging half on orchestrator main `d0e0e477` (pushed to main by a subagent's bare push; reviewed and kept by the operator 2026-10-22): `seeding_diagnostics.jsonl` rows carry `turn1_grammar_shape` and `turn1_output` {sha256, chars, head (400 chars), truncated}, null unless the turn-1 grammar was enforced. Live from the next API reload. A/B half still open: frontdoor:repl, `ORCHESTRATOR_TURN1_GRAMMAR=off|legacy|call` ABA-alternated, same questions/seed, ~60 min CPU window, keep/remove rule predeclared; classify with `scripts/analysis/ufh14_lb3_turn1_grammar_replay.py` over `turn1_output.head`.
    - [x] UFH14-LB3.1a logging half (`turn1_grammar_shape` + `turn1_output` in `seeding_diagnostics.jsonl`) on orchestrator main `d0e0e477` ✅ 2026-10-22
    - [x] UFH14-LB3.1b A/B run (inference). Spec: role frontdoor:repl on the production CPU frontdoor server, orchestrator code at or after `d0e0e477` (API reloaded, or the in-process graph), arms `ORCHESTRATOR_TURN1_GRAMMAR=off|legacy|call` ABA-alternated over the same pinned tool-required question set and seed; per arm report tool-call share, turns, pass rate and the `turn1_output.head` classification from `scripts/analysis/ufh14_lb3_turn1_grammar_replay.py`; ~60 min CPU window, no GPU; keep/remove rule written into a PREDECLARATION before the first arm. Default stays `legacy` until it lands. (filed 2026-10-22, f8 evening wrap-up) ✅ 2026-10-23
      - *(2026-10-22, f8, launcher prepared, not run.)* MERGED with GRAM-LAZY-1 step 2 (`speculative-decoding-mtp-refresh.md`) into ONE 4-arm run, arms `off|legacy|call|lazy-legacy`, ABCD-rotated per (question, rep) cell: launcher `/mnt/raid0/llm/tmp/f8-launchers-20261022/turn1-grammar-4arm/` (job.sh, launch.sh, PREDECLARATION.md incl. the keep/remove rule, ab_driver.py, analyze.py, FILLERS_ROW.md; class block-timing-pairable; ~56-80 min CPU, frontdoor 0-95 shape, private server, in-process driver, never the live API). Orchestrator branch `f8/turn1-grammar-lazy` (local, unpushed): `02bbf904` adds the `lazy-legacy` value; `248c86ea` fixes a defect found by the mock proof: a function-local `import os` in `_execute_turn` made the turn-1 grammar block raise UnboundLocalError on every first turn and the blanket `except` hid it, so since `517e24d4` (UFH14-LB3) NO turn-1 grammar (legacy, call, lazy-legacy) was applied; the run needs `248c86ea` in the serving code. Not ticked: the run has not happened.
      - *(2026-10-23, f8 wrap-up.)* ARMED: launcher pid 403555 (FILLERS row `turn1-grammar-4arm`, engine `filler_run7.sh`, class cpu). The operator approved appending it to the 10-23 whole-CPU block (`/mnt/raid0/llm/tmp/compute-flags/grant-block-20261023.sh`, last step, 90 min, after `locals-kvu-lb1-arch-decode-ab`); the 503 window on the 0-95 serving roles is extended to ~12:30Z; workspace-58 booked it ~10:45-12:15Z. Serving code = orch branch `f8/turn1-grammar-lazy` (`02bbf904` + `248c86ea`, unmerged). Not ticked: the run has not happened.
      - [x] UFH14-LB3.1c — land `02bbf904` (`lazy-legacy`) only if the verdict keeps it: resolved, NOT landed: lazy-legacy rejected (pass 3.3%). Branch `f8/turn1-grammar-lazy` stays unmerged (`248c86ea` never merges: same fix as main `a498ffba`). ✅ 2026-10-23
      - *(2026-10-23, f8, RESULT.)* Job `turn1-grammar-4arm` PASSED 08:42Z, 30/30 cells (10 tasks x 3 reps), verdict `GRAM_LAZY_1_KEEP_LEGACY`; UFH14-LB3.1b rule gives `off` -> REMOVE_GRAMMAR, `call` -> KEEP_LEGACY. Aggregates only:
        | Arm | Pass rate | Turns | turn-1 ms/token |
        |---|---|---|---|
        | off | 66.67% | 1.4 | 17.8 |
        | legacy | 40.0% | 2.5 | 23.6 |
        | call | 36.67% | n/a | 25.0 |
        | lazy-legacy | 3.33% (answers FINAL immediately; valid 100% but wrong) | 1.0 | 54.8 |
        off vs legacy: pass +26.67 pp (bootstrap 95% CI +10 to +46.67), median turn-1 step -24.5%. **`call` was no better than legacy** (36.67% vs 40.0%, and slower per token), so tightening the shape does not rescue the grammar.
      - *(2026-10-23, f8, OPERATOR DECISION.)* Production default of the turn-1 REPL grammar is now **off**: default off, live at the next API reload (`ORCHESTRATOR_TURN1_GRAMMAR` default `legacy` -> `off` in `src/graph/helpers.py`; `legacy` and `call` stay opt-in). Orch commit `93055064` on branch `f8/turn1-grammar-off` (unpushed until the main session pushes); add it to the API-reload verification bar under UFH14-LB10.
      - *(2026-10-23 15:45Z, f8 late-afternoon wrap-up.)* Live: the 14:59:25Z API-only reload (pid 3932317) runs `93055064`, and its env does not set `ORCHESTRATOR_TURN1_GRAMMAR`, so the default `off` applies.
      - *Caveats:* (1) the validity metric is an artifact for `legacy` and `off` (the legacy grammar admits code lines, so 'valid' is not discriminating); pass rate is the endpoint that carries the decision. (2) Small n (10 tasks x 3 reps). (3) Host load average rose to 114 during the run; ms/token figures carry that noise, though the arms were ABCD-rotated per cell.
      - [ ] UFH14-LB3.4 — confirmation run on a larger task set (>=30 tasks x 3 reps, the same 4-arm harness but with only the `off` and `legacy` arms) to confirm the pass-rate gain before the next champion bundle; plus, after the API reload, watch live `parse_events` / `serving_calls` for any rise in malformed turn-1 tool calls. (filed 2026-10-23, f8)
        - *(2026-10-23 15:45Z, f8 late-afternoon wrap-up.)* The reload half is ready: the API has run the `off` default since 14:59:25Z, so the live `parse_events` / `serving_calls` watch for malformed turn-1 tool calls can start now. The confirmation run is still owed, so the box stays open.
        - *(2026-10-24, workspace-f8 sweep.)* **The confirmation launcher is PREPARED and has not been run.** It is at `/mnt/raid0/llm/tmp/f8-launchers-20261024/ufh14-lb3-4-confirm/`, with FILLERS row `ufh14-lb3-4-confirm` drafted as BACKLOG (it is not registered).
          - Arms are `off` and `legacy` only, ABAB-rotated per (task, rep) cell.
          - It runs 31 pinned tasks: the old 10 byte-identical plus 21 new ones from the same generator (`tasks.json` sha256 `200624b9…`). That is x 3 reps = 93 cells, 186 runs.
          - The orchestrator is pinned to a detached worktree at origin/main `fc0c0be5`.
          - The rule is in `PREDECLARATION.md` (sha256 `6c332ce2…`), checked by `job.sh`. CONFIRMED if the task-cluster bootstrap 95 % CI lower bound > 0; REVERSED if the upper bound < 0; NOT_CONFIRMED otherwise. The new-only subset, the turns count, turn-1 ms/token and a per-cell load average are report-only.
          - `DRY_RUN=1 bash launch.sh` rc 0 with the mock driver: 186/186 runs; grammar on the wire 93/93 legacy and 0/93 off.
          - It needs the whole 0-95 CPU set for about 45 min (minimum window 60 m), and it 503s the 0-95 serving roles. Waiting on: a CPU grant.
          - The live-watch half waits on traffic: no `parse_events` and no `serving_calls` have been written since the reload, because the stack is down (see UFH14-LB2.1).
        - 2026-10-27 harvest (ufh14-lb3-4-confirm, ended 2026-10-25T05:14Z rc 0): the confirmation run RAN and is **CONFIRMED** against its predeclared rule (task-cluster bootstrap 95% CI lower bound of the pass-diff > 0 pp). 31 tasks x 3 reps x 2 arms (93 cells, 0 errors, 0 integrity defects, taskset sha `200624b9…`, orch `fc0c0be5`): pass off 66.67% vs legacy 45.16%, diff +21.51 pp, CI [+11.83, +32.26] (pair-level [+12.90, +30.11]); turns -1.376 [-1.742, -1.011]; turn-1 ms/token paired median ratio 0.6655. Report-only: new-21 +17.46 pp [+6.35, +31.75]; old-10 +30.0 pp [+13.33, +46.67]. Caveat: host load median 93 (91/93 cells >= 48), so the timing ratio is INDICATIVE; the pass-rate verdict is the correctness-class result. Artifact `/mnt/raid0/llm/tmp/f8-launchers-20261024/ufh14-lb3-4-confirm/VERDICT.json`. The confirmation half of this box is met; the live `parse_events` watch half is still owed. [belief: cc]
- [x] **UFH14-LB4 — On an experimental build under a build-role claim, run the chat-parser test with five crafted strings: a native tool call cut by max_tokens and a non-partial parse failure; record whether arguments arrive as invalid JSON and whether the server returns HTTP 500 (intake-2388).** ✅ 2026-10-22
  - *(2026-10-22, f8, code done, not run.)* `9a338d4f1` on `experimental/locals-kernel-fixes-20261022` adds `tests/test-chat-parse-truncation.cpp` (no model; parser built from repo templates Qwen3-0.6B / Qwen2.5-7B Hermes JSON, Qwen3-Coder / Qwen3.5 XML; 7 crafted strings x is_partial 0/1). Traced path: the final result always parses with `is_partial=false` (`server-task.h:397-399`); a real parse failure throws (`chat.cpp:2891-2914`) -> HTTP 500 non-stream, or an SSE error after HTTP 200 with no `[DONE]` when streaming. Predictions to confirm: cut mid-arguments -> one call with invalid-JSON arguments, HTTP 200, finish_reason length; malformed closed call -> 500; cut right after `<tool_call>` -> call silently becomes content; unknown tool -> 500. Runs as step `chat-parse` of job `akx-lb4-followups`.
  - [x] UFH14-LB4.1 — side finding from the LB4 trace (not covered by the 7 crafted strings): a client that echoes a call's invalid-JSON `arguments` string back in the next request's history makes `workaround::func_args_not_string` throw `std::runtime_error` at `common/chat.cpp:2372` (`dd3d9721c` line numbers) for every template with `supports_object_arguments`, so one truncated call can poison every later turn of that conversation. Status is untraced: a static read says `ex_wrapper` maps a non-`invalid_argument` exception to ERROR_TYPE_SERVER (500), unconfirmed whether an intermediate catch remaps it. Add a history-echo case to `test-chat-parse-truncation` (no model: `common_chat_templates_apply` with a prior assistant tool_call carrying invalid-JSON arguments) and record exception type and the would-be status; if it is a 500, decide 400-vs-tolerate on the experimental branch. Build-role, rides the next `akx-lb4-followups`-style build. (filed 2026-10-22, f8 evening wrap-up) DONE 2026-10-23 (test half): `test_func_args_not_string_invalid_json_history` in `tests/test-chat.cpp`, fork branch `experimental/ufh14-lb4-1-test-20261023` sha `cff1a3776` (full `test-chat` passes). Exception type is `std::runtime_error` (NOT `std::invalid_argument`); `tools/server/server-http.cpp` maps non-`invalid_argument` to ERROR_TYPE_SERVER, i.e. would-be status 500 per static read (not exercised live). The 400-vs-tolerate decision remains open on the experimental branch.
  - *(2026-10-22, job akx-lb4-followups PASSED at 9a338d4f1, step chat-parse.)* rc 0, 56 RESULT lines (4 formats: Qwen3/Qwen2.5 Hermes JSON, Qwen3-Coder/Qwen3.5 XML; 7 cases x is_partial 0/1), control_failures 0, threw 10, args_invalid 12; `/mnt/raid0/llm/tmp/f8-launchers-20261022/akx-lb4-followups/out/ufh14-lb4-results.txt`. (a) cut mid-arguments -> CONFIRMED: 1 call with non-JSON arguments, HTTP 200 (XML cut between parameters likewise). (b) malformed closed call -> CONFIRMED: throws; non-stream HTTP 500, stream HTTP 200 then an SSE error with no [DONE]. (c) cut right after the tool-call open tag -> REFUTED: not returned as content but as 0 calls and an EMPTY message (HTTP 200), i.e. the output is silently dropped. (g) unknown tool -> CONFIRMED: 500 / 200+SSE error. Unpredicted: an XML integer parameter with a non-numeric value throws (500); double-encoded JSON arguments parse to `{}` with HTTP 200 (arguments silently lost); every is_partial=1 variant of a throwing case parses to an empty message. Rule: 500 only when the final parse throws; every truncation returns 200, with invalid-JSON arguments or an empty message.
  - [ ] UFH14-LB4.2 — the two silent-loss paths found by UFH14-LB4: (c) a reply cut right after the tool-call open tag returns an EMPTY message with HTTP 200, and double-encoded JSON arguments parse to `{}`; detect both orchestrator-side (count them as truncation / repair events in `parse_events`, retry or surface instead of treating the turn as a valid empty answer), then decide whether an upstream issue is worth filing.
- [x] **UFH14-LB5 — Render-test every role's GGUF chat template for the prefix property under enable_thinking=false: render(turn k) plus the generated reply must be a byte prefix of render(turn k+1) over captured agent conversations; template and tokenizer only, no model (Locals keeps the empty think block on earlier replies for this reason) (intake-2386).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / locals-c.)* Result at `enable_thinking=false` (template + vocab only, research `65152c086` on the research branch `f8/locals-c-research-20261022` (worktree `/mnt/raid0/llm/worktrees/f8-locals-c-research`, unmerged, unpushed) (landed on research main; verified 2026-10-22); `audit.py`): reply-prefix, token-prefix and shared-trunk HOLD for every as-served role — frontdoor/worker (35B + terse override file), architect_critic/coder_escalation/ingest_long_context (27B + terse file), architect_general (Flash-Next embedded) — and for the 27B embedded and Qwen3-VL embedded templates. The ONLY failure is the stock Qwen3.6-35B embedded template: it drops the empty `<think>\n\n</think>\n\n` block from earlier assistant replies (`think_block_dropped`), so every follow-on turn would diverge inside the previous reply; that is exactly what the terse override prevents, and the property pins it. Thinking-ON is not audited (the reply would carry reasoning text no fixture can supply). Caveat: this is the raw jinja engine (`test-chat-template --no-common`), not llama-server's `common_chat_templates_apply` path.
  - [ ] **UFH14-LB5.1 — confirm the passing rows through the live server path (`/apply-template` or a `-lv 4` request on a scratch server, same fixtures) before relying on the static result for the tool-call fixtures. Needs a scratch llama-server load: 27B Q8_0 ≈ 30 GiB RAM or the 35B ≈ 38 GiB, ~10 min, CPU, own port outside 8000-8199.**
    - *(2026-10-27, Codex NI prep.)* Scratch launcher prepared and MAIN-reviewed; no model was loaded and this box remains open. The proposed q1 24-47 CPU row reserves 50 GiB, 900 s (600 s minimum), and port 18994 for the 27B terse template at thinking=false only. Same-entry server-start preflight, model-free HTTP and lifecycle fault fixtures, normal row validator/grant check/admission passed. Source seal `6465d724b38feee7439fe330a8039a856e0e4d5a20b99822ce25c4e1cbde8e86`; packet and belief-source wiring draft: `artifacts/ufh14-lb51-prep-20261027/`. The actual 27B run, other model rows, and prospective source writer/adapter remain unproven. [belief: cc]
    - *(2026-10-27 22:43:54Z, ws58.)* Live-template run completed. Readout pending from NI; result bullet only, no tick. [no-belief: completion notice, no readout yet]
- [ ] **UFH14-LB6 — Restore per-call serving_calls recording (19 records since 2026-10-05 despite a live hook) and extend each record with finish_reason, streamed inter-token gap p99, p99.9, max and stall count with the raw gap list, using roughly 40 lines of stream-gap capture in our own client; never report a p99.9 gap without its sample and stall-arrival counts (intake-2389, intake-2405).**
  - *(2026-10-22, workspace-f8 / locals-a.)* Extension landed, restore NOT proven (branch `f8/locals-a-orch-20261022` (unmerged, not pushed) (landed on orchestrator main; verified 2026-10-22), commit `365b20c6`). Records now carry top-level `finish_reason` (also passthrough and the dispatch.v1 lanes) and `notes.stream_gaps` = `{n_gaps, p50_ms, p99_ms, p999_ms, p999_min_samples_met, max_ms, stall_threshold_ms (500), stall_count, stall_idx, gaps_ms (raw, capped 4096), gaps_truncated}`: gaps between consecutive `on_chunk` deliveries on the backend lane and between SSE output events on the passthrough lane (TTFT excluded; a p99.9 over fewer than 1000 gaps is flagged `p999_min_samples_met=false` and ships its sample). Diagnosis of the 19-record gap (read-only): the shared clone's `logs/serving_calls/serving_calls.jsonl` holds 75 records in total, ZERO with `method=infer` (all `infer_stream_text` / `passthrough` / `undispatched`), while `logs/orchestrator.log` (to 2026-10-11) holds 4,739 `llama POST ... start` lines, all written only by the non-stream `infer` path (4,244 chat, 495 /completion), 4,711 of them in the last API session; unit tests show `infer` records correctly in isolation, so the live API workers' non-stream path was not writing and nothing said so (the writer swallowed every exception). The cause is NOT reproduced offline and the API is not running now. Fix shipped: the recorder now counts `recorded / skipped_disabled / skipped_nested / build_failed / write_failed` per process (`serving_calls.health()`), logs the first failure of each kind at WARNING with its exception, and 6 new tests cover it. Unrecorded HTTP call sites that bypass `recorded_call` (cannot appear in serving_calls at all): `worker_pool.py:847` (/completion), `chat_pipeline/scout_stage.py:719,757`, `chat_vision.py:305,557`, `vl_describe.py:207`, `tools/web/research.py:124`, `structured_output/repair.py` `http_chat_completer`, `LlamaServerBackend.infer_stream`.
  - [ ] UFH14-LB6.1 — after merge + API reload, prove restoration: `serving_calls.health()` per worker pid and the ratio of `method=infer` records to `llama POST ... start` log lines over one hour of real traffic must be ~1; if `write_failed`/`build_failed` are non-zero the WARNING names the exception; fix that. Trigger: reload.
    - *(2026-10-23 15:45Z, f8 late-afternoon wrap-up.)* The trigger fired at 14:59:25Z: API pid 3932317 runs `cbe542ca` (the landed `365b20c6`) and `d0e0e477`. The box stays open until the one-hour ratio check over real traffic and `serving_calls.health()` per worker pid are done.
    - *(2026-10-24 08:46Z, workspace-f8 sweep; read-only.)* **Not provable yet, because there is no traffic.** No `llama POST` line has been written since the 14:59Z reload, and `logs/serving_calls/serving_calls.jsonl` and `logs/dispatch/dispatch.jsonl` were both last written 13:55Z 10-23, before the reload.
      - Two `POST /v1/chat/completions` at about 15:00Z 10-23 answered 200 with neither a serving_call nor a dispatch record. The model stack was down, so they never reached a backend dispatch. That points to a backend that was never called, not to a recorder fault, because `recorded_call` records exceptions too.
      - Trigger: the production stack up plus 1 h of real traffic, then the ratio and `serving_calls.health()` per worker pid.
  - [x] UFH14-LB6.2 ✅ 2026-10-24 — wrap the unrecorded call sites listed above (worker_pool /completion first: it is the ingest/worker lane) with `recorded_call` or a `write_record` of the same schema.
    - *(2026-10-22, f8.)* On orchestrator main `d0e0e477`: new `serving_calls.record_http_call` (same schema as `recorded_call`, never raises, skipped inside a recorded call, kill switch honoured) wraps worker_pool `/completion` (`worker_pool_completion`), schema repair (`structured_repair_chat`) and both chat_vision VL calls (`vision_vl_answer`, `vision_react_turn`); requests unchanged; 7 new tests, 341 + 76 related pass. Still unwrapped: `scout_stage.py` (2 sites, shared httpx client + streaming), `vl_describe.py:207`, `tools/web/research.py:124`, `LlamaServerBackend.infer_stream`. Live from the next API reload.
    - *(2026-10-23 15:45Z, f8 late-afternoon wrap-up.)* `d0e0e477` is live since the 14:59:25Z API reload.
    - [x] UFH14-LB6.2a worker_pool `/completion`, schema repair and both chat_vision VL call sites recorded via `record_http_call` (orchestrator main `d0e0e477`) ✅ 2026-10-22; LB6.2 stays open for the four unwrapped sites above.
    - *(2026-10-24, workspace-f8 sweep.)* **The four remaining sites are wrapped** on orch branch `f8/lb6-2-remaining-sites-20261024` @ `b9788f04` (pushed, based on origin/main `fc0c0be5`, unmerged). All of them use `record_http_call`. Requests and responses are unchanged, and the recorder never raises.
      - `scout_stage` `ChatCompletionsTransport.complete` records as `scout_stage_chat_stream`, with finish_reason, timings and `notes.stream_gaps`.
      - `scout_stage` `prefill_trunk` records as `scout_stage_prefill_trunk`.
      - `vl_describe._analyze_with_server` records as `vl_describe_chat`.
      - In `research.py`, line ~:124 only builds the URL. The model call is the worker_general `/completion` urlopen in `_synthesize_page`, recorded as `research_synthesis_completion` per attempt. The plain web and crawl4ai fetches are not model calls and stay unwrapped.
      - `LlamaServerBackend.infer_stream` had no recorder anywhere, its caller included. It is a generator, so it now records from `finally` as `llama_server_infer_stream`, with finish_reason and stream gaps; an early close counts as early_stop.
      - gitnexus upstream impact is LOW for all five symbols.
      - Tests: the new `tests/unit/test_ufh14_lb62_remaining_sites.py` has 8 tests, and 259 pass across the 10 related modules.
      - Waiting on: the owning session's review and merge, then an API reload. Tick on landing.
    - *(2026-10-24, workspace-f8 main; merge record.)* Orchestrator `f8/lb6-2-remaining-sites-20261024` @ `b9788f04` MERGED to orch main as `efe37dbb` (reviewed MERGE, MEDIUM risk); the box's own criterion (wrap the sites) is met, so it is ticked. NOT live yet; it needs two events: (1) the shared orch clone `/mnt/raid0/llm/epyc-orchestrator` (at `fd1a8941`) fast-forwarded past `efe37dbb` (the armed `nib2-gnx1-reindex-2` job does this), then (2) an API-only reload (`orchestrator_stack.py reload orchestrator`). Live proof rides on UFH14-LB6.1.
- [x] **UFH14-LB7 — Decompose the cache-idle-slots ON-arm penalty: turns.jsonl shows the stall sits before prompt evaluation (TTFT minus prompt_ms median 43.5 s ON vs 1.0 s OFF over 15 turns, one rep), not in re-prefill; attribute it with -lv 4 on a scratch server (neighbour idle-saves vs own prompt_load vs draft resync), and amend the idle-slots package: explicit id_slot reuse overwrites the victim without saving it, only id_slot=-1 LRU reuse demotes to cache-ram; state pool-full behaviour with four idle contexts resident (intake-2398, intake-2400).** ✅ 2026-10-24
  - *(2026-10-23, workspace-f8.)* Launcher ARMED (`/mnt/raid0/llm/tmp/f8-launchers-20261023/locals-ufh14-lb7-stall/`, FILLERS row `locals-ufh14-lb7-stall`, GPU exclusive mi210_0+184-191, ~1.6 h, min 32 m; grant requested from workspace-58). Champion GPU store image gpu-20261021-49550eda5-c-nemotron with `-lv 4 --log-prefix --log-timestamps` only (every delimiting TRACE line strings-verified; no code branch). Replays the B4i turns (3 conv x 6 turns, B4i argv, ON vs `--no-cache-idle-slots`, ABBAAB n=3/arm) and partitions each turn window into NEIGHBOUR_IDLE_SAVE / OWN_PROMPT_LOAD / OTHER_PROMPT_LOAD / QUEUE_AND_LOOP_BUSY; verdict OWNER / SHARED / UNATTRIBUTED / NOT_REPRODUCED / INSTRUMENT_FAIL per PREDECLARATION.md (written before compute). DRY + parser self-test + driver mock PASS.
  - *(2026-10-23, f8 wrap-up.)* GPU-LEAK-1: graphs stay ON, because each session starts a fresh server for 3 conversations x 6 turns, which fits the budget. An own-pid VRAM guard at 61440 MiB was added. The run is in the f8 GPU chain after `kpf17-4-19-1a-27b-dflash2` (workspace-58).
  - [x] UFH14-LB7 run — `locals-ufh14-lb7-stall`, 6 fresh-server sessions ABBAAB, verdict by PREDECLARATION.md §5. ✅ 2026-10-23
    - *(2026-10-23 15:45Z, f8 late-afternoon wrap-up; `/mnt/raid0/llm/tmp/f8-launchers-20261023/locals-ufh14-lb7-stall/VERDICT.json` + `RUN_RECORD.json`.)* **ENDED 15:05:50Z, rc 0, 6/6 sessions OK (18/18 turns parsed in each), verdict `UNATTRIBUTED`.** No amendments. Binary: the champion GPU store image 49550eda5/10411 (llama-server sha256 `51baea5e…`), linkage rc 0, own pid on :18307 with KFD VRAM 50 GiB in every session.
      - Gates passed: reproduced (ON median gap 42.7 / 33.6 / 47.6 s vs OFF 1.05 / 1.02 / 0.24 s over pairs s1/s2, s4/s3, s5/s6), instrument OK (ON coverage 1.0 in all 3 pairs), stall before prompt evaluation (pre-header share 1.0).
      - Median ΔW per group over the 3 pairs: OTHER_PROMPT_LOAD 19.9 s (f 0.511 / 0.475 / 0.516), OWN_PROMPT_LOAD 11.0 s (f 0.281 / 0.409 / 0.258), NEIGHBOUR_IDLE_SAVE 8.8 s (f 0.225 / 0.123 / 0.252), QUEUE_AND_LOOP_BUSY -0.6 s.
      - Why the rule landed on step 6: OWNER needs f >= 0.5 in EVERY pair, and OTHER_PROMPT_LOAD is 0.475 in s4/s3. SHARED needs the two largest groups' median f to sum to >= 0.8, and OTHER + OWN is 0.792.
      - Report-only (never gates): OWN + OTHER prompt load as one mechanism, median f 0.792. Copy throughput median 0.117 GiB/s, tagged transfer-count bound (fragmented ranges / per-cell scatter). Draft-copy estimate 0.55 s per ON turn.
      - **What the rule says UNATTRIBUTED leads to (§6, written before compute):** the stall is loop time that no `-lv 4` line delimits, and the next stage adds timing probes on an `experimental/` branch from 49550eda5 around `process_single_task`, `get_available_slot`, `prompt_save`/`load` (target vs draft) and `update_slots` admission, under a new predeclaration amendment. Filed as UFH14-LB7.1.
      - UFH14-LB7 stays open: nothing is attributed, and the package amendment (UFH14-B4j.1) is still owed. FILLERS row `locals-ufh14-lb7-stall` COMPLETE (engine, 15:05:53Z).
      - *(2026-10-24, workspace-f8 sweep.)* **Closed without a rule attribution.**
        - The two predeclared rules gave UNATTRIBUTED (LB7) and NOT_REPRODUCED (LB7.1).
        - The idle-slots package amendment this task asked for is written (UFH14-B4j.1, `AMENDMENT-B4j1-20261024.md`). It carries the corrected id_slot statement and the pool-full statement.
        - The decision the attribution was to inform is already applied: `--no-cache-idle-slots` is live on :8083 (signed 2026-10-05).
        - Report-only, the ON cost is per-cell RAM→VRAM restore transfers (see UFH14-LB7.1).
        - Reopen trigger, prose only and not a box: a proposal to turn cache-idle-slots back ON. That would first need the run-coalesced `state_read_data` restore on the experimental line.
  - [x] **UFH14-LB7.1 — the next stage the LB7 rule names for UNATTRIBUTED (PREDECLARATION §6).** Add timing probes on an `experimental/` branch from 49550eda5 around `process_single_task`, `get_available_slot`, `prompt_save`/`prompt_load` (target vs draft split) and `update_slots` admission, behind a default-OFF CMake option. Then re-run the same 6-session ABBAAB replay under a dated `## Amendment 1`, written before its first session. Purpose: split the restore copies (report-only median f 0.792 at 0.117 GiB/s) into target vs draft and transfer count vs bandwidth, so that B4j.1 and any contiguous-`find_slot` or batched-scatter probe have a measured owner. (filed 2026-10-23, f8 late-afternoon wrap-up)
    - FILLERS-ready proposal (BACKLOG, not registered), as two rows like the gpu-zos-1a pair.
      - Row (1) `ufh14-lb7-1-build`: CPU build role, one quarter. Cold HIP gfx90a llama-server build of the probe branch, recipe gfx90a-house-v1 plus the option, then a strings gate with a champion negative control. About 15 m, 24 GiB, no GPU, no model.
      - Row (2) `ufh14-lb7-1-stall`: GPU exclusive mi210_0 + 184-191 (claim role build). It is the `locals-ufh14-lb7-stall` job with the binary swapped: 6 fresh-server sessions, about 1.6 h (min 32 m), 48 GiB, graphs ON with the own-pid 61440 MiB guard, and it refuses while :8083 listens.
      - **Blocker:** the probe code and Amendment 1 are not written. Dispatch both now; unwritten code is not a reason to wait. Row (2) also needs row (1) PASSED.
    - *(2026-10-23 16:50Z, workspace-f8 subagent.)* **Probe code, Amendment 1 and both launchers are done. Both dry runs exit rc 0. Nothing has been started.**
      - **Probe branch.** `experimental/ufh14-lb7-1-probes-20261023` @ `6420fca59`, pushed to the fork. It is 49550eda5 plus one commit of 288 inserted lines, 0 deleted, in 7 files.
        - A new CMake option, `LLAMA_LB7_PROBES` (default OFF), defines the macro PRIVATE on `llama` and `server-context`.
        - The commit adds one `lb7p:` line per event:
          - `io_write`/`io_read`: per state copy call; transfer count, bytes, walk vs flush time, and ≥ 1 MiB transfers timed apart.
          - `kv_read`/`kv_write`: contiguous vs per-cell scatter, and runs.
          - `save`/`load`: target vs draft copy, scan, alloc, free.
          - `gas`, `pst` and `admit`: `get_available_slot`, the cache-idle-slots loop, and `update_slots` admission.
      - **Default OFF and compile check.**
        - With default OFF, the four sources preprocess to the champion's text, except the `__LINE__` literals in assert messages.
        - The CPU-only compile check (`-j 8`, `llama-server`, ON) builds clean. `strings` shows 4/4 libllama and 5/5 server probes, and the champion image has 0. Evidence: `/mnt/raid0/llm/tmp/f8-launchers-20261023/ufh14-lb7-1-probes/cpu-check/`.
      - **Amendment 1** (`ufh14-lb7-1-probes/AMENDMENT-1.md`, sha256 `2ec0eb59…7972`, written before compute). It keeps LB7's shape, sessions, pairs and f rule, and adds probe gates (clock, line counts, io presence, ON coverage ≥ 0.90).
        - It regroups each turn window W into TGT_RESTORE / TGT_SAVE / DFT_COPY / CACHE_BOOKKEEPING / LOOP_UNPROBED.
        - For the owning copy class it tags WALK / TRANSFER_COUNT / BANDWIDTH bound, against an in-run ≥ 1 MiB bandwidth reference.
        - Next steps are stated in advance, for example: count-bound on the scatter path leads to a run-coalesced or batched-scatter restore.
        - The LB7 §5 verdict is re-computed on the new run as a replication record only.
        - Parser `lb71_parse.py`, reusing an unchanged copy of `lb7_parse.py`. Synthetic self-test PASS: the known owner is recovered, the gates can fail, and the LB7 parser output is unchanged with the probe lines present.
      - **Launchers.** Row (1) is `/mnt/raid0/llm/tmp/f8-launchers-20261023/ufh14-lb7-1-build/` (gpu-zos-1a-build pattern). Row (2) is `/mnt/raid0/llm/tmp/f8-launchers-20261023/ufh14-lb7-1-probes/` (LB7 job with the probe binary).
        - Row (2) has id `ufh14-lb7-1-probes`, not the proposal's `-stall`, so the id matches the directory.
        - It runs on port 18317 and arms behind `--precond-cmd` on row (1) PASSED.
        - Its GPU proof is own-pid KFD VRAM only, plus `libllama`/`libggml-hip` mapped from the build dir. It keeps the 61440 MiB VRAM guard and refuses below 50 GiB free on the MI210 (22 GiB free at 16:44Z).
        - FILLERS rows were drafted for the owning session to apply. They are not registered.
      - **Blocker:** grants only. Row (1) needs a CPU quarter for about 15 m. Row (2) needs GPU exclusive for about 1.6 h, after row (1) PASSED, with :8083 down and the card free.
    - *(2026-10-23, workspace-f8 evening wrap-up.)* Row (1) `ufh14-lb7-1-build` **PASSED 11/11 at 16:57:46Z** (launch.log RESULT `all_pass=true`). Row (2) `ufh14-lb7-1-probes` is armed and booked for the early hours of 10-24 (block-correctness, `--no-fold-siblings`); no result yet, so the box stays open.
    - *(2026-10-24, workspace-f8 sweep; read-only, `ufh14-lb7-1-probes/VERDICT.json`, `RUN_RECORD.json`, `LB7_RULE_VERDICT.json`.)* **Row (2) ENDED 08:40:27Z, rc 0, 6/6 sessions OK, `PASSED`, A1 verdict `NOT_REPRODUCED`.** The FILLERS row is COMPLETE. The LB7 rule, recomputed on this run, also gives `NOT_REPRODUCED`.
      - Why NOT_REPRODUCED: §5 gate 2 needs an ON median gap ≥ 20 s in every pair. The ON median gaps were 32.7 / 15.9 / 16.0 s, against OFF about 1 s. `PROBE_PERTURBATION` is flagged: the median ON gap of 16.0 s is outside [0.5×, 2×] of LB7's 42.7 s.
      - Probe gates passed in every pair: clock, line counts, io presence, and ON coverage 1.0.
      - Report-only (never gates):
        - ΔW per pair: 20.6 / 18.1 / 18.1 s.
        - Median fraction of ΔW: TGT_RESTORE 0.996, TGT_SAVE 0.004, DFT_COPY 0.007, CACHE_BOOKKEEPING 0.008, LOOP_UNPROBED -0.015.
        - Target restore is TRANSFER_COUNT_BOUND:
          - about 20.2 M transfers of about 1.5 KB, at about 22 µs each;
          - 0.06 GiB/s effective, against a 23.2 GiB/s H2D reference;
          - scatter share 0.83 and a median 4,903 cells per run.
        - Draft bytes are 4.0 % of the ON copy bytes.
      - A1.7 names a run-coalesced restore in `llama_kv_cache::state_read_data` as the next change, but only for an OWNER/SHARED verdict. So it is recorded as the report-only candidate, not filed.
      - The results went to UFH14-B4j.1 per A1.7 (ticked 2026-10-24). The box's work is complete; it is left for its owner to tick.
    - ✅ 2026-10-24 *(workspace-f8, the owner, ticked.)* Verdict `NOT_REPRODUCED` (6/6 sessions OK, 3 valid pairs, rc 0, `PASSED`): `/mnt/raid0/llm/tmp/f8-launchers-20261023/ufh14-lb7-1-probes/VERDICT.json` (sha256 `76fcbd25b961…`, schema `epyc.ufh14.lb71.verdict.v1`). Rule: AMENDMENT-1.md A1.5-A1.7, sha256 `2ec0eb59534f…7972`, appended to PREDECLARATION.md, sha256 `a37500991837…` (= RUN_RECORD `predeclaration_sha256`). Nothing further is filed: A1.7 files the run-coalesced restore only for an OWNER/SHARED verdict.
- [x] **UFH14-LB8 — One nice'd read-only pass over opencode.db (step-finish parts of local-provider sessions, LIMITed per session, V1 tables): step-level prefix-cache hit, gap CDF split human vs tool, append-length bimodality and per-tool duration CDF, as the interim prefix-cache-policy baseline until per-call records accrue (session aggregates show qwen-gpu at 0.880 token-weighted hit) (intake-2389, intake-2398).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / mining-m1.)* **Code done; full run scheduled** (`mine_m1.py`, `ufh14_lb8.aggregate.json`; read-only snapshots via `dh_sources.open_ro`, message/part tables by session index, LIMIT 20k parts per session). Per source x local provider: step prefix hit (token-weighted, and excluding each session's cold first step), gap CDF human vs tool, append-length log2 histogram + bimodality coefficient, per-tool duration CDF, opencode version set and date frame. Sample (50 newest epyc local sessions + all 27 host): qwen-gpu 0.832 token-weighted hit (0.866 excl. first step) over 987 steps, tool gap p50 4.2 s vs human 39 s, tool append p50 630 tok, BC 0.50 (below the 0.555 bimodal mark); host mi210-local 0.896 hit over 629 steps.
  - *(2026-10-22, workspace-f8 / mining results.)* **Baseline measured; acceptance met.** 202 epyc opencode sessions over 8 days (1.18.31 only), 4,093 steps. Step prefix hit: token-weighted 0.915 (0.940 excluding each session's cold first step), per-step mean 0.864, p50 0.988, p25 0.93, p10 0.124 (a cold tail, not a uniform loss). Gap CDF: human p50 48 s (p90 163 s, p99 3,614 s) versus tool p50 3.8 s (p90 18.8 s, p99 66 s). Append length: tool turns p50 427 tokens, p90 4,165; bimodality coefficient (log2) 0.513. Per-tool duration CDF in the aggregate. Reading: tool gaps are short (p99 66 s) while human gaps have a long tail (p99 about 1 h), so a cache-retention policy only matters for the human-gap tail. No new task (interim baseline; per-call records supersede it). Full tables: `docs/design/dev-harness-mining-results-20261022.md`.
- [x] **UFH14-LB9 — Offline: compare the re-tokenized length of each logged reply text with its predicted token count to size non-canonical re-tokenization (one of the two divergence classes behind the 17.8% of follow-on turns that diverge inside the previous output) (intake-2386).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / locals-a.)* Measured offline (branch `f8/locals-a-orch-20261022` (unmerged, not pushed) (landed on orchestrator main; verified 2026-10-22), commit `3bbb443c`; `scripts/analysis/ufh14_lb9_retokenize_gap.py`, read-only `opencode.db`, HF `tokenizer.json` of the Qwen3.8-27B exl3 build, LIMITed: 162 qwen-gpu sessions, 11 qwen-local). Comparable turns are text-only `finish=stop` replies (no reasoning, no tool part): n=87 (qwen3.8-27b) + 4 (flash-next). reported `tokens.output` minus canonical re-tokenized length: modal offset +1 (the EOS token) in 85/87 = 97.7%; 2/87 = 2.3% show one extra token (95% Wilson CI about 0.6-8%). So non-canonical re-tokenization of plain-text replies is about 2%, one token each: small, and unable to explain 17.8% of follow-on turns by itself. NOT covered: 3,797 tool-call turns and 187 reasoning turns (their reply is tool-call XML / reasoning text the store does not hold in token form); caveat: HF-vs-GGUF pre-tokenizer differences would shift the offset on every row, not spread it.
  - [x] UFH14-LB9.1 — repeat the comparison on tool-call turns by rendering the call through each role's GGUF chat template (shares the render harness with UFH14-LB5), since 93% of local turns are tool-call turns and that is where a non-canonical argument string would show. ✅ 2026-10-22
    - *(2026-10-22, workspace-f8 / clerical, offline, no inference.)* `scripts/analysis/ufh14_lb9_1_toolcall_retok.py` (root): each logged tool-call turn (no reasoning part; text + tool parts) is rebuilt as a structured assistant message, rendered through the role's GGUF chat template (research `65152c086` render harness: v10 `test-chat-template` + `llama-tokenize` vocab_only; GGUF header read only), and the segment the template appends is tokenized; diff = reported `tokens.output` - rendered length. Read-only snapshots; 60 newest sessions per model, 150 turns per cell. Result (epyc snapshot): qwen3.8-27b, 27B terse-file template n=150: 148 exact (98.7%), 0 rendered SHORTER than generated, 2 rendered LONGER (-13, -177 tokens; the logged arguments are bigger than what was generated, so a logging/truncation effect, not re-tokenization); 27B embedded template identical. qwen3.8-flash-next (Flash-Next embedded template) n=150: 148 exact (98.7%), 2 rows +1 token (the non-canonical signature, 1.3%, one token each). Pooled over the three (model, template) cells: 444 of 450 rows exact (98.7%). Conclusion: the tool-call argument string is not a source of non-canonical re-tokenization at a measurable rate (share above mode 0% and 1.3%), so the divergence inside the previous output is not the tool-call arguments. Exclusions: 666 reasoning turns, 22 no-tool-part, 3 no output tokens; host snapshot has no qwen3.8 turns that are clean tool-call turns (all reasoning); qwen3.6-27b-mtp (host) has no GGUF on disk (deleted) so no template was rendered. Per-turn rows (token counts only) in `/mnt/raid0/llm/private/dev-harness-traces/ufh14_lb9_1/`.
- [x] **UFH14-LB10 — Add an orchestrator-side guard that rejects any request grammar starting with %llguidance before it reaches a llama-server role port, returning a request error instead of forwarding it, with a unit test; it protects the frozen production build until the experimental-line abort fix ships (being implemented by another agent; tick on its landing commit) (intake-2401).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8.)* Landed on orchestrator main `1e707b8d`: `reject_unsafe_grammar` in `src/backends/grammar_guard.py`, applied on the passthrough path, both llama_server lanes and worker_pool call/batch/_http_call; 14 new tests. The shared clone is fast-forwarded but the API process is NOT reloaded, so the guard is not yet live. Direct role-port clients bypass it; the kernel abort fix is on the experimental line.
  - [x] reload orchestrator API to activate UFH14-LB10 guard (`orchestrator_stack.py reload orchestrator`, API only; pending operator; verify the running pid's start time is after `1e707b8d`). ✅ 2026-10-23
    - *(2026-10-23.)* Same reload also makes live: orch 93055064 (turn-1 grammar default OFF, operator decision), 96c30079 (<think> extraction fix), a498ffba (turn-1 grammar import-os fix), a73af3cc (exec_write_flags). Verify the new API pid started after 2026-10-23T09:00Z.
    - *(2026-10-23, f8 wrap-up.)* The same API-only reload also makes live orch main `a498ffba` (UFH14-LB3.2, turn-1 grammar), `96c30079` (UFH14-LB11, `<think>` strip) and `a73af3cc` (`exec_write_flags`, SEC-EXEC-POST-e1, whose live proof follows the reload). Verification bar for this box: the running API pid started after `96c30079` (2026-10-23T06:09:49Z). No :8000 listener at 2026-10-23T06:32Z, so none of these is live yet.
    - *(2026-10-23 15:45Z, f8 late-afternoon wrap-up; verified read-only.)* **The API was reloaded on its own** after 3c4ca599's fold gate exited.
      - uvicorn pid 3932317 (:8000, `--workers 6`) started 2026-10-23T14:59:25Z.
      - The shared orchestrator clone has been at main `f3ab78b2` since 09:55:50Z (reflog). `1e707b8d`, `93055064`, `a498ffba`, `96c30079`, `a73af3cc` and `f3ab78b2` are all ancestors of it, and LB2/LB6 `365b20c6` landed as `cbe542ca`. So the verification bar (pid started after `96c30079`, 06:09:49Z) holds.
      - Process env: `ORCHESTRATOR_FEATURE_EXEC_WRITE_FLAGS=1`, `ORCHESTRATOR_FEATURE_REPL_THINK_FENCE_CONTINUE=0` and `ORCHESTRATOR_FEATURE_THINKING_ROLES_CHAT_LANE=1`. `ORCHESTRATOR_TURN1_GRAMMAR` is unset, so the code default `off` applies.
      - **NOT live:** anything on orchestrator origin/main after `f3ab78b2`. That includes `a765945b` (KPF-26.1h, committed 14:59:24Z) and `b254df4e` (HS-4-PB-TRUNC, 15:00:16Z).
- [x] **UFH14-LB11 — Fix `extract_code_from_response` so Qwen3-style `<think>...</think>` reasoning is stripped before code-candidate extraction (complete and empty blocks removed, an unclosed `<think>` drops everything after it, a stray `</think>` drops everything before it); today reasoning prose containing `=` is swept into the candidate, `ast.parse` fails, `''` is returned and the "all comments" nudge runs to "Max nudges (3) reached".** ✅ 2026-10-23 on orchestrator branch `f8/think-extract-fix` (`96c30079`, unpushed; synthetic unit tests in `tests/unit/test_prompt_builders.py`). Exposure: thinking-on roles on the raw `/completion` lane (`coder_escalation`, `architect_critic`, `ingest_long_context` while `thinking_roles_chat_lane` is off); thinking-off roles are unaffected. Open follow-up: the `"\n```\n"` stop sequence can still cut a turn inside an unclosed `<think>`.
  - *(2026-10-23.)* Landed on orchestrator main 96c30079 (160 prompt_builders tests pass). Live from the next API reload. Exposed roles: architect_critic, coder_escalation, ingest_long_context (enable_thinking true, raw /completion while `thinking_roles_chat_lane` is off).
  - *(2026-10-23 15:45Z, f8 late-afternoon wrap-up.)* Live since the 14:59:25Z API reload. The running env carries `ORCHESTRATOR_FEATURE_THINKING_ROLES_CHAT_LANE=1`.
  - [ ] UFH14-LB11.1 — the stop sequence `"\n```\n"` can still cut a thinking turn inside an unclosed `<think>` (the extractor now drops it, but the turn is wasted): exclude stop sequences while inside `<think>`, or move the thinking roles to the chat lane (`thinking_roles_chat_lane`), then measure the "Max nudges" rate on coder_escalation before/after.
    - *(2026-10-23.)* Implemented on orchestrator main f3ab78b2, flag-off: counter `diag_counters["turn_ended_in_unclosed_think"]` + parse_event `think_fence_cut` always on; option (b) one bounded continuation of a fence-cut turn behind `repl_think_fence_continue` (env `REPL_THINK_FENCE_CONTINUE`, default OFF = byte-identical). Option (a) (drop the fence stop) rejected for now: reintroduces the repetition loops the stop prevents. Structural alternative (c): flip `thinking_roles_chat_lane` for architect_critic/coder_escalation/ingest_long_context after the RI-23b A/B. Next: read the counter on live traffic after the reload, then A/B the flag vs (c) on "Max nudges" rate.
    - *(2026-10-23 15:45Z, f8 late-afternoon wrap-up.)* The counter and the `think_fence_cut` parse_event are live since the 14:59:25Z API reload; `REPL_THINK_FENCE_CONTINUE=0` in the env. Next step: read the counter on live traffic.

