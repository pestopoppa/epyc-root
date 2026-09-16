# 2026-09-16 — sub-op42: OP-42 readiness package (M-12a Tulving → M-12b BEAM)

This lane ran no model inference and started or stopped no processes. The only tool that touched a model
file was `llama-tokenize` (production tree `build/bin`, `vocab_only = true` at `tools/tokenize/tokenize.cpp:146`,
so no weights are loaded and there is no forward pass). GGUF metadata was read with `gguf-py`. Prompts were
built by the lane-branch adapters: research `sub/memeval-20260916` @ `87991705`, exported with `git archive`
and run under `/mnt/raid0/llm/delta-Mem/.venv` (the research venv has no pyarrow).

- Scratch: `/mnt/raid0/llm/tmp/sub-op42/`
  - `out/*.jsonl`: the rendered prompts
  - `counts_{qwen,gemma,q3next}.txt`: per-prompt token counts
  - `stats.py`, `est.py`
- Owning handoff: `handoffs/active/episodic-memory-integrity.md` → M-12.
- Instruments: `handoffs/active/conversational-memory-eval-instrument.md` (CME-1..4).

---

## 1. Prompt lengths in TOKENS (each model's own GGUF-embedded tokenizer)

Qwen3.8-27B and Qwen3.6-35B-A3B have **byte-identical vocabularies**: same token list, same merges, pre-tokenizer
`qwen35`, sha256 prefix `fb1dfd53a1e5e03c`. One count therefore serves both. gemma-4-26B-A4B Q8_0 and Q4_K_M
also share a vocabulary (`650c0bb9ff16962c`).

The counts are the raw rendered prompt. They exclude the chat-template wrapper (about 10–30 tokens) and the output
budget.

| Instrument (prompts) | Tokenizer | p50 | p95 | max | > 32,768 | > 65,536 | > 131,072 | > 196,608 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **BEAM 100K split, vanilla/full-history** (400 = 20 conv × 10 abilities × 2) | Qwen3.x (qwen35) | 128,526 | 187,763 | **191,456** | 400 | 400 | **160 (40%)** | 0 |
| same | gemma-4 | 132,256 | 186,844 | 190,049 | 400 | 400 | **200 (50%)** | 0 |
| same | Qwen3-Next-80B (prod ingest) | 122,160 | 181,726 | 183,799 | 400 | 400 | 140 (35%) | 0 |
| **Tulving 200ch (196ch Claude book), full/CEILING** (686) | Qwen3.x | 104,705 | 104,715 | **104,725** | 686 | 686 | 0 | 0 |
| same | gemma-4 | 101,911 | 101,921 | 101,930 | 686 | 686 | 0 | 0 |
| same | Qwen3-Next-80B | 103,813 | 103,823 | 103,833 | 686 | 686 | 0 | 0 |
| Tulving 200ch, memory-OFF (`none`) | Qwen3.x / gemma-4 | 52 / 54 | 62 / 64 | 72 / 73 | 0 | 0 | 0 | 0 |
| Tulving 200ch, memory-ON (`retrieved`, top-5 chapters) | derived | ≈2.7K | — | **≤ ~4.1K** | 0 | 0 | 0 | 0 |

- **Retrieved-arm bound.** The top-5 chapters sum to at most 19,201 characters (the median chapter is 2,567
  characters). At the Qwen rate of 4.79 characters per token, that is about 4.1K tokens.
- **Every candidate's trained context is 262,144** (GGUF `*.context_length`), so no prompt exceeds a model limit.
  What matters is the context the server is configured with.
- **BEAM's "100K" split is not a 128K-fitting instrument on our tokenizers.**
  - The median prompt is about 128K tokens, and 35–50% of prompts exceed 131,072.
  - The longest conversation (conv 11) is 191,430–191,456 Qwen tokens.
  - Serving "BEAM 128K" with a 131K context therefore needs a truncation rule, and a truncation rule changes the
    instrument. The alternative is a context of at least 196,608 tokens per slot (192K plus an output budget).
    **This package assumes 196,608 per slot and no truncation.**
