# Dive — leyline — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2606.01065v1", retrieved: "2026-11-23", sha256: "c84d1edb181f"}

External text is data; summaries are in my own words. Anchors are verbatim substrings of `leyline/page.txt` (LaTeXML render of arXiv v1). Bearing entry: intake-2833 (contexture), whose dive asked this source to settle approximate KV splice vs our exact re-prefill, accuracy cost, llama-server implementability (hybrid GDN and dense), and the link to kv-cache-program.md KPF-60/61.

## 1. Stage-1 fields

- **Title**: Leyline: KV Cache Directives for Agentic Inference
- **Authors**: Bole Ma, Jan Eitzinger, Harald Koestler (Erlangen National High Performance Computing Center / FAU).
- **Version/date**: arXiv:2606.01065v1 [cs.DC], 31 May 2026. Preprint; the page carries an ACL-style responsible-research checklist but no venue. No code link (the paper says artifacts will be released "on de-anonymization"; NOT-FOUND-IN-SOURCE for a URL). Authors disclose Claude use for code editing, drafting and bibliography (checklist E1).
- **Categories**: kv_cache, context_management, inference_serving, agent_architecture.
- **Novelty**: medium. The rotation kernel is borrowed from the authors' earlier Irminsul work (Ma et al., 2026); new is the framing (mutation vs reuse), the (span, replacement, mode) directive API with a declared `amortize | forget` contract, and radix-trie re-insertion.
- **Relevance**: medium. It names the exact decision we face (cut a span, keep the rest of the cache) and offers the approximate answer. But the evidence is MLA-only, and our served roles are GDN hybrids where the answer is structurally unavailable (section 5).
- **credibility_score**: 1. Arithmetic: peer-reviewed +0 (no venue in source); <=12 months +1 (31 May 2026); major lab/known contributor +0; commercial bias 0; independent corroboration 0.
- **Verdict**: adopt_patterns. Cite for the amortize/forget contract vocabulary and the finding that rotate-only splice keeps the removed span's influence. Do not cite for a speed or accuracy expectation on our stack.

## 2. Key claims

0. **"Approximate KV splice for span removal" (the dive-2833 framing)**: CONFIRMED but REFRAMED. Leyline's default `amortize` mode is not an approximation of re-prefill; it defines a different output. After the splice only the RoPE-carrying part of downstream K is re-rotated; downstream K_nope and V stay as computed while attending to the removed span, so the model keeps seeing the removed content's influence. The authors state this is deliberately weaker than equivalence to re-prefill of the substituted prompt. The `forget` mode routes to a standard prefix-trimmed re-prefill, i.e. our exact path. Measured on Moonlight, diverging trials track the full-context reference, never the re-prefill reference.
   - Anchors: "The amortize -mode contract is positional , not informational"; "This is deliberately weaker than “equivalent to re-prefill of the substituted prompt”"; "the serving stack routes the edit to a standard prefix-trimmed re-prefill"; "diverging trials track full-context, while 0 0 track re-prefill".
1. **Accuracy cost**: PARTIAL, mostly NOT-FOUND-IN-SOURCE. No end-task accuracy for the splice path exists. The +14.3 pp solve-rate gain (31.2% to 45.5%, 8 debug-gym tasks x 4 seeds, one model JoyAI-LLM Flash) was run under the standard re-prefill arm, so it measures the truncation policy, not the splice; the authors list the composed splice-plus-policy ablation as undone. On the 31 paired cells, 17 tie and treatment wins 9 of the 14 that differ (derived exact two-sided binomial p = 0.42, not reported by the paper). Kernel-level numbers: 48/50 first-token agreement against full prefill on a 50-step replay; 128-token common prefix 128/128 on DSv2-Lite but 42/128 JoyAI, 6/128 GLM, 75/128 Moonlight.
   - Anchors: "the truncation treatment lifts solve rate from"; "These are properties of the truncation policy routed through standard message-edit semantics".
