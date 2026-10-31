# Chat Templates — Per-Model Turn Markers and Routing Endpoints

**Category**: `chat_templates`
**Last compiled**: 2026-10-31 (operator wiki sweep, workspace-58): LB5.1 live-server template check confirmed on four residual rows. Earlier: 2026-10-28 (workspace-58 wrap): CT-21 HOLD and the failed v2 exploratory run. Earlier: 2026-10-24 (wrap-up sweep 21, 3c4ca599 delta): the control-token neutraliser is widened to the non-Qwen lineup (CT-12.1b). Earlier: 2026-10-24 (wrap-up sweep 9). Earlier: 2026-10-22 (wrap-up sweep 10: stock Qwen3.6-35B template breaks prefix property). Earlier: 2026-10-22 (wrap-up sweep 9: Qwen3.x thinking is turned off at the server source). Earlier: 2026-10-22 (wrap-up sweep 7: CT-18 closed, DP-G ruling, prefix-property render test filed). Earlier: 2026-10-21 (wrap-up sweep 3: the CT-12 injection surface is closed at the orchestrator an). Earlier: 2026-10-20 (wrap-up sweep 2: DeepInfer intake, DS41 1017 swap). Earlier: 2026-09-17 (incremental: CT-series mmlu_pro cells under-scored by the A–H scorer; re-score estimates); earlier: 2026-08-23

> Quick reference for which chat template each production model uses, which
> orchestrator code path applies the template (client-side vs server-side
> jinja), and how to wire a newly-onboarded model so it produces clean
> output through the routing layer.

**Compiled**: 2026-06-15
**Primary sources**: `src/api/routes/chat_utils.py`, `src/backends/llama_server.py`,
`src/llm_primitives/backend.py`, `scripts/server/stack_numa.py`,
`src/chat_completions_roles.py`,
`progress/2026-05/2026-05-22.md`, `progress/2026-05/2026-05-23.md`,
`progress/2026-06/2026-06-15.md`,
`handoffs/active/model-stack-single-source-update-pipeline.md`

---

## Compiled Update — 2026-10-28 (workspace-58 wrap): CT-21 decision is HOLD; v2 exploratory rerun failed and changes nothing

- **CT-21 predeclared decision applied: HOLD, flag stays default OFF.** 2352 unique records, recomputed analysis matches. Investigate surface fails the competence gate: OFF 13/200 vs ON 11/200, ON-OFF -1.0 pp, Tango one-sided 95% lower bound -4.18 pp (must exceed -3.0), aligned-twin net loss 6 (limit 1). An earlier slice failed on an unparseable multiple-choice answer; the fix scores that as an incorrect outcome and preserves all completed rows.
- **v2 exploratory run (`ct21-direct-exploratory-v2`, 2026-10-28)** ended rc=1: 80/80 raw request/response files retained but no producer sidecar and no COMPLETE marker. Observation only: no score, no correction to the original CT-21 result; the parent box stays open.
- **Repair is preparation only**: successor source sealed (validator fix, per-request-marker sampler with interval containment); a new owner receipt and rerun are required and CT-21 is not armed.
- **Scope incident**: a stale shim used revoked CPUs 76,77 for about 42 s; owner ruled no invalidation since co-tenancy cannot change a correctness verdict.

### Source References (2026-10-28 workspace-58 wrap)

- [handoffs/active/qwen-chat-template-evaluation.md](../handoffs/active/qwen-chat-template-evaluation.md) — CT-21 HOLD, v2 run, repair and incident
- [handoffs/active/agentic-serving-harness-fixes.md](../handoffs/active/agentic-serving-harness-fixes.md) — terse-template (27B, thinking=false) prep, no model loaded
- [progress/2026-10/2026-10-28-workspace-58.md](../progress/2026-10/2026-10-28-workspace-58.md) — session record

## Compiled Update — 2026-10-24 (wrap-up sweep 21, 3c4ca599 delta): the control-token neutraliser is widened to the non-Qwen lineup (CT-12.1b)

**Confidence: verified** (vocab-only tokenizer probe, before/after artifacts).

- **The shipped neutraliser was ASCII-only and the DeepSeek-V4.1 control spellings are not.** DS41 uses fullwidth U+FF5C bars and U+2581 (`<｜begin▁of▁sentence｜>`, `<｜User｜>`, `<｜tool▁calls▁begin｜>`, `<｜DSML｜`); 16 of 18 probed DS41 control spellings were OPEN under the old `DEFAULT_CONTROL_TOKEN_REGEX`.
- **Fix: orchestrator `7f949c7c`.** Bars `[|｜]`, name class gains `/ ▁ "`, plus DSML forms, `<SPECIAL_n>`, `<tts_*>` and bracket specials (`[CLS] [SEP] [INST] [/INST] [TOOL_CALLS]`...); escape is ZWSP after `<` or `[`. Re-probe: every vocab control spelling of every loadable family is CLOSED (DS41 21/21, gemma4 18/18, llama3 10/10, nemotron 14/14).
- **Residual is policy, not a defect.** Plain-text template tags (`<think>`, `</think>`, `<tool_call>`, `<tool_response>`, bare `｜DSML｜`) are text in llama.cpp, not control ids, and are deliberately untouched; escaping them would alter quoted code, so it is an operator call (recommended: leave unless a measured injection via these tags appears).

Sources: [qwen-chat-template-evaluation](../handoffs/active/qwen-chat-template-evaluation.md).
## Compiled Update — 2026-10-24 (wrap-up sweep 21, 3c4ca599 delta): the control-token neutraliser covers DS41, Mistral and BERT families

- **CT-12b probe: 16 of 18 DS41 control spellings were open.** DeepSeek-V4.1-Flash writes its specials with fullwidth bars and U+2581 (`<｜begin▁of▁sentence｜>`), which the ASCII-bar default regex missed. The gemma-4 (18/18) and Llama-3.2 (10/10) families were already closed. The DS41 role and tool markers are plain text in the GGUF vocab (not control ids) but the template emits identical bytes, so a user-typed spelling is indistinguishable from a real role marker (44 text markers open).
- **Fix is a wider default regex (orchestrator `7f949c7c`).** Bars `[|｜]`, a name class with `/` `▁` `"`, the DSML and `<SPECIAL_n>` and `<tts_*>` forms and the bracket specials (`[INST]`, `[CLS]`, ...). After it every vocab control spelling of every loadable family probes CLOSED. False-positive check over 74 MB of repo text added 85 matches in 8 files, all literal mentions of BERT/Mistral specials.
- **Residual is policy.** Plain-text template tags (`<think>`, `<tool_call>`, `<tool_response>`, bare `｜DSML｜`) stay untouched, as for Qwen; escaping them would alter quoted code, so it waits for a measured injection through those tags.

Sources: [Qwen chat template evaluation](../handoffs/active/qwen-chat-template-evaluation.md)

## Compiled Update — 2026-10-22 (wrap-up sweep 10): the stock Qwen3.6-35B template breaks the prefix property, and CT-THINK-CODER is an open owner decision

**Confidence: verified** for the static template render results and the CT-18.2 locator check (tests, no live server); **inferred** for live behaviour, which UFH14-LB5.1 has yet to confirm.