- **The Tulving full prompts share one prefix.** All 686 prompts are the same ~104.7K-token book followed by a
  52–72-token question.
- **BEAM prompts share a prefix within each conversation.** All 20 questions of a conversation share that
  conversation's transcript.

## 2. GPU serving candidates (MI210, 64 GiB)

**KV sizing: only the full-attention layers hold KV.** The hybrid GDN layers carry a fixed recurrent state of a few
MB per sequence per layer, independent of context. All figures below are f16 KV, which is what the canonical GPU
recipes use (`ctk=f16`, `ctv=f16`, `fa=on`, `kv_unified=false`).

| Model | Arch (GGUF) | Weights | Full-attn layers | KV / token | KV @131,072 | KV @196,608 | Recurrent state / seq |
|---|---|---:|---|---:|---:|---:|---:|
| **Qwen3.8-27B-Q8_0** | `qwen35`, 64 layers + 1 NextN; attention every 4th; n_kv 4 × 256 | 27.04 GiB | 16 (+1 MTP) | **64 KiB** (68 incl. MTP) | 8.0 (8.5) GiB | 12.0 (12.75) GiB | ≈150 MB (48 GDN layers) |
| **Qwen3.6-35B-A3B-MTP-Q8_0** | `qwen35moe`, 40 + 1 NextN; attention every 4th; n_kv 2 × 256 | 35.19 GiB | 10 (+1 MTP) | **20 KiB** (22) | 2.5 (2.75) GiB | 3.75 (4.1) GiB | ≈60 MB (30 GDN layers) |
| gemma-4-26B-A4B (Q8_0 ORIG / Q4_K_M) | `gemma4`, 30 layers, SWA window 1024 on 25 layers | 25.00 / 15.64 GiB | 5 global (n_kv 2 × 512) | **20 KiB** global, plus SWA ≈200 KiB/token × ~3K window | 2.5 GiB + ~0.6 GiB SWA | 3.75 GiB + ~0.6 GiB SWA | — |
| Qwen3-Next-80B-A3B Q4_K_M (the production `ingest_long_context` artifact) | `qwen3next`, 48 layers, 12 attention | 45.08 GiB | 12 | 24 KiB | 3.0 GiB | 4.5 GiB | ≈45 MB |

### Fit (estimates, not measurements)

**How the base was estimated.** The fixed non-KV base comes from the measured residency peaks in
`docs/design/champion-max-performance-20260908.md` §3 and §6, taken at ctx 16384:
- 27B + DFlash2: 33.09 GiB at np=1, 37.67 at np=4.
- 35B-A3B MTP: 36.6 GiB at np=1, 41.37 at np=16.

The KV that the base already contained was subtracted, and **about 1.5 GiB was added for the long-context
compute/mask buffer (ubatch 2048 × ctx)**. That buffer is an estimate; nobody has measured it.

- **Qwen3.8-27B + DFlash2, 131K per slot:**
  - np=1 ≈ 42 GiB ✅
  - np=2 ≈ 52 GiB ✅
  - np=3 ≈ 61–62 GiB ✗ (too tight)
- **Qwen3.8-27B + DFlash2, 196K per slot:**
  - np=1 ≈ 46 GiB ✅
  - np=2 ≈ 59–61 GiB ✗ (too tight)
- **Qwen3.6-35B-A3B-MTP, 131K per slot:**
  - np=4 ≈ 49–50 GiB ✅
  - np=6 ≈ 55–56 GiB ✅ (margin is thin)
  - np=8 ≈ 60–62 GiB ✗
- **Qwen3.6-35B-A3B-MTP, 196K per slot:**
  - np=4 ≈ 54–55 GiB ✅
  - np=6 ≈ 62–64 GiB ✗
- **gemma-4-26B-A4B Q8_0:** about 30–33 GiB at np=1 and 196K, with room for np=4. It is **not known-good on the
  champion.** There is no canonical GPU recipe, and nothing measures prefill at depth.
