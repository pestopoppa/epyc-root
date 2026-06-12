# turbovec — Google TurboQuant standalone vector index (intake-686 deep-dive)

`date: 2026-06-12` · `intake: intake-686` · `source: github.com/RyanCodrai/turbovec` · `paper: arXiv:2504.19874 (TurboQuant, ICLR 2026)` · **refined verdict: NO-GO for the orchestrator repl_memory/strategy_store swap as framed; CONDITIONAL-WATCH for the KB-RAG corpus; kernel-mining is a NON-STARTER**

---

## TL;DR / Refined recommendation

**No-go on the headline framing.** The intake recommends benching turbovec "vs current FAISS repl_memory/strategy_store path." That comparison is mis-scoped: turbovec's entire value proposition is **8x RAM compression with FAISS-PQ-parity recall**, but our repl_memory path does **not** run a compressed PQ index — it runs **`faiss.IndexFlatIP`** (exact, uncompressed brute-force inner product) over **1024-dim BGE-large** vectors. The two stores it would replace are tiny:

- **Episodic store** (`sessions/embeddings.faiss`): ~**72.8K** vectors → **298 MB** float32. 8x cut saves **~261 MB**.
- **Strategy store** (`strategies/strategy_embeddings.faiss`): ~**1.3K** vectors → **5.3 MB**. 8x cut saves **~4.7 MB**.
- Combined live footprint **~304 MB on an 1.1 TB host** (0.03% of RAM). The RAM win is real but **irrelevant** at our scale — the headline 31 GB→4 GB story is a 10M-doc corpus we don't have.

**The QPS angle is also weak on our hardware.** turbovec's +12–20% search win is **ARM/NEON-only**. On x86 AVX-512 it is roughly **PQ-parity (+5% at 4-bit, −8% at 2-bit single-thread)** — and that parity is **vs FAISS PQ-FastScan, not vs our IndexFlatIP**. Against an exact flat index over 73K vectors (where FAISS brute-force is already ~1–3 ms), a lossy compressed scan offers no latency headroom worth the recall hit and the lost `index.reconstruct()` capability (see Risks).

**Kernel-mining is a non-starter.** turbovec's AVX-512BW kernel is a **nibble-LUT FastScan code-distance scanner** (adapted from FAISS FastScan: 4-bit packed codes, u16 accumulators, LUT lookups). Our Q8_0 kernel at `ggml/src/ggml-cpu/arch/x86/repack.cpp` is an **8-bit×8-bit integer GEMV** (VPMADDUBSW-based, BW-bound, dot-product over full-precision-ish quantized weights). Different data layout, different arithmetic, different bottleneck (LUT-throughput vs DRAM-bandwidth). There is no transferable kernel.

**Highest-value next action:** Do **not** bench turbovec against repl_memory. Instead, re-aim it at the only place where the compression story could matter — the **KB-RAG corpus (~13.5K chunks today, GTE-ModernColBERT multi-vector, growing)** — and gate any work behind a concrete scale trigger (see gates). Until that trigger fires, intake-686 stays **worth_investigating / parked**, not actioned.