- **All as-served templates hold the prefix property at `enable_thinking=false`; the stock Qwen3.6-35B embedded template does not.** The stock template drops the empty think block from history, so a historic assistant turn renders differently from how its generation prompt began; the terse override fixes it. This is the same divergence found at prompt end - 4 in the CME-7 cache miss, where the end-4 checkpoint covers it. Live-server confirmation is filed as UFH14-LB5.1.
- **A server-side guard now tests the property.** Prefix-property tests (reply-prefix, token-prefix, shared-system-trunk) run the v10 `test-chat-template` jinja engine and `llama-tokenize` over four synthetic captured-client fixtures (tool loop and its trunk-sharing partner, plain chat, REPL code lines); 22 tests with expected outcomes pinned per role.
- **CT-THINK-CODER is an open owner decision.** The source fix makes Qwen3.x filler servers launch with `--reasoning off`; a per-request `enable_thinking:true` still overrides it, and the coder server is the one place thinking stays on as a pre-registered exception. Until one decision line is recorded (keep ON citing the pre-registration, or switch to server-side off, naming the dependent arm), no harness may assume either state: it must send `enable_thinking` explicitly.
- **Thinking-off is also what the CME-7 first run needed.** Thinking consumed the 2048-token budget and left `content` empty (pydantic `json_invalid`); the fix sends `enable_thinking=False` via `chat_template_kwargs` and raises a loud EndpointError on empty content. That the served llama-server honours the per-request kwarg was unverified at the time of the fix. After it, call 0 of runs 0 and 1 still generated the full 2048 tokens (CME-7T, open; raw-reply capture landed, research `2f704ba4a`).
- **CT-18.2 locators verified (hash only).** The Skill-Inject belief sidecars point at `RESULTS.skillinject.architect.jsonl` (951 rows) and `RESULTS.skillinject.worker.jsonl` (951 rows, shared by the CPU and GPU worker strata, split by the sidecar's served pin); all 9 `results_sha256` values match disk. The results files stay uncommitted because they hold fixture text and the repo is public; an earlier sweep had mis-read the worker path as shared by all three.
- **CT-19.1 closed as a digest, not a panel.** `scripts/security/injection_flag_digest.py` (orchestrator `7ef529d8`) reports flag counts by source, field and threat plus freshness; an absent ledger is reported as absent, never as clean. Today no ledger exists because `skill_injection_scan` is off. CT-21-code added a default-off `architect_untrusted_boundary_sentence` flag and run prep with a predeclared decision rule; the competence A/B on a frozen set of at least 200 architect items remains open.

### Source References (2026-10-22 wrap-up sweep 10)

- [handoffs/active/qwen-chat-template-evaluation.md](../handoffs/active/qwen-chat-template-evaluation.md) — CT-THINK-CODER, CT-18.2, CT-19.1, CT-21-code
- [progress/2026-10/2026-10-22-cme7-fix.md](../progress/2026-10/2026-10-22-cme7-fix.md) — thinking-on root cause and the chat_template_kwargs fix
- [progress/2026-10/2026-10-22-cme7-cache-miss.md](../progress/2026-10/2026-10-22-cme7-cache-miss.md) — historic-turn think block and the end-4 divergence
- [progress/2026-10/2026-10-22-workspace-f8.md](../progress/2026-10/2026-10-22-workspace-f8.md) — UFH14-LB5 static template result

## Compiled Update — 2026-10-22 (wrap-up sweep 9): Qwen3.x thinking is turned off at the server source, not per harness

**Confidence: verified** for the llama.cpp v10 source reading (read-only, line numbers below) and the tests; **inferred** for the effect on a live run, since no inference was started.

- **Cause.** Qwen3.6 defaults to thinking ON. Under a token cap the reasoning consumed the whole budget and `content` came back empty, which voided the first runs of cme7, hsprof1 and the KPF-64 partial arms. Each harness had been patched per request; the cause is one level lower.
- **Frozen v10 source semantics.** `--reasoning off` sets `enable_reasoning=0` and `default_template_kwargs["enable_thinking"]="false"` (`common/arg.cpp:3463-3465`); `--chat-template-kwargs enable_thinking` is deprecated in its favour (`arg.cpp:3310`). A per-request `chat_template_kwargs {enable_thinking:true}` overrides the server default (`tools/server/server-common.cpp:1074-1087`), so a server-side off is safe for a job that has a pre-registered thinking-ON arm such as YaRN OOL-1. `--reasoning-budget` is a separate sampler budget and is not needed.
- **Fix in the job layer.** `jobs/qwen_thinking_lib.sh` gives `qwen_reasoning_args` and `qwen_first_reply_preflight` (rc 9 if reasoning is present or content is empty). It is wired into hil15a, hil18a, kpf261-outcome, cme7-poker-smoke and hsprof1-beam; the KPF-64 launcher and `rte_pfx2_role_recipe.py` (orchestrator `c91f3a781`, 13 tests) got the same flag and a 16-token "Reply with OK." preflight after the own-PID port proof. Yarn jobs are untouched because their harness already sends `enable_thinking` per item.
- **Open decision.** Whether the coder server keeps thinking ON as a pre-registered exception is filed as CT-THINK-CODER in `qwen-chat-template-evaluation.md`; until it is decided a harness must send `enable_thinking` explicitly.

### Source References (2026-10-22 wrap-up sweep 9)

- [progress/2026-10/2026-10-22-qwen-thinking-source-fix.md](../progress/2026-10/2026-10-22-qwen-thinking-source-fix.md)
- [progress/2026-10/2026-10-22-rtepfx2-thinking-off.md](../progress/2026-10/2026-10-22-rtepfx2-thinking-off.md)
- [docs/guides/agent-workflows/compute-fillers.md](../docs/guides/agent-workflows/compute-fillers.md)

## Compiled Update — 2026-10-22 (wrap-up sweep 7): CT-18 closed, DP-G ruling

**Confidence: verified** for the CT-18 / CT-18.1 completion and DP-G ruling (951/951 rows; static fixtures only); **inferred** for UFH14-LB5 and CT-21 (filed, not run).

- **CT-18 and CT-18.1 are COMPLETE.** Both Skill-Inject results files hold 951/951 rows (317 items x 3 arms, plus one `skipped_ctx_overflow` row, 316 complete triples). Worker: 66 items CPU and 250 complete triples GPU-MI210, no item mixes substrates; architect all GPU. Two overnight filler deaths (rc=1) had one cause, an HTTP 400 context overflow on SI-C037 arm C, fixed by `ct18_resume_v2.py` recording a skip instead of raising.
- **Result:** IB2 strongly favours the boundary sentence (architect ASR 45.8 -> 4.2%), but Skill-Inject gives the worker no benefit and harm under B (25.9 vs 32.0%, p2 .006). Reading is static-fixture only (CT-20 wording rule).
- **DP-G = "Hold; architect trial" (operator, 2026-10-22):** no template or prompt change for worker/REPL; CT-21 trials an architect-only, default-off, byte-identical-when-off variant with a predeclared competence A/B.
- **UFH14-LB5 (filed):** render-test every role's GGUF chat template for the prefix property under `enable_thinking=false` (render(turn k) plus the generated reply must be a byte prefix of render(turn k+1) over captured agent conversations; template and tokenizer only, no model). Motivation: 17.8% of follow-on turns diverge inside the previous output, and Locals keeps the empty think block on earlier replies for this reason; UFH14-LB9 sizes non-canonical re-tokenization as the second divergence class.

### Source References (2026-10-22 sweep 7)

- [handoffs/active/qwen-chat-template-evaluation.md](../handoffs/active/qwen-chat-template-evaluation.md)
- [handoffs/active/agentic-serving-harness-fixes.md](../handoffs/active/agentic-serving-harness-fixes.md)
- [progress/2026-10/2026-10-22-ct18-final.md](../progress/2026-10/2026-10-22-ct18-final.md)

## Compiled Update — 2026-10-21 (wrap-up sweep 3: the CT-12 injection surface is closed at the orchestrator and the server, and DS41 template parity is not yet a result)

**Confidence: verified** for the recorded tests and A/B counts; the live effect of the orchestrator layer depends on the shared orchestrator clone being on main, and the champion fold (CT-12.5) is not done.

- **CT-12.1 (tokenizer probe):** control spellings are OPEN on all 7 lineup families the probe could load (Qwen2.5-0.5B draft, Qwen3-Coder DRAFT 0.75B, Qwen3.6-35B-A3B, Qwen3.8-27B, Qwen3-VL-30B-A3B, Qwen3.8-Flash-Next MTP head and UD-IQ4_XS): every ChatML control spelling tokenizes to its control id with parse_special, to multi-token text without. The 27B DFlash2 drafter could not be loaded standalone (shares the 27B tokenizer). ([Qwen chat-template evaluation](../handoffs/active/qwen-chat-template-evaluation.md))
- **CT-12.2 (served path) and a correction.** Confirmed OPEN on the champion chat path via the CT-12.4 A/B (Qwen2.5-0.5B: injected text costs exactly the plain parse_special count; probe 40 tokens vs 60 guarded). The earlier job-06 record (`<|im_end|>` = 248046) is **not** champion/Qwen2.5 evidence: its own server failed to bind :18971 and the probes hit another session's Qwen3.5+ server, so job helpers now require the job's PID to own the port before declaring ready. ([Qwen chat-template evaluation](../handoffs/active/qwen-chat-template-evaluation.md))
- **Layered fix, both layers landed.** (a) Orchestrator neutraliser, epyc-orchestrator `50f7ffbd`: `src/security/control_tokens.py` inserts U+200B after the `<` of any control spelling, wired at request models, prompt builders, web fetch and kb_rag; the orchestrator's own template markers and stop tokens are untouched (`src/backends/llama_server.py` builds raw ChatML on purpose); 44 new tests; kill switch `ORCHESTRATOR_CONTROL_TOKEN_NEUTRALISE=0`. CT-12.3c (`a43759b7`, `a24723c3`, `5dde3006`) extended it to every model-bound assembler while keeping REPL/tool/web/RAG DATA raw (byte-identical file reads, enforced by a data-plane module guard) and added an AST sweep test that fails on any new model-sink caller without the neutraliser. (b) Server patch `6dfbc9e86` on `experimental/ct12-is-input-parse-special-20261021`: records byte spans of `is_input` parts during template render (including `tojson` of input values, which upstream drops) and tokenizes control spellings lying entirely inside one span as text; prompts with no such spelling take the unchanged path; chat request types only, raw `/completion` untouched; opt-out `--chat-input-parse-special`. Known residual: a spelling straddling a template/input boundary is not caught. Upstream issue #28249 steps 1-2 merged (#28250, #30389), server wiring not landed. ([Qwen chat-template evaluation](../handoffs/active/qwen-chat-template-evaluation.md))
- **CT-12.4 no-regression gate: 164 pass / 0 fail** (champion vs `6dfbc9e86`, CPU, 3 template sets x 11 fixtures): renders byte-identical, clean prompts token-identical, raw path identical. The CT-7 golden fixtures were never persisted and were rebuilt from the README, which is why CT-12.6 (persist them) exists. The patch was folded as V11-095 into a separate candidate C2 so the C measured by the bundle gate keeps its identity. ([Qwen chat-template evaluation](../handoffs/active/qwen-chat-template-evaluation.md); [llama.cpp v11 release manifest](../docs/reference/kernel-manifests/llama-v11-manifest.md))
- **DS41 template parity is a harness finding, not a parity result.** Both DS41 GGUFs (Sept Q4, 1017 shard 1) lack `tokenizer.chat_template` and `src/llama-chat.cpp` has no V4/V4.1 built-in, so jobs 60 ran the ChatML fallback and got 0/14 token-identical against both encodings. The authored template `deepseek-v41-flash-epyc-v1.jinja` is 14/14 text-identical under a jinja2 proxy but, in llama.cpp's real jinja runtime, 0/14 at add_special=false (the template emits no BOS; add_special adds exactly one, so no double BOS) and 6/14 with BOS added (thinking, effort high/max/int75, reasoning-retention cases). Divergences: golden1 at id 586/622, golden2-4 and tool cases at id 6, mid_system at id 3, golden5 HTTP 500 (image, no mmproj). Chat cases were also served with a `Reasoning Effort` preamble because no `enable_thinking:false` was sent. The proxy's text identity did not transfer; DS41-T3.3c lists the closing steps. ([DeepSeek-V4.1 Flash evaluation](../handoffs/active/deepseek-v41-flash-evaluation.md))
- **Encoding-version trap:** the Sept and 1017 DS41 encodings differ in `find_last_user_index` under thinking mode (Sept counts a tool-result-only user turn as the last user turn, dropping the earlier assistant reasoning; 1017 does not); the cutover checkpoint must be served with the 1017 rule. ([DeepSeek-V4.1 Flash evaluation](../handoffs/active/deepseek-v41-flash-evaluation.md))

**Sources (sweep 3):** [Qwen chat-template evaluation](../handoffs/active/qwen-chat-template-evaluation.md); [DeepSeek-V4.1 Flash evaluation](../handoffs/active/deepseek-v41-flash-evaluation.md); [llama.cpp v11 release manifest](../docs/reference/kernel-manifests/llama-v11-manifest.md).

## Compiled Update — 2026-10-20 (wrap-up sweep 2): control-token injection and DS41 renderer parity are probe-first tasks

**Confidence: inferred.** Both items are unchecked tasks from the 2026-10-20 DeepInfer intake (operator-approved); nothing has been probed yet.

### Key findings

- **Control-token spelling in user text may become the control token (`CT-12`).** At the pinned experimental commit the server flattens the rendered chat parts into one string and tokenizes it with special-token parsing on, so user, tool or retrieved text that spells a control token could tokenize as that token. This is a prompt-injection surface that the community-template analysis (CT-3) already flagged for frog and sharp templates, now at the tokenizer. Plan: (1) probe each lineup family on an experimental server with `/tokenize` and a chat request whose user text is the literal spelling, comparing token ids and usage `prompt_tokens`; (2) only if open, choose between a champion-branch patch (tokenize input parts without special parsing) and an orchestrator-side neutraliser; (3) A/B against the template goldens before any fold. Source: intake-2118#record.
- **DS41 needs token-id parity against two official renderers (`DS41-T3.3`).** The 1017 release's `encoding/encoding.py` differs from the September copy (tool-result-only user turns no longer start a turn), and the separate `deepseek-recipe` renderer differs again: a second reader found it drops reasoning on non-prefix assistant turns where `encoding.py` keeps it. The task renders the five goldens plus tool, thinking, effort, mid-system and reasoning-retention cases, tokenizes with the DS41 vocabulary, and diffs against the served `/apply-template` plus `/tokenize`, reporting the first divergence per case and which oracle disagrees. Host-side only, no inference. Sources: intake-2118#record, intake-2121#record.
- **Vendor sampling is part of the template contract.** `DS41-W7.1` records the 1017 card's sampling (temperature 1.0, top_p 1.0) as the recipe's recommended sampling, so every DS41 quality or A/B harness sends it explicitly or records the deviation. It lands with the weight cutover, not before the shards are complete.

### Decisions and rationale

- The oracle for DS41 rendering is the official first-party code; the recipe repo is treated as a second statement, not authority, because the two disagree.

### Open questions

- Which lineup families are actually open to control-token injection under the current server path?
- Which of the two DeepSeek renderers matches the 1017 weights' training format where they disagree?

### Related

[speculative-decoding](speculative-decoding.md), [quantization](quantization.md).

### Source References

- [Qwen chat-template evaluation](../handoffs/active/qwen-chat-template-evaluation.md) — CT-12 and the CT-3 injection analysis.
- [DeepSeek-V4.1-Flash evaluation](../handoffs/active/deepseek-v41-flash-evaluation.md) — DS41-T3.3 and DS41-W7.1.

## Compiled Update — 2026-09-17: every CT-series mmlu_pro cell is under-scored

**Confidence: verified** for the cause, which was checked on the full MMLU-Pro corpus. The re-scored numbers are **estimates**: an offline re-score of the recorded 200-character `answer_tail`, not re-runs.

CT-1, CT-1b, CT-E7 and CT-E7b all scored mmlu_pro through the shared pool with `scoring_config={}`, before CJ-8, and the scorer's letter range was A–H. Ten of the 40 pinned items have gold I or J, so they were forced False whatever the model answered. The same 40 ids were used in every arm. So the directions and paired flips keep their sign, and the other suites are unaffected. But the absolute mmlu_pro levels quoted on this page are too low. The inline caveat in the 2026-08-23 (evening) section below already flags this. This section records the corrected estimates.

### Key findings

- **The re-scored estimates run about 10–12.5 pp above the recorded cells.** They use the fixed scorer (`choice_labels`, orchestrator `f0015306`, branch only).

  | cell | recorded | re-scored |
  |---|---|---|
  | CT-1 arm0 | 37.5% | ~47.5% |
  | CT-1 arm1 | 37.5% | ~47.5% |
  | CT-1b arm2 | 40.0% | ~52.5% |
  | E-7 frontdoor | 37.5% | ~50.0% |
  | E-7 architect_general | 27.5% | ~40.0% |

  ([qwen-chat-template-evaluation](../handoffs/active/qwen-chat-template-evaluation.md), [sub-scorer-fix](../progress/2026-09/2026-09-17-sub-scorer-fix.md))
- **The CT-E7b master-registry values carry the under-score, and so do the E-7 belief sidecars.** The registry values are 37.5 for frontdoor and 27.5 for architect_general. The sidecars (`/workspace/tmp/e7-recal/*/belief_measurements.jsonl`) were never ingested into the ledger. Correcting both needs a re-stamp on the fixed scorer, which means inference. ([qwen-chat-template-evaluation](../handoffs/active/qwen-chat-template-evaluation.md), [sub-scorer-fix](../progress/2026-09/2026-09-17-sub-scorer-fix.md))
- **Not every mmlu_pro number was affected.** `v7_quality_gate_runner`, the architect bench and the 56.7% Qwen3.8 mmlu_pro figure used `extract_letter_answer`, which handles A–J. Only `debug_scorer` consumers of pool rows were hit. ([sub-scorer-fix](../progress/2026-09/2026-09-17-sub-scorer-fix.md), [Benchmark Methodology](benchmark-methodology.md))

### Open questions

- When does the registry re-stamp run for frontdoor and architect_general mmlu_pro? It needs inference on the fixed scorer, which must first land on orchestrator `main`.

### Sources

- [qwen-chat-template-evaluation.md](../handoffs/active/qwen-chat-template-evaluation.md): the CAVEAT 2026-09-17 block, with the re-score table and the list of what still holds.
- [2026-09-17-sub-scorer-fix.md](../progress/2026-09/2026-09-17-sub-scorer-fix.md): the scorer root cause, the consumers, and the affected-results table.
- [per-request-reasoning-budget.md](../handoffs/active/per-request-reasoning-budget.md): the PRB-T4 mmlu_pro crash that exposed the A–H limit.

---

## Summary

Production chat templates are part of the model-serving contract: the selected endpoint, client-side
wrapping, server-side Jinja behavior, and per-model reasoning kwargs must agree. A mismatch can produce
plausible HTTP success while silently degrading output or routing evidence.

## Key Findings

- Prefer `/v1/chat/completions` with server-side Jinja for dynamic or multi-channel templates.
- Treat model-family detection and `enable_thinking` behavior as per-role configuration, not global defaults.
- Validate the rendered turn markers with a live completion whenever a model or endpoint changes.

## Per-family templates currently in production

The orchestrator's family detector (`_detect_template_family` in
`chat_utils.py`) maps a model name to one of these families and applies
the corresponding template wrap when the request goes through the
`/completion` path. For roles that route via `/v1/chat/completions`, the
orchestrator skips client-side templating entirely — llama-server's
`--jinja` flag applies the GGUF's embedded chat_template server-side.

