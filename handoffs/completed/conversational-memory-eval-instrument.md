# Conversational / Episodic Memory Eval Instruments — BEAM + Tulving adapters

**Status**: stub
**Created**: 2026-09-07 (via research intake, operator-approved plan 2026-09-07)
**Categories**: benchmark_methodology, memory_augmented, context_management
**Related**: [episodic-memory-integrity.md](episodic-memory-integrity.md) (M-12 consumes these),
[unified-trace-memory-service.md](unified-trace-memory-service.md) (the retrieval backend),
[canonical-judge-suite-revamp.md](canonical-judge-suite-revamp.md) (the judge),
[../completed/long-context-eval-datasets.md](../completed/long-context-eval-datasets.md) (roster gap)

## Objective

Build the two adapters M-12 needs and that our five-suite long-context roster lacks: a BEAM
128K/100K adapter, and a `context_mode` axis on the existing `tulving_episodic` adapter.

## Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-1330 | BEAM | instrument for M-12 | adopt-as-instrument | dive-verified |
| intake-1337 | MemPalace issue #125 | fold + judge-prompt evidence | adopt-with-caution | dive-verified |
| intake-408 | Tulving Episodic Memory Benchmark | primary M-12 instrument | adopt-as-instrument | dive-verified |
| intake-1342 | LOCA-bench | surveyed candidate | declined | dive-verified |

## Tasks