- **Qwen3-Next-80B Q4_K_M:** about 52 GiB at np=1 and 196K, so it probably fits. **Its HIP serving has not been
  validated on the champion.** The only MI210 row is IQ2_M in the model-probe scoreboard.
- **More slots do not speed up prefill.** It is compute-bound on one card. Extra slots only parallelise decode
  and the short arms.

### Prefill time (bench-class instrument, so planning only)

Under MEASUREMENT.md INSTRUMENT-CLASS-1, these are `llama-bench` figures. They are **not** serving rates and must
not be quoted as absolute rates.

A per-token cost `t(d) = a + b·d` was fitted to the measured average rates at p2048 and p32768. It was then checked
against the p8192 row, which it reproduces within 0.1–0.6%. Everything **beyond 32K is an extrapolation of that
fit, not a measurement.**

Sources:
- **35B-A3B:** frozen-v9 `0db32c06e`. Figures are p2048 2068.44, p8192 1979.59 and p32768 1646.41 t/s, from
  `/mnt/raid0/llm/autokernel/probes/k28-rocprofv1-attribution-20260811-r3/receipt.json`.
  - The run used r=1, under the profiler, with graphs disabled.
  - It is **not the champion.**
- **27B:** there is **no long-prefill row for Qwen3.8-27B.** The proxy is Qwen3.6-27B Q8 (same `qwen35` shape) on
  experimental v7 `cf051d3e1`. Figures are p2048 854.17, p8192 807.61 and p32768 666.62 t/s (n=2,
  observation-only), from
  `epyc-inference-research/data/gpu-mi210/qwen36-27b-dense-v7-context-20260718T2225Z/summary.json`.
  - Qwen3.8's pp512 is 727.29 against Qwen3.6's 839.72, which suggests the **proxy may understate the 27B's time
    by about 15%**. Sources: `qwen38-27b-replace-qwen36.md` and `qwen36-27b-mtp-q8-v7-context-*`.

| Cold prefill of | 27B (proxy) | 35B-A3B |
|---|---:|---:|
| 104,725 tok (Tulving full) | 238 s (≈440 t/s avg) | 94 s (≈1114 t/s) |
| 131,072 tok | 335 s | 132 s |
| 191,456 tok (BEAM max) | 613 s (≈312 t/s) | 239 s (≈802 t/s) |
| warm suffix (~2.1K tok re-decoded at 103K depth) | ≈7.1 s | ≈2.8 s |

**Prefix reuse decides whether a run fits in one window.**
- **Tulving full arm.** Without reuse, the 27B needs 686 × 238 s ≈ 45 h of prefill and the 35B about 18 h. With
  reuse, the 27B needs about 1.4 h and the 35B about 0.55 h.
- **BEAM vanilla arm.** Without reuse, the 27B needs about 42 h and the 35B about 16 h. With reuse, the 27B needs
  about 3.0 h and the 35B about 1.2 h.

**How reuse would work on the champion.** On hybrid/recurrent models, reuse only happens through **context
checkpoints**, because the recurrent state cannot be rolled back to an arbitrary prefix. The champion
(`ef81196d5:tools/server/server-context.cpp:3640-3660`) creates checkpoints in two places:
- at user-message starts;
- at `4 + n_ubatch` and at 4 tokens before the prompt end.

Because the Tulving and BEAM question suffixes are shorter than 2,052 tokens, the second checkpoint falls inside the
shared prefix, so the next question should restore it and re-decode about 2.1K tokens. **This comes from reading
the code; it has not been observed.** It needs:
- `--ctx-checkpoints ≥ 2`;
- a `--cache-ram` large enough for BEAM (a 192K Qwen3.8 prefix is about 11.7 GiB) — or conversation-contiguous
  ordering;
- one checkpoint-hit smoke before the window is booked.

### Match against the M-12 spec