### Qwen (3.x, 2.5, 3-Next, distillations)

```
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant

```

**Detection key**: name contains `qwen` (case-insensitive). DeepSeek-R1-
Distill-Qwen variants also detect as qwen.

**Special kwargs**: most Qwen models (3.5, 3.6, 3-Next) require
`chat_template_kwargs.enable_thinking=False` at the chat-completions
layer when not explicitly using the reasoning path — without it the
template emits a leading `<think>...</think>` block that the model is
prone to fill with degenerate loops. See
`feedback_qwen3x_enable_thinking_false` for the empirical fix (+33pp
accuracy on frontdoor's cheap-kill task set).

### Gemma 2 / Gemma 3 (`<start_of_turn>` style)

```
<start_of_turn>user
{prompt}<end_of_turn>
<start_of_turn>model

```

**Detection key**: name contains `gemma` but NOT `gemma-4` / `gemma4`.

### Gemma 4 (multi-channel; production: gemma-4-26B-A4B-it)

The proper format per the GGUF's embedded chat_template (12045 chars of
Jinja, verified 2026-05-22 via `llama-server /apply-template`):

```
<|turn>user
{prompt}<turn|>
<|turn>model
<|channel>thought
<channel|>

```

Notes:
- **Asymmetric markers**: `<|turn>X` opens a turn, `<turn|>` closes one.
  This is NOT a balanced pair — they're distinct tokens.
