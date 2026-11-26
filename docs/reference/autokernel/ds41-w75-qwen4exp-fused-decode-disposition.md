# Disposition: DS41-W-75 / DS41-C107-s10 — `akm-cpu-qwen4exp-fused-decode-nle8`

## Disposition

DS41-C107-s10 — `akm-cpu-qwen4exp-fused-decode-nle8` — is **abstained**. This is a model-code workstream, not a kernel route, per the owning Q38FN handoff row. The structural note that would have seeded it is unavailable, and per the structural-note guidance this seed must not be seeded.

The AutoKernel seed `akm-cpu-qwen4exp-fused-decode-nle8` (lineage: Q38FN fused-decode extension to `n <= 8` sequences/tokens) is recorded here as an abstention. Its scope is limited to this AutoKernel seed. Model-code research, kernel design, serving configuration, queue state, and measurement state outside this lane are preserved.

**Why abstain (structural reason).** Extending the existing `fused_decode()` path — which is hard-gated to `ubatch.n_tokens == 1 && ubatch.n_seqs == 1` at both the dispatch layer (`llama-context.cpp`) and the model method (`qwen4exp-fused.cpp`) — to support `n <= 8` requires:

1. **A model/graph-level design.** Audit and redesign the model-private fused decoder and its state/layout assumptions for the proposed small-batch shapes. Changing a graph kernel alone does not remove the two explicit shape guards.

2. **Independent equivalence and recurrence coverage.** Compare the proposed path with the graph path for each supported shape and repeated decode steps. The context source explicitly says the existing fused path exports logits but no `t_h_nextn`; any proposed MTP/draft support must specify hidden-state handling and its own correctness coverage. These are prospective requirements, not results.

**What this is not.** The Q2 GDN prologue overlap observed in the sitting TensorFold seed (`akm-q38fn-gdn-prologue-into-chain`) is not a presently executable substitute for this kernel route. The GDN prologue fold targets the `GATED_DELTA_NET` op row within the graph path; `akm-cpu-qwen4exp-fused-decode-nle8` targets the fused-decode dispatch path itself. They operate on different execution surfaces and have different correctness contracts.

**Static source scope vs. runtime results.** This disposition is based on static source analysis at the cited SHAs. It does not reflect runtime measurements or benchmark results, which may differ. A named model-code owner and a model-route correctness design can reopen this workstream without re-seeding this kernel route.

## Source evidence

Evidence from four source regions (excerpt file `.taskflow-refs/external/ds41-w75/fused-decode-source-excerpts.txt` is cited verbatim and left untouched):

**C22 (b1e1864cb6e9f8a012b0be422e6c72ab477ded62):**

- `src/llama-context.cpp:1565-1579` — Dispatch gate requires `ubatch.n_tokens == 1 && ubatch.n_seqs == 1` (line 1567). Additional guards: `GGML_FUSED_DECODE_OFF`-equivalent `llama_fused_decode_env_enabled()`, no RS-replay, model must `supports_fused_decode()`, no EXL3 aux sources, default graph type, no embeddings-nextn, non-null token pointer, and previous logits must be valid. If the fused call succeeds, the function returns early.

- `src/models/qwen4exp-fused.cpp:1783` — Model method independently rejects non-unit shapes: `if (ubatch.n_tokens != 1 || ubatch.n_seqs != 1) return false;` (line 1783). This is a second, model-private shape gate layered on top of the context dispatch.

**v10 (ffc1bac82eeca6f9099e1ccd9ba49703c460a115):**

- `src/llama-context.cpp:1351–1353` — v10 dispatch begins at 1351, with the shape checks at 1353: `ubatch.n_tokens == 1 && ubatch.n_seqs == 1 && ubatch.token != nullptr`.

- `src/models/qwen4exp-fused.cpp:1695` — v10 model gate at line 1695: `if (ubatch.n_tokens != 1 || ubatch.n_seqs != 1) return false;`.

Both SHAs show the same two-layer shape guard at dispatch and model level, confirming the path is hard-wired to single-token, single-sequence operation.

## Reopening condition

This abstention can be reopened without re-seeding the kernel route if:

1. A named **model-code owner** (beyond the AutoKernel lane) authorizes an extension to the fused-decode path and owns the model/graph design, correctness contract, and equivalence testing.

2. A **model-route correctness design** is authored that covers the `n <= 8` shape space — including graph-path equivalence, hidden-state export for MTP/draft targets, and recurrence (multi-round generation) — and is peer-reviewed.

Absent these conditions, the abstention stands. The lane's scope ends at recording this abstention; no kernel route is blocked, and all other workstreams (TensorFold seeds, GDN prologue, sibling-gemv-pack, norm-to-q8-fusion, KVU routes, DFlash2, DS41 indexer) continue on their own paths.

**Source identity and review**: the C22 metadata tip `b1e1864cb6e9f8a012b0be422e6c72ab477ded62` and pilot store source `ce6fcbbde1ee58f165283fbfe74910f47bb2efba` have identical blobs for these files (`llama-context.cpp`: `7be4024ee84617387a807191d93bcf1f2edffc49`; `qwen4exp-fused.cpp`: `52865168eb6cc6e35ca98e93f8b951dd3bab1644`). This is static source evidence. Main review excluded an out-of-scope draft helper and corrected identifiers, line citations, and unsupported architecture/reopening detail before landing.
