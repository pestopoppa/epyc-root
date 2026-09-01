# GLM-5.3-Flash Evaluation (glm5next)

**Status**: READY — artifact on disk, unowned until this handoff; arch-support audit is the gate
**Created**: 2026-08-31 (spun out of the OP-8 KILL ruling; inherits the GLM-MoE-DSA findings)
**Priority**: MEDIUM — one of the two operator-named novel-under-test models (with qwen3.8-next-flash)
**Categories**: inference_serving, local_inference, kernel_architecture
**Workstream**: Inference Acceleration
**Parent index**: [`inference-research-index.md`](inference-research-index.md) (row INF-69)
**Related**:
- [`../completed/glm51-reap-cpu-evaluation.md`](../completed/glm51-reap-cpu-evaluation.md) — the
  GLM-5.2 evaluation (KILLED 2026-08-31, artifact deleted): the evidence record this handoff inherits from
- [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) — owns the generic DSA
  D2/D3 sparse-attention profiling gates (do not duplicate them here)
- [`tree-draft-forward-port-plan.md`](tree-draft-forward-port-plan.md) — native GLM MTP head port scoping

## Artifact identity

| Field | Value |
|---|---|
| Local path | `/mnt/raid0/llm/models/unsloth/GLM-5.3-Flash-GGUF/UD-Q4_K_XL/` (6 shards) |
| Architecture | **`glm5next`** — NEW arch, not `glm-dsa`; 288×10B experts (`general.size_label`) |
| DSA surface | `glm5next.attention.indexer.{head_count,key_length,top_k,kpool}` — same Lightning-Indexer family, plus a new `kpool` field |
| MTP surface | `glm5next.nextn_predict_layers` present |

## Inherited findings (from the GLM-5.2 evaluation — verify each against glm5next before relying on it)

1. **DSA-DENSE-MASK**: on this fork the generic DSA path computes the indexer + top-k but final
   attention still runs over FULL KV with a mask (`build_attn` constructs `kq_mask_top_k` over full
   KV length; no sparse gather). Any glm5next support inherits this until the sparse-gather gate in
   `llama-cpp-dsa-contribution.md` lands. Never claim long-context sparse-compute value without it.
2. **`indexer_top_k` is the final-attention KV selection cap, and an under-sized cap CORRUPTS
   output** once prompt length exceeds it (GLM-5.2: exact-output fails beyond the cap; safe policy
   was next-power-of-two ≥ prompt tokens). glm5next adds `kpool` — re-derive the semantics, do not
   assume the 5.2 thresholds.
3. **NextN/MTP**: GLM GGUFs preserve the NextN tail block but the fork's GLM archs skip those
   tensors and never dispatch `LLM_GRAPH_TYPE_DECODER_MTP`; the smallest credible port is Qwen-style
   tail-tensor loading + a `DECODER_MTP` graph (not a flag flip). Applies if glm5next's MTP is wanted.
4. **Wiring precedent**: experimental-v7 `3dee86a5a` is the worked example of wiring a GLM arch into
   `llama_kv_cache_dsa` + the DeepSeek32 DSA graph (incl. forced indexer Hadamard tensors and the
   arch tests that validated it).
5. **Evidence contract** for any long-output/throughput/quality probe: streaming progress, retained
   trace logs, server-log timing extraction, minimum completion-token floor; record every quality
   claim with `(prompt tokens, chosen indexer_top_k)` together.

## Tasks

- [ ] T0 — **Arch-support audit**: does any tree on this host load `glm5next` (production v9: no —
  frozen pre-arch; experimental/champion: check; upstream llama.cpp: check for a landed PR)? Output:
  the backport-or-wait decision, same shape as the qwen4exp bringup.
- [ ] T1 — Load + short-context coherence smoke on the chosen tree (abort on repetition loops),
  CPU-only, canonical env; record `(arch, indexer defaults, kpool)` from the load log.
- [ ] T2 — DSA-path disposition for glm5next: DENSE-MASK vs sparse (expect DENSE-MASK per finding 1);
  `indexer_top_k`/`kpool` semantics probe BEFORE any quality run (finding 2).
- [ ] T3 — Throughput baseline at the canonical recipe (interleave + no-mmap, t48/t64, r5) —
  observation-grade first; codified attestation only if it becomes a serving candidate.
- [ ] T4 — Quality/role fit per the standard suites; GO / WAIT / KILL disposition with the disk-retention
  decision (artifact is in the novel-under-test keep bucket until this verdict).

## Constraints

- Inference is operator-gated per standing policy (region claim; no concurrent-inference assumptions).
- Do NOT add a `model_registry.yaml` role without operator approval.
- Any DSA correctness finding also updates `llama-cpp-dsa-contribution.md` (single owner of the
  generic gates).
