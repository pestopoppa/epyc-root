# RoPE context extension (YaRN / NTK / LongRoPE / DCA): assessment against the 2026-10-04 stack

**Scope.** Read-only. No inference, no processes, no edits outside this file.

**Sources read:**
- handoffs (active, completed, archived), `research/`, `wiki/`, `progress/` and the intake index (local and `origin/main`);
- the `kb-search` ColBERT query, which returned the same hits as grep;
- the frozen v10 tree `/mnt/raid0/llm/llama.cpp` @ `ffc1bac82`, plus a diff against the champion `90c12df42`;
- GGUF headers, read with the frozen tree's `gguf-py` under the orchestrator venv;
- vendor model cards on disk (`models/turboderp/*/README.md`, `config.json`);
- the registry, `tmp/kv-sizing-8083-20261003/DECISION.md`, the KVU-16b and Q38-T7 reports, and `kv-unified-stack-rollout.md` on `origin/main`.

**Provenance tags.** **[M]** means measured or read from a source, with the source given. **[D]** means derived, with the arithmetic shown.

---

## 0. Headline

1. **One stale handoff carries the topic: INF-59, `handoffs/active/yarn-context-extension-research.md`.**
   - Created 2026-03-09. Status QUEUED LOW. It contains no measurements.
   - Everything model-specific in it has rotted. It targets Qwen3.5 and Qwen3-Next-80B, which are gone. It assumes KV memory on CPU RAM, plans a TurboQuant path that was abandoned, and treats 32K as the "operational line" when production now serves 262K per request.
   - No handoff exists for NTK, LongRoPE, DCA or "context boost to 1M". The "1M" in the operator's memory comes from this handoff's "256K → 1M with YaRN" framing and from the vendor model cards.
2. **The technique itself is current and vendor-blessed for every production LLM.**
   - Qwen documents static YaRN for Qwen3.8-27B and Qwen3.8-Flash-Next: factor 4.0, `original_max_position_embeddings` 262144, "extensible up to 1,000,000 tokens". For a typical length around 524K, the cards recommend factor 2.0.
   - The v10 graph and kernels implement YaRN correctly for these models' interleaved-MRoPE, partial-rotary heads.
3. **Correction to the brief: the v10 server clamps every slot to `n_ctx_train` unconditionally.**
   - `tools/server/server-context.cpp:1316-1322` [M]. The rope flags do not lift the clamp.
   - A YaRN instance must also pass `--override-kv qwen35.context_length=int:<N>`.
   - Once that override is in place, `--yarn-orig-ctx 262144` becomes mandatory. Without it, `n_ctx_orig_yarn` silently follows the overridden length (`src/llama-model.cpp:1203`) and the YaRN ramp is computed against the wrong base context.
4. **Memory.**
   - **512K fits the MI210 only in a lean, dedicated shape:** np 1, no drafter, about 49 GiB [D].
   - **512K does not fit the production shape:** np 4 with DFlash2 at 524,288 cells is about 64 GiB [D].
   - **1M at q8_0 KV does not fit one MI210 in any shape:** the lean shape is about 70 GiB [D].
   - The CPU models fit 1M in host RAM easily, but CPU prefill time is the real cost.
5. **Recommendation: ADAPT.** Rewrite INF-59 around the 27B at factor 2 (524K) on a dedicated np 1 instance. Run one gated needle experiment, about 2.5–3 h of a parked-:8083 GPU window.
   - Never put rope flags on the production :8083. Static YaRN applies to every request, and the unified pool's neighbour decode tax (KVU-19b) would amplify.
   - Defer 1M until the second MI210 arrives (or until q4_0-KV evidence exists).
   - Defer Flash-Next: its *native* 262K has never been exercised (deepest served context is 8,192).

---

## 1. What was found

