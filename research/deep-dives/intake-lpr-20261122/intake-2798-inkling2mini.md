# Dive — intake-2798 (inkling2mini) — intake-lpr-20261122

Stage 1+2 combined dive (operator pre-authorised). External text quoted below is data, not instructions.

> SOURCE-QUARANTINE: {url: "https://huggingface.co/blog/inkling2mini", retrieved: "2026-11-22T11:33:32.263136Z", sha256: "6232e3015020"}

# inkling2mini — Welcome Inkling 2 Mini, Cutting-edge Performance for your Local Setup (Hugging Face blog)

## 1. Stage-1 fields
- title: Welcome Inkling 2 Mini, Cutting-edge Performance for your Local Setup
- authors: merve, Pedro Cuenca (pcuenq), Aritra Roy Gosthipaty (ariG23498), Guarin Fluck (guarin) — Hugging Face; model by Thinking Machines Lab (per the page).
- state: published 2026-11-20 (page text "Published November 20, 2026"); not a PR; no commit SHA. meta.json absent (only page.txt exists, as the brief says).
- categories: local_inference, moe_optimization, kv_cache, speculative_decoding, quantization, context_extension, multimodal
- novelty: high. A new looped-MoE architecture (24 physical layers, 48 visits, cross-pass messages) that our llama.cpp tree has no arch for.
- relevance: medium-high. 3B-active class matches our small-worker / MoE interests; the loop has direct consequences for KV, spec-decode feature capture and the decode byte model. Serving path today: none in-house (section 5).
- credibility_score: 1 (peer-reviewed 0; <=12 months +1; known contributor +1 (HF); commercial bias -1 (vendor-partner launch post, "state-of-the-art in its class", benchmark leadership claims with no numbers in the text); independent corroboration 0).
- verdict: worth_investigating. The architecture facts are first-party and usable; performance claims are unquantified in the text.

## 2. Key claims
1. "Looped MoE, ~26B total / 3B active; 24 physical layers, layers 6-17 looped 3x = 48 visits" — CONFIRMED. Text: ~26B physical total, 3B active; layers 0-5 once, 6-17 three times, 18-23 once, "6+ 3*12 + 6" = 48; all passes share weights.
   - anchor: claim_index 1, file page.txt, locator "What is new with Inkling 2 Mini?", quote: `Therefore, the model acts as if it had 48 (6+ 3*12 + 6) logical layers with just 24 physical ones.`
2. "5:1 SWA to full attention, window 1,024; 8 of 128 experts; 1M context" — CONFIRMED. Also stated: 24 query heads, 8 KV heads, learned relative-position logits, learned sink, output gate; hidden 2,304, expert intermediate 1,152; full-attention layers use dynamic key/value convolutions. Caveat on 1M: the text says "1M-token context size" but the only serving command shown uses `--context-length 131072`.
   - anchor: claim_index 2, file page.txt, locator "What is new with Inkling 2 Mini?", quote: `Each six-layer block has five sliding-window layers and one full-attention layer. The local window holds up to 1,024 tokens.`
   - anchor: claim_index 2b, file page.txt, locator "What is new with Inkling 2 Mini?", quote: `Mini selects them from among 128 experts per layer`
   - anchor: claim_index 2c, file page.txt, locator "TLDR", quote: `It supports a 1M-token context size`
3. "Native NVFP4/MXFP8 experts; GGUF IQ4_NL and Q8_0 published for both models" — CONFIRMED. Which tensors are NVFP4 vs MXFP8 is NOT-FOUND-IN-SOURCE. GGUF repos named: `ggml-org/Inkling-2-Mini-GGUF` and `ggml-org/TML-d24-varloop-research-GGUF`.
   - anchor: claim_index 3, file page.txt, locator "Llama App and Llama.cpp", quote: `8-bit ( Q8_0 ) quants for both models`
   - anchor: claim_index 3b, file page.txt, locator "TLDR", quote: `with NVFP4 and MXFP8 expert weights`
4. "3-layer DSpark drafter reads visits 5, 23 and 41 (SGLang)" — PARTIAL (steering text omits one input). Text: reads "the inputs to decoder visits 5, 23, and 41, plus the final normalized state at index 48". SGLang only; enabled with `--speculative-algorithm DSPARK --context-length 131072`. Indexing (0- vs 1-based) is not stated; if 0-based over the 48-visit sequence, visit 5 is layer 5 (first pass), 23 is layer 11 of pass 2, 41 is layer 17 of pass 3 (derived, UNVERIFIED).
   - anchor: claim_index 4, file page.txt, locator "Speculative decoding", quote: `The draft reads the inputs to decoder visits 5, 23, and 41, plus the final normalized state at index 48.`