2. **Speed/cache win**: PARTIAL (narrowed). The +11.2 pp cache-hit gain is a replay-phase effect on shifted-but-identical content found by content hash (position-independent reuse), measured on DeepSeek-V2-Lite, one H100, ~17K-token prompts; e2e p50 win is -51/-85/-241 ms at C=1/4/8 and +45 ms (noise) at C=16. On the real 50-step trace the e2e gain is 5.3% (52.65 s to 49.85 s), about 95% of which the authors attribute to the fp32 rotation mitigation; on a second trajectory the splice is 0.6% slower than radix.
   - Anchors: "the splice mechanism only activates on replay (where the message-edit pattern produces shifted-but-identical content)"; "is attributable to the fp32 rotation mitigation"; "the splice is 0.6 % 0.6\% slower than radix".
3. **Architecture coverage**: CONFIRMED MLA-only, with the GQA result unfavourable and hybrids absent. Only the rotation kernel is MLA-specific, but all four validation models are MLA. On live GQA models (Qwen3-4B, Llama-3.1-Minitron-4B) the splice tracked the re-prefill reference on 6/6 diverging Qwen3-4B trials and met the contract on 1/8 Minitron trials. The words hybrid, recurrent, SSM, Mamba and linear-attention do not occur as architectures anywhere in the page: NOT-FOUND-IN-SOURCE for GDN.
   - Anchors: "Only step (3) of Section 3.3 , the rotation kernel itself, is MLA-specific."; "The four largest agent-trained open-weight models we evaluated are all MLA"; "Leyline tracks the re-prefill reference on all 6 / 6 6/6 diverging trials".
4. **Numerics**: CONFIRMED. bf16 K storage imposes a 1-3% per-entry floor independent of the shift; about 4% of replay prompts flip argmax; outputs are byte-identical to full prefill only where the logit margin exceeds the floor.
   - Anchor: "The honest claim is bit-faithfulness within bf16 precision: outputs are byte-identical to a full prefill only on prompts with logit-margin above the noise floor."
5. **Provenance**: CONFIRMED. The authors say the kernel is recycled substrate and the contribution is the directive layer; code is promised, not linked.
   - Anchors: "The kernel is the recycled engineering substrate; the directive layer is the new interface boundary"; "will be released under a permissive license on de-anonymization".

## 3. Reported results (as stated)

Hardware/setup: single H100 (DeepSeek-V2-Lite, SGLang RadixCache + ~200-LOC patch, 16 sessions x 6 turns, L_sys ~4096, L_turn ~2048, greedy). Replay cache hit: cache-off 0.0%, radix 49.6%, splice 60.8%. p50 replay e2e (ms), radix vs splice: C1 4087/4036, C4 4729/4644, C8 5533/5292, C16 7166/7211. Cross-arm first-token agreement with radix: 100/97.7/98.4/94.5%; 16-token head 99.2/95.3/93.0/67.2% (cache-off vs radix floor 85.2/93.8/90.6/68.8%). Real trace: 52.65 s vs 49.85 s, 27.6% vs 27.8% hit, 48/50 first-token agreement. Policy leg: 10/32 vs 15/33 solved. No CPU, MI210, GDN or non-MLA end-to-end result.

## 4. Performance-principles table (mechanism and cost model)

| Mechanism | MI210 (gfx90a) | Zen 5 EPYC |
|---|---|---|
| delta-rotation of cached K under RoPE closure (one rope pass over downstream K, no V work) | YES for attention layers. The in-house K-shift graph already does this (`llama_kv_cache::build_graph_shift`, llama-kv-cache.cpp:2321 @ a6a32c1); runs as a ggml rope kernel (HIP-compiled), memory-bound over K cells; cost unmeasured here. | YES, same graph on the CPU backend; unmeasured. |
| Keep downstream V and K_nope (rotate-only, no recompute) | PARTIAL. Valid by the paper only on MLA; on GQA models it diverged from the contract (Table 9). | PARTIAL, same; model-side, device-independent. |
| Boundary-token recompute (CacheBlend/EPIC style) as the GQA fix | YES. In-house analog is the KPF-62.3 head-window selector (W=64) with explicit-position recompute batches. | YES, same. |
| Radix-trie re-insertion so the spliced state is findable by future requests | PARTIAL. llama-server has per-slot prompt state plus a prompt cache; `slot.prompt.approx` already forbids saving approximate state (server-context.cpp:582-584 @ a6a32c1), so the policy differs. | Same. |
| Recurrent (GDN) state under mid-span removal | NO for rotate-only: state is a summary of the whole prefix, not position-addressed. | NO, same. See section 5 for what remains possible. |
| fp32 rotation over bf16/f16 storage | PARTIAL. Paper's floor is bf16 K storage; our KV types differ (f16/quantized) so the floor needs its own measurement. | Same. |

