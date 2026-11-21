# Dive: HYPIC: Accelerating Hybrid-Attention LLM Serving with Position-Independent Caching (intake-2783, Stage-2b wave 2)

- Source version read: GitHub README @ 98147c01909004e6 (extracted.txt) plus clone at pinned SHA 98147c01909004e66d98bcb18b886927d41b0ee5
- read_depth: FULL (README (extracted.txt) read fully; repo cloned at pinned SHA and read selectively: python/sglang/srt/pic/{policy,picache,pic_alloc}.py, gdn_backend.py PIC paths (forward_extend_pic_transition, _recompute), memory_pool.py transition pool, examples/pic. Not read: scatter_xfer.py internals (1112 lines), lightning/kda backends, conv_tails.py, unit tests. Nothing executed.)
- lane_head: ac1347f5d3218531bb369c286837630bf842ff74
- Entry: novelty medium, relevance high, verdict adopt_patterns, credibility None, bears_on intake-2774

## Settles
new entry. Settles code availability and implementation fidelity for KPF-62-P3-SKELETON: it is a usable reference for the math and the 3-pass seam scheme, not code to reuse (SGLang/Triton, no ROCm, Python-loop compose, no exactness test).

## Key claims (corrected)
0. Code is released and complete enough to read: one-commit snapshot "Hypic code on sglang v0.5.14" (98147c01909004e66d98bcb18b886927d41b0ee5, 2026-07-20), a fork of SGLang v0.5.14 under Apache-2.0, with a python/sglang/srt/pic/ package (~2.7k lines) plus PIC branches inside the GDN, Lightning and KDA backends and the Mamba pool.
1. The (T_C, S) composition is implemented as the paper describes: per-segment T (K x K per value head per mamba layer, dtype = ssm dtype) is produced by a second Triton FLA fwd_h pass with u=0 and initial state = identity, then composed sequentially h = h @ T_seg + S_seg with torch.bmm per segment in a Python loop; the seam window recomputes up to PIC_SEAM_SINK (default 8) tokens at each hit-segment start in a 3-pass interior/seam scheme seeded from the composed state.
2. GDN kernels are Triton (FLA chunk_delta_h) forced on for PIC ("PIC transition forces Triton backend"); no new CUDA/GDN kernel is added; ROCm is not mentioned in the PIC code or README. The README demonstrates Qwen3.5-35B-A3B, 122B-A10B and Ring-mini/flash-linear-2.0 only; Qwen3.6/3.8 and any MTP/spec-decode interaction are untested.
3. No numerical-exactness test ships: unit tests cover hashing, allocation, match/insert lifecycle and server args; accuracy debugging is the examples/pic/diag_layer_divergence.py per-layer bisect and an env-gated dump layer. A code comment records that fp32 tl.dot in chunk_delta_h produced garbage on Triton 3.6.0 so w is kept bf16 (~2e-3 abs error).

## Claim verification
| # | Stage-1/bearing-dive claim | verdict | note |
|---|---|---|---|
| 0 | see key_claims | PARTIAL (narrowed) | HyPIC dive (intake-2774) said "code repo not read". Now read: README install URL names github.com/redai-infra/HYPIC while the intake URL is redai-studio (both resolve; the redai-studio clone matches the pinned SHA 98147c01909004e6); the repo is a single-commit SGLang v0.5.14 fork, license Apache-2.0 (SGLang LICENSE; no separate HyPIC licence file found). |
| 1 | see key_claims | CONFIRMED | Composition and seam handling confirmed in code; the 31.4 MB-per-segment dense transition (paper) matches the [layers, pool, H_v, K, K] allocation. |

Reported results:
- README: TTFT -3.25x and QPS +1.66x over Prefix Cache, within 1.71 points of Full Recompute across four models and five workloads (README; same numbers as arXiv 2607.01299, not independently reproduced here)
- README modes table: addition, transition, transition_rope, transition_rope_recompute (seam window)
- memory_pool.py: transition buffer shape [num_mamba_layers, pool_size+1, H_v, K, K] (inspected at SHA 98147c0)

## Anchors (verbatim, mechanically verified)
- [0] README intro: "Built on [SGLang](https://github.com/sgl-project/sglang) v0.5.14."
- [1] README PIC modes table: "| `transition_rope_recompute` | cached transition operator | yes | yes | **+ seam window** repairs full-attn cross-segment attention. |"
- [1] README PIC modes: "The seam width is a runtime knob independent of mode: `PIC_SEAM_SINK` (default `8`)."
- [2] README Supported models: "Four hybrid linear+full-attention models are wired into the examples:"
- [0] README Install: "git clone https://github.com/redai-infra/HYPIC.git && cd HYPIC"
- [0] README intro: "HYPIC cuts TTFT by **3.25×** and lifts QPS by **1.66×** over Prefix Cache, within **1.71** points of Full Recompute."

