# Peer-Verifier Speculation — Scoping Spike

**Status**: SPIKE RESOLVED — **NO-GO-roofline + NO-GO-backend** (2026-05-27). Re-eval triggers documented in § Resolution below. Keep in active/ as a frozen reference for the re-eval conditions; do NOT promote to implementation handoff.
**Created**: 2026-05-27 (from research-intake of Fortytwo Network)
**Categories**: speculative_decoding, swarm_techniques, agent_architecture, hardware_optimization
**Priority**: LOW until the premise is verifiable; do NOT start before [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md) Phase-1 decision is in.
**Depends on**: nothing for scoping; implementation would depend on backend introspection of `LlamaServerBackend`.

## Premise — fragile, source-call-only

During the 2026-05-26 sales call with Ivan Nikitin (Fortytwo Network co-founder), the speaker described a "chunk-ranking" / "continuous ranking" pipeline distinct from their published peer-ranked-consensus paper (intake-615). The verbatim claims:

> "We're doing continuous ranking, where we rank chunk by chunk, and we're kind of like this[-] warm based on certain milestones, so this becomes closer to kind of like a continuous single shot generation rather than having multiple models producing their like independent attempts at the right response... we actually do call it single shot, because only give each model like one attempt at getting the right answer, but effectively under the hood, obviously this is like eight different models that did the work."

> "On vision tasks with chunk ranking. We recently achieved 16 parallel inferences... the performance hit was kind of negligible."

**Verification status (2026-05-27)**:
- The published arxiv:2510.24801 (intake-615) covers **strictly post-hoc pairwise ranking on full completions** — confirmed by direct ar5iv read. Chunk-ranking is **NOT in the paper**.
- No company blog post or research page describes chunk-ranking (verified — fortytwo.network/research returns 404 as of 2026-05-27).
- No code or technical disclosure.
- **The claim exists only as founder verbal pitch.**

This handoff is a spike to (a) enumerate plausible mechanical realizations and (b) determine whether the most plausible one could be prototyped on our backend if Fortytwo never publishes — i.e., whether the **idea** is harvestable independent of their specific implementation.

## Research Context

| Intake ID | Title | Relevance | Notes |
|---|---|---|---|
| intake-614 | Fortytwo Network homepage + sales-call intake | medium | Source of the unverified claim; see `contradicting_evidence:` field for the explicit gaps |
| intake-615 | arXiv:2510.24801 (the published Fortytwo paper) | medium | Confirms chunk-ranking is NOT in the published method |

## Hypothesis variants — how chunk-ranking might actually work

These are mechanical realizations consistent with the founder's verbal description. Ranked by plausibility on our specific hardware/backend.

### Variant 1: Peer-as-verifier speculation [most plausible]

- Mechanism: one "leader" model emits a chunk (e.g., 64–256 tokens, or up to a natural boundary — newline, end-of-tool-call, end of JSON object). The remaining N−1 peers do **not** generate — they **score** the chunk via a single prefix-forward pass (cheap). Scoring signal: mean log-prob, learned reward head, or pairwise "would-I-have-said-this" judgment against each peer's own 1-token continuation.
- Aggregation: BT-rank chunk scores (same algorithm as intake-615, applied to chunks instead of full completions).
- Branching: if peers agree, commit and continue with same leader. If not, switch leadership to the highest-scoring peer's continuation (which requires keeping all peers' KV caches warm — expensive in RAM, cheap in compute).
- **Why this is most plausible**: it is the only variant where "8 models effectively single-shot latency" is mechanically true. Verification cost (prefix forward) is dominated by leader generation cost.
- **Why this could be what Fortytwo built**: peer-ranked consensus on full completions (their published method) generalizes naturally to chunk granularity. Their stated optimal model band (27–31B dense, intake-614) is exactly the band where peer verification is cheap enough to amortize.

### Variant 2: Milestone-gated parallel beams

- Mechanism: all N models generate concurrently in their own KV caches. At natural milestones (every K tokens, or at structural boundaries), streams pause; latest chunks are exchanged and pairwise-ranked; loser streams reseed from the winner's chunk and resume.
- **Why less plausible**: this is multi-stream MCTS with hard pruning. The "16 parallel inferences on vision" line fits this shape if they run 16 streams from a smaller pool of underlying models with different sampling seeds. But the cost is N× concurrent generation, which contradicts the "negligible per-stream hit" claim.

### Variant 3: Token-budgeted continuation auction

- Mechanism: each peer gets a small token budget (~32 tokens), generates a continuation candidate in parallel, peers cross-score the candidates, winner is committed, cycle repeats.
- **Why less plausible at our scale**: scoring N candidates against each other every 32 tokens is O(N²·chunk) cost; only feasible with a tiny dedicated reward model rather than full forward passes through the candidate generators.