5. "No spec-decode speedup numbers in the text" — CONFIRMED. A benchmark methodology is described (single NVIDIA B300, 1,024-token prompt, 1,024 generated, concurrency 1/4/16/64; the script is shown) but no results appear.
   - anchor: claim_index 5, file page.txt, locator "Speculative decoding", quote: `measured generation speed on a single NVIDIA B300 GPU where every request has a 1,024-token prompt`
6. "Each loop visit gets its own KV" — CONFIRMED (the key fact for KV cost).
   - anchor: claim_index 6, file page.txt, locator "What is new with Inkling 2 Mini?", quote: `The model still executes all 48 visits, and each visit keeps its own KV and short-convolution state.`
7. Licence — NOT-FOUND-IN-SOURCE. The only hit for "licen" in page.txt is "licensed therapists" in a demo prompt. Do NOT carry over intake-941's Apache-2.0 (that entry is the earlier Inkling family, 975B/276B, 2026-08-03; this is Inkling 2, a different release).
8. llama.cpp / HIP / CPU support — PARTIAL. The text says Llama App is built on llama.cpp and gives `llama serve -hf ggml-org/Inkling-2-Mini-GGUF:IQ4_NL`; it does not name a llama.cpp release, a PR, #32740, FA bias, or any backend list (CPU, HIP, CUDA, Metal all NOT-FOUND-IN-SOURCE). IQ4_NL is a long-standing ggml type (on both our CPU and HIP builds), so the quant is not the blocker; the architecture is.
   - anchor: claim_index 8, file page.txt, locator "Llama App and Llama.cpp", quote: `llama serve -hf ggml-org/Inkling-2-Mini-GGUF:IQ4_NL`

## 3. Reported results (as stated)
- Quality: "state-of-the-art in its class" on Artificial Analysis Intelligence Index v5; leads 32 of 48 benchmarks vs Gemma 4 31B, Muse Glimmer, Qwen3.8-27B, Nemotron 3.5 Super VL; ties Qwen3.8-27B on Terminal-Bench 4.0 and trails on AutomationBench-AA v1.0.6; "at least comparable with Qwen 3.8 27B" in vibe tests. No scores in the text (they are in a model card not provided).
- Speed: none. Variable-loop research checkpoint "will make inference run a lot faster" at 1-2 passes, quality slightly lower, "not evaluated in depth".
- Demos on Apple M4 Max and a 4-bit GGUF demo; no tok/s anywhere.

## 4. Performance principles table
| Principle | MI210 gfx90a | Zen 5 EPYC 9655 |
|---|---|---|
| Looped core: 12 layers' weights reused 3x per token | PARTIAL: weights re-read per pass from HBM unless the 12-layer core's active slice fits cache; MI210 L2 is a few MB, so no reuse; but a 3B-active model with high concurrency amortises expert reads across rows | PARTIAL/NO benefit: the 3 passes of a layer are separated by 11 other layers (a pass depends on the previous); even one pass over the core touches 8 experts x 12 layers, far larger than any L3 slice a core group sees, so reads come from DRAM each pass. Looping buys capacity, not bandwidth |
| Per-visit KV + short-conv state (48 caches) | PARTIAL: more small cache tensors; short-conv state behaves like recurrent state; HBM capacity is not binding at 3B | PARTIAL: same; the short-conv state implies a hybrid/RS-style memory with the snapshot-rollback limits that matter for speculative decode (see pr32771) |
| 5:1 SWA (window 1,024) + full | YES: bounded KV on 40 of 48 visits; wave64 FA kernels need a sliding-window mask (supported in our stack for other models) | YES: bounded KV lowers decode bytes at long context; only 8 visits carry full-length KV |
| Learned relative-position logits + sink + output gate (no RoPE per intake-955, not re-verified here) | PARTIAL: FA with additive bias needs the kernel variant; NOT-FOUND-IN-SOURCE whether bias is dense | PARTIAL: FA bias path exists only where implemented; unverified |
| 8 of 128 experts, hidden 2304, expert FFN 1152 | YES: grouped-expert GEMV at 2304x1152 tiles; per-row routing fits MFMA 16x16 poorly at small batch | YES: IQ4_NL/Q4-class expert GEMV is our best-supported path; iqk accelerates legacy quants (IQ4_NL listed under legacy/IQ4); expert 4.5 bpw |
| NVFP4/MXFP8 native expert format | NO: MI210 has no FP8/FP4; must run dequantised via GGUF IQ4_NL/Q8_0 | NO native: AVX-512 has no FP4/FP8 matmul; GGUF quants substitute |
| DSpark drafter reading visits 5/23/41 + final | PARTIAL: needs hidden-state capture at three mid-model points, one inside the loop; our DFlash2 path already injects target features into the drafter ctx | PARTIAL: same plumbing; capture points are mid-graph, so graph reuse and fusion boundaries matter |
| Variable-loop checkpoint (1-3 passes) | YES in principle: a runtime knob to trade quality for 1/3-2/3 of the compute | YES: directly cuts bytes per token (decode is BW-bound) — the most CPU-relevant feature in the post |