**The spec does not name a reader model.** M-12 is a within-reader memory-ON/OFF A/B, and M-12c(4) only requires
"judge ≠ reader, both held fixed across arms". Two things point at the CPU production role, though:
- The adapters register both suites only under the `ingest` and `long_context` roles (`suites.py:302-303`).
- The only historical Tulving run (`20260619_141212`, the 20ch set, SRS 0.5684 under scorer v2) was served by
  `ingest_long_context` = **Qwen3-Next-80B-A3B Q4_K_M on CPU** (:8085, 2 NUMA instances, n_ctx 262144).

**Saying it plainly:** if the operator wants the answer *for the production ingest role as served*, that requires
CPU inference, which is currently disallowed. A GPU reader answers "does trace retrieval help **this reader**". It
is a valid A/B, but it is not comparable to the June SRS (different model and a 20ch book).

| Config | Serves 104.7K / 191.5K? | Known-good on champion | Spec fit |
|---|---|---|---|
| **Qwen3.6-35B-A3B-MTP-Q8_0, np=4, 196K/slot** | ✅ / ✅ | ✅ (recipe `qwen3.6-35b-a3b-q8-gpu-mtp`, ctx 16384 only) | Best GPU fit: fastest prefill, and it is the same model the frontdoor role serves on CPU today. It therefore reads as "does memory help the root-LM model" |
| Qwen3.8-27B-Q8_0 + DFlash2, np=1, 196K | ✅ / ✅ | ✅ (recipe ctx 16384 only) | Valid, 2.5× slower. It is the architect/coder_escalation model (already GPU-served) |
| Qwen3-Next-80B Q4_K_M on GPU, np=1 | ✅ / ✅ (est.) | ✗ (not validated on HIP) | Closest to the spec's registered role, but it is not the production recipe |
| gemma-4-26B-A4B | ✅ / ✅ | ✗ | Not recommended: no recipe, no depth data, and a SWA checkpoint path adds risk |

A long-context recipe variant for any of these is new work in `artifacts/serving-recipes/`. Recipes are imported,
never transcribed. The new variant would differ only in `ctx`, `np` and `--ctx-checkpoints`/`--cache-ram`. It
carries a new `recipe_hash`, and its DFlash2/MTP acceptance at a depth of 100K or more has **never been measured**.
For eval, spec-decode does not change greedy output, so it only affects wall-clock.

## 3. Run plan

**Reader:** Qwen3.6-35B-A3B-MTP-Q8_0 (recommended); the 27B is the fallback.
**Launch:** long-context recipe variant, served with `-np 4 -c 786432` (4 × 196,608, kv_unified=false),
`--ctx-checkpoints 4`, `--cache-ram -1` (or ≥ 64 GiB), temperature 0, top_k 1. Use the row-exact route per
OP-39(C) for np > 1, or run the long arms at np=1.
**Operator-run only:** `run_benchmark.py` is operator-run (standing rule), so the commands below are for the
operator.

### M-12a — Tulving 200ch (n = 686 per arm; the headline SRS uses the 548 `get=="all"` rows)

| Arm | Env | Prompt tokens | Est. wall-clock, 35B (27B) |
|---|---|---|---|
| OFF | `TULVING_CONTEXT_MODE=none` | ≤72 | ~0.4 h (~1 h) |
| ON | `TULVING_CONTEXT_MODE=retrieved TULVING_RETRIEVAL_TOP_K=5` | ≤~4.1K | ~0.8 h (~1.9 h) |
| CEILING | `TULVING_CONTEXT_MODE=full` | 104.7K shared prefix | ~1.2 h with checkpoint reuse (~2.4 h); **~18 h (~46 h) without** |

- **Decode assumptions.** The wall-clock estimates assume about 150 output tokens per answer, at 45 t/s for the
  35B and 30 t/s for the 27B at depth. Neither decode rate has been measured.
- **Total:** about 2.5 h (35B) or about 5.5 h (27B), plus load and smoke. **M-12a needs no judge.**

Commands:

```bash
# each arm (research repo, interpreter WITH pandas+pyarrow)
TULVING_CONTEXT_MODE=<arm> python scripts/benchmark/run_benchmark.py --server-mode \
  --existing-server-port <port> --model <gpu-role> --suite tulving_episodic \
  --skip-moe-reduction --skip-speed-tests --new-run
python scripts/benchmark/score_tulving_run.py <result.json> --out-json … --out-md … \
  --belief-measurements --arm <arm> --variant Udefault_Sdefault_seed0 --chapters 200
```

