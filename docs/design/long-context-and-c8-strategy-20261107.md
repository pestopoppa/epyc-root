# Long-context (YaRN ≥256k) and C8 package strategy — 2026-11-07

> **Durable copy** of the INF-22 strategy memo (`/mnt/raid0/llm/tmp/inf22-strategy-memo-20261107/MEMO.md`, scratch).
> Body below is the memo verbatim; scratch paths it cites (MEM, E1R, GDN) are evidence locations at
> time of writing and may be reclaimed. [no-belief: derived design memo; no new measurement]
>
> **Operator decisions taken on this memo (2026-11-07, applied in `a33e52917` / `fc89efd16`):**
> - **Park all ≥256k YaRN work** (LSA-YARN-512K option A, YARN-CPU-512k, YARN-1M, YARN-DCA*, YARN-E2,
>   JETLONG-*) until the C8 long-context attention-decode fix lands; keep YARN-NATIVE-WINDOW-GATE,
>   native-window inertness, KSHIFT-FIX-MODEL-TEST, YARN-AGG-1 spec, YARN-E1-PROOF.
> - **C8 package includes GDN now** (overriding the memo's "defer GDN to C9"): C8-1 H17 profile →
>   attention fix, C8-2 H16 at M=36, C8-3 zero-split census, C8-6 GDN chunked core, plus the prefill pair.
> - **Framing: HBM saturation is the goal.** Decode attention reads KV at ~160 GB/s (~10% of MI210
>   HBM); the target is to saturate HBM bandwidth, not to save VRAM.
>
> **Headline measured numbers** (27B Q8_0, q8_0 KV, MI210, no draft): decode 17.4 / 12.4 / ~7 tok/s at
> 128k / 240k / 500k (fit 29.7 + 0.217·ctx_k ms/token); usable VRAM ceiling ~63.8 GiB (62 GiB KFD
> operating gate); DFlash2 drafter on GPU at 512k ≈ 52.55 GiB load, ~54 GiB projected peak — fits;
> moving KV to host is strictly worse (attention moves to slower memory).

---

# INF-22 strategy memo: YaRN 512k, long-context decode, YDNLC uptake, C8 package, StreamingLLM (2026-11-07)

**For:** main-inf22. **Method:** read-only. Evidence comes from logs, handoffs and source. The only computation is CPU arithmetic (`calc/decode_vs_ctx.py` and the inline fits below). No GPU was used, no process was touched, no handoff was edited.
**Belief tag:** [no-belief: derived from committed and scratch evidence; no new measurement]

Abbreviations:
- LCP = `handoffs/active/long-context-program.md` @ origin/main
- KVP = `handoffs/active/kv-cache-program.md` @ origin/main
- MEM = `/mnt/raid0/llm/tmp/yarn-e1-mem-c7-20261106/out`
- E1R = `/mnt/raid0/llm/tmp/yarn-e1-20261004/results`
- GDN = `/mnt/raid0/llm/tmp/gdn-share-mi210-20261106/out`
- SEEDS = epyc-inference-research origin/main `scripts/kernel_rnd/autokernel/loop/seeds/hypotheses/07-mi210-asm-port-open-seeds.md` (@ `272b39a1a`)

## TL;DR

1. **The VRAM budget was a judgement margin, not a hardware limit.**
   - 55 GiB is a pre-registered cell in YaRN-E1 (LCP:91, C4). 52 GiB is 55 minus 3 GiB of slack (PLAN E3).
   - The card's practical top is about 63.8–63.9 GiB: processes reached that before OOM (LCP:106-108, `wiki/inference-serving.md:202`). The operating gate actually in use is **62 GiB KFD** (KVP:2465).
   - DFlash2 on GPU at 524k loads at **52.55 GiB**. Adding E4's in-request growth (+1.46 GiB) gives an estimated peak of about **54 GiB**, which leaves about 8 GiB under the 62 GiB gate.
   - **Keep the drafter on GPU.** Moving KV to host instead is strictly worse on this stack (see Q1).
2. **Decode at long context is measured, and it is slow.**
   - No-draft ms/token ≈ **29.7 + 0.217 × ctx_k**:
     - 128k: 57.5 ms (17.4 tok/s)
     - 240k: 80.8 ms (12.4 tok/s)
     - 400k: 116–122 ms (8.2–8.7 tok/s)
     - 499k: 137–145 ms (6.9–7.3 tok/s)
   - The context-dependent term reads KV at only **≈160 GB/s, about 10% of HBM**.
   - Cold prefill is 5.1 min at 128k, 17 min at 250k and **63 min at 499k**.
   - Verdict:
     - 256k is marginal: about 85 s per 1k-token answer without a draft, an estimated 50 s with DFlash2.
     - 512k is **not interactively usable**: about 140 s per 1k tokens, 9–25 min for a thinking-length answer, plus an hour of prefill.
   - The fix is a kernel problem (attention-decode efficiency), not a memory problem.
3. **YDNLC paper (intake-2628).** Short context managed by a harness (compaction plus file-based selective reads) matches long context for frontier models. Open-weight models are the counter-result.
   - We filed compaction and governance tasks, but no REPL/retrieval task. Nothing filed re-scopes YaRN.
   - **Recommendation:** deprioritize ≥256k YaRN work, LSA-YARN-512K included, until the decode-attention fix lands. LSA-YARN-512K needs an operator ruling (it carries one from 2026-11-06), and its expected gain is about 1.03x at 512k.
   - Prioritize instead:
     - TOC-CMP-1..5 and UFH-21
     - REPL-EMB-3.1 / REPL-EMB-4.1, the bounded-read surface
     - YARN-NATIVE-WINDOW-GATE, YaRN native-window inertness and KSHIFT-FIX-MODEL-TEST
4. **GDN core is a prefill lever, not a decode lever.**
   - For 27B, a 2x/3x faster GDN kernel gives:
     - prefill +8.6% / +11.8%
     - no-draft decode +0.7% / +0.9%
     - DFlash2 verify step +1.7% / +2.3% at np1 and +3.4% / +4.5% at np4
   - For A3B prefill it gives +11.9% / +16.5%.
   - **The ranked C8 package puts long-context attention efficiency and the np4 verify GEMM first** (see Q4).
5. **streaming-llm-baseline: keep it closed.**
   - A hybrid carve-out is feasible: evict attention-only KV and leave the GDN state untouched, about 2–4 days plus the K-shift fixes.
   - But the payoff for our workloads is low. Eviction defeats retrieval by construction, the only floor evidence is a quality fail on a dense 1.7B model, and a harness achieves the bounded-context speed with quality we control.
   - Reopen triggers are listed in Q5.

---

## Q1. YaRN 512k VRAM: the real ceiling, the 55/52 origin, and KV-to-host options

### Measured (C7 `c420b9d1a`, Qwen3.8-27B Q8_0, q8_0 KV, -c 524288, np1; MEM/RESULT.json)

| Config | Load KFD | Notes |
|---|---|---|
| ub 2048 | 48,403 MiB = **47.27 GiB** | post-request 47.59 GiB |
| ub 1024 | 47,219 MiB = 46.11 GiB | −1.16 GiB vs ub 2048 |
| ub 512 | 46,627 MiB = 45.54 GiB | −1.73 GiB |
| E2: 60 short requests, graphs on | peak 47.62 GiB, slope **0.0 MiB/req** | the GPU-LEAK-1 fix holds on C7 |
| E3: DFlash2 draft on GPU | **52.55 GiB** (+5.28 GiB vs E1) | the buffer census is empty, so the +5.28 is unattributed. Draft weights are 1.9 GiB; the other ~3.4 GiB is draft compute and taps, unmeasured |
| E3: draft on CPU (`-ngld 0 -devd none`) | **crashed, rc=−6** | `dflash requires ctx_other to be set` → `ggml_abort` (MEM/logs/e3-draft-cpu-*.log:8,239). Draft-on-CPU is broken on C7 independently of memory |
| E4: 498,729-token needle, ub 2048, no draft | in-request peak **48,730 MiB = 47.59 GiB** over 3,799 samples; 3,802 s; hit | +1.46 GiB from load to peak |

Static budget at 524k (PLAN §1):
- weights 25.36 GiB
- KV 17.0 GiB (16 layers × 524,288 × 1024 × 2 × 1.0625 B)
- recurrent state 0.15 GiB
- compute buffer 4.31 GiB at ub 2048
- runtime about 0.5 GiB

### Why 55, and what the real ceiling is

- **55 is a gate, not a physical limit.** It is the pre-registered YaRN-E1 cell C4, "KFD peak ≤ 55 GiB" (LCP:91), reused at `wiki/context-extension.md:403` and `handoffs/completed/mi210-serving-program.md:377-378`. I found no derivation; it leaves about 9 GiB of margin on a 64 GiB card. The **52** in E3 is that 55 minus 3 GiB of slack (PLAN §3 E3).
- **Hardware top: about 63.8–63.9 GiB.** E1 A1 reached 63.9 GiB (LCP:106-108). The GPU-LEAK-1 run climbed from 36.8 to 63.8 GiB before OOM (`wiki/inference-serving.md:202`). No `hipMemGetInfo` total/free and no max-single-allocation probe is recorded anywhere, so the last ~0.5 GiB (HIP context and fragmentation) is not quantified.
- **The gates actually in use are higher than 55:**
  - :8083 capacity gate 62 GiB KFD (KVP:2465, 2530, 2549)
  - the gate library recycles at 60 GiB (`wiki/context-extension.md:48`)
  - the KPF-18 supervisor aborts at 60 GiB (`docs/reports/kv-cache/kpf18-g3-supervisor-integrated-20261105/supervisor.py:69`)
- **Recommendation: budget YaRN-512k against 60 GiB** (the recycle line), with 62 as the hard gate.
  - DFlash2 on GPU projects to 52.55 + 1.46 ≈ **54.0 GiB** peak at 500k, which is ≥6 GiB under 60. The draft's own in-request growth is unmeasured, so that number is an estimate.
  - One confirmation run (an E4 rerun with `-md`) settles it. If the window is too expensive, a 128k needle with the draft is enough to measure the draft's in-request delta and extrapolate.
  - **E3's "FAIL" is a failure against an arbitrary 52, not against the card.**

### Putting KV/context on host instead of the drafter

Source is the champion tree's offload logic: `src/llama-kv-cache.cpp:205-219`, `common/arg.cpp:2223-2226`, `common/common.cpp:1617`. These line numbers were read on the `0db32c06e` tree; the offload logic is unchanged through C7r as far as I checked.

| Option | What it does | Feasibility on C7r | Cost at 512k |
|---|---|---|---|
| `-nkvo` / `--no-kv-offload` | **All** KV goes to host, and the KQV ops run on CPU | works, all-or-nothing | Saves 17 GiB of VRAM. But decode attention then reads 17.8 GB/token from DDR5: about 120–170 ms/token at `-t 8`, maybe about 60 ms at a full NUMA node, while contending with the CPU roles. Prefill attention moves from 14 TFLOP/s on GPU to CPU, so the 63 min prefill becomes hours. **Worse than the current state.** |
| Partial `-ngl` | KV follows its layer's device (`dev_layer(il)`) | works, but moves whole layers' weights as well | Each moved layer costs weight streaming over PCIe or CPU compute. Not a KV lever. |
| `-ot` / `--override-tensor` | weights only, never KV | no KV effect | n/a |
| Per-layer KV-to-host mask (new flag) | KV of selected attention layers on host, weights stay on GPU | **code change** (a per-layer `offload_kqv`); about 2–3 days | Either CPU attention for those layers (as `-nkvo`, per layer) or streaming the KV over PCIe at 28.89 GB/s (KVP:1832; 55x slower than HBM). Streaming is about 37 ms per layer per token at 512k, so it is hopeless. |
| `--kv-unified` | one shared KV buffer across sequences | works | **No saving at np1**; it only helps at np>1 |
| KVU-16 series | :8083 pool sizing and allocator work (393k unified pool, 262k per-request cap, the `656c9a66b` allocator fix, budgeter), KVP:2455-2812 | done or open; not host KV | KVU-16f (`-b/-ub 512`, −3.1 GiB) is the only VRAM lever there; it is already reflected in the ub table above |
| HSF-5 host KV mirror | write-through host copy for **parking idle np4 slots** (`docs/design/hsf-5-host-kv-mirror-costing-20261024.md:70-76`) | costed on paper | This is the right use of host RAM: park idle sequences, not active attention |
| q4_0 KV on the 16 global layers | halves KV | hd256 FA support to be checked | saves about 8 GiB at 512k; quality risk at 512k (R10 advised q8_0). Reserve it for 1M. |

**Conclusion.** The drafter costs 5.3 GiB and fits under the real ceiling. Host-KV saves VRAM the stack does not need, and it slows the dominant long-context cost (attention) by moving it to a slower memory. The cheap VRAM levers, if any are ever needed, are ub 1024 (−1.2 GiB) and then q4_0 KV.

---

## Q2. Decode speed at long context (measured, then extrapolated)

### Measured, no draft, np1, Qwen3.8-27B Q8_0, q8_0 KV

`calc/decode_vs_ctx.py` over E1R/A0.server.log and E1R/A1.server.log (v10-era FA path, 2026-10-04) and MEM/logs/e4-500k-*.log (C7):

| context | ms/token (n requests) | tok/s | source |
|---|---|---|---|
| short (≤10k) | 32.2–32.7 (median, n=51) / 31.3–32.4 on C7 | 31 | E1R A0/A1; E4 post-needle short requests (MEM/logs/e4:531-716) |
| 128,1xx | 57.2–59.4 (n=5, 8–10 tokens); 63–64 at 57–70 tokens | 17.4 (15.7) | A0 and A1 |
| 239,5xx | 80.5–81.1 (n=5); 90.1 at 73–81 tokens | 12.4 (11.1) | A0 and A1 |
| 399,47x | 115.3–121.8 (n=5); 128.8 at 80 tokens | 8.2–8.7 (7.8) | A1 |
| 498,96x | 134.0–141.6 (n=5); 153.6 at 94 tokens | 7.1–7.5 (6.5) | A1 |
| 498,729 | **145.1** (9 tokens) | **6.89** | **E4, C7 `c420b9d1a`** (MEM/logs/e4-500k:522) |

- **Fit:** ms/token ≈ **29.7 + 0.217 × ctx_k**. The v10-era path and C7 agree within 5% at 500k, so C7's CK hd256 FA did not change decode.
- The KV read per position is 16 layers × 2 × 1024 × 1.0625 B = **34.8 KB**. The slope therefore implies an **effective 160 GB/s, about 10% of MI210 HBM (1.6 TB/s)**.
- At 80% of HBM (about 1.3 TB/s) the attention term would be:
  - 3.4 ms at 128k, giving about 33 ms total
  - 6.9 ms at 256k, about 37 ms
  - 13.7 ms at 512k, about 43 ms, i.e. **23 tok/s rather than 7**
- Decode n_q=1 is not served by the AK-H10 `gv_fattn_kernel`: `GGML_CUDA_FA_GQA_VERIFY_MIN_NQ` defaults to 2 (`fattn-gqa-verify.cu:51-53` @ `62cb6a6af`). It falls through to the stock FA path, and its split/occupancy at n_kv = 500k is unprofiled.
- The GDN-share `tg@d32768` cell cannot answer this. Its profile includes the depth prefill (rocBLAS Cijk kernels and CK FmhaFwd dominate it; GDN_CORE share is −0.001). It is a measurement artifact.

### Prefill, measured (E4 chunk timings, ub 2048; MEM/logs/e4-500k)

- 2048-token chunk time ≈ 1.06 s + 0.0576 s per 1k of depth. Rates by depth:
  - 871 t/s at 8k
  - 253 t/s at 127k
  - 131 t/s at 256k
  - 69 t/s at 490k
- The attention term runs at about **14 TFLOP/s**, roughly 8% of the f16 MFMA peak.
- Cumulative cold prefill: 128k 307 s · 250k 1,014 s · 400k 2,456 s · 499k **3,800 s**.

### DFlash2 at long context: not measured past 152k

Production-shape probe (np4, `-c 393216 --kv-unified`, n_max 7; `handoffs/active/harness-program.md:2787-2796`):

| context | DFlash2 tok/s | acceptance | no-draft tok/s | ratio |
|---|---|---|---|---|
| ~2k | 41.6 | 0.33 | 29.6 | 1.41 |
| ~16k | 40.4 | 0.35 | 25.8 | |
| ~50k | 36.9 | 0.39 | 21.6 | |
| ~80k | 32.1 | 0.39 | 18.5 | 1.74 |

Agentic traffic ran at 25–30 tok/s at 57–152k (harness-program.md:2781).

**Extrapolation model.** Step time = verify base (v9 kernel time 47.7 ms, GDN RESULT) + attention(ctx) + draft (constant; SWA 2048 drafter). Take τ ≈ 2.2 tokens/step, calibrated from 41.6 tok/s at 2k. Verify uses the GQA-packed kernel, which reads KV once for all 8 queries.

| ctx | no-draft (measured/fit) | DFlash2 est. at current attention efficiency | DFlash2 est. at 4x attention efficiency |
|---|---|---|---|
| 128k | 17.4 tok/s | about 25 tok/s | about 38 |
| 256k | 11.7 | about 20 (range 14–22) | about 33 |
| 512k | 7.1 | **about 13 (range 9–15)** | about 26 |

Uncertainty:
- (a) Acceptance at more than 152k is unknown. It could fall under YaRN.
- (b) The gv kernel's long-context bandwidth is unmeasured; if it is worse than the n_q=1 path, DFlash2 speedup decays toward 1.
- (c) n per cell is 5 requests of 7–11 tokens. Longer answers ran about 10% slower (57–94-token rows).

Overall about ±25% at 256k and about ±35% at 512k for the DFlash2 rows.

### Is it practically usable?

| ctx | 1k-token answer, no draft | 1k with DFlash2 (est.) | 4k-token thinking answer (DFlash2 est.) | cold prefill |
|---|---|---|---|---|
| 128k | 57 s | about 40 s | about 2.7 min | 5.1 min |
| 256k | 85 s | about 50 s | about 3.4 min | 17 min |
| 512k | 141 s | about 77 s | **about 5–7 min** (9.4 min no draft) | **63 min** |

- **256k:** usable only for offline or batch single questions over a cached prefix.
- **512k:** not interactively usable today. One question costs an hour of prefill plus minutes of decode. It is usable only as an ingest-once, ask-a-few job with slot-save.
- Of the two gaps, decode efficiency is the cheaper one to close: about 2–3x at 512k is available on paper from the 10% → ≥40% bandwidth gap. Prefill attention (8% of MFMA peak) is H18's domain.

---

## Q3. YDNLC (intake-2628, arXiv 2611.05306): claim, our uptake, and recommendation

Source: `research/deep-dives/ydnlc-20261106/` (origin/main only; README:3-23, intake-2628 dive:10-43, PLAN:30-80, 767) and commit `ada27e8e7`.

### What the paper claims

- **Long-horizon tasks.** Compaction at the end of the conversation, at budgets of 48K/36K down to 8K/6K, keeps accuracy within −3.7..+5.6 ppts (Opus 4.5) and −3.3..+4.4 (GPT 5.6 Sol) across six benchmarks. At most 5 of 22 configurations lose more than 2 ppts.
- **Long-input tasks.** Keeping documents as files and reading them selectively (grep/sed/a bounded doc-read) matches or beats full input on 6 of 7 benchmarks; LongBench v2 is −0.4.
  - NIAH reaches 100%.
  - RULER goes 62.5 → 95.7 (Opus) and 65.5 → 96.4 (GPT).
  - BABILong gains +24.9 / +23.3.
- **Single-action compaction.** SWE-bench Verified 70.0 → 70.2 and Terminal-Bench 47.2 → 51.8 (Opus), at a median peak context of 7–9K. A six-field execution brief beats a narrative summary.
- **Caveat that matters to us:** open-weight models are the counter-result (Appendix D). Qwen3 Coder Next falls 53.0 → 3.6; Qwen 3.6 27B falls 68.6 → 65.0, and that model is the family of our architect. The cost multipliers (3.6–7x) come from H100/API pricing. On MI210 the gain is mainly capacity (dive:40-43).
- **Siblings** (2629–2640, all dive-verified): compaction harms governance and constraints.
  - 2636: violations go from 0 to 30% after one compaction.
  - 2637: open-weight compactors retain 6.06% of constraints.
  - 2638: 87–100% laundering across five harnesses, including OpenCode.

### What we filed (commit `ada27e8e7`, all `[ ]`)

- TOC-CMP-1..5 (`context-and-token-economy.md:23-27`)
- UFH-21, the OpenCode `/compact` laundering probe (`harness-program.md:2209`)
- REG-ENF-1/2 (`coordination-and-churn-pipeline.md:29-30`)
- DEPTH-ENV-1, a 16k/32k/48k/128k throughput envelope (`cpu-decode-roofline-program.md:105`)

Not filed:
- **No REPL/retrieval box.** The paper's strongest result, file-based bounded reads, survives only as the gated dive probe "A7" (dive:51).
- M1, "cite the short-context result once in the YARN go/no-go", was never applied. LCP has no mention of 2611.05306, intake-2628 or ydnlc. PLAN:60 and 79-80 explicitly kept YaRN un-rescoped.

### Harness + REPL + short context vs native long context, for our workloads

| | Native long context (YaRN 512k) | REPL + bounded reads + compaction (≤32k working set) |
|---|---|---|
| decode | 7 tok/s at 512k, 11.7 at 256k (no draft) | about 27 tok/s no draft, about 40 DFlash2 at ≤32k (Q2 fit; harness table) |
| prefill | 17–63 min cold | seconds per turn, with 90–96% cache hits (harness-program.md:2778) |
| VRAM | 47.6–54 GiB, one slot | fits the :8083 np4 pool |
| retrieval quality | YaRN A1 5/5 needles at 400k/500k (LCP:106); no aggregation arms yet (YARN-AGG-1) | paper: NIAH 100%, RULER +30 ppts for frontier models; **unproven on our 27B**; the open-weight caveat applies |
| main risk | unusable latency; YaRN regressing the native window | compaction loses constraints and governance (2636/2637/2638); open-weight compaction collapse |

For our agentic workloads (architect, coder, ingest) the harness route dominates on speed by 3–5x at matched content. The open question is quality on our model, and TOC-CMP-4's pre-registered A/B is built to decide exactly that. Native long context keeps one niche: whole-document reasoning that cannot be decomposed into reads. That niche does not need 512k at 7 tok/s while 262k native exists.

### Recommendation

**Deprioritize ≥256k extension work until long-context decode is sensible**, meaning the C8-1 attention fix in Q4 brings 512k decode to ≥15 tok/s no-draft or 256k to ≥20. Park these, in order:

| Item | Status / reason |
|---|---|
| LSA-YARN-512K (LCP:1853) | carries the 2026-11-06 operator ruling, so parking it needs an operator decision (package below). Its own expected gain is about 1.03x TTFT at 512k (LCP:1853), and the LSA H12 indexer was **FUTILE** at 32k (0.368x; LCP:1850). It cannot move decode from 7 to usable; the attention kernel can. |
| YARN-CPU-512k (LCP:153) | park |
| YARN-1M (LCP:260) | park |
| YARN-DCA and YARN-DCA-E1 at 400k/500k (LCP:185, 209) | park |
| YARN-E2, the on-demand long-context stack mode (LCP:176) | park |
| JETLONG-* runs (LCP:297-310) | park |

**Keep:**
- YARN-NATIVE-WINDOW-GATE (LCP:356): YaRN must not regress the native window (standing rule).
- YaRN native-window inertness (LCP:171).
- KSHIFT-FIX-MODEL-TEST (LCP:295).
- YARN-AGG-1 spec (LCP:330); this is zero inference.
- YARN-E1-PROOF (LCP:122).

**Prioritize instead:**
- **TOC-CMP-4 then TOC-CMP-3.** The pre-registered compaction A/B on our 27B decides whether the paper transfers to an open-weight model. TOC-CMP-1 and TOC-CMP-5 are cheap and local.
- **UFH-21**: live security exposure.
- **REPL-EMB-4.1 `context.search()` and REPL-EMB-3.1 spill summary** (`harness-program.md:2609, 2601`). This is our version of the paper's bounded-read surface. Also file the missing "A7 file-plus-bounded-read" probe as an orchestrator box; the owning session applies it.
- **CF-3c** (`context-and-token-economy.md:31`): the live compaction-quality monitor.
- **DEPTH-ENV-1**.
- **The C8-1 long-context attention kernel** (Q4). It is the one lever that serves both strategies: it speeds DFlash2 at 50–150k agentic contexts today and is the precondition for any ≥256k work.

**Decision package for the operator (LSA-YARN-512K):**
- (A, recommended) Park until C8-1 lands, then re-judge at 512k on the faster dense baseline.
- (B) Keep it live. It would compete for GPU windows with a ≤1.03x expected gain.
- (C) Close it. That loses the option if C8-1 makes 512k usable.

---

## Q4. GDN as the C8 target, and the ranked C8 package

### GDN share (GDN/RESULT.json; C7r `62cb6a6af`; kernel-time share, graphs on)

Wall shares are null (the wall records are empty). For decode, kernel time ≈ wall (32.5 ms kernel vs 31.6 ms/token measured).

| 27B cell | GDN_CORE share | GDN ms/unit | notes |
|---|---|---|---|
| pp2048 | **15.8%** | 333 ms per 2048 tokens (48 layer calls, 6.95 ms each) | Cijk rocBLAS 67%, convert+dequant 7.4% |
| pp32768 | 14.6% | | CK FmhaFwd 8.0%, filed under OTHER (class-map gap) |
| tg@d0 / d4096 | 1.36% / 1.57% | 0.44 ms/token | |
| tg@d32768 | −0.1% | | invalid: depth prefill contaminates the profile |
| verify v9@d0 (np1, 9 tokens) | 3.4% | 1.63 ms/step | `q8wv_mul_mat` 71.7% |
| verify v36@d0 (np4, 36 tokens) | 6.5% | 5.8 ms/step | MMQ 68% plus stream-k fixups 8.8% |
| A3B pp2048 / tg | 21.2% / 2.3% | | |

### Amdahl: e2e gain = 1 / (1 − s + s/k)

| unit | s | 1.5x | 2x | 3x | ∞ |
|---|---|---|---|---|---|
| 27B prefill (pp2048) | 0.158 | +5.6% | **+8.6%** | **+11.8%** | +18.8% |
| 27B prefill (pp32k) | 0.146 | +5.1% | +7.9% | +10.8% | +17.1% |
| 27B decode, no draft | 0.0136–0.0157 | +0.5% | +0.7–0.8% | +0.9–1.1% | +1.6% |
| 27B DFlash2 step, np1 | ≤0.034 | +1.1% | +1.7% | +2.3% | +3.5% |
| 27B DFlash2 step, np4 | 0.065 | +2.2% | +3.4% | +4.5% | +7.0% |
| A3B prefill | 0.212 | +7.6% | +11.9% | +16.5% | +26.9% |

The DFlash2 rows are upper bounds: the drafter's time is not in the v9/v36 denominator, which only makes s smaller.

### Roofline at our shapes

48 v-heads, d_k = d_v = 128 (`ssm_d_inner` 6144, `d_state` 128, `dt_rank` 48), f32 state of 3.15 MB per layer.

**Prefill.**
- The kernel is the sequential `gated_delta_net_cuda<128,…>`, a token-serial recurrence.
- Cost is about 4·d_k·d_v FMAs per head per token, i.e. 6.3 MFLOP per layer per token and 12.9 GFLOP per layer per 2048 tokens.
- 12.9 GFLOP in 6.95 ms is **1.85 TFLOP/s, about 8% of FP32 vector peak (22.6)**.
- Bytes are trivial: q/k/v/g/β ≈ 74 KB per token per layer, about 0.1 ms per 2048 tokens.
- So it is bound by serial latency and parallelism; only 48 heads × 128 columns run in parallel.
- A chunked (WY/UT, chunk 64) formulation turns most of the work into MFMA GEMMs. **2–3x is realistic and about 10x is the paper ceiling.**

**Decode.**
- State read plus write is 6.3 MB per layer × 48 = 302 MB/token, which is 0.22 ms at 1.4 TB/s; measured 0.44 ms.
- **At most 2x headroom**, which is worth ≤0.8% e2e.

**Verify (9 tokens).** The state is read once and the steps are serial, so there is about 3x headroom in theory, worth ≤2.3% at np1.

**Verdict.** GDN is a **prefill/ingest lever (+9–12% on 27B, +12–17% on A3B) costing M–L**: a new chunked kernel with gated decay, plus a test-backend-ops gate. It does nothing material for 27B DFlash2 decode, which is what agentic serving spends its wall time on (90–96% prompt-cache hits).

### Other candidates (SEEDS:36-100) re-costed against today's numbers

| Rank | C8 item | Target | Expected e2e | Cost | Evidence / caveat |
|---|---|---|---|---|---|
| **1** | **C8-1 = AK-ASM-H17 (profile, S), then a new long-context attention-decode/verify efficiency seed.** Covers the n_q=1 FA split and occupancy at n_kv ≥ 32k, and the gv kernel's split heuristic (2·nsm/n_head_kv = 52 splits with a 1-WG/CU launch bound, `fattn-gqa-verify.cu:607-623`) | 27B decode and DFlash2 verify at ≥32k | **+16% at 32k, +55% at 128k, about 2.4x at 512k (no draft)**, if attention reaches 40% of HBM (from 10%). At the 50–150k agentic contexts: +25–55% | S + M | measured 160 GB/s effective (Q2 fit over 22 requests, two builds). The decode kernel's identity at n_q=1 is unprofiled, so H17 comes first. This also unblocks Q3's ≥256k items |
| **2** | **AK-ASM-H16, re-scoped to the production verify M.** np4 × 9 = M 36 (MMQ path, 77% of the v36 step), plus M 12–16 for np2 | 27B DFlash2 verify under load | if the matmul share reaches about 60% of BW: step 1.2–1.4x, i.e. **+15–30% aggregate decode at np4** [inferred] | M | SEEDS:36-43 says MMQ is at ~31% BW at M ≥ 12; H1b hit 927 GB/s at M ≤ 11. As written the seed targets M 12–16, which is not the np4 shape |
| **3** | **AK-ASM-H19, zero-split census** (27B and A3B, decode and prefill) | mandatory policy (SEEDS:61-73) | gate, not gain; unknown for 27B | S–M per split class | operator policy 2026-11-06. It runs in the package regardless of rank |
| **4** | **AK-ASM-H18, hd256 CK FMHA at long-context prefill** | 27B prefill ≥32k | prefill attention is at 14 TFLOP/s (8% of MFMA). At 128k, attention is 87% of chunk time; 2x FA cuts 128k cold prefill from about 307 s to about 170 s | S (measure), then M | Q2 fit; seed estimate +10–20% at ≥32k |
| **5** | **AK-ASM-H20, tuned rocBLAS/hipBLASLt plus fused convert** | 27B/A3B prefill | +5–10% [seed]. Note the convert+dequant share is **7.4%** of pp2048, not the 15% the seed says, so the fusion half is worth ≤ +7% | S–M | GDN runs.json kernel breakdown |
| **6** | **GDN chunked core** | 27B/A3B prefill | 2x: +8.6% (27B) / +11.9% (A3B); 3x: +11.8% / +16.5% | M–L | this memo, the table above |
| 7 | AK-ASM-H21, QSA prefill for Q38FN | Q38FN | n/a: Q38FN is CPU-served (SEEDS:84-90) | M | apply only if H22 adopts a hybrid deployment |

**Recommended C8 package:**
- **Core:** C8-1 (H17, then the long-context attention fix) + H16 re-scoped to M 36 + H19 census.
- **Prefill pair, if desk capacity remains:** H18 + H20.
- **Defer:** GDN to C9, or run it as the prefill item only if ingest_long_context prefill becomes the bottleneck. Its value grows for A3B-on-GPU.

Expected agentic decode gain of the core package is about +30–70% at 50–150k contexts (C8-1 and H16 compose multiplicatively on different parts of the step). That is an inferred design prior, not measured.

---

## Q5. streaming-llm-baseline: expected benefit, hybrid feasibility, recommendation

**What it was for** (LCP:1586-1640). It was an easy floor: sink K=4 plus a window of 1024–4096, built as `--kv-streaming-sink` / `--kv-streaming-window` over the context-shift path (`seq_rm` + `seq_add`; commits `632ce0f92`, `111bff89d`, `cf051d3e1`). The May-2026 KV-reduction cluster (PBKV/LU-KV/KVP/ForesightKV/SP-KV) had to beat it.
- The only result is the pre-v7 sweep: Qwen3-1.7B Q8 on CPU, `-c 384`. **All arms failed quality**, and speed was 0.990–1.011x, so `admit_cluster=false`.
- The 72-cell sweep ran zero cells in 2.5 months (decline text at LCP:1727).

**Why it is blocked on C7r.**
- `tools/server/server-context.cpp:1616-1625` @ `62cb6a6af` disables `ctx_shift` and `n_cache_reuse` when `llama_memory_can_shift()` is false.
- On C7r the hybrid case returns `mem_attn && mem_recr` (`src/llama-memory-hybrid.cpp:133-136`). The recurrent side is **always false** (`src/llama-memory-recurrent.cpp:706-710`, V11-098 guard `8b08c9f25`).
- The pre-guard tree (`0db32c06e`) returned true for hybrids, which is the stale-state bug the guard fixed.

**Feasibility of a hybrid carve-out.**
- GDN layers carry no positional encoding, and the conv state covers only the last 4 tokens. Evicting a middle range **from the 16 attention layers only**, and K-shifting what remains, while leaving the recurrent state untouched, is well-defined. The model sees an attention gap while GDN retains a lossy summary of everything.
- The guard is right for **cache reuse** (chunk reuse needs a state that matches an exact prefix). It is over-broad only for deliberate streaming eviction.
- Implementation:
  - a hybrid `seq_rm`/`seq_add` that acts on `mem_attn` only, behind the streaming flags
  - `can_shift` kept false for cache_reuse
  - the H1–H3 K-shift fixes (YaRN mscale, `pos_div` sign, q8_0 Hadamard nrot; LCP:283), which are unit-verified only on `f9cb7cd32` and needed for any shift under YaRN
- Effort: about 2–4 desk days plus a model-level K-shift test (KSHIFT-FIX-MODEL-TEST), then one GPU quality cell. It could ride a champion build, but only after KSHIFT-FIX lands there.

**Expected payoff.**
- **Speed:** decode is capped at the window. For example W = 32k gives about 37 ms/token instead of 85 (256k) or 141 (512k).
- **Quality:** retrieval of evicted content fails by construction, and that is the whole point of long context. Whether GDN recall of evicted spans is useful is untested; no evidence either way. The dense floor already failed quality.
- **Better routes to the same speed:**
  - the harness (Q3) gives bounded context with chosen content rather than recency
  - C8-1 lowers the cost of keeping everything
- The KV cluster it was meant to gate is itself unprioritized.

**Recommendation: keep it closed.** The reason is not "cannot run on hybrids" (a carve-out can). It is that the payoff is dominated by the harness route and C8-1, and the only floor evidence is negative.

**Reopen triggers:**
- (a) TOC-CMP-4 shows compaction collapse on our 27B, the paper's open-weight failure mode. "Attention window + GDN memory" then becomes a cheap model-side alternative worth one quality cell.
- (b) A production workload needs unbounded streaming dialogue past 262k.
- (c) The KV-reduction cluster is re-prioritized and needs its floor.

Correction to the decline text: point (3) should read "needs a hybrid attention-only eviction carve-out", not "cannot run".

---

## Evidence index

- MEM/RESULT.json (E1–E4)
- MEM/logs/e4-500k-1794010865.server.log:37-155 (prefill chunks), :521-522 (500k decode), :531-716 (short requests)
- MEM/logs/e3-draft-cpu-1794010853.server.log:8, 239
- E1R/A0.server.log, E1R/A1.server.log (decode vs context, parsed by `calc/decode_vs_ctx.py`)
- `/mnt/raid0/llm/tmp/inf22-yarn-mem-20261106/PLAN.md` §1-3
- GDN/RESULT.json, GDN/runs.json (kernel breakdown)
- Champion source @ `62cb6a6af`:
  - `ggml/src/ggml-cuda/fattn-gqa-verify.cu:51-53, 500-623`
  - `tools/server/server-context.cpp:1616-1625`
  - `src/llama-memory-hybrid.cpp:133-136`
  - `src/llama-memory-recurrent.cpp:706-710`
- LCP:91, 106-108, 122, 153, 171, 176, 185, 209, 260, 283, 295, 330, 356, 1586-1727, 1761-1762, 1844-1853
- KVP:1832, 2116, 2455-2812
- `handoffs/active/harness-program.md:2209, 2601, 2609, 2775-2796`
- `handoffs/active/context-and-token-economy.md:23-31`
- `handoffs/active/cpu-decode-roofline-program.md:105`
- `research/deep-dives/ydnlc-20261106/` (origin/main), commit `ada27e8e7`
- SEEDS:36-100 (@ `272b39a1a`)
- `docs/design/hsf-5-host-kv-mirror-costing-20261024.md:70-76`
- `wiki/inference-serving.md:202`, `wiki/context-extension.md:48, 403`

Scratch helpers: `calc/` (decode parser, origin/main snapshots of LCP, KVP and SEEDS). They can be deleted after review.
