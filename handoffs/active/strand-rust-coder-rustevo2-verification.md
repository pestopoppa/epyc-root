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

#### A-1: Download the GGUF — DONE 2026-05-27

- Source: `mradermacher/Strand-Rust-Coder-14B-v1-GGUF`, quant **Q4_K_M**.
- Storage: **`/mnt/raid0/llm/models/strand-rust/Strand-Rust-Coder-14B-v1.Q4_K_M.gguf`**.
- File size: **8,988,111,296 bytes (8.37 GiB / 8.99 GB SI)** — matches mradermacher's advertised size.
- SHA-256: `6abca8fd0c512bdb26600313d44aa9e950be78baa21a281735aa3c868d162046` (recompute against HF page hash before benching as a tamper check).
- GGUF header inspection (`gguf_dump.py --no-tensors`) confirms identity + integrity:

| Field | Value |
|---|---|
| `general.architecture` | `qwen2` |
| `general.base_model.0.name` | `Qwen2.5 Coder 14B Instruct` |
| `general.base_model.0.repo_url` | `https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct` |
| `general.dataset.0.name` | `Strandset Rust v1` |
| `general.dataset.0.organization` | `Fortytwo Network` |
| `general.dataset.0.repo_url` | `https://huggingface.co/Fortytwo-Network/Strandset-Rust-v1` |
| `general.license` | `apache-2.0` |
| `general.size_label` | `14B` |
| `qwen2.block_count` | 48 |
| `qwen2.context_length` | 32768 |
| `qwen2.embedding_length` | 5120 |
| `qwen2.attention.head_count` / `head_count_kv` | 40 / 8 (GQA) |
| `qwen2.rope.freq_base` | 1,000,000 |
| `tokenizer.chat_template` | present (Qwen2 chat template with tool-use branch) |
| `tokenizer.ggml.eos_token_id` | 151645 (`<|im_end|>`) |
| Tensor count | 579 |

Independent corroboration from the GGUF metadata:
- The model is genuinely a Qwen2.5-Coder-14B-Instruct fine-tune (matches founder's claim).
- The dataset reference matches intake-616's Strandset-Rust-v1 link.
- Apache-2.0 license confirmed in the GGUF itself, not just on HF.
- The fine-tune method is **not** recorded in the GGUF metadata (no LoRA / DPO / full-SFT marker) — only the base model + dataset are. Founder's "simplest possible fine-tune" framing remains an external claim.

#### A-2: Locate the RustEvo2 benchmark and its leaderboard — DONE 2026-05-27

**Benchmark identified**: **RustEvo²** (paper [arxiv:2503.16922](https://arxiv.org/abs/2503.16922), repo **`https://github.com/SYSUSELab/RustEvo`**), Linxi Liang et al., 2025.

**Scope**: 588 API-evolution tasks synthesized from Rust standard libraries (380) + 15 third-party crates (208). Four categories: Stabilizations, Signature Changes, Behavioral Changes, Deprecations.

**Metrics**: Pass@1 and API Usage Accuracy.

**Harness shape**:
- Python (100% per GitHub language stats).
- Entry point: `cd evaluate && ./run.sh eval_models.py --model_name <name>`.
- Model is invoked via `evaluate/generation.py`, which **the user is expected to modify** to point at their model under test ("Replace the target LLM in the evaluate/generation.py"). The repo's README explicitly says it's under construction; **the harness is NOT OpenAI-API-compatible out-of-the-box** — a thin adapter must be written that proxies whatever interface the existing `generation.py` expects to a local `llama-server` on a dev port (avoid production stack collision).
- Repo activity: 10 commits total, no release tags, "Repo Under Construction" notice on the README. This is a fragile dependency — pin to a specific commit SHA before benching to avoid mid-evaluation moving-target.

**Public leaderboard** (from README, current as of 2026-05-27):

| Model | Pass@1 | API Usage Accuracy |
|---|---|---|
| Claude-3.7-Sonnet | 65.3% | 78.2% |
| (other entries — GPT-4o, Gemini, DeepSeek, Llama, Qwen — present, exact rank ordering not transcribed; need to read README directly for full list) | — | — |

Category-specific aggregates from the paper: 65.8% Pass@1 on Stabilizations; **38.0% Pass@1 on Behavioral Changes**; 56.1% on before-knowledge-cutoff APIs vs 32.5% on after-cutoff tasks.

**CRITICAL FINDING for the verification gate**:
**Strand-Rust-Coder-14B is NOT on the public RustEvo² leaderboard** as of 2026-05-27 (verified by reading the GitHub repo README + paper). The Fortytwo founder's "**#1 on RustEvo2**" claim from the sales call (intake-614) therefore cannot be corroborated from public sources. Two possibilities:

1. Fortytwo ran the bench themselves but did not submit results to the maintainers (plausible — the repo's submission process is not formalized).
2. The leaderboard is stale and Strand was submitted but not yet integrated (less plausible given the repo's low commit volume — any pending PR would be visible).

Either way, the local-bench result is the only way to verify the claim. The verification gate's STRONG-GO threshold (≥10pp over base, claimed #1) should be tempered by this: even if we beat the listed top model, "#1" requires comparison against the same submissions; if leaderboard is stale, our number is corroborating but not conclusive on the rank claim.

**Adapter work for Phase B** (must be done before B-1 launches):
- Read `evaluate/generation.py` in the pinned commit. Identify what call signature it expects (e.g., does it use the `openai` SDK? `requests` to a custom endpoint? `transformers.pipeline()`?).
- Write a minimal adapter that translates that interface to a POST against a local `llama-server` `/v1/chat/completions` endpoint on a dev port (e.g., :9091).
- Document the adapter as part of B-1 launch protocol.

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