### M-12b — BEAM 100K split (n = 400 per arm, 20 conversations, 1,051 nuggets)

**Arms:**
- VANILLA: full history. This is BEAM's memory-off column; it is implemented.
- `pair_chunk` RAG: the naive-memory control. **Not implemented.**
- trace/navigation: the arm under test. **Not implemented.**

**Wall-clock, 35B:**
- vanilla: about 1.2 h prefill with reuse, plus about 1 h decode (400 × 400 tokens);
- each memory arm: about 1 h;
- judge: 3 arms × 1,051 = **3,153 per-nugget calls**, about 1.5–3 h depending on the judge model.

The total is about 6–8 h, including a model swap to the judge. The 27B needs about 11–13 h.

**Commands:**
- `run_benchmark.py … --suite beam`
- then `judge_beam_run.py <result> --out-json … --judge-model <id> --judge-url <url>`
- then `score_beam_run.py <judged> --out-json … --check-dataset --belief-measurements --arm <arm>`

**Judge constraint.** The judge must be a different model from the reader, held fixed. It cannot co-reside with a
196K reader on 64 GiB, so run the judge phase after the reader is unloaded. **One option:** a 35B reader with the
Qwen3.8-27B as judge (short judge prompts, np=4 recipe as-is).

### Blockers before any run (zero-compute unless noted)

- **B1 — NEW, a latent silent-wrong-ground-truth defect.** It has two parts:
  - The 200ch set cannot be selected through `run_benchmark`. `dataset_adapters.get_adapter` instantiates
    `cls()`, so the chapter count is always the default 20, and no env var overrides it.
  - `score_tulving_run.build_prompt_index` also builds with that default.
  - **The id scheme collides:** `tulving_{variant}_ch-001_q{idx}`, because `chapter` is -1. **All 456 20ch ids
    also appear among the 686 200ch ids, and none of their prompts match** (verified here). A 200ch run scored
    today would therefore grade 456 answers against the *wrong questions'* ground truth and drop 230 as missing.
    The same collision would let run_benchmark's skip-existing logic mix the two books in one run dir.
  - **Fix:** a `TULVING_CHAPTERS` env var or a constructor argument honoured by both the producer and the
    scorer; put the chapter count (or book id) into the question id; make the scorer refuse a chapter mismatch.
- **B2 — no memory arms in the BEAM adapter.** `BEAMAdapter` only renders the full transcript. The `pair_chunk`
  RAG control and the trace arm are needed, with identical chunking and retrieval budget (M-12c(6)) and the same
  prompt contract (M-12c(7)).
- **B3 — output budget.** `run_benchmark` defaults to `max_tokens` 512.
  - M-12c(3) forbids a synthesis budget below what the highest-nugget ability needs. That is up to 9 nuggets
    (summarization, event_ordering), so the budget needs to be set explicitly.
  - Thinking must be disabled for Qwen3.6+ (`enable_thinking=false`, chat-completions path), or the 512 budget is
    consumed by reasoning.
- **B4 — judge not chosen.** `judge_port 8082` is a placeholder; the registry's 8082 is a stale Qwen2.5-7B worker
  row. `--judge-model` is required.
- **B5 — no long-context GPU recipe exists.** The recipe needs:
  - a ctx/np variant with a new `recipe_hash`;
  - a `--ctx-checkpoints`/`--cache-ram` smoke (one prompt pair, checkpoint restored). **This smoke is the only
    inference prerequisite, and it can be the window's first 10 minutes.**
  - BEAM must be ordered conversation-contiguous, or run with an unlimited `--cache-ram`, because
    `_load_adapter_suite` sorts by `(-tier, id)`.
- **B6 — merges.** Three branches must merge first: research `sub/memeval-20260916` (CME-4, M-12e-a raise, and
  the resume fix `194a83a9`), orchestrator `dae95a86` (`request_llm_judge_text`), and root
  `sub/memeval-root-*`. `/workspace` is 388 commits behind.
