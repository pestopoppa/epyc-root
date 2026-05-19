# δ-mem Reproduction + Frozen-Memory Topology Spike

**Status**: ready-to-claim (3-day reproduction → 3-week M.3 KV-Extension prototype → 6-week full δ-mem GGML port, gated)
**Created**: 2026-05-19 (post-cluster-deep-dive)
**Categories**: memory_augmented, context_management, ssm_hybrid
**Priority**: HIGH (released code + adapter checkpoint = cheapest first-week validation in the May 2026 batch)
**Depends on**: `log-linear-gated-deltanet-readiness.md`, `internal-kb-rag.md`, `context-folding-progressive.md`
**Companion completed handoff**: `orchestrator-conversation-management.md` (B1 User Modeling is the natural integration consumer)
**Source deep-dive**: [`/workspace/research/deep-dives/2026-05-19-frozen-memory-cluster.md`](../../research/deep-dives/2026-05-19-frozen-memory-cluster.md)

## Objective

Reproduce the δ-mem (intake-539, `github.com/declare-lab/delta-Mem`, CC-BY-4.0) 1.31× MemoryAgentBench / 1.20× LoCoMo claim on our hardware using the released Qwen3-4B-Instruct-2507 adapter checkpoint. If reproduction validates, prototype the **M.3 KV-Extension** topology from intake-568 (the topology with zero custom GGML ops required) against gemma4 worker_general, wired into the orchestrator's existing B1 User Modeling slot.

The intake-568 paper catalogues **six attachment patterns**; M.3 KV-Extension is the easiest llama.cpp integration path (just prepend learned K/V vectors to the cache at decode start).

## Falsified Baseline Finding

The deep-dive surfaced that our shipped B1 User Modeling — SQLite snapshot of user_conclude/user_profile injected into the system prompt per `orchestrator-conversation-management.md` (completed) — is **functionally M.1 Prefix**, which intake-568 measures as collapsing to ~0% at low capacity. The orchestrator's User Modeling slot is the natural integration target for δ-mem (online) or M.4 Hebbian (long-lag) sidecar memory.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-539 | δ-mem (arxiv:2605.12357) — delta-rule online associative memory | medium | worth_investigating (**released code + adapter**) |
| intake-568 | Trained Persistent Memory for Frozen Enc-Dec (arxiv:2603.16413) — 6 topologies | high | worth_investigating |

## Spike Plan (3 phases, gated)

### Phase 1 — δ-mem released-checkpoint reproduction (3 days, 1 nightshift compute)

**Goal**: validate the 1.31× MemoryAgentBench / 1.20× LoCoMo claim against our EPYC hardware using the released `github.com/declare-lab/delta-Mem` Qwen3-4B-Instruct-2507 adapter.

```bash
# In a throwaway venv (NOT in /workspace tree)
python3.11 -m venv /tmp/dmem-spike && source /tmp/dmem-spike/bin/activate
pip install torch transformers
git clone https://github.com/declare-lab/delta-Mem.git /tmp/delta-Mem
cd /tmp/delta-Mem
# Download Qwen3-4B-Instruct-2507 + the released δ-mem adapter
# (per repo README — verify checkpoint path before running)
python scripts/eval_memoryagentbench.py  # name TBD, check repo
python scripts/eval_locomo.py             # name TBD, check repo
```

**Gate criteria**:
1. Adapter loads cleanly against Qwen3-4B-Instruct-2507.
2. MemoryAgentBench delta vs unmodified backbone is within ±20% of the claimed 1.31× (i.e., 1.05×–1.57×).
3. LoCoMo delta within ±20% of 1.20× (i.e., 0.96×–1.44×).
4. CPU inference is tractable (decode tps within 2× of unmodified Qwen3-4B-Instruct-2507 baseline on EPYC).

