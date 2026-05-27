# Strand-Rust-Coder-14B — RustEvo2 Independent Verification

**Status**: NEW 2026-05-27 — actionable as soon as approved for launch (single standalone bench)
**Created**: 2026-05-27 (from research-intake of Fortytwo Network)
**Categories**: benchmark_methodology, training_distillation, local_inference
**Priority**: MEDIUM — gate task; cheap (~half day); blocks higher-priority [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md)
**Depends on**: nothing
**Blocks**: [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md) (Phase 1 = this handoff's exit signal)

## Objective

Independently verify the Fortytwo Network's two founder-call claims about [Strand-Rust-Coder-14B-v1](https://huggingface.co/Fortytwo-Network/Strand-Rust-Coder-14B-v1) (intake-616):

1. **"#1 on RustEvo2"** — claimed in the 2026-05-26 sales call with Ivan Nikitin; not on the model card; not in their arxiv paper (intake-615).
2. **"Beats GPT-5 Codex on Rust" after "simplest possible fine-tune" of Qwen2.5-Coder-14B-Instruct on a swarm-generated 191k-sample dataset in 8 days** — same source.

If the #1 claim holds, that is the strongest external evidence we'd have that the **swarm-as-dataset-generator** pipeline (the actual technique we'd consider harvesting in [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md)) produces deployable artifacts on the first try. If the model lands mid-pack, the founder's claim is marketing and the dataset-distillation pipeline is not worth our compute.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-614 | Fortytwo Network homepage + sales-call intake | medium | worth_investigating |
| intake-615 | arXiv:2510.24801 — "Fortytwo: Swarm Inference with Peer-Ranked Consensus" | medium | worth_investigating |
| intake-616 | Strand-Rust-Coder-14B-v1-GGUF (mradermacher mirror) | medium | worth_investigating |

## Why a verification handoff and not just a bench command

- The result is a **gate** for a multi-week investment (`swarm-dataset-distillation.md`). It deserves a stable filename so the gate decision can be cited from both intake-616 and the dataset-distillation handoff.
- The RustEvo2 leaderboard methodology is not yet inspected — this handoff also captures whether the benchmark itself is something we want to anchor future Rust-capability claims against.
- The artifact is a single eval log; the handoff serves as the place to attach it (Phase 4 below).

## Phased Plan

### Phase A — Acquisition & sanity checks [~1–2 hours, no inference]

#### A-1: Download the GGUF

- Source: `mradermacher/Strand-Rust-Coder-14B-v1-GGUF`, quant **Q4_K_M** (~8.99 GB) — our standard band ([`feedback_psplit_default.md`](../../...nope) cf. memory `project_coder_quant_decision.md`).
- Storage: `/mnt/raid0/llm/models/` (cf. user memory `user_hardware.md` 3.7TB raid0).
- Sanity: SHA, file size, gguf header (`gguf_dump.py`) to confirm Qwen2.5 14B arch and chat template presence.

#### A-2: Locate the RustEvo2 benchmark and its leaderboard

- Find the official repo / leaderboard for **RustEvo2** (no internal reference in our tree). Resolve:
  - The eval harness (Python? Rust?).
  - The pass@k metric definitions.
  - The current leaderboard top-K and whether GPT-5 Codex / Claude / Gemini results are listed there or claimed separately.
  - Whether the harness supports OpenAI-compatible `/v1/completions` (works with `llama-server`) or expects a specific provider SDK.
- If the harness only accepts a provider SDK, write a thin adapter that proxies to `llama-server` on a chosen port (do **NOT** wire to the production stack — use an isolated dev port).

#### A-3: Pick comparison baselines (must include all three)

1. **Base model**: Qwen2.5-Coder-14B-Instruct Q4_K_M (apples-to-apples — isolates the fine-tune delta).
2. **Production worker_general**: gemma4-26B-A4B MTP Q4_K_M (sanity — confirms our current general coder is or isn't a Rust gap).
3. **Frontier baseline from the RustEvo2 leaderboard** (whatever the leaderboard reports for GPT-5 Codex / Claude / Gemini).

Strand-Rust-Coder-14B Q4_K_M is the model under test.

### Phase B — Single-instance bench (USER APPROVAL REQUIRED)

Per memory `feedback_no_concurrent_inference.md`: never launch llama-server/cli/bench on EPYC without explicit per-run approval. This handoff **does not authorize** any inference; the agent picking it up must request approval before launching.

#### B-1: Launch protocol (when approved)

- **No autopilot, no parallel agents.** Single standalone `llama-server` instance.
- Canonical CPU baseline per `feedback_canonical_baseline_protocol.md`: `taskset -c 0-95 -t 96 -fa 1`, no `--numa distribute`, no env overrides.
- OMP env stack per `feedback_omp_env_stack_required.md`: `OMP_PROC_BIND=spread`, `OMP_PLACES=cores`, `OMP_WAIT_POLICY=active`, `numactl --interleave=all`.
- Drop-caches + throttle check per `feedback_host_throttle_check.md` before launch.
- Log full output to a file then `cat` (per `feedback_never_pipe_llama_output.md`).

#### B-2: Bench order (sequential — one model loaded at a time)

1. Strand-Rust-Coder-14B-v1-Q4_K_M → run full RustEvo2 → save log + scores.
2. Stop server. Drop caches. Re-warm with `numactl --interleave` per `feedback_drop_caches_numa_eviction.md`.
3. Qwen2.5-Coder-14B-Instruct Q4_K_M → full RustEvo2 → save log + scores.
4. Stop server. Drop caches. Re-warm.
5. gemma4-26B-A4B MTP Q4_K_M → full RustEvo2 → save log + scores.

Frontier numbers come from the leaderboard, not from local inference.

### Phase C — Analysis & disposition

#### C-1: Score table

Produce a single markdown table:

| Model | RustEvo2 pass@1 | pass@10 | Rank on leaderboard (if listed) | Delta vs base |
|---|---|---|---|---|

#### C-2: Decision matrix

| Outcome | Action |
|---|---|
| Strand-Rust-Coder-14B at **#1** AND clearly beats Qwen2.5-Coder-14B-Instruct base by ≥10pp pass@1 | **STRONG GO** for [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md). The swarm-as-dataset-generator pipeline produces deployable artifacts on first try. |
| Top-3 AND beats base by ≥5pp | **QUALIFIED GO** — proceed with `swarm-dataset-distillation.md` but tighten its Phase-3 ranking gate; the founder claim was overstated but pipeline is real. |
| Top-10 OR beats base by <5pp | **WEAK SIGNAL** — pause `swarm-dataset-distillation.md`. The "8 days, simplest fine-tune" claim is doing heavy lifting. Re-evaluate when Fortytwo publishes pipeline details. |
| Below top-10 OR fails to beat base | **NO-GO** — fold the kill-decision back into intake-614 / intake-616 notes; the dataset-distillation handoff is not worth pursuing on Fortytwo's evidence. |

#### C-3: Side observation worth recording

Note whether **Qwen2.5-Coder-14B-Instruct itself** outperforms our gemma4-26B-A4B worker on Rust. If yes, that's an independent finding worth raising as a coder-pool-composition note (currently we don't carry a Rust specialist; if Rust shows up in our workloads, the cheap path is the base 14B, not necessarily the Strand fine-tune).

## Exit criteria

- One eval log per model in `progress/2026-MM/2026-MM-DD-rustevo2/` (artefacts directory created at run time).
- Score table appended to this handoff at the end.
- A one-line disposition pushed back into intake-616's `notes:` field via index update, citing this handoff.
- If GO: update [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md) status from `stub / gated on task 1` to `active`.

## Open questions

- Is RustEvo2 a stable benchmark or is it actively being patched? If actively patched, snapshot the version we ran against.
- Does the leaderboard accept self-reported submissions? If yes, our `Qwen2.5-Coder-14B-Instruct` baseline number may be a useful corroborating contribution regardless of the Strand outcome.

## Cross-references

- **Source intakes**: intake-614 (Fortytwo Network), intake-615 (arxiv:2510.24801), intake-616 (Strand-Rust-Coder-14B-v1)
- **Downstream handoff (gated on this result)**: [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md)
- **Methodology references**: canonical-baseline protocol (memory `feedback_canonical_baseline_protocol.md`), OMP env stack (memory `feedback_omp_env_stack_required.md`), no-concurrent-inference rule (memory `feedback_no_concurrent_inference.md`), llama-bench fa-default (memory `feedback_llama_bench_fa_default.md`), drop-caches re-warm (memory `feedback_drop_caches_numa_eviction.md`)
- **Index entries**: this handoff is registered in [`research-evaluation-index.md`](research-evaluation-index.md) Subsystem Status