- **B7 — venv.** Neither repo's venv has pandas or pyarrow (M-12j). Either install them (needs network) or run
  under `delta-Mem/.venv`.
- **Still-open design items:**
  - **M-12f** (whether the CAS single-item questions are excluded), **M-12g** (SRS bin sets) and **M-12i**
    (offline re-score protocol) do not block running. They do block citing CAS or a cross-book SRS.
  - **M-12h** matters only if a judge is ever wired to Tulving.
- **CPU.** The run needs none, as long as the reader is a GPU model. CPU is needed **only** if OP-42 is read as
  "evaluate the production `ingest_long_context` role as served".

## 4. OP-42 decision package

**Context.** M-12 has two dive-verified instruments (intake-408#record, intake-1330#record) and a pre-run checklist
(intake-1337#record). This package measured the token lengths, the GPU fit and the blockers. OP-42 bundles three
separate choices: instrument admission, the inference window, and (implicitly) eval-pool registration.
**Registration is NOT part of this decision** (CJ-GATE precedent). No MEASUREMENT.md text changes under any option,
because the trust boundary is human-amendment-only. P-AB-1 (orchestrator A/B, paired effect) is the governing
protocol, and P-PAIRED is still only staged.

**Options:**

- **A. Admit both as M-12 instruments now. Grant ONE GPU window with a Qwen3.6-35B-A3B-MTP reader, M-12a then
  M-12b, after B1–B7 close (Recommended).**
  - Cost: about 10 h of MI210 time in total (about 2.5 h for M-12a, 6–8 h for M-12b), plus a 10-minute checkpoint
    smoke.
  - Risk: prefix reuse fails, and the CEILING and VANILLA arms balloon toward 18 h and 16 h. The smoke catches this
    before any arm starts.
  - Quality: answers "does trace retrieval help the frontdoor model". It is not the CPU ingest role.
  - Reversible: yes, since nothing is registered.
- **B. Admit both; grant the window in two parts. M-12a now (it needs only B1, B5, B6 and B7; no judge); M-12b
  later, after B2–B4.**
  - Earliest evidence: an M-12a-only window is about 3 h.
  - Tradeoff: two GPU bookings, and the M-12b design work (the RAG arm, the judge) runs in parallel.
  - This option is equally good if GPU time is scarce.
- **C. Admit Tulving only; defer BEAM.**
  - Rationale: BEAM's "100K" split runs to 191K tokens, and its published harness has the CME-3 defects.
  - Cost: M-12 loses its conversational (two-role) instrument, and the protocol filed 2026-09-07 is amended.
- **D. Admit both, but insist on the production CPU `ingest_long_context` reader.**
  - This reverses the GPU-only rule for this window. It gives June comparability only for the reader identity;
    the book size still differs.
  - Qwen3-Next CPU decode is about 14–21 t/s (registry). CPU prefill of 104K–184K tokens per prompt, times 1,086
    long prompts, is multi-day unless prefix reuse works on that path too.

**Recommendation: A**, with B as its degenerate form if B2–B4 lag. The 35B reader fits 196K × 4 slots with about
10 GiB of headroom, prefills about 2.5× faster than the 27B, and the M-12 claim is a within-reader delta, so no CPU
role is needed. If torn, the tie-breaker is the checkpoint-reuse smoke. If it fails, only B (M-12a with full-arm
n cut) is bookable within a single window.

**Default if no choice is made:** M-12 stays compute-gated. The zero-compute blockers B1–B7 do not depend on this
decision and should close regardless; B1 is a correctness defect.

## Belief kernel

Nothing was measured here: the token counts are dataset properties, and the fits are planning estimates. The Tulving
producer is wired (SC67), and so is BEAM (SC68). **No unwired sources were found.** The two llama-bench prefill
sources used here (the k28 rocprof receipt and the `gpu-mi210` context rows) predate the write-side hooks, so they
remain bench-class priors, not claims.