- **Thought channel prefix**: when `enable_thinking | default(false)` is
  false (the default), the template appends a `<|channel>thought\n
  <channel|>` prefix. The model is trained to fill in this channel then
  emit its final answer.
- **`/completion` is broken for this format** (verified empirically
  2026-05-22 against ik_llama.cpp's MTP build): sending the proper
  template via `/completion` times out with 0 tokens. The path forward
  is `/v1/chat/completions` (see below).

### Llama 3.x (header-id style)

```
<|begin_of_text|><|start_header_id|>user<|end_header_id|>

{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>


```

**Detection key**: name contains `llama-3`, `llama3`, or `meta-llama-3`.

### MiniMax-M2 and Phi-4

Both empirically accept Qwen-style ChatML markers. Detected separately
in `_detect_template_family` so future deviations can be caught, but
currently routed through `_TEMPLATE_QWEN_CHATML`.

### Unknown families

Pass-through (no template wrap). The model receives the raw user prompt.
Safer than guessing wrong; logged at `DEBUG` so the operator can flag
miswired roles.

---

## Two routing endpoints — when to use which

### `/completion` (legacy, client-side templating)

The orchestrator wraps the user prompt with the role's chat template
(via `apply_chat_template_for_role` / `apply_chat_template_for_model`)
and POSTs the templated string to `http://llama-server:port/completion`.
llama-server does NOT apply jinja for this endpoint.

**Works for**: Qwen 2.5 / 3.x / 3-Next, Gemma 2/3, Llama 3.x — any model
whose chat template can be replicated as a static prefix/suffix wrap.

**Does NOT work for**: Gemma 4 (multi-channel format with sequence-
sensitive marker semantics) — server returns 0 tokens.

### `/v1/chat/completions` (newer, server-side jinja)

The orchestrator sends `{"messages": [{"role": "user", "content":
prompt}]}` (raw prompt as user content). llama-server's `--jinja` flag
applies the GGUF's embedded chat_template server-side AND parses the
multi-channel response cleanly, returning only the final-channel
content in `choices[0].message.content`.

**Required for**: Gemma 4 (multi-channel format).

**Available for**: any model launched with `--jinja`. Today's stack has
this flag on for all worker_general / worker_fast / etc. instances
(gemma-4-26B-A4B-it Q4_K_M).

**Selection mechanism**: env var `ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES`
(comma-separated role names) still overrides everything, but the
default set is now derived from generated stack priors rather than a
frozen literal list. `src/chat_completions_roles.py` reads the live
artifact and selects roles whose launch metadata says
`launch.runtime.flags.jinja == true` and
`acceleration.enable_thinking == false`. If the priors artifact is
missing or malformed, the helper falls back to a narrow degraded set:
`frontdoor`, `coder_escalation`, `worker_general`, `worker_math`,
`worker_summarize`, `toolrunner`.

`_init_caching_backends` reads the shared set and sets
`use_chat_completions=True` on each affected role's `ServerConfig`.
`LlamaServerBackend.infer()` and `infer_stream_text()` dispatch to the
chat-completions code paths when the flag is set.

`chat.py` and `_try_cheap_first` both check this shared set and SKIP
client-side templating for those roles — sending a pre-templated
prompt as messages[].content would inject our markers as literal user
input and confuse the model.

---

## Onboarding a new model — checklist

When swapping in a new model to a production role:

1. **Identify the chat template family** — dump the GGUF metadata:
   ```bash
   python3 -c "import struct; ..."  # see scripts/dump_gguf_kv.py
   ```
   Look for `tokenizer.chat_template` and the `general.architecture`
   field. Compare against the patterns above.

2. **Update `_detect_template_family`** if it's a new family or named
   variant. Add a `if "newfamily" in n: return "newfamily"` branch
   BEFORE the broader Qwen match (the qwen branch is the
   fallthrough-broad catch).

3. **Choose endpoint**:
   - If the template can be replicated as a static prefix wrap → use
     `/completion`, add a `_TEMPLATE_NEWFAMILY` constant and wire it in
     `_wrap_for_family`.
   - If the template is dynamic / multi-channel / version-coupled → use
     `/v1/chat/completions`, add the role name to the default value of
     `ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES` in
     `src/llm_primitives/backend.py:_init_caching_backends`.

4. **Verify with `llama-server /apply-template`**:
   ```bash
   curl -X POST http://127.0.0.1:PORT/apply-template \
     -H 'Content-Type: application/json' \
     -d '{"messages":[{"role":"user","content":"test"}]}'
   ```
   This returns the exact prompt the server would build via jinja. Use
   it as the source of truth when comparing against client-side templates.

5. **Smoke test the role via the orchestrator**:
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H 'Content-Type: application/json' \
     -d '{"prompt":"What is 2+2?","force_role":"NEW_ROLE","real_mode":true,
          "stream":false,"timeout_s":30}'
   ```
   Expect: a clean answer with no marker artifacts. If output contains
   `<|channel>` / `<|turn>` / `<|im_start>` / `<start_of_turn>` literals,
   the template wiring is wrong.

6. **Run the family-detection smoke test in `tests/unit/`** (if
   present): there's a small inline test fixture that exercises
   `apply_chat_template_for_model` against a fixed list of model names.
   Add the new model's expected family.

---

## Historical incidents (anti-patterns this page exists to prevent)

### 2026-05-08 — Worker swap to gemma-4 broke routing silently

The `worker_general` role was swapped from Qwen3-Coder-30B-A3B (Qwen
family) to gemma-4-26B-A4B-it (gemma 4 family). The orchestrator was
hardcoded to apply the Qwen template at `chat.py:498`. After the swap:
- gemma-4 received `<|im_start|>` markers it didn't recognize
- Returned 0 tokens / immediate EOS
- Autopilot fell back to frontdoor for every worker_general request
- Classifier interpreted "worker_general: 0.1% success" as a real signal
  and started routing 97% of traffic to frontdoor

**Discovered 2026-05-22** via inspection of the inference_tap log
showing the worker_general / frontdoor 60s-pause / fall-back pattern.

**Fixed via**:
- `206701f` — per-role template helper in `chat_utils.py`
- `2c1711a` — `/v1/chat/completions` migration for gemma-4 worker roles

**Time-to-discovery**: 14 days. Cost: ~2 weeks of skewed routing data.

### 2026-05-22 — Pre-templated prompts via `/completion` for gemma-4

Even with the per-family template detector landed, gemma-4 still
required the multi-channel format that `/completion` can't apply
server-side. Sending the proper gemma-4 template via `/completion`
empirically TIMES OUT with 0 tokens on the ik_llama.cpp MTP build.

The pragmatic fix was to route gemma-4 worker roles through
`/v1/chat/completions` — server-side jinja handles templating AND
multi-channel response parsing.

**Anti-pattern**: trying to replicate dynamic / multi-channel chat
templates as a client-side static wrap. If the template uses
conditional logic (`{% if enable_thinking %}...`) or auto-emits
channel prefixes based on kwargs, ALWAYS use `/v1/chat/completions`.

---

## Measured 2026-08-21: the terseness prompt pays; thinking-mode deficits were budget artifacts

Sources: `handoffs/active/qwen-chat-template-evaluation.md` (CT-1/CT-1b/CT-5, all dive- and
run-verified same day), artifacts under `artifacts/chat-templates/`.

**CT-1 (embedded vs epyc-qwen3x-v1, 160 paired questions, CPU):** perfect parity — byte-identical
renders on the bare single-turn no-think shape, therefore bit-identical generations. epyc-v1 is a
proven zero-regression drop-in on the production path; the templates only diverge on system
prompts, tools, history and effort steering. (Method lesson: render-diff the arms ON THE EVAL SHAPE
before a long run.)

**CT-1b (+terseness arm, same pinned ids, fixed 900-token budget):** never worse, significantly
better where budget binds, at 34–99.5% fewer answer tokens — math 80=80% at −34%; mmlu_pro
37.5→40.0% at −99% (mean 2.0 tokens: the model finally obeys "letter only"); gpqa_diamond
42.5→60.0% (flips 0:7, p≈0.016, mostly truncation-avoidance); cruxeval 27.5→30.0% at −36%. The
CCoT math-penalty hazard did not materialize. Deployable artifact:
`epyc-qwen3x-v1/chat_template_terse_arm2.jinja` (sha `1443ea9ab4bb…4551`, injection-free).

**CT-5 (thinking ON vs OFF on Qwen3.8/MI210, 60 paired GPQA-Diamond-CoT):** at a 4,096 cap,
thinking read −6.7pp — decomposition showed the deficit was ENTIRELY truncation zeros
(completed-subset 95.1% vs 94.9%). At symmetric 16K caps: **85.0% vs 86.7%, flips 2:3 for
thinking (n.s.), truncation 0/1** — a statistical tie at +21% tokens-per-solved. Standing rule
this yields: **an accuracy deficit measured under a token cap is not a quality finding until
decomposed by finish_reason** — and every anti-reasoning datum this stack produced (think-loops,
termination defects, caps) has been infrastructure, not model quality. `enable_thinking=false`
remains posture on economics, now measured on the production model itself.

## The embedded template is per-MODEL, not per-family (measured 2026-08-21)

The family table above answers *which turn markers* a model uses. It does **not** answer what the
GGUF's embedded template actually does, and those diverge — including between two models of the
same family. Extracted by GGUF header read from every production GGUF (no model loaded):

| Model / role | Embedded template | `reasoning_effort` outside {xhigh,medium,low} | `xhigh` by default | Blank-`<think>` duplication | Retains history thinking |
|---|---|---|---|---|---|
| Qwen3.8-27B — `architect_general` | 9,993 B `12827f24b742` | **raises** on `none`; `high` silently → `xhigh` | **yes** | **yes** | yes |
| Qwen3.6-27B — `coder_escalation` | 8,057 B `55d4931433fe` | ok | no | no | **no — discards** |
| Qwen3.6-35B-A3B — `frontdoor` | 8,057 B (byte-identical to above) | ok | no | no | **no — discards** |
| Qwen3.5-122B-A10B — `architect_critic` | 7,992 B `8452ca85cb1e` | ok | no | no | **no — discards** |

Four models, **three distinct templates**. Consequences worth carrying:

- **We do not serve stock Qwen templates.** Every one of these is an Unsloth-patched variant (the
  Qwen3.8 one ends `{#- Unsloth fixes - developer role, merged system messages, tool calling #}`);
  stock `Qwen/Qwen3.8-27B` is 8,952 B. No registry descriptor records this.
- **`reasoning_effort` is a live footgun on Qwen3.8 only.** Stock *raises* on `high`; our Unsloth
  variant silently *coerces* `high → xhigh`. An OpenAI-style client sending the ordinary value
  `high` therefore gets a hard 500 upstream and silent maximum-effort reasoning here — opposite
  failure modes. Both raise on `none` and `minimal`.
- **The `xhigh` default injects tokens.** With no kwargs, Qwen3.8 renders 345 B including a
  209-character reasoning instruction; at `medium` it renders 136 B.
- **All of the above sit INSIDE the `enable_thinking` gate.** Our stack-wide
  `chat_template_kwargs.enable_thinking: false` makes every one of them unreachable — which is why
  the fleet is not currently exposed, and why that setting is load-bearing beyond loop prevention.
- **Three of four incumbents discard history reasoning entirely**, in both history shapes
  (`reasoning_content` field and inline `<think>` tags). Inert under `enable_thinking=false`; it
  becomes a prefix-cache question the moment any role runs thinking-ON.

## The template is compiled once at model load, not per request

Verified in frozen `production-consolidated-v9` (`/mnt/raid0/llm/llama.cpp` @ `0db32c06e`):
`common_chat_templates_init` has exactly one server call site,
`tools/server/server-context.cpp:1454`; the per-request path is
`oaicompat_chat_params_parse` → `common_chat_templates_apply` (`server-common.cpp:1092`), which
renders an **already-compiled** program. So template *parse* cost is a one-time cost at startup and
cannot affect steady-state throughput. Render cost is AST-shaped (the runtime traverses the compiled
program by recursive `execute(ctx)` per node) but is sub-millisecond and invisible against prefill.

**This is the standing refutation of "flatten the template AST to speed up inference" claims.**

## The engine is `common/jinja/`, NOT minja

A grep for `minja` in the production tree returns three hits and **every one is stale** — a TODO
comment at `common/chat.cpp:749`, a test, and a doc. The actual engine is first-party, at
`common/jinja/` (lexer / parser / runtime / value / caps), introduced upstream in
ggml-org/llama.cpp PR#18462 and inspired by huggingface.js's jinja package.

It implements **input marking** as a security property: `jinja::string` carries an `is_input` flag
through one-to-one, one-to-many and many-to-one transformations so user content cannot forge special
tokens, and `common/chat.cpp` normalises input *before* it reaches the runtime
(`common/jinja/README.md`). **A chat template is executable code in the prompt-construction
position** — substituting a third-party template moves that code and must be checked against this
path. No community template repository mentions it.

---

## Cross-references

- `feedback_qwen3x_enable_thinking_false` (memory) — Qwen reasoning loop
  prevention via `chat_template_kwargs.enable_thinking=False`
- `feedback_verify_current_stack_before_claiming_role_replacement`
  (memory) — verify what's actually deployed in a role before claiming
  a model is a "drop-in replacement"
- `progress/2026-05/2026-05-22.md` — full diagnosis chain for the
  worker_general silent failure
- `progress/2026-05/2026-05-23.md` — `/v1/chat/completions` migration
  and live verification

## Open Questions

- Which template invariants should be promoted into automated per-role startup attestations?
  The 2026-08-21 sweep makes three concrete candidates: the embedded-template digest per role, a
  `reasoning_effort` round-trip probe, and a stock-vs-served divergence check.
- Should any role run thinking-ON with history retention, which is the only configuration where the
  incumbents' discard behaviour costs anything? Tracked as CT-5 in
  `handoffs/active/qwen-chat-template-evaluation.md`.

## Related Categories

- [LLM Prompting](llm-prompting.md)
- [Model Serving](model-serving.md)
- [Tool Implementation](tool-implementation.md)

## Source References

- `src/api/routes/chat_utils.py`
- `src/backends/llama_server.py`
- `src/llm_primitives/backend.py`
- `scripts/server/stack_numa.py`
- `progress/2026-05/2026-05-22.md`
- `progress/2026-05/2026-05-23.md`
- `handoffs/active/model-stack-single-source-update-pipeline.md`
- `handoffs/active/qwen-chat-template-evaluation.md` (2026-08-21) — the fleet sweep, the defect
  matrix, and the template-swap decision
- `progress/2026-08/2026-08-21-research-intake.md` (2026-08-21)
- `research/intake_index.yaml` — intake-1212, intake-1213#record, intake-1216#record (dive-verified /
  dive-overturned; digests and per-claim anchors recorded there)