- [x] **CME-1 — Author `BEAMAdapter` (a `BaseAdapter` subclass) for the 128K/100K split** in
      `epyc-inference-research/scripts/benchmark/long_context_adapters.py`, registered at the five
      points the intake-1330 dive enumerated: the lazy-import bridge `_get_long_context_adapter`
      (`dataset_adapters.py`, verified in-tree at :89–96), the `ADAPTER_SUITES` set (:50), the
      `get_adapter` dispatch (:182 region), and `ROLE_SUITE_MAP` in `suites.py`. Load from HF
      parquet (`Mohammadta/BEAM`, split `100K`, 20 rows; `probing_questions` is a STRING needing
      `ast.literal_eval` per the dataset card) or from the repo tree. Emit
      `scoring_method: "llm_judge"` with `scoring_config {"judge_port": 8082}` and carry the nugget
      list in `scoring_config` so the existing served-judge path scores per-nugget, not per-answer.
      **Re-resolve the four line anchors before editing** — they were verified 2026-09-07 and the
      registration *structure*, not the numbers, is what is load-bearing. (intake-1330#record)
      *Evidence 2026-09-15 (research `5fb27644`, branch `sub/cme-1-beam-adapter`, NOT ticked):*
      `BEAMAdapter` authored and registered at all five points (anchors re-resolved: ADAPTER_SUITES,
      the bridge, `get_adapter`, `ROLE_SUITE_MAP` ingest + long_context); loads HF parquet or the repo
      tree, fails loudly on missing `pyarrow` / unparseable `probing_questions`; emits `llm_judge`,
      `judge_port: 8082`, and the nuggets + probing question in `scoring_config`. 41 offline tests in
      `scripts/benchmark/test_beam_adapter.py` on a synthetic fixture shaped like the HF features.
      **Remains:** (1) the served-judge consumer does NOT yet score per nugget —
      `epyc-orchestrator:scripts/benchmark/debug_scorer.py::_score_llm_judge` is a boolean
      per-answer judge that ignores `scoring_config.nuggets`; it must call the judge once per nugget
      with `beam_scoring.build_nugget_judge_prompt` and keep the 0/0.5/1 verdicts
      (`parse_nugget_verdict`) for `score_beam_run.py`; (2) a real-data smoke on the staged
      `data/100K-00000-of-00001.parquet` (5,429,768 B) under `/mnt/raid0/llm/data/eval/beam/`.
      ✅ 2026-09-16 (sub-memeval): both remains closed. (1) orchestrator `dae95a86`
      (`sub/memeval-orch-20260916`) moves the judge transport into public
      `debug_scorer.request_llm_judge_text` and makes the boolean `_score_llm_judge` REFUSE
      `per_nugget` items (`llm_judge_per_nugget_item`). Research `87991705` (`sub/memeval-20260916`)
      adds `scripts/benchmark/judge_beam_run.py`, which makes one served-judge call per nugget with
      `build_nugget_judge_prompt` and parses each reply with `parse_nugget_verdict`, writing the
      judged payload `score_beam_run.py` folds. Unavailable or unparseable questions go to
      `unjudged`, never 0.0, and the fold refuses a payload with any. Verdicts persist per
      question, so a rerun resumes. Tests: orchestrator +7 (822 passed across every
      llm_judge/debug_scorer test), research +9. (2) The data was not actually staged: fetched
      HF rev `3205395e` after re-checking the licence (CC BY-SA 4.0 / MIT). 5,429,768 B, sha256
      `c0519be2…`, provenance in `/mnt/raid0/llm/data/eval/beam/PROVENANCE.txt`. Offline smoke:
      20 conversations → 400 prompts (40 per ability), all `llm_judge`, 1–9 nuggets (median 2),
      0 dropped. **Prompt length 404k–905k chars (median 581k)**: check it against the serving
      context before M-12a. A real judged run needs the orchestrator commit merged, because the
      research shim loads the main clone's `debug_scorer.py`.
      *Note 2026-09-16 (`sub-m12-blockers`, B2, research `3f16537d`, merged at `cfbfa448`):* BEAM now has
      three arms — `full`, `rag` (pair_chunk × BM25) and `trace` (pair_chunk via the trace store,
      `order="relevance"`) — and the judge/scorer refuse an `--arm` that disagrees with the recorded
      `context_mode_by_row`.
- [x] **CME-2 — Make the FOLD an explicit, tested contract** (intake-1337#record): per question, mean
      of three-valued nugget verdicts; per ability, mean over questions; headline, unweighted mean
      of the reported ability columns. Emit the rubric-item micro-average and any binarised pass
      count as clearly-labelled secondary diagnostics only. **Add a unit test that a synthetic
      all-0.5 run scores 0.500 on the headline and NOT 1.000** — the exact mutation that catches a
      `>= 0.5` binarisation regression.
      ✅ 2026-09-15 — research `5fb27644`: `scripts/benchmark/beam_scoring.py::fold_beam`
      (`FOLD_VERSION` 1, read off BEAM `report_results.py` @ `b2da22ea`; `tau_norm` for
      event_ordering when present, else the nugget mean with `event_ordering_basis` reported);
      micro-average + binarised pass count emitted under a "not the BEAM fold" label.
      `test_all_half_run_scores_0500_not_1000` pins 0.500 (and asserts the binarised rate reads 1.000
      as a labelled diagnostic); further tests cover the unweighted-column headline vs the
      question-weighted and rubric-weighted alternatives, both folds' counts, and off-scale refusal.
- [x] **CME-3 — Carry the BEAM harness-defect note wherever a BEAM number is quoted, ours or
      anyone's** (intake-1330#record). Verified 2026-10-07 against upstream BEAM
      `mohammadtavakoli78/BEAM@b2da22eac88bb0874c64665f13457eb99835774a`:
      `src/evaluation/run_evaluation.py` passes `probing_question` into all ten evaluators;
      `src/evaluation/compute_metrics.py` accepts it in each evaluator but never reads it while
      building the judge prompt, whose responsiveness section therefore has no question input.
      A static function-body census confirms this for all ten (`evaluate_abstention`,
      `evaluate_contradiction_resolution`, `evaluate_event_ordering`,
      `evaluate_information_extraction`, `evaluate_instruction_following`,
      `evaluate_knowledge_update`, `evaluate_multi_session_reasoning`,
      `evaluate_preference_following`, `evaluate_summarization`, and
      `evaluate_temporal_reasoning`). In the published 100K prompt files, all 40 abstention
      questions have one-item refusal rubrics; this is a scoped observation, not a survey of
      every split. The caveat is now adjacent to the live 100K numeric quotes in
      `wiki/memory-augmented.md`, `episodic-memory-integrity.md`, and
      `context-folding-progressive.md`; `wiki/benchmark-methodology.md` also distinguishes count
      granularity from judge validity. This describes the upstream published artifact; the local
      scorer's question-aware fix does not repair upstream scores. Source: [pinned judge code](https://github.com/mohammadtavakoli78/BEAM/blob/b2da22eac88bb0874c64665f13457eb99835774a/src/evaluation/compute_metrics.py),
      [pinned prompt template](https://github.com/mohammadtavakoli78/BEAM/blob/b2da22eac88bb0874c64665f13457eb99835774a/src/prompts.py),
      and [pinned 100K prompt files](https://github.com/mohammadtavakoli78/BEAM/tree/b2da22eac88bb0874c64665f13457eb99835774a/chats/100K).
      ✅ 2026-10-07 — exact source/callsite census and 20-file, 40-question rubric audit. [MAIN source review](../../artifacts/ni08/beam-caveat-source-20261007/README.md).
- [x] **CME-4 — Add a `context_mode` parameter {none, retrieved, full} to the Tulving adapter's
      `_row_to_prompt`** (verified at `tulving_episodic_adapter.py:582`, which always prepends the
      book). Route `retrieved` through the `src/trace` FTS5 + `navigation.py` surface. **The
      `"context"` key the adapter already emits at :637 is INERT** (`run_benchmark.py` never reads
      it), so each arm must be expressed in the prompt itself. (intake-408#record)
      ✅ 2026-09-16 — research `ccc41d4b` (`sub/memeval-20260916`). `context_mode` ∈ {none, retrieved,
      full}, set by constructor argument or `$TULVING_CONTEXT_MODE` (`get_adapter()` takes no
      arguments). The default is `full`, which is byte-identical to the old prompt: all 456
      stored prompts of `20260619_141212` are reproduced. Each arm has its own prompt header,
      and `none` is the bare question. `retrieved` goes through the new
      `tulving_trace_retriever.py`: one trace `Event` per chapter in a PRIVATE store built with
      the orchestrator's `ensure_schema`, queried through `navigation.search_records`, then
      bm25-ranked. **Finding:** `src/trace/query.query` says "rank by bm25" but orders by
      `ts_utc DESC`, so a limited search keeps the latest matches, not the best. The retrieved arm
      raises rather than degrade when no retriever exists. On the real 19ch book with top_k=3,
      prompts average 8.2k chars vs 50.9k for full. The scorer now reads the arm off the stored
      prompt headers (`context_mode_by_prompt`) and REFUSES a `--belief-measurements --arm` that
      disagrees. 23 new tests + 6 scorer tests; 136 passed.
- [x] **CME-5 — Spec for a thin registered CL-Bench system that sends each turn to the orchestrator /v1 chat endpoint (design only; no repo code is executed).** CL-Bench routes every call through LiteLLM with no `api_base` plumbed through the ICL, notepad and structured-output path, so a local endpoint needs a custom system registered with `@register_system` implementing respond, reset and name (`intake-2168#00`, `intake-2168#01`). The spec lists the interface points to satisfy (Query, Response, TaskStepResult; usage events with pricing None), a provider_mode-independent client, and a prefix-stable prompt layout for KV reuse. One bounded smoke (`clbench run exploitable_poker --schedule quick_test`, 5 hands x 3 runs) is not filed: it needs the CR3 trigger (spec accepted and a granted compute window), and the run size must be fixed on the served model's prefix-cache hit rate and a context of at least about 128K (`intake-2168#03`). The CL-Bench suite is borrowed for its metric, never as a production or promotion gate. ✅ 2026-10-20
  - 2026-10-21 the adapter specified here is built as CME-7 (research `b4c0c6b48`, `scripts/benchmark/clbench_epyc_local/`).
- [x] **CME-6 — Recompute paired stateful-minus-stateless gain from the shipped CL-Bench run files (zero inference; analysis artifact only, no MEASUREMENT edit).** ✅ 2026-10-21 From `/mnt/raid0/llm/tmp/dive-clbench-repo/repo/final_results/runs/icl-gpt-5.4` and `icl-claude-sonnet-4.6` (repo SHA 5f8c50eb1e84b2eda2ef4faff757dfc812a0ea26; re-clone if absent; gzip JSON read with `python3 -I`, no repo code run) report per-instance paired gain, the headroom-normalised gain, and the spread of the single stateless run versus the five stateful rollouts, i.e. how much of the published interval width the unreplicated stateless baseline hides (`intake-2149#01`, `intake-2149#02`). Frozen input manifest: the run directories with file digests; baseline: the published Table 1 values; denominator: every instance including failed ones; decision rule predeclared: report only; the output feeds decision package DP-E as its worked example.
  - 2026-10-21 the adapter specified here is built as CME-7 (research `b4c0c6b48`, `scripts/benchmark/clbench_epyc_local/`).
- [x] **CME-7 — Build the thin CL-Bench system adapter specified by CME-5 (the missing local-endpoint path is a build cost).** CL-Bench routes every call through LiteLLM with no api_base plumbed through, which CME-5 specified around as a thin registered system sending each turn to the orchestrator /v1 chat endpoint. Build that adapter now (about 1-2 days) with a stub-endpoint test and a smoke run against a fake server, so the only thing left for the instrument is a compute window; no repo code beyond the registered system file is executed against a model and no run is started. Also record the same-shape adapters for the SkillGenBench, AutoSkill, AgentBreeder and safety-under-scaffolding repositories as the M27 build-cost items (a local-endpoint shim, 1-2 days each), since no local-endpoint path is a build cost and was not a reason to decline. Acceptance: the adapter passes a stub-endpoint test and the smoke run, and the CME-6 and CME-5 notes point at it. Estimate: 1-2 days. ✅ 2026-10-21
  - 2026-10-21 (fillers-3c4ca599): smoke registered as queue item `s5-cme7-poker-smoke` (NOT armed): needs CL-Bench Python env, research origin/main runner, M-12 server on :8199, sizing decision per CME-5.
  - 2026-10-21 (queue-builders-3; research `76f5143d9`, `2e479ee01`, pushed) smoke made runnable. Env: `/mnt/raid0/llm/tmp/clbench-venv` (python 3.13.7, litellm 1.81.6, typer, texasholdem 0.11.0, matplotlib, openai 2.16.0; `clbench doctor` passes) + repo copy `/mnt/raid0/llm/tmp/clbench-epyc-repo` @ 5f8c50e with epyc_local installed. BUG FOUND in the runner built under this task: it passed `--system.base_url` / `--system.max_context_tokens`, which clbench's argparse rejects (hyphens required), so the window would have been burned; fixed, and the runner now proves port ownership. Proved end to end against a FAKE endpoint: the full real `clbench run exploitable_poker --schedule quick_test` (3 runs x 5 hands) completed through the wrapper and `cache_hit_report.py`. CME-5 SIZING DECISION (recorded here): 3 concurrent runs need >= 3 slots; per-run cap `max_context_tokens=120000` needs >= 131072 positions per slot; use the EXISTING eval recipe `qwen3.6-35b-a3b-q8-gpu-mtp-longctx196k-np4` (4 x 196608, prompt cache on) on a private port (not 8199). The 95% cache gate is over PREFIX-REUSABLE tokens (calls >= 2; reusable = min(input, prev input + prev output)), with raw cached/input reported beside it, because a 5-hand history misses 95% on raw arithmetic alone. No model run yet; row `s5-cme7-poker-smoke` `ready=y`, bundle sub-row.
  - 2026-10-21 `dpf-skill` done: research `b4c0c6b48` — `scripts/benchmark/clbench_epyc_local/system.py` (`@register_system("epyc_local")`, stdlib HTTP to a local `/v1`, prefix-stable history, UsageEvents with `cost_usd=None`), 6 stub-endpoint tests pass, `smoke_fake_server.py` ok (10 requests, append-only prefixes), `install_into_clbench.sh`, and the window-guarded `scripts/benchmark/run_clbench_epyc_local.sh` (`WINDOW_CONFIRMED=1`). The real smoke (`exploitable_poker --schedule quick_test`) still needs a compute window sized per CME-5. Same-shape adapters (DPF-W2-CME7-SGB, -AUTOSKILL, -AGENTBREEDER, -SAFESCAF) moved to `harness-improvement-loop.md` M27.
- [x] ~~**CME-7R — Re-run the CME-7 CL-Bench poker smoke (`s5-cme7-poker-smoke`) after the thinking-off fix.** The 2026-10-22 13:08Z run failed rc=1 (pydantic `json_invalid`: Qwen3.6 thinking consumed the 2048-token budget, empty content). Fix research `cd69f694c` (`enable_thinking=False` via `chat_template_kwargs`, loud EndpointError on empty content, 10 tests). Re-arm the filler through FILLERS.md and a grant. Done when a run writes a CL-Bench trace dir with a valid score and server.log shows n_decoded well under 2048 on the first hands. Detail: `progress/2026-10/2026-10-22-cme7-fix.md`. (filed 2026-10-22)~~ (closed 2026-10-29 audit: SUPERSEDED → CME-7S (same file, next box) re-ran after cache fix and is the canonical rerun; 10-22 rerun valid but gate MISSED and first calls hit 2048 tokens (CME-7T))
  - 2026-10-22 (3c4ca599, zero inference) the rerun ran VALID at 13:12-13:15Z (run dir `/mnt/raid0/llm/tmp/cme7-poker-out/run-20261022T131252Z/`, 3 runs x 5 hands, scores -0.40 / +0.40 / -2.00) but NOT ticked: its prefix-cache gate MISSED (`hit_ratio_reusable` 0.7948 vs 0.95) and the first call of runs 0 and 1 still generated 2048 tokens (see CME-7T). Cache finding in [`progress/2026-10/2026-10-22-cme7-cache-miss.md`](../../progress/2026-10/2026-10-22-cme7-cache-miss.md): 130,762 reusable tokens, 26,829 missed = 52.4% (14,058) client layout (the schema instruction was attached to the OUTGOING last user message only, so the previous user message changed at its tail and the hybrid server, which can only resume from a checkpoint, re-prefilled that whole message every turn) + 41.1% (11,028) previous-call output that a hybrid server cannot reuse (accounting) + 6.5% (1,743) parse-retry history rewind. Slot routing cost 0 tokens. Fixed in research `08ace05fd` (instruction stored in the user message; gate gains `prompt_prefix` basis and a missed-token split). Code-only; a rerun is needed to confirm.
- [x] **CME-7S — Re-run the CME-7 poker smoke on research >= `08ace05fd` and confirm the cache gate on the `prompt_prefix` basis.** Same job and recipe as CME-7R (`qwen3.6-35b-a3b-q8-gpu-mtp-longctx196k-np4`), plus `-lv 4` on the server so `SLT_TRC` prints `restored context checkpoint (n_past = ...)` / `forcing full prompt re-processing` per request (the 2026-10-22 server.log was INFO level, so the checkpoint mechanism there is inferred from the cached-token arithmetic, not read from a log line). Re-arm the filler through FILLERS.md and a grant; the poller exited, the job file is not edited. Predicted (recorded data replayed with cached = previous input - 4): `hit_ratio_prompt_prefix` about 0.99 versus gate 0.95; the CME-5 `hit_ratio_reusable` tops out near 0.91 on this model because generated tokens are never reusable, so it is printed but no longer gates. Done when cache_hit_report.json shows PASS (`basis: prompt_prefix`) and server.log shows the n_past restored to within a few tokens of the previous prompt length. (filed 2026-10-22) ✅ 2026-10-27 harvest: cache gate PASS on the `prompt_prefix` basis, `hit_ratio_prompt_prefix` 0.9977 (273,661 of 274,294 prefix tokens cached) vs gate 0.95 and vs the predicted ~0.99; server.log at `-lv 4` shows 54 `restored context checkpoint` lines against 6 `forcing full prompt re-processing`; run `cme7-poker-out-s2/run-20261023T003634Z` (ended 2026-10-23T00:40Z, rc 0). [belief: cc] ✅ 2026-10-29 (audit: conversational-memory-eval-instrument.md:132 inline "2026-10-27 harvest": cache_hit_report.json PASS prompt_prefix 0.9977 vs 0.95, server.log 54 restored checkpoint lines; run cme7-poker-out-s2/run-20261023T003634Z) [no-belief: audit-reconciliation]
  - 2026-10-27 harvest (s5-cme7-poker-smoke, ended 2026-10-23T00:40Z): `clbench/cache_hit_report.json` verdict PASS, `problems: []`, 3 runs x 5 hands (14/14/20 calls). `hit_ratio_reusable` 0.951 (printed, no longer gating), `raw_cached_over_input` 0.8874. Missed split: generated_tokens_unreusable 13,475, history_rewind 0, prompt_prefix_lost 633 (about 13 tokens per call across 48 calls, the "within a few tokens" clause). Legacy score aggregate mean 0.200 std 0.721 (smoke, not a capability measure). Artifacts `/mnt/raid0/llm/tmp/cme7-poker-out-s2/run-20261023T003634Z/{GATE.txt,clbench/cache_hit_report.json,server.log}`; belief ingest already by 3c4ca599 (`vidya-belief-substrate-program.md`, 2026-10-24 row, hit 0.9977). Correctness-only. [belief: cc]
  - 2026-10-22 (3c4ca599, zero inference) PREPARED for the rerun, not run: server `-lv 4` through a new opt-in `GPU_RECIPE_EXTRA_ARGS` in `jobs/gpu_recipe_lib.sh`, set only in `s5-cme7-poker-smoke_job.sh`; job output moved to `cme7-poker-out-s2` and COMPLETE now written only for verdict PASS or MISS; job refuses (rc 7) unless the shared research clone contains `08ace05fd` and `2f704ba4a` (the clone was at `cd69f694c`: it must be fast-forwarded by its owner before the grant). Proposed 18-cell row validates `--for-grant`; arm steps in `/mnt/raid0/llm/tmp/fillers-3c4ca599/arm_cme7s.sh.txt`. Main arms.
- [x] **CME-TRV-DOC — fix the stale `scripts/benchmark/tulving_trace_retriever.py` docstring (research repo).** It still says `src.trace.query.query` orders text searches by `ts_utc DESC`; since 2026-09-16 `order="relevance"` (bm25 before `LIMIT`) is the default when `text` is given (`src/trace/query.py`), so the "ask for every match" workaround is no longer needed (found by HIL-6i, `docs/design/hil6i-pilot-design-first-feature-20261022.md` §14). Check whether the retriever still passes the workaround and drop it only if the 23 retriever tests stay green. Zero inference. ✅ 2026-10-23 (3c4ca599): research `0742c647e`. Docstring rewritten. Workaround CHECKED and KEPT, not dropped: the 23 retriever tests stay green with `limit=top_k`, but `query` breaks bm25 ties by `ts_utc DESC`, so 12 identical chapters at top_k=3 return [10,11,12] instead of [1,2,3] and already-scored runs would shift. New test `test_trace_retriever_breaks_score_ties_by_lowest_chapter` pins it (24 retriever tests, 45 with the beam arms).
- [x] **CME-7T — Find why the first call of a run generates the full 2048-token budget (runs 0 and 1 of the 2026-10-22 smoke; run 2 stopped at 199).** `enable_thinking=false` is now sent, yet call 0 (457-token prompt, temperature 0) hit `max_output_tokens`, failed the schema, and the parse-retry then carried the 2048-token failed reply in its prompt (2,505 tokens, then a history rewind to 870): about 5.8k of the 26.8k missed tokens and about 7.5 minutes of one 165 s run's wall. The failed text is not stored in the trace; capture it (log the rejected `text` and `finish_reason` in `system.py`, tests with the stub) and decide between a lower `max_output_tokens`, a repetition penalty in the request, or a stricter instruction. Code-only. (filed 2026-10-22) ✅ 2026-10-25 — diagnosis/choice complete from CME-7S; bounded rationale candidate recommended, efficacy untested. [no-belief: committed conclusion prepared; register capture not yet applied]
  - [x] Prepare prospective CME-7T diagnostic capture and model-free controller fixtures ✅ 2026-10-27 [no-belief: preparation/fixture only]. Private packet `/mnt/raid0/llm/tmp/refactor-01a16fc3/ufh01-budget-measurement-unblock/`: source manifest SHA-256 `8c316f497973c4c43e7e71cacca288ef44e5613c25c549b503fcea816efdab8e`, PF `56b107e4b7b633c134dcbe80fcb10d58db6baffffc785979`; normal admission and validator q0h 0/0. q0g exercises private archive/install, owned socket and fake server, truncation/error/TERM cleanup, and pinned HIP plus owned KFD VRAM observer positive and refusal fixtures. Native prospective capture is diagnostic only; response ClaimTuple projection and canary remain open under VB-CME7T-RESPONSE-WIRE. No model or inference run, efficacy claim, or paired CME-7S baseline (different kernel). Source enrollment publication remains the local prerequisite; row remains BACKLOG, unarmed, pending grant. Preserve `output/clbench/**` including native traces; only `output/tmp/**` is raw. Window 3300 s (minimum 3000), exclusive MI210 and CPUs 184-191, RAM 96 GiB plus 64 GiB margin, 2 GiB output with 150 GiB remaining. Six small checksums were read outside the wrapper, a disclosed narrow envelope deviation.
  - [x] Capture the rejected replies (code part) ✅ 2026-10-22 — research `2f704ba4a`: every parse-failed, empty or max_tokens reply is appended untruncated (content, reasoning_content, finish_reason, completion_tokens, error) to `raw_replies.jsonl` next to `cache_hit_report.json` (`CLBENCH_EPYC_RAW_LOG`, set by the runner); a distinct `runaway` event is logged on `finish_reason: length`; 3 new stub tests, 15 pass. CME-7S raw replies are available; the 2026-10-25 desk diagnosis/choice below completes the remaining decision.
  - 2026-10-25 (Codex NI T1; canonical ROOT 249855e78 / research e8d57acd): CME-7S PASS run 2026-10-23 raw_replies.jsonl SHA-256 a9b5ee5a7495bde9ace34746318fb51f55b70dfedd5c000a04c66a4623dd3ef6 contains one unique runaway. Response chatcmpl-6U1HOEz9UlHrOTaX4BK3gy6b51aAO5fs joins exactly to baseline instance_trace0/first interaction, not stateful runs 0/1/2. Visible JSON thinking is unfinished at 2048 output tokens, finish_reason=length, reasoning_content=null. Recommend bounded rationale instruction for a separately granted candidate; retain 2048 cap and current penalties. Efficacy untested; no deployed fix or explanation of every 10-22 event. Retained server receipt identifies build 10345 / dd3d9721c; immutable launch-time model/binary digests absent. Full additive findings: [docs/reference/cme7t-inf64-accepted-findings-20261025.md](../../docs/reference/cme7t-inf64-accepted-findings-20261025.md). [no-belief: committed conclusion prepared; register capture not yet applied]
  - [x] **CME7T-V2-FAILURE-ACCOUNTING-PREP** — repair original baseline4 schema-abort accounting without schema weakening or redraw; freeze separate v2 diagnostic cohort with all worker/hand/attempt/response journals, explicit unattempted cells and closed raw/native artifact seals. Actual CLBench process-pool/fake-HTTP whole-entry fixture and raw/log mutation refusals passed; current source `be94659116730798a3a730b93bc31c0e85b1b9c55febb3d021787a8b3804dde8`, PF `d46a51db27ceefe9c32739223a88177c89e6ffb2bd4aa41c`, normal3300s admission and validator0/0. Native failure remains failure; diagnostic accounting is separate. Existing response source/task extended, reader/canary still open. See [repair record](../../progress/2026-10/2026-10-27-native-repair-packets-2255.md). ✅ 2026-10-27 [no-belief: source preparation and synthetic fixtures only]
  - [x] Validate a separate bounded-rationale candidate using the existing configurable system_prompt (two short sentences/60 words; exact text in [durable findings](../../docs/reference/cme7t-inf64-accepted-findings-20261025.md)). If using the official wrapper, expose an explicit opt-in runner parameter and verify parsing with fake transport before a separate model grant. Bind prompt/hash and launch identities; retain 2048 cap/current penalties initially and count unique baseline/stateful schema failures separately. Recommendation only; efficacy untested. ✅ 2026-10-29 (audit: EVL50 bounded-rationale diagnostic candidate [x] 2026-10-28 (rc0 17:51Z, run evl50-cme7t-bounded-rationale-r1-20261028T174948Z-925358): 0 schema-failure/runaway on both sides; efficacy untested noted in text) [no-belief: audit-reconciliation]
  - 2026-10-28 (ws58 results filing): `codex-cme7t-recovery-20261028` rc0 12:27Z, independent diagnostic collection 8/8 accounted, no infrastructure errors. Distinct schema-failure response IDs: baseline 1 (of 5 tasks), rollout 0 (of 3); length response IDs 0/0. Diagnostic only per the predeclared rule (counts, no efficacy or quality inference). Evidence: `/mnt/raid0/llm/tmp/codex-cme7t-recovery-20261028/output/clbench-run/independent/COLLECTION.json`. [belief: cc]
  - [x] **EVL50 bounded-rationale diagnostic candidate** — keeper completed rc=0 on 2026-10-28T17:51:48Z; run `evl50-cme7t-bounded-rationale-r1-20261028T174948Z-925358`. Native `COMPLETE.json` reports 56 raw replies (14 unique baseline, 42 unique candidate interactions), with zero schema-failure and runaway attempts/interactions on either side. The run is diagnostic-only; bounded prompt efficacy remains untested. Server linkage identifies the configured ROCm build/model path, but no fresh KFD/VRAM sample was captured, so GPU residency is not independently established. This is a completed operational/diagnostic conclusion, not an efficacy or cache measurement; no historical ClaimTuple is reconstructed. Prospective producer-authored summary-sidecar wiring is added to existing VB-CC-PILOT/CME-7T work. ✅ 2026-10-28 [belief: cc]
  - *(2026-10-27 evening, ws58.)* CME7T v1: INCONCLUSIVE (2 invalid-JSON baseline responses). v2 is running. [no-belief: inconclusive run, no claim]

  - 2026-10-21 `noninf-memeval` computed, NOT ticked: scripts, per-instance output and run-file digests in [`artifacts/noninf-memeval-20261021/`](../../artifacts/noninf-memeval-20261021/) (`cme6.py`, `cme6_result.json`; `python3 -I`, gzip JSON only, repo at 5f8c50eb, 6 tasks x 2 systems, 5 stateful rollouts + 1 `reset_each_instance` baseline each, no null rewards, every instance counted whether `success` or not). The shipped manifest `cumulative_gain` is the MEAN per-instance paired gain (`stateful mean over 5 rollouts - stateless`), reproduced to 1e-4 for all 12 task x system cells. Mean paired gain, gpt-5.4 / sonnet-4.6: database_exploration 0.2087 / 0.2120; blind_spectrum_monitoring 0.2937 / 0.1869; cohort_studies -0.0209 / -0.0040; codebase_adaptation 0.0363 / 0.1424; sales_prediction 0.3027 / 0.4033; exploitable_poker -0.3153 / 0.1935 (poker reward is chips, not on a 0-1 scale). Headroom-normalised gain (sum of gain over sum of `1 - stateless`, defined only where rewards are <= 1): gpt-5.4 0.2422 / 0.3764 / -0.0208 / 0.0723 / 0.5674 and sonnet-4.6 0.2534 / 0.2395 / -0.0038 / 0.2264 / 0.7095 in the same task order (database, spectrum, cohort, codebase, sales). Baseline-hiding: the stateless baseline is ONE draw, so its own noise is not estimable from these files. Direct evidence it matters: at instance 0 the stateful rollouts have no memory yet, so the true gain there is 0, yet the measured paired gain at instance 0 is e.g. sales_prediction -0.0132 (gpt) / -0.1261 (sonnet) against a pooled per-instance rollout sd of 0.0641 / 0.1039, and exploitable_poker +7.5 / +20.2 chips against sd 7.46 / 15.03. Under the stated assumption that a stateless draw has the same per-instance variance as a stateful rollout, a standard error built from the 5 rollouts alone understates the gain's uncertainty by a factor of sqrt(6) = 2.45 (that factor is the assumption, not a measurement). NOT done: comparison with the published Table 1 values, because Table 1 is not in the cloned repo (no copy found by grep of README/agent_docs); the shipped manifest headline stands in as the baseline here. Table 1 comparison (added same day, from the saved paper text `/mnt/raid0/llm/tmp/dive-clbench/paper.txt`; `cme6c.py`, `cme6_table1_compare.json`): the paper's normalized gain is the mean over the six tasks of `(mean stateful - mean stateless) / (r_max - mean stateless)` with r_max from Appendix A (poker 9.49 bb/hand, cohort 0.162 bits, the other four 1.0). Recomputed from the shipped run files: ICL GPT-5.4 18.28 +- 7.37 percent against published 20.1 +- 9.1; ICL Claude Sonnet 4.6 23.99 +- 3.0 against published 25.4 +- 3.6 (CI = 1.96 x sqrt(sum of per-task rollout variances / 5) / 6). DISAGREE by -1.8 and -1.4 points, ordering (Sonnet above GPT) and rough size agree; the recomputed and published intervals overlap for both systems. Cause not isolated (candidates: published table built from a different batch than `final_results/runs`, or a different r_max/poker unit); recorded, not resolved. DP-E hand-off (note only): use `cme6_result.json` as the worked example and carry the caveat that the stateless baseline is ONE draw whose noise is not estimable from these files (instance-0 gains are non-zero where the true gain is 0).

## Open Questions

- Does the currently resolved served judge reliably honor the requested nugget output schema
  during its owner-controlled inference window? Current local parsing records unusable output as
  typed, unjudged failure, not0.0; the historical upstream `judge_rubric` hazard belongs to CJ-10.
  [MAIN current-source clarification](../../artifacts/ni08/cme-judge-current-source-20261008/README.md).
  CJ-10 upstream transcription/provenance comparison remains separately tracked.
- ~~Is BEAM's licence compatible with staging under `/mnt/raid0/llm/data/eval/`?~~ **Resolved 2026-09-15:**
  data CC BY-SA 4.0 (HF dataset card `license: cc-by-sa-4.0`, `Mohammadta/BEAM` sha `3205395e`),
  code MIT (`github.com/mohammadtavakoli78/BEAM` LICENSE). Local staging for evaluation is
  compatible. Download size: 100K split 5,429,768 B (500K 33,956,263 B; 1M 66,156,374 B).

## Notes

Compute-gated work is filed here, never run. Adapter authoring is pure code and needs no inference.

## Research Intake Update — 2026-10-20 (harness cluster)

Operator-approved 2026-10-20 via research intake (plan sha256 1dc83054706ca0bae002602307b0d9ba6435b010be4d6ffd8a495a04605f3967). Monitor and knowledge records below are prose: no checkbox, no index next action.

- **M6 (monitor, 2026-10-20) — Memory-instrument follow-ons (CL-Bench smoke, congested-memory leg).** Trigger: CME-5 accepted and a compute window granted; or the HS-4 P2 profile-on arm is scheduled. First step when it fires: Size the CL-Bench smoke on the served model's prefix-cache hit rate; add the congested-memory leg. No immediate step remains: Both need an instrument or arm that does not exist yet.