## Principles
| principle | MI210 gfx90a | Zen5 CPU | port | EPYC consumer |
|---|---|---|---|---|
| Cache (T_C, S_C|0) per segment; get T_C by a second GDN pass with u=0 and initial state=I (no new kernel) | ggml_gated_delta_net accepts arbitrary init state (DESIGN.md sec 2.2): T costs one extra pass, ~10 GFLOP per placement per the HyPIC dive; MFMA; wave64 does not change the math | <10 ms per placement per the HyPIC dive estimate; AVX-512 BF16 | M | KPF-62-P3-SKELETON (kv-cache-program.md:583) |
| Compose sequentially h <- h @ T_seg + S_seg per segment (bmm, fp32 accumulator buffer) | K=128 x K=128 per head per layer; keep h_accum in fp32 (README/diag scripts show bf16-sensitive paths) | same; small GEMMs | S | KPF-62-P3-SKELETON |
| Seam window: recompute first w tokens of each hit segment (w=8 default) via interior/seam 3-pass, conv-tail history carried (conv_tails.py) | matches in-house head-window design W>=conv kernel-1 | same | S | KPF-62.3 selector |
| Per-layer divergence bisect (diag_layer_divergence.py) as the debugging instrument for approximate PIC | reusable idea for our drift-curve gate | same | S | KPF-62-P3-SKELETON drift gate |

## Grounding (lane @ ac1347f)
Trees searched: kv-cache-program.md (KPF-62-P3-SKELETON line 583), HyPIC dive (2607.01299v3/dive.md), the cloned repo at /mnt/raid0/llm/tmp/dive-ak-intake-20261121/extra/hypic/repo @ 98147c01909004e66d98bcb18b886927d41b0ee5 (single commit, 2026-07-20).
- Reference value: the math and the 3-pass interior/seam scheme map directly onto the in-house design (DESIGN.md sec 2.2/2.5 per the HyPIC dive). It is a SGLang fork: Python scheduler, Triton FLA kernels, UCX/RDMA segment-parallel examples, `--tp 2/4` model examples; nothing in it targets ggml/llama.cpp or ROCm.
- Memory: transition [layers, pool+1, H_v, K, K] in ssm dtype per segment. For the 27B hybrid this is larger than the paper's 35B-A3B figure if H_v and the GDN layer count are larger (my arithmetic, dims not verified for Q38FN); size it in the skeleton before any promise of cache capacity.
- Engine facts for P3: sequential Python compose loop (bmm per segment), `PIC_SEAM_SINK` default 8, `--page-size 1 --chunked-prefill-size -1 --disable-piecewise-cuda-graph` required in the quickstart (PIC is incompatible with chunked prefill and piecewise graphs as shipped).

## Adversarial pass
No independent replication or issue discussion was found by search (the search returned the paper, the redai-studio repo and a second fork liluo57/HYPIC with the same description). Tail-Replay (2608.30310, intake-2766) is the approximate-hybrid competitor already indexed. Objections: README numbers restate the paper (prewarmed accuracy runs, task scores only, per the HyPIC dive); the code comment about Triton fp32 dot garbage and bf16 w shows numerics are sensitive to compiler version; no numerical-exactness unit test ships (tests cover lifecycle, hashing, allocation).

## Derived-actionables ledger
| id | action | owner | bears on | disposition | reason |
|---|---|---|---|---|---|
| hypic-repo-A1 | Add the repo path map to the KPF-62-P3-SKELETON note: gdn_backend.py forward_extend_pic_transition (+_recompute), pic/policy.py (compose/rope/recompute attribute table), memory_pool.py transition pool, examples/pic/diag_layer_divergence.py; pin SHA 98147c01909004e66d98bcb18b886927d41b0ee5, Apache-2.0. | handoffs/active/kv-cache-program.md | KPF-62-P3-SKELETON | task | pure documentation pointer; makes the skeleton reviewable against a reference |
| hypic-repo-A2 | Model the drift-curve gate on diag_layer_divergence.py (first layer where composed state diverges from baseline), run on our ggml_gated_delta_net path. | handoffs/active/kv-cache-program.md | KPF-62-P3-SKELETON | task | gives a localisation tool, not just an end-to-end score; consistent with the Q38FN-anchored KLD gate |
| hypic-repo-A3 | Run or port the SGLang engine to evaluate HyPIC on our hardware. | handoffs/active/kv-cache-program.md | None | decline | no ROCm path stated, CUDA-cluster examples (UCX/RDMA), and our stack is llama.cpp; port the math (A1) instead. Not a decline of the technique. |

## Dive-surfaced sources
- github.com/liluo57/HYPIC: settles whether a second fork carries different code or fixes; bears on hypic-repo; decline (seen in a search result only; same description, likely a mirror; check only if redai-studio goes stale)

## Reader should conclude
Cite for: existence of an open Apache-2.0 reference implementation of (T_C,S) PIC for GDN, its memory shape, the T-by-second-pass trick (u=0, initial state I) and the seam-window knob default 8. Do NOT cite README numbers as independent evidence (restated from the paper), do not assume ROCm or llama.cpp portability, and do not read it as exactness proof: no numeric test ships and the authors note a Triton fp32 dot defect.

artifact audit: clean