- `/mnt/raid0/llm/llama.cpp` @ `0db32c06e` — `tools/server/server-context.cpp:1454`,
  `tools/server/server-common.cpp:1092`, `common/jinja/README.md`

## Compiled Update — 2026-08-21 (evening): CT-5(c) measured — at a 4K budget thinking does not pay, and the deficit is a truncation artifact, not a capability fact

The (c) arm ran to completion on the MI210 (60 paired gpqa_diamond_cot, Qwen3.8-27B, v9 HIP
residency proven by three instruments, 0 errors). Two-part result, then a same-day correction that
changes what it may be cited for:

1. **The R2d think-loop tail did NOT reproduce** on Qwen3.8 — non-termination 19/60 (thinking OFF)
   vs 21/60 (ON): mode-independent, driven by the 4,096 cap plus the suite's own CoT prompt.
2. **Thinking-ON failed to pay at this operating point**: 63.3% vs 70.0% accuracy, paired flips 7:3
   against (n.s., McNemar p≈0.34), +23% tokens-per-solved. Posture (a) stands; (c) declined for
   deployment.
3. **THE CORRECTION (operator-prompted): the 6.7pp deficit is ENTIRELY a truncation/budget
   artifact.** Completed-subset accuracy is 95.1% vs 94.9% (paired both-completed flips 1:0);
   every truncated thinking row is an automatic zero (0/21 ever emitted an answer line; truncated
   rows' median think 11,078 chars vs 3,187 completed). Public Qwen thinking numbers run ~32K
   budgets where truncation ≈ 0. **So CT-5(c) answered the OPERATING-POINT question (at 4K total,
   thinking does not pay) — NOT the capability question.** Prior anti-reasoning findings here
   (+33pp no-think, R2d tails) were broken-serving artifacts on other models; reasoning has never
   been measured on this stack with working serving AND adequate budget. A symmetric-16K rerun was
   launched the same day; until it reports, cite this measurement only with the operating-point
   scope attached.

**Standing citation rule this creates: never cite a thinking-vs-no-thinking accuracy delta without
its token budget and per-arm truncation rates.** A capped budget converts runaway thinking into
automatic zeros and manufactures an anti-reasoning result that vanishes on the completed subset —
the survivorship-bias shape, inverted.

### Source References

- [`handoffs/active/qwen-chat-template-evaluation.md`](../handoffs/active/qwen-chat-template-evaluation.md) — CT-5 ✅ full result + correction + operator ruling; 16K rerun tracking
- `artifacts/chat-templates/ct5c-gpu-20260821/` — per-question JSONL, paired ids, server log

## Compiled Update — 2026-08-23: Qwen3.8 template evaluation + CT-5c/ab-cpu runs

**Confidence: verified** for the measured arms and the rendered proofs; `inference` for the E-7
stamp-gap recommendation (extension from the intake-892 precedent, sound but not yet ratified
doctrine).

The CT-5(c) 4K/16K arms and the CT-1b ab-cpu terseness arms are compiled above (2026-08-21); this
section adds what landed around and after them — the calibration-price inventory, the injection
verdict on the community templates, the EPYC-owned build, the live deployment, and the first
decision-gating stamps.

- **CT-2 — a template swap is not a config change, and it voids the calibration this stack was
  measured under.** `--chat-template-file` has **zero occurrences** in the orchestrator's launcher
  and registry code, so every measured row this stack owns was produced through each model's
  GGUF-embedded template and there is **no already-swapped control arm anywhere**. The flag exists
  in the frozen kernel (`common/arg.cpp:3487`) — adoption needs new launcher plumbing, priced as a
  prerequisite of adoption, not of the swap. A stack-wide swap voids **4 expensive / 5 moderate /
  2 cheap** artifacts — and the expensive four (SWE-verified oracle-40, the R2a +32pp CoT-prompt
  result, GPQA/LCB, the certified reasoning-effort curves) are the entire comparative authority of
  `architect-model-selection-bench.md`. A **single-role pilot** voids only that role's slice.
  Related gap, still open: the E-7 re-calibration stamp `(model, quant, kernel/era)` omits the
  template, yet the prompt-template axis is the *larger* measured effect so far — a swap would pass
  E-7's validator silently; `template_sha256` belongs in the stamp (recorded as a cross-handoff
  finding for `reasoning-effort-levels.md`).