| # | Item | Date / status | What it proposed | Measurements | Why it stalled / current relevance |
|---|---|---|---|---|---|
| 1 | **`handoffs/active/yarn-context-extension-research.md`** (INF-59, row in `inference-research-index.md:66`) | Created 2026-03-09; QUEUED (LOW). Intake updates 03-24, 04-18 and 05-20; rescope 09-07. | YaRN 256K→1M for the Qwen3.5 and Qwen3-Next-80B ingest role. It lists the llama.cpp flags and 5 research questions: RULER curve, KV memory, speed, model comparison, GGUF metadata. | **None.** | Gated on "context_extension becomes a concrete workload requirement AND the workload tolerates degraded position-discrimination above 32K". The second clause was added from intake-569#record. `stale-open-audit-2026-07-18.md:217` classifies it as PARKED, trigger not fired. Its model targets are retired. |
| 2 | `handoffs/completed/long-context-eval-datasets.md` | 2026-03-26 → 04-05, READY | Download LongBench v2, RULER, NIAH, ZeroSCROLLS and L-Eval. Next step 2 was "YaRN degradation curve 256K→512K→1M". | Datasets validated. Tulving, BEAM and AA-LCR are also on disk under `/mnt/raid0/llm/data/eval/`. | The YaRN step was never run, and its eval model (Qwen2.5-7B) is stale. **Reusable:** `long_context_adapters.RULERAdapter` generates noise haystacks of arbitrary length, but it puts one needle per prompt, so every needle costs a full prefill. |
| 3 | `handoffs/completed/kv-cache-quantization.md` | 2026-03-24 → 03-28, COMPLETED | Motivated by "1M tokens (YaRN-extended Qwen3.5)". Hadamard q4_0 shipped; TurboQuant, PolarQuant and QJL were ABANDONED. Risk R10 (:1271): "use q8_0, not q4_0, at 1M". | KV quality at 32K, on a different model | The motivation is historical. The R10 advice still stands. |
| 4 | `research/deep-dives/2026-05-20-rope-long-context-bounds.md` (intake-569#record) | 2026-05-20 | Theory: raising the RoPE base trades position fidelity for token fidelity. Proposed A1, a 4-element indexing sanity check per model (~100 min). | None; A1 was never run | Posture only. Its "32K hard line" is contradicted in practice by production serving 262K per request. It analyses full-RoPE heads; our models rotate only 64 of 256 dims (see §3). |
| 5 | `wiki/context-extension.md` | Compiled 2026-04-18, incrementally updated 05-20 | Layered plan: YaRN for 256K→1M, plus KV compression, plus MemAgent-style chunking. | none | Stale facts: "384GB RAM budget" (the host budget is about 1,069 GiB), "Hadamard q4_0 deployed" (:8083 runs q8_0), the Qwen3.5 and Qwen3-Next targets, and the TurboQuant path. **Needs recompilation after INF-59 is rewritten.** |
| 6 | `handoffs/completed/qwen35-frontdoor-benchmark.md:432` | 2026-03-09 | `ingest_long_context` = Qwen3-Next-80B ("RULER 91.8% avg to 1M"). | Vendor claim only | The role is now an alias on :8083, served by the 27B. |
| 7 | `design-backlog-triage-2026-07-23.md` C25, D5, D9; `multiscreen-attention-evaluation.md` (MoBA 1M) | Triage, July 2026 | Adjacent non-RoPE long-context items: MoBA, log-linear GDN at 1M, TBQ KV. | — | Not RoPE scaling. Listed for completeness. |
| 8 | `handoffs/active/deepseek-v41-flash-evaluation.md:217`; `handoffs/completed/deepseek-v41-…-through-2026-09-26.md` | Sept 2026 | The DS41 port had to *force* YaRN, because the GGUF lacks `rope_scaling.rope_type` and the generic reader defaulted to linear (`wiki/local-inference.md:25`). | Port decodes correctly | **Useful precedent.** Our tree's YaRN path is exercised in-house, and the "metadata silently defaults" failure mode has bitten before. |
| 9 | `progress/2026-03/2026-03-07.md:234` | 2026-03-07 | The stub created item 1. | — | — |

**Intake entries:**
- intake-032#record: the YaRN paper, marked `already_integrated`.
- intake-152#record and intake-387#record: Qwen3.5/3.6 serving claims, "262K native, YaRN to 1M+".
- intake-569#record: the RoPE bounds paper.
- intake-808#record: the Hy3 community "1M" RoPE extension, which degrades to about 70% on needle tests. This is a cautionary datapoint.
- intake-1347#record: a pattern, "after any rope_scaling change retrieve a needle *through the serving path* above `original_max_position_embeddings`; move aside token-prefix-keyed caches built under the old geometry".
- intake-1849#record: the upstream issue behind KVU-19.
- Adjacent: intake-408#record and intake-409#record (Tulving, EM-LLM), and intake-191#record, intake-192#record and intake-193#record (TurboQuant family).

No intake or handoff covers LongRoPE, NTK-by-parts or dynamic NTK, or DCA.

---

## 2. Technique support in llama.cpp v10 (`ffc1bac82`; champion `90c12df42` is identical on these paths)

| Technique | v10 support [M] | Applies to our models? | Verdict |
|---|---|---|---|
| **YaRN (static)** | Flags: `--rope-scaling {none,linear,yarn}`, `--rope-scale N` (sets `freq_scale = 1/N`), `--yarn-orig-ctx`, `--yarn-ext-factor`, `--yarn-attn-factor`, `--yarn-beta-slow`, `--yarn-beta-fast` (`common/arg.cpp:2142-2201`). Context setup is at `src/llama-context.cpp:130-136` and `:181-231`: ext_factor defaults to 1 under yarn, and mscale `0.1·ln(f)+1` is applied in-kernel and cancelled in `attn_factor`. Graph paths: `qwen35.cpp:299-307`, `qwen35moe.cpp:323-332`, `qwen4exp.cpp:525-530` and the indexer at `:760-771` all pass `n_ctx_orig, freq_scale, ext_factor, attn_factor, beta_*` to `ggml_rope_multi`. Kernels: rope type IMROPE for all three archs (`llama-model.cpp:2718-2721`); the HIP rope kernel's imrope path calls `rope_yarn` with the correction dims (`ggml-cuda/rope.cu:246-302`). | **Yes**, all three Qwen LLMs. Vendor-documented (§3). | **The only viable technique.** |
| Linear position interpolation | `--rope-scaling linear` plus `--rope-scale`/`--rope-freq-scale` | Mechanically yes | Not vendor-recommended, and it hurts more than YaRN without fine-tuning. **No.** |
| NTK-aware base raising | Static only, via `--rope-freq-base`. Neither dynamic NTK nor dynamic YaRN exists: scaling is fixed per context. | θ is already 1e7 | This is exactly the move intake-569#record bounds, and YaRN ("NTK-by-parts") supersedes it. **No.** |
| LongRoPE | The enum `LLAMA_ROPE_SCALING_TYPE_LONGROPE` exists (`include/llama.h:171`), but it needs trained per-model `rope_long`/`rope_short` factor tensors (`llama-model.cpp:2077-2088`; Phi-3 style). | No production GGUF ships them | **N/A.** |
| DCA (Dual Chunk Attention, Qwen2.5-1M) | Not implemented: zero hits in `src/`, `common/` and `tools/server/`. | — | **N/A** without a port. |
| "Context boost to 1M" | — | The hosted Qwen Cloud "1M by default" (model cards, line 16/19) is a service feature. For open weights the route is YaRN at factor 4. | Not a separate technique. |

**Two v10 traps that the old handoff's flag recipe walks straight into:**

- **Server clamp [M].** `server-context.cpp:1316-1322` reads:

  ```
  if (n_ctx_slot > n_ctx_train) { …capping…; n_ctx_slot = n_ctx_train; }
  ```

  `n_ctx_train` is the raw GGUF `context_length` (`llama-model.cpp:1099`, `:2498-2500`), and nothing scales it by `--rope-scale`. So the old recipe in INF-59 (`-c 1048576 --rope-scaling yarn --rope-scale 4 --yarn-orig-ctx 262144`) **still caps every slot at 262,144**.

  The fix is `--override-kv qwen35.context_length=int:524288`. Overrides are honoured by every `get_key` (`llama-model-loader.cpp:420`). With the override, `n_ctx_orig_yarn` defaults to the *overridden* value (`llama-model.cpp:1203-1204`). `--yarn-orig-ctx 262144`, or a `qwen35.rope.scaling.original_context_length` override, is therefore required, not optional.
- **Flash-Next fused decode ignores YaRN [M].** `qwen4exp-fused.cpp:1709-1717` hardcodes `freq_scale=1, ext_factor=0, n_ctx_orig=0` ("filled by the caller… defaults here"). The fused path runs only when `GGML_FUSED_DECODE_OFF` is unset and no MTP draft is attached (`llama-context.cpp:1351-1353`).
  - Production is safe: the recipe exports `GGML_FUSED_DECODE_OFF=1` (`epyc-inference-research/scripts/lib/qwen38_flash_next_recipe.py:530`), and :8074 runs draft-mtp.
  - However, any YaRN experiment on Flash-Next that drops either condition would prefill with YaRN and decode without it, silently.
  - This is latent at native length as well: `n_ctx_orig=0` is only harmless while ext_factor is 0.

---

## 3. Per-model applicability

GGUF headers [M]: no production GGUF carries any `rope.scaling.*` key. All three Qwen LLMs have `rope.freq_base = 1e7`, `rope.dimension_count = 64` against a head dim of 256 (partial rotary 0.25), `rope.dimension_sections = [11,11,10,0]` (interleaved MRoPE), `context_length = 262144` and `full_attention_interval = 4`. The HF `config.json` files on disk show `rope_type: "default"`.

| Model (port, device) | Arch facts [M] | Vendor YaRN [M] | Applies? | KV per token | 512K / 1M memory | Verdict |
|---|---|---|---|---|---|---|
| **Qwen3.8-27B Q8_0** (:8083, MI210; live `-c 393216`, np 4 unified, slot clamp 262,144, DFlash2 n-max 7) | `qwen35`, 65 blocks = 64 + 1 nextn; **16 attention layers**, 48 GDN; 4 kv-heads × 256 | Card `turboderp/Qwen3.8-27B-exl3-4.00bpw/README.md:53, 514-575`: "262,144 natively and extensible up to 1,000,000", yarn factor 4.0, orig 262144; "static YaRN… potentially impacting performance on shorter texts"; "if typical length is 524,288… set factor 2.0" | **Yes** | 34,816 B q8_0 KV; about 42 KiB marginal including the KQ mask (4 KiB at ub 2048) and FA f16 scratch | **Production shape:** 58.88 GiB peak at 393,216 [M, KVU-16b] + (c − 393,216) × 42 KiB → **524K ≈ 64.1 GiB ✗**, **1M ≈ 85 GiB ✗**. **Lean np 1, no drafter** [D] (fixed ≈ 27.9 GiB = weights 25.36 + GDN state 0.15 + compute 1.06 + runtime 1.28): **524K ≈ 48.9 GiB ✓**, 786K ≈ 59.4 GiB (marginal), **1M ≈ 69.9 GiB ✗**. 1M fits only with q4_0 KV (26 KiB/token → about 54 GiB, quality unmeasured) or with 2 GPUs. | **Primary candidate**: factor 2 → 524,288, dedicated instance. |
| DFlash2 drafter (`Qwen3.8-27B-DFlash2-Q8_0`) | `dflash`, 5 layers, SWA 2048, θ = 1e7, ctx 262144 | none | Inherits the base rope params through `common_base_params_to_speculative` (`server-context.cpp:1238`), so YaRN would perturb the drafter's attention. Acceptance under YaRN is unmeasured. | ~200 MiB, flat | — | Run **no-draft** in the experiment, which also saves about 4.3 GiB. |
| **Qwen3.6-35B-A3B MTP Q8** (:8070/:8080/:8180, CPU; `-c 262144`, 4 slots → 64K per slot) | `qwen35moe`, 41 blocks; **10 attention layers**, 2 kv-heads; 256 experts | intake-387#record ("262K native, extensible to 1M+ with YaRN"); no local card to check the factor | Yes, mechanically | 10,880 B q8_0 | 1M ≈ 10.1 GiB per sequence on about 1 TiB of host: trivial | **No workload.** It is the front door with 64K slots, and static YaRN would tax every short request. Do not pursue. |
| **Qwen3.8-Flash-Next UD-IQ4_XS** (:8074, CPU, all four regions, MTP, f16 KV forced) | `qwen4exp`, 48 blocks; **12 Qwen-Sparse-Attention layers** + 36 GDN; 512 experts; indexer of 4 heads × 128 dims, compress ratio 4, budget 2048 | Card `turboderp/Qwen3.8-Flash-Next-exl3-3.05bpw/README.md:71, 598-642`: same JSON, factor 4.0 | Yes, on the graph path (the indexer's pooled block keys are roped at `blk_pos` with the same params). **The fused-decode trap applies (§2).** | 24 KiB f16 KV + ~9 KiB MTP head + ~0.75 KiB indexer cache [D, unmeasured] | 1M ≈ 33 GiB + 87 GiB weights ≈ 120 GiB: fits | **Defer.** Its *native* 262K has never been exercised: the deepest context served is 8,192 and the deepest benchmarked is d4096 (registry :1880-1882). Validate native long context first. A run here also takes all four CPU regions (AutoKernel windows). |
| BGE-M3 / bge-large-en-v1.5 (embedders) | `bert`, learned absolute positions, ctx 8192 / 512 | — | **No RoPE: N/A** | — | — | N/A |

### Is RoPE scaling on a quarter of the layers meaningful for these hybrids? Yes, with one unaddressed risk

- **RoPE is the only positional signal in these models.** The GDN layers carry no position embedding; their causal conv (kernel 4) is local and relative. Scaling the 16 (or 10, or 12) attention layers therefore scales the model's whole explicit position mechanism. Nothing else needs scaling.
- **Only 64 of 256 dims per head rotate.** The other 192 are position-free, so these attention layers are part-NoPE and less exposed than the full-RoPE heads that intake-569#record analyses.
- **Within the 64 rotary dims, YaRN changes only the low-frequency tail.** [D] from `ggml_rope_yarn_corr_dims` (`ggml.c:4466-4476`) with n_dims 64, θ 1e7 and orig 262,144:
  - pairs 0–13 are kept as they are (extrapolation);
  - pairs 14–22 are ramped;
  - pairs about 23–31 are interpolated by the factor.

  Those top pairs are exactly the ones whose wavelength (2π·θ^(i/32)) exceeds 262,144 tokens, that is, the dims whose angles at positions above 262K were never seen in training. The mechanism is well aimed.
- **Unaddressed risk: the recurrent state's own length generalisation.** GDN layers have fixed-size state and learned decay, so there is no positional out-of-distribution problem, but there is a capacity and forgetting question past 262K. YaRN does nothing for it. The vendor's 1M claim covers the whole model under YaRN, which is good evidence but not ours. Only a ground-truth test settles it.
- **Static YaRN applies to every request on the process.** llama.cpp has no dynamic mode, and the vendor itself warns about short-text degradation. A YaRN 27B therefore cannot be the shared production :8083 unless a short-context paired gate shows no regression. Plan for a *mode*, not an always-on flag.

---

## 4. Interaction with the unified-KV decode tax (KVU-18 / KVU-19)

**What has been measured:**
- KVU-16b at the 393,216 pool, with 4 slots decoding at about 308K resident: **sum 0.52 tok/s**, KFD peak 58.879 GiB (`tmp/gpu-block-27b-20261003/results/kvu16b/*/report.md`).
- KVU-18: no-draft decode **−32.6% with one parked neighbour of about 99K, −59.5% with three** (`kv-unified-stack-rollout.md` on origin/main, :442).
- KVU-19a, the masked-block skip, fixes *single-sequence* decode and verify behind idle neighbours (P3-mini 82 → 169 steps/s). It does **not** fix concurrent decodes, because a batched tile's live set is the union of all sequences. That gap is **KVU-19b, still open**.

**Consequences:**
- **On the production unified pool, contexts above 262K are both impossible and harmful.** They are impossible because the slot clamp and the 393K pool forbid them. If the pool were enlarged to admit them, every co-resident slot's decode would scan the long sequence's cells, which multiplies exactly the measured collapse. **Gate: no long-context YaRN in a unified multi-slot pool until KVU-19b lands *and* the KVU-18 cells are re-measured.**
- **A dedicated np 1 instance sidesteps KVU-19 entirely**, because it has no neighbours. Its own decode at 500K is inherently memory-bound. [D]: about 17.4 GB of KV plus about 27 GB of weights read per step, or roughly 25 tok/s as an upper bound at about 1.2 TB/s effective. That is fine for needle answers.
- **Stale-geometry caches** (pattern from intake-1347#record): `--cache-ram`, the `--slot-save-path` files and `tmp/kv_prefix_history.local_8083.json` are keyed by token prefix, but their KV was computed under native RoPE. A YaRN instance must use its own empty cache and a scratch slot path. It must never restore production slots.

---

## 5. Recommendation: ADAPT (neither a revival as written, nor an archive)

**Why not archive.**
- The operator wants long context.
- The vendor documents YaRN for every production LLM.
- v10 implements it correctly for IMROPE partial-rotary heads.
- The memory fits for 512K on the 27B.
- The test instruments already exist: the coherence_gate tier 1 `needle` grader, the Q38-T7 cached-prefix needle harness, and the RULER noise haystacks.

**Why not revive as written.**
- Every model target is retired.
- The flag recipe is defeated by the server clamp.
- The memory framing (CPU RAM, TurboQuant) is wrong for a GPU-served model.
- The "32K hard line" contradicts current practice.

**The adapted scope** (for the owning session to apply to INF-59; this subagent only prepares it):

1. **Target: Qwen3.8-27B at YaRN factor 2 (524,288), as a dedicated long-context *mode*.**
   - Shape: np 1, no drafter, q8_0 KV, separate caches.
   - Never as flags on the production :8083.
2. **1M is deferred to the second MI210** (expected around October 2026), where q8_0 at 1M fits split across two cards. Alternatively, it waits for separate evidence that q4_0 KV is safe on this model. The `kv-cache-quantization.md` R10 advice ("q8_0 at 1M") still holds.
3. **Flash-Next is deferred behind native-262K validation.** Native validation is the more valuable experiment for that model regardless of YaRN. Any YaRN arm on it must keep `GGML_FUSED_DECODE_OFF=1`.
4. **The 35B front door is dropped** (no workload). **The embedders are N/A.**
5. **Rewrite the gate.**
   - Replace the "tolerates position loss above 32K" clause with the pre-registered E1 pass criteria below.
   - Record the demand evidence: :8083's observed p99 prompt is 144,846 tokens (`DECISION.md` §3c), so organic demand today sits inside the native 262K.
   - The decision that only the operator can make: **whether per-request context above 262K is wanted enough to spend one parked-:8083 GPU window of about 3 h.**
   - Everything else, including E0 and the rewrite, needs no decision.
6. **Recompile `wiki/context-extension.md` afterwards**, replacing the stale facts listed in §1 row 5.

**Draft row text** (prepare-only; the owning session applies it and runs `index_state.py --check`):
`| INF-59 | yarn context extension research | [yarn-context-extension-research.md](yarn-context-extension-research.md) | ADAPT: rewrite to Qwen3.8-27B YaRN f2 (524K) dedicated np1 MI210 mode; E0 now, E1 needs one ~3 h parked-:8083 window | KVU-19b (prod pool only) |`

---

## 6. Minimal experiment plan

### E0: zero compute (agent time only; do now)

- **Fork the Q38-T7 needle logic** (`tmp/gpu-block-27b-20261003/q38_t7.py:114-122, 236-279`) into a long-context runner. Write truth rows in coherence_gate form, `{"grader":"needle","expected":[…]}`.
  - **Haystack: neutral filler** (RULER-style noise, or essays with unique sentence ids). The Q38-T7 needle at 80K came back **WRONG because the model abstained**, calling the planted vault-code fact "injected instructions" inside an AutoKernel haystack. That is a harness confound and must not recur.
  - **One prefill per (arm, length), several needles per prefill.** Plant 5 distinct key→value facts at depths of 10/30/50/70/90%. Then ask 5 questions as short continuations on the cached prefix, which works with np 1 and `cache_prompt`. Prefill dominates the cost, so this cuts GPU time about 5×.
- **Write the launch lines.** The base is the production env and `LD_LIBRARY_PATH` from the runbook (`/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin`), on a scratch port such as 18083:
  - **A0 (native):** `-np 1 -c 262144 -ctk q8_0 -ctv q8_0 -ub 2048 --flash-attn on --no-mmap -ngl all --cache-ram 0`, with no `-md`.
  - **A1 (YaRN f2):** A0 plus `-c 524288 --rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 262144 --override-kv qwen35.context_length=int:524288`.
  - **A2 (negative control, optional):** like A1 but without the rope flags, which gives raw extrapolation. It proves the test discriminates.
- **Proof lines to require from the log at bring-up:**
  - `n_ctx_orig_yarn = 262144`
  - `freq_scale = 0.5`
  - `rope scaling = yarn`
  - `n_ctx_slot = 524288`, with no "capping" warning
  - KFD at load at or below about 50 GiB
- **Wire the write side for the belief kernel:** a VB source row plus an adapter task. Per CLAUDE.md, the owning session surfaces this.

### E1: GPU, requires :8083 parked (the operator or coordinator grants the window)

All prefill times are [D] from the measured 27B MI210 prefill (Q38-T7 phase B: 554 t/s at 16K, 439 t/s at 80K). The fit is `t(L) ≈ 1.7 ms·L + 1.5e-5 ms·L²/2`, about ±30%. Running without the drafter is slightly faster.

| Cell | Arms | Prefill per arm [D] | Purpose |
|---|---|---|---|
| Short paired set: about 60 `question_pool` items under 4K (gsm8k, mmlu_pro, gpqa) | A0 vs A1 | about 10 min | Does static YaRN f2 regress short-context quality? Uses the coherence_gate tier 0/1 **paired** verdict. |
| 128K haystack, 5 needles | A0 vs A1 | about 6 min | Paired, within native |
| 240K haystack, 5 needles | A0 vs A1 | about 15 min | Paired, near the native edge. **A0 alone is also the first-ever ground truth near 262K for this model.** |
| 400K haystack, 5 needles | A1 (+ A2) | about 31 min each | Beyond native |
| 500K haystack, 5 needles | A1 | about 47 min | Beyond native, near the f2 ceiling |
| 3 launches of about 3 min each (27 GB `--no-mmap`) | — | about 10 min | — |

**Total:** about 2.5 h, or about 3 h with the A2 control. VRAM peak is about 49 GiB [D], with 13 GiB of margin under the 62 GiB gate. No CPU regions are needed.

**Pre-registered gate.** Greedy decoding, thinking off, real token ids for coherence_gate.

1. **Short context:** a coherence_gate **PASS** for A1 against anchor A0 (0 REGRESSION). If this fails, YaRN may only ever be a separate mode, which is already the plan, so the result is recorded but the run continues.
2. **Within native (128K and 240K):** A1 correct needles ≥ A0 correct − 1 (out of 10, paired), and degeneracy.v2 is clean.
3. **Beyond native (400K and 500K):** A1 at least 4/5 needles at each length. If A2 was run, A2 must score clearly worse; otherwise the needle test is not discriminating.
4. **Memory:** the KFD peak stays at or below 55 GiB.

**Outcomes:**
- **Pass:** prepare a stack-change package for an on-demand "long-context mode" profile, swapped in for :8083 during long-document work.
  - The package must say who waits during the swap.
  - It must change the orchestrator per-request cap in `src/backends/context_limits.py`, which currently does `min(n_ctx, n_ctx_train)` against `ctx_max: 262144`.
  - It must state the DFlash2 acceptance question. That needs its own measurement before the drafter can be kept in the mode.
- **Fail:** archive INF-59 with the evidence and keep 262K as the ceiling.
- **Pass at 512K:** 1M becomes a second-MI210 item, not something to do on this card.

### Not recommended now

- The 1M run on CPU: memory is fine, but prefill is about 2.8 h per prompt even on the GPU model [D], longer on CPU, and the CPU prefill is unmeasured.
- Any rope flag on production :8083, :8070 or :8074.
- intake-569's A1 indexing check as a substitute. It measures RoPE position indexing at 4–32K, not whether retrieval works past 262K.

---

## 7. Corrections to the brief

- The slot clamp is **unconditional**. Rope flags do not lift it; see §2.
- "Qwen3.8-Flash-Next n_ctx_train": confirmed at **262,144** [M].
  - Its KV is f16 and forced (registry :1846-1852).
  - Its architecture is QSA sparse attention plus GDN, not GDN plus dense attention.
  - It has never served beyond 8,192 tokens.
- The 58.9 GiB peak: confirmed [M] as the KVU-16b KFD peak of 58.879 GiB, at a 393,216 pool with about 310K resident. The Q38-T7 run at the same shape peaked at 59.77 GiB.
- "~42 KiB/token marginal": consistent [D]. It is 34,816 B KV + 4,096 B mask (`DECISION.md` §1.2) + about 4,096 B for FA's q8_0→f16 scratch. One layer's K+V at f16 is 4 × 256 × 2 × 2 B.