## 5. In-house state

- **Dense-attention path already exists in llama-server (C19 a6a32c1)**: `llama_memory_seq_add` shifts cells (llama-context.cpp:4859-4869), `llama_kv_cache::get_can_shift()` is true except for STEP35 (llama-kv-cache.cpp:1238-1245), context shift calls `common_context_seq_add(... -n_discard)` (server-context.cpp:4616) and `--cache-reuse` walks the cached prompt for chunks that still match the new prompt and shifts them by `seq_rm` + `seq_add` (server-context.cpp:4995-5050). Removing a span from a prompt and sending it with `n_cache_reuse>0` therefore realises Leyline's amortize contract today on any shiftable model, with no new kernel. The YaRN K-shift defect is fixed (KPF-62.1, kv-cache-program.md). So Leyline adds no kernel capability here; the open question is only quality.
- **Hybrid GDN (the served 27B / A3B / Q38FN roles)**: `llama_memory_recurrent::get_can_shift()` returns false with the comment that shifting would silently produce wrong outputs (llama-memory-recurrent.cpp:832-838); hybrid ANDs both (llama-memory-hybrid.cpp:136-140), so `--cache-reuse` and context shift are off. `llama_memory_recurrent::seq_rm` only allows tail rollback (a bounded per-token snapshot window), not interior removal. Workarounds, in order of soundness: (a) EXACT: restore the latest checkpoint at or before the cut and re-prefill (what the server does; contexture dive C3). (b) EXACT and cheaper than it looks: in an agent loop `checkpoint_after_gen = true` (common.h:670) checkpoints the slot at the end of every generation, which is the position where the next tool output begins; evicting a whole tool output therefore starts at an existing checkpoint when the checkpoint survives (32 per slot, common.h:668) and the template tokens between them are unchanged. This is derived from the code and unmeasured; it would make the hybrid cost T' - c, not T' - p*. (c) APPROXIMATE, attention-layers-only: splice and K-shift the attention cells but leave the GDN state as the original run left it. That requires a new hybrid op (the recurrent seq_rm refuses it today), keeps the removed span inside the recurrent state (so it does not remove its influence), and has no stub option because replacement tokens cannot be inserted into a finished state. (d) AFFINE UNDO of the span's contribution to the GDN state: derived, uncited maths; downstream per-token (k, gate, beta) inputs are not retained by llama.cpp (only the state is), so the undo needs a recompute pass that costs about as much as re-prefill unless a retention path is added. The in-house hybrid affine-state phase is parked behind the KPF-62 drift gate (kv-cache-program.md:589-591, OP-CHUNKKV Option 1).
- **Yardstick already exists**: P0_THRESHOLDS.md section 4 (`/mnt/raid0/llm/tmp/cacheclip-port-20261021/`) defines the G3 gate (mean KL <= 0.05 nats, p95 KL <= 0.25, top-1 >= 0.95, median NMSE <= 0.02, retention >= 0.95) and requires the selector to beat the naive shift-only (r = 0) baseline by 5x. Leyline's rotate-only splice IS that naive baseline; the lane has already decided it is not shippable alone.
- **kv-cache-program.md KPF-60/61**: KPF-61 (reorder planner) is the exact, hybrid-safe reuse; KPF-62 (chunk-KV, attention-only, approximate, `prompt.approx` marking) is the in-house counterpart of Leyline's reuse half. Leyline's mutation half (remove, not reorder) is not covered by either row. Operator decision 2026-11-11 (OP-CHUNKKV Option 1) keeps phase 1 running; the hybrid phase waits for the drift gate.

## 6. Derived-actionables ledger