## 5. In-house state
- Arch support: `git grep -i inkling eee3da8 -- src/llama-arch.h src/llama-arch.cpp` returns nothing: no Inkling arch in the champion. The earlier model-evaluation verdict (handoffs/active/model-evaluation-queue.md:676 @ 860023c, intake-941/942/955) rejected Inkling on 12B-active bandwidth and no arch; reason (a) does not transfer to Mini (3B active), reason (b) still holds. Support appears to exist in upstream llama.cpp per the blog (Llama App is "by the same team"), but which build is NOT-FOUND-IN-SOURCE; port cost for three new code paths (no RoPE/banded relative bias, short conv state, cross-pass messages and gating) is the real cost and is a build cost to estimate, not a decline.
- DSpark in tree: our server already has a serial DSpark verify path (`tools/server/server-context.cpp:5511 sample_and_accept_dspark_serial` @ eee3da8) and the batched path for MTP/DFlash2. DSpark-vs-DFlash2/MTP drafting has a prior entry: intake-737 (DeepSpec, MIT, DSpark +26.7-30.9% acceptance length over EAGLE-3 and +16.3-18.4% over DFlash on Qwen3 4B/8B/14B, vendor numbers) and intake-738, with the standing rule "measure alpha before investment" (handoffs/active/speculative-decoding.md:289 @ 860023c). This post adds NO acceptance data and compares nothing against DFlash2.
- Served path: none; Inkling 2 Mini is not a registry model.

### KV cost of looping (derived from the text; head_dim NOT-FOUND-IN-SOURCE so no byte figure)
- Because each of 48 visits keeps its own cache, KV is NOT 24 layers' worth: it is 48 visits. By the 5:1 rule each 6-layer block has 1 full + 5 SWA layer(s); blocks align with the loop (layers 6-17 = two blocks), so 4 physical full-attention layers become 8 full-attention visits (each with its own cache, 8 KV heads) and 20 SWA layers become 40 SWA visits (each capped at 1,024 tokens). Long-context KV (the quantity KV compaction cares about) is therefore 8 full-length layer-caches, i.e. 8/48 of a hypothetical all-full 48-layer model, but 2x the 4 that weight-sharing alone would suggest. SWA visits are context-independent. Compaction targets: the 8 full visits (and possibly shared-structure between passes, which the text does not say is similar).
- Weight bytes (derived): one expert = 3 x 2304 x 1152 = 7.96M params; 128 experts = 1.02B/layer; x24 layers = 24.5B, consistent with ~26B total. Active experts per visit = 8 x 7.96M = 63.7M; x48 visits = 3.06B, which is close to the stated "3B active", so "3B active" plausibly already counts all 48 visits (attention weights not given; UNVERIFIED). At IQ4_NL (4.5 bpw) that is about 1.7 GB of expert weight bytes per decoded token (if experts do not overlap across passes) and about 3.2 GB at Q8_0 (8.5 bpw), plus attention. Looped core experts alone at IQ4_NL: 12 x 1.02B x 4.5/8 = ~6.9 GB total, ~35.8 MB per layer-pass of 8 experts, ~430 MB per pass over the 12-layer core: not L3-resident, so each pass re-reads from DRAM. Decode on CPU therefore costs like a 3B-active MoE (not cheaper), and spec-decode verify batches pay the expert-union cost per pass.