**Explicit gates (all must hold to proceed past WATCH):**
1. A target corpus exceeds **~1M vectors** (or multi-vector token-embedding count) where float32 RAM crosses ~4 GB and exact flat search crosses ~10 ms. (Today: 73K / 298 MB — fails by ~14x.)
2. The target uses (or can use) a **single-vector inner-product** index. (KB-RAG is **multi-vector late-interaction MaxSim** — turbovec's single-vector MIPS API does not model MaxSim; fails today.)
3. We are RAM-pressured. (Today: 304 MB of 1.1 TB — fails.)

---

## What it is

turbovec (RyanCodrai, MIT, ~11K stars, ~152 commits, Rust core 45.6% + Python 54.4% via maturin, `pip install turbovec`) is a standalone vector index implementing **TurboQuant** (Zandieh/Daliri/Hadian/Mirokni — Google Research / Google DeepMind / NYU; arXiv:2504.19874, ICLR 2026).

**TurboQuant algorithm (from the paper):**
- **Data-oblivious** scalar quantizer: no per-dataset training. A **random rotation** makes coordinates near-iid Beta-distributed in high dimension; **Lloyd-Max** optimal scalar boundaries are then precomputed per bit-width (4 buckets @ 2-bit, 16 @ 4-bit).
- **Two-stage for unbiased inner product:** MSE-optimal quantization with (b−1) bits, then a **1-bit QJL (Quantized Johnson-Lindenstrauss)** residual to remove the inner-product bias that pure MSE quantizers introduce.
- **Distortion guarantees:** MSE `D_mse ≤ (√3·π/2)·4^(−b)` → within ~**2.7x** of the Shannon distortion-rate lower bound; at b=1 within ~**1.45x**. Inner-product estimator is **unbiased**.
- Targets **both L2/MSE and inner-product (MIPS)**. Paper also demonstrates 4x KV-cache compression (orthogonal to this intake).

**turbovec specifics (README + paper):**
- TQ+ per-coordinate calibration: shift/scale fit on first ingest, then **frozen** (so recall depends on first-batch representativeness).
- Length-renormalized scoring: stores `||v|| / ⟨u, x̂⟩` per vector to correct quantization bias; **searches directly against codebook values without decompression**.
- **Index structure: brute-force flat over compressed codes. No IVF/ANN/HNSW layer.** (`IVFTurboQuantIndex` exists only in the separate pure-Python Firmamento port, not in turbovec.)
- API: `TurboQuantIndex(dim, bit_width)`, `IdMapIndex` (stable uint64 IDs, O(1) `remove`), `search(q, k, allowlist=...)` (allowlist filtering at 32-vector SIMD block granularity), `.write()/.load()`. Rust API mirrors Python (`TurboQuantIndex::new(1536, 4)`).
- SIMD: NEON (ARM), **AVX-512BW (x86) with AVX2 fallback**, runtime-gated via `is_x86_feature_detected!`; `.cargo/config.toml` targets x86-64-v3. The x86 kernel **adapts FAISS FastScan's pack layout + nibble-LUT scoring + u16 accumulators**.

**Third-party corroboration:** Firmamento-Technologies/TurboQuant (pure-Python, ~20 stars, 3.8K parametrized tests, all six paper claims verified, 95.3% R@10 @6-bit, no SIMD) and 0xSero/turboquant (the paper's own KV-cache/Triton reference, ~1.6K stars). The algorithm is well-corroborated; turbovec is the only SIMD-on-x86 single-vector-search packaging. Credibility: **3 (solid)**.

---

## Fit to EPYC

**Exact call site (verified in code):**
- `orchestration/repl_memory/faiss_store.py` → `FAISSEmbeddingStore` uses **`faiss.IndexFlatIP(dim)`** with `normalize_L2` (cosine via IP). `dim` default **1024** = **BGE-large-en-v1.5** (`embedder.py:33-45`, model `bge-large-en-v1.5-f16.gguf`).
- Consumers: `episodic_store.py:267-270` (`FAISSEmbeddingStore(dim=1024)`, search `k*2` candidates at `:523`) and `strategy_store.py:109-113` (`strategy_embeddings.faiss`, `retrieve()` does **FAISS top-fetch_k fused with BM25 via RRF** at `:522-541`).
- **Hybrid RRF is load-bearing:** the FAISS half supplies the dense ranking that's reciprocal-rank-fused with BM25. turbovec returns `(scores, ids)` — droppable into the dense half — but it has **no metadata store**; the SQLite metadata + RRF fusion plumbing all stays ours.

**RAM math (computed from on-disk `.faiss` sizes, IndexFlatIP = ntotal·dim·4 B):**

| Store | file | ntotal | float32 RAM | turbovec 4-bit (8x) | saving |
|---|---|---|---|---|---|
| episodic | `sessions/embeddings.faiss` (298,274,861 B) | ~72,821 | 298.3 MB | ~37.3 MB | ~261 MB |
| strategy | `strategies/strategy_embeddings.faiss` (5,316,653 B) | ~1,298 | 5.3 MB | ~0.7 MB | ~4.7 MB |
| **total** | | **~74K** | **~304 MB** | **~38 MB** | **~266 MB** |

**266 MB saved on a 1.1 TB host = 0.024% of RAM.** The compression win is numerically real and economically meaningless at current scale.

**AVX-512 reality:** EPYC 9655 is AVX-512 (Zen 5, no NEON). turbovec's AVX-512BW path **will compile and run** (runtime-gated, x86-64-v3 baseline — well within Zen 5). But its measured x86 win is **PQ-parity, not the ARM headline**: +~5% (4-bit) / −~8% (2-bit, single-thread d=1536) vs FAISS **PQ-FastScan**. Our baseline is **IndexFlatIP (exact)**, which turbovec doesn't even claim to beat on recall — it trades recall for RAM. On 73K vectors, FAISS flat search is already ~1–3 ms (per the store's own docstring); there is no latency problem to solve.

**Kernel-mining verdict (the intake's "mine its AVX-512BW kernels vs our Q8_0 GEMV"):** structurally incompatible.
- turbovec kernel = **FastScan nibble-LUT distance scanner**: 4-bit packed codes, two 16-entry LUTs per query subspace, u16 saturating accumulators, block-of-32 layout. Throughput-bound on LUT gathers/shuffles.
- our kernel (`ggml/src/ggml-cpu/arch/x86/repack.cpp`, `avx512-helpers.h`, branch `production-consolidated-v5`) = **Q8_0 8x8 integer GEMV**: VPMADDUBSW dot-products over 8-bit activations × 8-bit weights, **DRAM-bandwidth-bound** (per project memory `feedback_cpu_decode_bw_bound`, `project_q8_8x8_avx512bw_outcome`).
- Different layout, different op, different bottleneck. Nothing ports. (If anything, the *FAISS FastScan* reference — which turbovec copies — is the upstream to study, not turbovec.)

---

## Decision gates & exact next steps

1. **DO NOT** bench turbovec against repl_memory/strategy_store. It would compare a lossy compressed scan against an exact flat index at a scale where RAM is a non-issue — a guaranteed recall loss for a 266 MB saving nobody needs. Drop that line item from intake-686.

2. **Re-aim at KB-RAG only, and only if it grows past the scale gate.** KB-RAG is `epyc-orchestrator/src/retrieval/` (~13,537 chunks, GTE-ModernColBERT 128-dim **multi-vector** MaxSim, flat `.npz` + SQLite, no vector-DB service today). Two blockers: (a) it's **multi-vector late-interaction**, which turbovec's single-vector MIPS index does not model — you'd quantize per-token embeddings and lose MaxSim semantics; (b) at 13.5K chunks the `.npz` path is already fine. **Gate: only revisit when the chunk×token embedding count crosses ~1M AND a single-vector first-stage retriever (not MaxSim) is in the pipeline.**

3. **If/when gate 1+2 fire, the EXACT operator bench** (single-vector first-stage, e.g. a BGE-large dense pre-filter over the grown corpus). Analysis-only here — operator runs manually, respecting `feedback_no_concurrent_inference` (no concurrent inference; get per-run approval):

   ```bash
   # One-off, CPU, no model load beyond the already-embedded vectors.
   # Prereq: export the live float32 embeddings the store already holds.
   pip install turbovec faiss-cpu
   python3 - <<'PY'
   import numpy as np, time, faiss
   # 1. Reconstruct the real corpus from the live FlatIP index (no re-embedding):
   idx = faiss.read_index("/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/sessions/embeddings.faiss")
   N, d = idx.ntotal, idx.d
   X = idx.reconstruct_n(0, N)                      # (N, 1024) float32, already L2-normalized
   Q = X[np.random.choice(N, 1000, replace=False)]  # 1000 in-distribution queries
   # 2. Ground truth via exact flat (current production behavior):
   t=time.time(); Df,If = idx.search(Q, 10); flat_ms=(time.time()-t)/len(Q)*1e3
   # 3. turbovec 4-bit:
   from turbovec import TurboQuantIndex
   tv = TurboQuantIndex(dim=d, bit_width=4); tv.add(X)
   t=time.time(); _,Itv = tv.search(Q, 10); tv_ms=(time.time()-t)/len(Q)*1e3
   # 4. Recall@10 vs exact flat, RAM, QPS:
   rec = np.mean([len(set(a)&set(b))/10 for a,b in zip(If, Itv)])
   print(f"N={N} d={d}")
   print(f"flat   : {flat_ms:.3f} ms/q  RAM~{N*d*4/1e6:.0f} MB")
   print(f"turbovec 4b: {tv_ms:.3f} ms/q  RAM~{N*d*0.5/1e6:.0f} MB  recall@10-vs-flat={rec:.3f}")
   PY
   ```
   **Pass criteria to even consider adoption:** recall@10-vs-flat **≥ 0.97** AND RAM-cut materially relieves a *real* pressure AND QPS ≥ flat. On today's 73K/304 MB corpus this fails the RAM-pressure premise regardless of recall, so **do not run it now** — it's the template for the post-scale-gate world.

4. **Kernel-mining: close it.** Mark "mine AVX-512BW kernels vs Q8_0 GEMV" as **rejected — incompatible kernel class** (FastScan LUT scanner vs BW-bound integer GEMV). If anyone wants the FastScan technique, study FAISS upstream directly, not turbovec.

5. **Cross-check NextPLAID (intake-355)** before any Rust-local-PQ adoption: NextPLAID is the existing Rust-local comparable and is already deemed "overkill" for the reranker task (`colbert-reranker-web-research.md:80,105`). turbovec is strictly simpler (no ANN layer) — if NextPLAID was overkill, turbovec is under-powered for corpus-scale ANN. Neither is currently warranted.

---

## Risks & contradicting evidence

- **Mis-scoped baseline (primary):** intake framed it vs "FAISS repl_memory path" implying a PQ index; the actual index is exact `IndexFlatIP`. The 8x-RAM / PQ-parity story has no purchase against an exact flat index at 73K vectors.
- **Loss of `reconstruct()`:** `faiss_store.py:206-223` and `episodic_store` rely on `index.reconstruct(idx)` to retrieve raw embeddings. A lossy quantized index returns codebook approximations, not the stored vector — silently degrading any downstream consumer that reads embeddings back (verifier/distiller paths). This is a correctness regression, not just a recall trade.
- **Frozen TQ+ calibration:** shift/scale fit on first ingest and frozen — risky for an **append-heavy** episodic store whose distribution drifts as new sessions accumulate; recall could decay without re-calibration plumbing we'd have to build.
- **Multi-vector mismatch (KB-RAG):** turbovec is single-vector MIPS; KB-RAG is per-token MaxSim. Quantizing token embeddings independently doesn't preserve late-interaction semantics — adopting it would mean re-architecting retrieval, not a drop-in.
- **x86 win is ARM-borrowed in the headline:** the +12–20% is NEON; on AVX-512 it's parity-to-slightly-negative at 2-bit. Project hardware is x86 AVX-512 (`feedback_llama_bench_fa_default`, Zen 5), so the QPS pitch does not apply.
- **Maturity caveat:** 11K stars is high but commit count (152) and 6 open issues suggest a young project; recall claims are author-run benchmarks. Independent Firmamento port (3.8K tests) corroborates the *algorithm*, not turbovec's SIMD kernels specifically.
- **Contradicting (in favor):** if the orchestrator ever consolidates episodic + strategy + a future large agent-memory into a single multi-million-vector store under RAM pressure, turbovec's data-oblivious zero-train ingest + MIT license + Python binding make it a clean candidate — hence WATCH, not hard-kill.

---

## Cross-refs

- Code: `epyc-orchestrator/orchestration/repl_memory/faiss_store.py` (IndexFlatIP, dim=1024), `embedder.py` (BGE-large), `episodic_store.py:267-270,523`, `strategy_store.py:109-113,491-541` (RRF fusion); `epyc-orchestrator/src/retrieval/` (KB-RAG).
- Our kernel: `llama.cpp` (branch `production-consolidated-v5`) `ggml/src/ggml-cpu/arch/x86/repack.cpp`, `avx512-helpers.h`, `quants.c`.
- Handoffs: `handoffs/active/internal-kb-rag.md` (intake-686 note L416-420; corpus 13.5K chunks L3; "no vector DB" L99), `handoffs/active/colbert-reranker-web-research.md` (NextPLAID intake-355 L80,105; PLAID L247).
- Project memory: `feedback_cpu_decode_bw_bound`, `project_q8_8x8_avx512bw_outcome`, `feedback_llama_bench_fa_default`, `project_engram_vs_longcat_distinction` (paper-faithful vs family-validating pattern), `feedback_dont_dismiss_creative_uses`.
- External: arXiv:2504.19874 (TurboQuant, ICLR 2026); github.com/RyanCodrai/turbovec; Firmamento-Technologies/TurboQuant (pure-Python port); 0xSero/turboquant (paper KV-cache reference).