- **CT-3 — the community templates are NOT drop-in safe: they add a user-controlled thinking
  channel that input marking cannot see.** frog and sharp both scan **ten out-of-vocabulary
  `<|think_*|>` pseudo-tokens** (in neither model's vocabulary) out of `msg.content` for roles
  `{system, developer, user}` and use them to overwrite the template's own thinking state, then
  strip the markers from the rendered prompt — so a client able to place fourteen literal
  characters into a user or system message **silently revokes the stack's role-keyed
  `enable_thinking=false`** for the whole conversation, with no trace in the output. Input marking
  cannot mitigate it: `is_input` constrains what input text may *become* (tokenization); it places
  no constraint on what template **control flow** may branch on. Rendered proof at
  `enable_thinking=False`: `sharp.jinja` 797 B → 1003 B with a marker-carrying user turn (thinking
  ON, +206 B injected effort prose), `frog.jinja` 81 B → 307 B; stock and our GGUF template stay
  inert (95 B). That is a low-trust input overriding a high-trust generation policy — a direct
  cost channel (unmetered token amplification). Mitigations if adoption is ever pursued:
  delete the two marker-scan blocks (retention behaviour is independent of them), restrict the
  scan to `system`-only, or strip the markers at the orchestrator boundary.
- **CT-7 — the EPYC-owned template `epyc-qwen3x-v1` is built and validated.** Feature-mined from
  froggeric v22.3 (Apache-2.0): history retention grafted, the two `<|think_*|>` marker-scan
  blocks **deleted by construction** (the CT-3 surface), the tag sanitizer kept, terseness excluded
  (an A/B arm, not a default). 24,659 B, sha256 `faaecb215031…d8c15`; vendored suite v21 9/9, fuzz
  clean over 2,000 conversations (nine invariants), v22 85/100 with all 15 failures being the
  deliberately-deleted feature; oneline build (19,421 B) parity holds; the decisive probe — a
  user-content `<|think_off|>` flips froggeric and does NOT flip epyc-v1; and frozen v9
  `common/jinja` renders all 7 fixtures **byte-identical** to Jinja2 goldens via `/apply-template`.
- **CT-DEPLOY — the terseness pilot is LIVE IN PRODUCTION (2026-08-22)** on frontdoor (all three
  instances, render-verified) and architect_general (+ coder_escalation via alias):
  `server_mode.<role>.chat_template_file` plumbing landed (orchestrator `34ff6fcc`), registry
  blocks with per-role one-line reverts (research `b9ba66e6`), stack-change check fully green
  INCLUDING runtime attestation (declared == compiled == live cmdlines — first time). The pilot
  serves the measured arm-2 template (`1443ea9ab4bb…4551`), not the community file.
- **CT-E7 — the CT-1b numbers REPRODUCE on the live path, and architect_general gets first-ever
  stamps** at `(model, quant, v9 0db32c06e/10125, template 1443ea9ab4bb)`: frontdoor (35B, CPU)
  math 82.5% @281 tok · mmlu_pro 37.5% @45 · gpqa_diamond 55.0% @2 · cruxeval 32.5% @394 —
  live == measured. architect_general (Qwen3.8, GPU) 85.0 / 27.5 / 47.5 / 22.5%, zero errors.
  `gpqa_diamond_cot` was VOIDED at maxtok 900 by the finish_reason rule (48/60 truncated — the
  budget trap again, self-inflicted this time); the 4096 rerun supersedes: **75.0% (45/60)**,
  +45pp from the cap fix alone and ABOVE the embedded template's CT-5 baseline (70.0%) on the same
  pinned ids. All 8 valid cells emitted as producer-authored belief rows grading
  Witnessed/Attested, empty reasons — the program's first decision-gating measurements.
- **CT-8 — the belief-kernel write side is wired for this axis**: producer writer
  `chat_template_ab_capture.py` (atomic sidecar at summarize-time, fail-loud on any guessable
  field — 40-hex kernel commit, 64-hex template sha, results-file hash attestation) + strict
  reader `chat_template_ab.py` (registered `chat-template-ab-measurement`; grading 100% delegated
  to `claim_tuple.grade()`); completed CT-1/CT-1b/CT-5/16K runs are pre-hook and emit zero rows by
  doctrine.

**Standing rule the sweep reinforces:** never adopt a third-party template without auditing its
control-flow surface — the marker-scan channel is the template-era analogue of the injection
classes the engine's input marking exists to stop — and keep the compiled citation rule for
thinking-vs-no-thinking deltas (budget + per-arm truncation rates, above).

### Source References (2026-08-23 Qwen3.8 template evaluation)

- [`handoffs/active/qwen-chat-template-evaluation.md`](../handoffs/active/qwen-chat-template-evaluation.md) — CT-2/CT-3/CT-5/CT-7 closures, CT-DEPLOY/CT-E7/CT-8 records, rendered proofs and artifact digests
- [`handoffs/active/qwen38-27b-replace-qwen36.md`](../handoffs/active/qwen38-27b-replace-qwen36.md) — Q38-T1/T3: reachability of the two Qwen3.8-only defects and the non-stock Unsloth template digest
- [`progress/2026-08/2026-08-21-research-intake.md`](../progress/2026-08/2026-08-21-research-intake.md) — the intake dives, the fleet-sweep correction, CT-7 build/validation, CT-1/1b arms
- [`progress/2026-08/2026-08-22-research-intake.md`](../progress/2026-08/2026-08-22-research-intake.md) — CT-DEPLOY end state, E-7 stamps and the voided/4096-rerun cells, CT-8 wiring, belief rows
- [`progress/2026-08/2026-08-21-operator.md`](../progress/2026-08/2026-08-21-operator.md) — the coordination-day context (EVL-50 closure, four-agent fan-out) around the CT work

---

## Compiled Update — 2026-08-23 (evening): CT-E7b stamps propagated to the master registry, and the CT-9 pilot-adoption decision

**Confidence: verified** — the CT-E7b propagation is a landed compile-chain regeneration (research `577f215a`, orchestrator `5c41567d`, guard green); CT-9 is a production-behavior sweep over an 18-hour window with the evidence bundle on file.

### CT-E7b — E-7 stamps are now in the MASTER registry quality rows; all nine cells live

The master-registry propagation is DONE and the compile chain is FULLY GREEN. frontdoor's `quality_pct: 93` (May-4 judge) is VOIDED → E-7 live-path re-stamp at template `1443ea9ab4bb` (math 82.5 / mmlu_pro 37.5 / gpqa_diamond 55.0 / cruxeval 32.5, CT-1b arm-2 REPRODUCED live); architect_general + coder_escalation's swe_verified 57.5 VOIDED (Qwen3.6-27B A3 arm — model AND template both swapped) → **first-ever Qwen3.8 stamps** (85.0/27.5/47.5/22.5 + gpqa_diamond_cot 45/60 = 75.0% @4096, superseding the 900-cap void). All nine E-7 cells live in the derived layer's `quality_by_axis.local`; `guard ok / guard_strict ok / acceptance: no-inference checks passed`. Belief sidecars: `chat_template_ab_capture.v1`, all Witnessed/Attested (`ctab_e1e56fda…` / `ctab_c16c50e1…` + the cot4096 superseding row). The stamp is now ENFORCED, not just practiced: the E-7 validator was extended 2026-08-23 (orchestrator `0e801e68`) — `REQUIRED_CERTIFICATION_FIELDS` is now `(model, quant, kernel_era, template_sha)`, the bound sha read from `roles.<role>.chat_template` falling back to `server_mode.<role>.chat_template`, compared in normalized 12-char form; 16 tests pass. **A template swap (or GGUF re-embed) invalidates certified effort levels exactly as a quant change does** — the template axis is a first-class member of the certification tuple.

> **Caveat (2026-09-17).** The `mmlu_pro` numbers above (CT-1b 37.5→40.0, E-7 frontdoor 37.5,
> architect_general 27.5, and the registry values stamped from them) are under-scored.
> 10 of the 40 pinned items have gold I or J, and the shared scorer at the time accepted only A-H, so
> those items were forced wrong. An offline re-score of the recorded answer tails gives roughly
> +10pp per cell (e.g. architect_general ~40%, frontdoor ~50%). Source:
> [`qwen-chat-template-evaluation.md`](../handoffs/active/qwen-chat-template-evaluation.md) → CAVEAT
> 2026-09-17.

### CT-9 — pilot adoption decision: HOLD all three roles; no fleet-wide extension

The adoption decision was made on **production behavior, not new benchmarks**: the 18-hour window (2026-08-22 13:55Z → 2026-08-23 08:00Z) carried **calibration traffic only — zero real user/autopilot traffic after 15:36:49Z**. Signal: 0 server errors, 0 truncations, 0 slot-restore failures, 0 KV-migration events on the four ports; one gateway-side 504 whose server-side completion returned 200. Decision lines: **frontdoor → HOLD** (E-7 stamps reproduce CT-1b arm-2 live; revert is one line); **architect_general → HOLD** (first-ever stamps; 282 clean slot releases); **coder_escalation → HOLD** (no production signal exists); **fleet-wide → NOT EXTENDED** — the adoption precondition "serves real traffic for a while" is unmet, and extending unmeasured roles would void their CT-2 calibration slices on an unmeasured basis. What flips a role to REVERT: any error/truncation/slot-restore signature or real-traffic quality drift — none observed. Follow-ups filed: CT-10 (cruxeval watch-item re-check under real coder traffic — the CT-1b watch-item has no production basis in the window) and CT-11 (re-decide after the first non-calibration traffic signal).

### Source References (2026-08-23 evening)

- [`qwen-chat-template-evaluation.md`](../handoffs/active/qwen-chat-template-evaluation.md) — CT-E7b propagation with the voided rows and superseding stamps, CT-9 decision lines and evidence record, CT-10/CT-11
- [`reasoning-effort-levels.md`](../handoffs/active/reasoning-effort-levels.md) — the E-7 validator extension (`0e801e68`, template_sha enforced) and the `active_kernel_era` v8→v9 correction (cross-listed with [Reasoning Compression](reasoning-compression.md))
- [`progress/2026-08/2026-08-23.md`](../progress/2026-08/2026-08-23.md) — the full CT-9 evidence bundle (read-only production sweep)

## Compiled Update — 2026-10-24 (wrap-up sweep 9, delta over 2026-10-23)

- **CT-THINK-CODER decided: keep thinking ON on the coder server.** The pre-registration is operator ruling C1 plus OP-69 option (a) / RI-23a (receipt `RATIFY-RI23A-20260929`). `coder_escalation` is an alias on the :8083 process (Qwen3.8-27B Q8 on the MI210); thinking-on is request-side via registry kwargs (`enable_thinking: true, reasoning_effort: medium`), so the 2026-10-22 filler `--reasoning off` fix does not touch it, and a per-request `enable_thinking:true` would override a server-side off anyway. Turning it off would reverse a ratified decision and needs its own `stack-change` package.

Sources: [Qwen chat template evaluation](../handoffs/active/qwen-chat-template-evaluation.md)

## Compiled Update — 2026-10-29: CT-21 HOLD stands; CT-12.5 fold confirmed

- **CT-21 (architect Skill-Inject/IB2 flag) verdict: HOLD, default OFF.** The predeclared rule (sha256 `4040098b...`) over 2352 unique records fails the investigate competence gate: OFF 13/200 vs ON 11/200, ON-OFF -1.0 pp, Tango one-sided 95% lower bound -4.18 pp (must exceed -3.0), aligned-twin net loss 6 (limit 1). Synthesis competence was 0/200 in both arms, an implausible floor flagged for scorer audit, so it is not evidence. Skill-Inject ASR improved on neither surface (synthesis 6/316 vs 3/316, p=0.254; investigate 0/316 vs 2/316); fixture-set static attacks only, no robustness claim.
- **Parse-outcome repair:** a native unparseable multiple-choice answer is now scored as an incorrect outcome (malformed fixture gold still refuses), after slice 3 failed rc1 on `AnswerParseError`; all 1956 completed rows were preserved and no historical response reconstructed.
- **v2 exploratory rerun (2026-10-28) ended rc1 at the belief writer** (`CaptureError`), with 80/80 raw files retained. It is an observation only: no score, no change to the HOLD, and CT-21 is not re-armed.
- **CT-12.5 closed by audit:** the `6dfbc9e86` fix is folded into the champion (patch-id equal commit `9a44414c4`, ancestor of champion `c72ec82f5`), with test-chat-input-spans and `test_chat_special_tokens.py` recorded as PASS.

Sources: [qwen-chat-template-evaluation handoff](../handoffs/active/qwen-chat-template-evaluation.md); [CT-21 aggregate verdict](../artifacts/chat-templates/ct21-verdict-20261027/AGGREGATE.md); [ct21-direct-ready progress](../progress/2026-10/2026-10-28-ct21-direct-ready.md); [codex-ni-01a16d6b progress](../progress/2026-10/2026-10-28-codex-ni-01a16d6b.md)

## Compiled Update — 2026-10-31 (operator wiki sweep, workspace-58)

**Confidence: verified** for the template-rendering confirmation (CPU rendering/tokenization only); no GPU compute, throughput or quality claim.

- **Static template results held on the live server path.** The predeclared all-four P1/P2/P3 rule confirmed `35b-terse`, `27b-embedded`, `vl-embedded` and `fn-embedded` (each passed four original fixtures and the shared trunk), joining the earlier 27b-terse result. HIP/KFD/VRAM samples prove model residency only; this closes LB5.1's live-path check, nothing broader. ([source](../handoffs/active/agentic-serving-harness-fixes.md))
- **The typed-vs-tool prompt diverges right after the user turn marker.** In the TD-29 pair, rendered prompts shared 17 bytes / 3 tokens, diverging immediately after `<|im_start|>user\n` (`Fill in` vs `Answer`); reported and tokenized lengths matched. One pair, no cohort cache verdict. ([source](../handoffs/active/typed-decision-plane.md))

Sources: [agentic-serving-harness-fixes](../handoffs/active/agentic-serving-harness-fixes.md) · [typed-decision-plane](../handoffs/active/typed-decision-plane.md)