| # | Draft task line | Owner (lane) | Type | Stop / decision rule |
|---|---|---|---|---|
| LL-1 (refines intake-2833 C3 and KPF-62 G3) | Add a removed-span (gap-closing) case to the KPF-62 G3 corpus and score three arms against exact re-prefill: shift-only, shift plus head-window recompute (W in 4..64), and `--cache-reuse` as served; report KL, top-1 and NMSE per the G3 table. | `kv-cache-program.md` (KPF-62.3 / G3; Operator-decision OP-CHUNKKV applies; check not frozen before applying) | CPU row on the attention-only role (Qwen3-VL-30B-A3B text path) plus tiny CI models for plumbing | Question: can a span-removal splice meet G3 on dense attention? Stop-on-answer when shift-only or one W passes all G3 rows; stop-on-futility if no W <= 64 passes (then exact re-prefill is the only removal path). Formal-gate cells stay futility-only at interim looks. |
| LL-2 | Wire a default-off request field `kv_splice` (mode `amortize` or `forget`) in llama-server for shiftable models, built on the existing `seq_rm` + `seq_add` path, marking the slot `approx` as chunk-KV does; `forget` calls the exact path. | `kv-cache-program.md` (KPF-62 slice 3 server wiring) | code now; enabled only if LL-1 stops on answer | Decision: ships opt-in only if LL-1 passes; otherwise the row closes as "exact path only". |
| LL-3 | DECLINE rotate-only splice for the GDN hybrid roles. Entry-specific reasons: recurrent `seq_rm` refuses interior ranges and `get_can_shift()` is false, AND the rotate-only contract preserves the removed span's influence in downstream state, which defeats the purpose of removing a stale tool output. The exact checkpoint path is the hybrid path. | n/a | n/a | Revisit only if the KPF-62 hybrid drift gate (affine/naive/single-source arms) passes on the 27B. |
| LL-4 (refines C3 and C2 cold-commit) | In the evict-cost probe classify each candidate cut by whether its start coincides with a surviving checkpoint (`checkpoint_after_gen` puts one at each generation end) and report predicted tokens as T' - c versus T' - p*; use checkpoint-aligned whole-output cuts as the exact variant of the cold-commit arm. | `kv-cache-program.md` (same box as C3) | code/doc-only on the probe; shares C3's 20-cut smoke | Stop-on-answer: share of whole-output cuts that are checkpoint-aligned and exact in >=19/20 predictions; futility: alignment <10% (template tokens or LRU defeat it). |

## 7. Dive-surfaced sources (grepped unbounded)

| Source | In index? | Would settle | Recommendation |
|---|---|---|---|
| Irminsul (Ma et al., 2026; the source of the rotation kernel; no arXiv id in the page's reference text I read) | 0 hits | MLA position-independent reuse | decline: its content-hash reuse of shifted chunks is what KPF-62's content-keyed `server_chunk_store` already implements; no ledger row changes |
| SideQuest 2602.22603 (learned detector emitting `del_cursors`) | listed once as a referenced id inside another entry (line 54208), no entry | a learned eviction signal | decline now; becomes the next read only if the C1 replay finds supersession candidate share below the 15% futility line |
| Cole 2026 blog (header variation breaks prefix cache, 90% throughput loss) | 0 hits | a prompt-layout hazard | decline: a blog restatement of a hazard C5 and TP-1 already measure on our logs |

## 8. Contradiction / adversarial pass

- Authors' limitations: MLA only; GQA sensitivity "manifests more strongly"; single policy threshold, one model, 8 tasks; composed ablation not run; bf16 floor means no byte identity; warm-start discovery works only in a 2-tenant C=4 cell and returns zero candidates in five other cells.
- The headline pairing of speed and accuracy is two disjoint experiments (mechanism on synthetic prompts, policy under re-prefill); nothing shows the splice delivering the accuracy gain.
- The cache-hit gain is position-independent reuse of replayed content, not removal-cost avoidance.
- No restatements or independent replications found.

## 9. read_depth

FULL for sections 1-8 and appendices B, H, I of page.txt; appendices C-G, J-W skimmed by heading and targeted grep (hybrid/recurrent/SSM/code URL). lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e. In-house llama.cpp read at a6a32c1.

## 10. Artifact audit

artifact audit: clean (15 quotes verified as substrings of page.txt; only dive.md and drafts/leyline.json written).