### Variant 4: Hidden-state-level aggregation [dark horse]

- Mechanism: don't rank text chunks at all — aggregate residual streams or logits across models at chunk boundaries (weighted average, or routed via a learned head).
- **Why dark horse**: technically "single shot" because output is one stream. Requires shared tokenizer and roughly-aligned representations. The intake-614 note that they band on 27–31B dense (Qwen/Gemma family) **does** make this feasible — Qwen2.5 / Qwen3.x share a tokenizer family.
- **Why not most plausible**: would not call this "ranking" — and Fortytwo's marketing language is explicitly ranking-flavored.

## Most-plausible-real candidate — first-cut design (Variant 1)

If we were to prototype Variant 1 on EPYC, the high-level shape:

1. **Substrate**: frontdoor `:8070` shared process (per memory `project_stack_consolidation_2026_05.md`, coder_escalation + worker_summarize already co-resident). This is the only place in our stack where multiple models live in one llama-server instance with comparable RAM budgets.
2. **Generation loop** (pseudocode):
   ```
   leader = select_initial_leader(peers)
   while not done:
       chunk = leader.generate_chunk(prefix, max_tokens=128 or until boundary)
       scores = {p: p.score_prefix(prefix + chunk) for p in peers}  # prefix forward, no generation
       winner = bradley_terry_rank(scores)
       if winner != leader:
           leader = winner   # KV cache swap — see open question below
       prefix += chunk
   ```
3. **Reuse**: Bradley-Terry implementation from autopilot's P17 (shared module across this handoff, [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md), and the autopilot scoring upgrade backlog).

## Backend gating questions — the actual go/no-go pivot

The spike's job is to answer these before any code is written:

1. **Does `LlamaServerBackend` (our production backend, NOT `openai.py`) expose mid-stream control to swap continuation sources?** Specifically, can a client request a partial generation, inspect logprobs / KV state, and then resume generation from the same prefix on a different role's KV cache? Probable answer: **no, not without a wrapper**. The orchestrator currently treats `llama-server` as a black-box generation endpoint.
2. **Can multiple roles share a prefix KV cache?** Per memory `feedback_same_model_roles_share_server.md`, same-GGUF roles share one process; different-GGUF roles do **not** share KV. Variant 1 needs N independent KV caches (one per peer) all advancing along the same prompt prefix. RAM cost: ~N × per-role KV size. Plausible on our 1.1TB host for small N (≤4) but a real constraint.
3. **What is the prefix-score endpoint?** llama-server has `/completion` (with `n_predict=0`?) and `/embedding`. We need to verify whether a prefix-only forward pass is exposed via the HTTP API or only via the C++ embedding. If only C++, the spike scope inflates to "write a forwarding endpoint in `epyc-llama`" — which is a multi-week thing, not a spike.
4. **Latency model**: is the "negligible hit" claim plausible given our throughput? Our worker_general @ 76.5 t/s solo. Adding N=3 peer prefix-scorers at ~ 100 t/s prefill each = ~3 t/s scoring overhead per chunk. For 128-token chunks that's ~38 t/s effective generation rate — a **50% degradation**, not negligible. This roofline alone may kill Variant 1 on EPYC even if the backend supports it.

## Falsification criterion / go-no-go gate

The spike completes when one of the following is in this file's status line:

- **GO**: backend exposes prefix-only forward; KV-cache cohabitation works for N≤4; latency roofline shows <30% per-stream regression at expected chunk sizes. → promote spike to design phase, write a real implementation handoff.
- **NO-GO — backend-blocked**: backend does not expose mid-stream control and adding it is multi-week. → close spike, fold the kill-decision into intake-614 notes, keep this handoff as a frozen reference for "if Fortytwo ever publishes, here's what we'd need."
- **NO-GO — roofline-blocked**: even if backend support existed, the latency math says >30% per-stream regression on our hardware. → close spike, same as above; record the roofline numbers so future re-evaluation against new hardware (e.g., DGX Spark) is cheap.

## Resolution — 2026-05-27 (NO-GO, two gates)

Spike resolved by direct inspection of `src/backends/llama_server.py` + protocol + concurrency-aware wrapper. Both go/no-go gates fail. Detailed findings below.

### Gate 1: Backend introspection — **NO-GO-backend**

**Question**: Does `LlamaServerBackend` expose mid-stream control to swap continuation source?

**Answer**: No, not without a wrapper. Three specific gaps:

1. **No prefix-score request mode.** The native `/completion` path is constructed in `LlamaServerBackend._build_payload` (`src/backends/llama_server.py:937-990`) with `n_predict = request.n_tokens` — there is no path that exposes `n_predict=0` + per-prompt-position log-probs as a callable request mode. The only existing log-probs hook is `n_probs=64` set conditionally for frontdoor when the `logit_probe` feature flag is enabled (line 985-988) — and that captures **first-generated-token** alternatives, not prompt-position log-probs.

2. **No mid-generation handoff.** `infer_stream` / `infer_stream_text` are one-shot stream-to-completion. There is no API surface to (a) pause an in-flight generation, (b) hand its current KV-cache state to a different role, (c) resume generation from that point under the different role. The closest primitives are `save_slot` / `restore_slot` (lines 1036-1080) which serialize KV state to disk — round-trip cost is dominated by file IO, not the swap math, and the disk format is **not portable across different GGUFs** (per memory `feedback_same_model_roles_share_server.md`, same-GGUF roles share one process; different-GGUF roles run in separate llama-server processes with incompatible slot files).

3. **OpenAI-compatible `/v1/completions` with `echo=true, logprobs=N`** is the standard llama-server way to get prompt-position log-probs in a single call. Our backend does not currently use this path for any role. Wiring it up would add ~30-50 LOC in `_build_payload` + result-parsing, plus a new `prefix_score_only: bool` field on `InferenceRequest` (src/backends/protocol.py:32-58). Not infeasible, but not "free" — and only solves the scoring half of the problem; the KV-state handoff between heterogeneous models remains unsolved.

**Verdict**: The "prefix-score" half is a ~1-day backend change. The "swap continuation source mid-stream across heterogeneous models" half is multi-week (probably requires changes in llama-server itself, not just our wrapper). Gate fails.

### Gate 2: Latency roofline — **NO-GO-roofline**

**Question**: On current EPYC config, would peer-verifier speculation deliver ≤30% per-stream regression?

**Answer**: No — the roofline math says 35–50% regression on the conservative model. Setup:

- Leader = gemma4-26B-A4B MTP, measured solo decode = **76.5 t/s** (per memory `project_worker_general_swap_2026_05_08`).
- Prefill rate for 26B Q4_K_M on EPYC NPS4 is in the ~200–300 t/s band (per memory `feedback_cpu_decode_bw_bound`; prefill is compute-bound, not BW-bound — uses more of the 460 GB/s aggregate but isn't the limiter at this scale).
- Chunk size: 128 tokens (per spike Variant 1 design).
- N = 3 peer verifiers.

**Sequential verification**:
- Leader generates 128 tokens at 76.5 t/s = **1.67 s** per chunk.
- Each peer verifier prefills `prefix + chunk` over the 128 new chunk tokens at ~250 t/s = **0.51 s** per peer.
- Total: 1.67 + 3 × 0.51 = **3.20 s** per chunk → **40 t/s effective**.
- Per-stream regression: (76.5 − 40) / 76.5 = **48%**. Above the 30% gate.

**Parallel verification (peers run concurrently on shared CPU)**:
- N peers compete for the same 96-thread CPU pool that leader is using. Per `project_concurrent_split_throughput` (4×48t → 32×6t = +44-58% aggregate), splitting CPU degrades per-stream throughput sub-linearly but degrades it.
- Conservative model: leader on 48 threads (~half throughput → ~38 t/s) + 3 peers on 16 threads each. Leader-bound chunk time = 128 / 38 = 3.37 s → **38 t/s effective**, **50% regression**.

**Either scheduling model breaches the 30% gate by 20–30 absolute points.** Mitigations exist (smaller peer verifiers, every-Nth-chunk verification, embedding-similarity scoring instead of log-probs) but each erodes the value proposition: a small verifier doesn't represent peer's true preferences; sparse verification loses the per-chunk swap signal; embedding similarity is not log-prob-equivalent.

### Re-evaluation triggers (when to revisit this spike)

Re-open this spike if **any** of the following change:

1. **Fortytwo publishes the chunk-ranking method.** A real paper / blog / code release would replace our hypothesis-driven Variant 1 reconstruction with the actual mechanism — possibly cheaper than our roofline assumes.
2. **DGX Spark (or other unified-memory hardware) arrives** (per memory `project_dgx_spark_target.md`). New hardware potentially changes the prefill-to-decode ratio (Spark's bandwidth/compute profile differs from EPYC NPS4). Re-do the roofline math at that point — the gate may flip.
3. **The orchestrator backend grows mid-stream-control primitives for an unrelated reason** (e.g., RAO+ReDel substrate work in P#42 of `master-handoff-index.md` adds sub-decision handoff). If those primitives exist as a side effect, the Gate-1 cost drops from "multi-week" to "wire it up", and only Gate-2 remains binding.
4. **Smaller specialist peers become the new norm** (e.g., the swarm-as-dataset-distillation pipeline in `swarm-dataset-distillation.md` produces 8B specialists). N=3 8B verifiers prefill faster (~400 t/s) than 26B verifiers, shrinking the per-chunk overhead from 0.51 s to ~0.32 s. Roofline at that point: 1.67 + 3 × 0.32 = 2.63 s → 49 t/s effective, **36% regression**. Still above the gate but much closer; combined with every-other-chunk verification (2x reduction) it lands at ~18% — under the gate.

### What was not investigated (deliberately out of scope for this spike)

- Variant 2/3/4 alternative mechanisms (milestone-gated beams, continuation auction, hidden-state aggregation). The spike committed to Variant 1 as the most-plausible-real form. If a re-eval trigger fires, re-pick the variant against the new constraints rather than testing all four blind.
- Production routing-mode design — that is DAR-6's territory in [`decision-aware-routing.md`](decision-aware-routing.md). DAR-6's post-hoc full-completion fanout is independently buildable; it is **not** blocked by this spike's negative result.

## Out-of-scope (explicit non-goals for this spike)

- **Not** implementing Variants 2, 3, or 4. Spike focuses on Variant 1 only because it's the most plausible-real form of the founder's claim.
- **Not** chasing Fortytwo for source code. They've explicitly stated swarm-inference is closed-source even though models are open (intake-614, ~17:00 in transcript).
- **Not** building a production routing mode. That is [`decision-aware-routing.md`](decision-aware-routing.md) DAR-6's territory and is the **post-hoc full-completion** form of the same idea (which is harvestable today, unlike this spike).

## Why a spike instead of an immediate kill

The user explicitly flagged this for handling. The two reasons it's worth a scoping doc rather than just deleting the founder claim:

1. The spike is **cheap** (~1 week of investigation, mostly reading our backend code, with no inference launches). The asymmetric payoff if Variant 1 is buildable is large: it would be a routing primitive we currently lack.
2. The spike's negative result is **also valuable** as a record. If we ever revisit Fortytwo's claims (e.g., they publish chunk-ranking, or DGX Spark arrives and the roofline changes), we want the prior NO-GO recorded with its specific gating conditions so the re-eval is fast.

## Cross-references

- **Source intakes**: intake-614 (Fortytwo Network with sales-call transcript), intake-615 (arxiv:2510.24801 — the OLD pipeline)
- **Sibling at request-time level**: [`decision-aware-routing.md`](decision-aware-routing.md) DAR-6 covers the **published** full-completion swarm-routing form. That one is buildable today; this spike covers the speculative chunk-level form.
- **Related but different**: `tree-speculation-numa-drafting.md`, `hsd-hierarchical-self-speculation.md`, `gemma4-mtp-drafter-evaluation.md` — all draft-target speculation (small drafter, large target). Peer-verifier speculation is **same-tier peer cross-verification** — different mechanism, do not merge.
- **Index entries**: registered in [`inference-acceleration-index.md`](inference-acceleration-index.md)

---

## Research Intake Update — 2026-05-27

Companion `/research-intake` run surfaced two papers relevant to this handoff.

### New Related Research

- **[intake-617] "Accelerating LLM Inference with Lossless Speculative Decoding for Heterogeneous Vocabularies"** (arxiv:2502.05202, ICML 2025 oral)
  - Relevance: Peer-verifier speculation across different model families is currently blocked by the tokenizer-compatibility wall (chapter 01: "exact tokenizer compatibility... DeepSeek-R1-Distill-Qwen-32B cannot use DeepSeek-R1-Distill-Qwen-1.5B"). Timor et al. removes this constraint losslessly via SLEM (string-level exact match, merged in HF Transformers) and TLI (token-level intersection). Directly unblocks peer-verifier setups where the peers have different vocabs.
  - Key technique: byte/string canonical form as shared intermediate; rejection sampling preserves target distribution.
  - Reported results: 2.8× over autoregressive; up to 37.5 t/s on Gemma-2-9b + vicuna-68m (CNN-DM).
  - Delta: was previously a hard "tokenizer must match" gate on this handoff's peer pool; now a soft "acceptance rate degrades with vocabulary overlap" trade-off.

- **[intake-042] "Cascade Speculative Drafting"** (arxiv:2312.11462, ICML 2024) — already in index as intake-042 (added 2026-03-14); duplicate detected during 2026-05-27 session, no new intake row created. Vertical cascade (recursive drafter chain, terminating in a Max-Gram statistical model) is a natural fit for peer-verifier setups where draft confidence varies across the peer pool.

See `gpu-drafter-mi200-investigation.md` § Research Intake Update for the full 9-entry intake batch.