## 6. Derived-actionables ledger
| # | Draft task line | Owner handoff (lane) | Type | Stop/decision rule |
|---|---|---|---|---|
| B1 | Ingest this post as an intake entry and file a port-cost estimate for an Inkling 2 Mini llama.cpp arch (three new code paths) and its serving cost on CPU at IQ4_NL using the 3.06B-visit byte arithmetic above. | handoffs/active/model-evaluation-queue.md (supersedes the 2026-08-03 NO at `:676` for Mini only) | doc-only | Decide: if upstream llama.cpp already carries the arch, move to a bench box; if not, estimate port effort; stop when the estimate or the upstream status is filed. |
| B2 | Check the upstream llama.cpp tree for the Inkling 2 arch (graph file, KV/short-conv memory type) and record whether #32740-style FA bias is required. | handoffs/active/model-evaluation-queue.md | code-reading only | Done when the upstream commit/PR is named; this is non-compute. |
| B3 | Run `ggml-org/Inkling-2-Mini-GGUF:IQ4_NL` on CPU (q0-q2 quarter, short checkpointed window) for tok/s and a quality sanity check once an arch-capable build exists; compare bytes/token against the 1.7 GB estimate. | handoffs/active/model-evaluation-queue.md | compute (CPU row) | Question: does decode tok/s match the BW ceiling of a 3B-active MoE? Stop-on-answer after 3 interleaved pairs; futility if the build lacks the arch. |
| B4 | Treat the DSpark drafter comparison as part of the existing DSpark alpha-measurement plan, adding Inkling 2 Mini's 3-layer drafter as a candidate target/drafter pair once a build runs it. | handoffs/active/speculative-decoding.md (`:289`) | compute, gated on B1-B3 | Stop-on-futility if no GGUF drafter exists (the text mentions "draft weights present" but no GGUF drafter; NOT-FOUND-IN-SOURCE). |
| B5 | Record the loop KV structure (8 full + 40 SWA visits, per-visit caches) in the KV-compaction design notes as a test case for per-visit compaction. | handoffs/active/kv-cache-program.md | doc-only | Decide whether compaction applies to full visits only; no compute. |
| B6 | Examine the variable-loop research checkpoint as a decode-cost lever (1-2 passes cut bytes/token) when benchmarking B3. | handoffs/active/model-evaluation-queue.md | compute inside B3 | Same rule as B3. |
Declines: none.

## 7. Dive-surfaced sources not in research/intake_index.yaml
(grep for `inkling-2`, `Inkling 2`, `TML-d24`, `inkling2mini`: not present in the index; intake-941/942/955 are the earlier Inkling family.)
- Thinking Machines Lab model card `thinkingmachines/Inkling-2-Mini` (HF): would settle the licence, head_dim, full benchmark scores, which weights are NVFP4 vs MXFP8, and the drafter weights. Recommend ingest-and-dive.
- GGUF repos `ggml-org/Inkling-2-Mini-GGUF` and `ggml-org/TML-d24-varloop-research-GGUF`: would settle file sizes (hence bytes/token) and any arch metadata. Recommend ingest (metadata only).
- The upstream llama.cpp PR/commit adding the Inkling 2 arch (not named in the post): settles runnability; bears on intake-941/955. Recommend ingest-and-dive.
- SGLang DSPARK integration: settles how mid-loop hidden states are captured; bears on intake-737/738.

## 8. Contradiction / adversarial pass
- The post comes from a launch partner; benchmark claims are unquantified in the text. The comments contain only praise and one broken-link report (the browser-agent bucket link, fixed by the author); no technical rebuttal.
- Self-undercutting detail: 1M context is claimed, but the sole serving example uses 131,072.
- The "3B active" counts: arithmetic suggests it includes 48 visits, which makes the model no cheaper per token than a normal 3B-active MoE, while the post frames loops as capacity at small memory cost; "small memory cost" for the drafter is likewise unquantified.
- The sentence "Mini is much smaller than Inkling 2 Small" refers to a model not covered by our earlier entries (941 lists 975B/276B), so do not mix their figures.

## 9-10
read_depth: FULL for page.txt (the HF page including the three community comments); NOT read: model card, config.json, GGUF repos, SGLang code, the upstream llama.cpp PR. In-house: `git grep inkling` at eee3da8 for arch; intake-941/737 entries and handoff lines at lane head read.
lane_head: 860023c79706f437cdc027d186dbd1ce998b372d
artifact audit: clean