**Dev cost**: ~1 day (setup + reproduction). **Compute cost**: 1 nightshift (~8 hours of CPU benchmarking, requires `feedback_no_concurrent_inference` per-bench approval).

**Failure mode**: if the adapter doesn't reproduce on Qwen3-4B-Instruct-2507 or the benchmarks regress relative to claims, kill the spike — intake-539's headline numbers are unreliable and the 6-topology survey (intake-568) doesn't have released code to fall back on.

### Phase 2 — M.3 KV-Extension prototype on gemma4 worker_general (3 weeks)

**Goal**: ship M.3 KV-Extension (intake-568's 4.2M-param topology, **no custom GGML ops needed**) as a sidecar memory module for gemma4-26B-A4B Q4_K_M MTP, wired into the orchestrator's existing B1 User Modeling data path (user_conclude / user_profile).

**Why M.3 first**: the other 5 topologies (M.1 Prefix, M.2 XAttn, M.4 Hebbian, M.5 Gated, M.6 Slot) require either backbone surgery, custom GGML ops, or both. M.3 just prepends learned K/V vectors to the cache at decode start.

**Steps**:
1. Train a small (4.2M-param) M.3 memory module on user_conclude/user_profile data harvested from existing orchestrator traces (consult `unified-trace-memory-service.md` for the harvest pipeline). Training is feasible on CPU at this scale.
2. Wire the learned K/V vectors into llama-server's prefix-cache layer (similar to the prefix-tree integration tracked in `llama-cpp-fork-rebase.md`).
3. A/B against the current SQLite-prompt-injection B1 implementation on a held-out conversation suite.

**Success criteria**: ≥1.2× recall on multi-session user-modeling tasks; zero degradation on single-session tasks.

**Dev cost**: ~3 weeks (1 week training + 1 week llama.cpp integration + 1 week A/B harness).

### Phase 3 — δ-mem full port + cross-session persistent bank (6 weeks, gated on Phase 2)

If Phase 2 passes, port δ-mem proper as a custom GGML op (delta-rule primitive is shared with the active `log-linear-gated-deltanet-readiness.md` handoff — kernel scaffolding can be reused). Combine with M.4-style Hebbian associative memory for long-lag retention.

**Dev cost**: ~6 weeks (3 weeks GGML op + 2 weeks orchestrator persistent-bank schema + 1 week A/B + integration).

## Non-Goals

- **Backbone fine-tuning**: all three phases are frozen-backbone. δ-mem is specifically a frozen-backbone-augmentation technique; do not re-open this scope.
- **Long-context replacement**: this is cross-session memory, not context-window extension. Use `yarn-context-extension-research.md` for the latter.

## Open Questions for User

1. **Phase 2 model target**: gemma4-26B-A4B worker_general is the natural choice (matches `project_worker_general_swap_2026_05_08`), but the released δ-mem adapter is for Qwen3-4B-Instruct-2507. We'd need to train an M.3 sidecar from scratch for gemma4 — OK to invest the training compute?
2. **B1 schema extension**: M.3 needs orchestrator changes to persist memory K/V across sessions (currently SQLite holds user_conclude/user_profile strings only). Extend the schema in this handoff or branch into `orchestrator-conversation-management.md`?
3. **Cross-handoff coordination**: δ-mem GGML op shares the delta-rule primitive with `log-linear-gated-deltanet-readiness.md`. Should Phase 3 be folded into that handoff once the spike validates, or kept standalone?

## References

- Deep-dive: `/workspace/research/deep-dives/2026-05-19-frozen-memory-cluster.md`
- δ-mem repo: `https://github.com/declare-lab/delta-Mem`
- δ-mem paper: `https://arxiv.org/abs/2605.12357`
- intake-568 paper: `https://arxiv.org/abs/2603.16413`
- Related handoffs: `log-linear-gated-deltanet-readiness.md`, `internal-kb-rag.md`, `context-folding-progressive.md`, `orchestrator-conversation-management.md` (completed)
