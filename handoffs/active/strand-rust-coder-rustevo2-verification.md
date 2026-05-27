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

**Pinned commit for benching**: `aed98f6` (HEAD of main 2026-05-27). Repo cloned to `/workspace/tmp/rustevo/RustEvo` for inspection.

**Public leaderboard** (from README at pinned commit, 10 models):

| Rank | Model | Pass@1 | API Usage Accuracy | Coverage |
|---|---|---|---|---|
| 1 | Claude-3.7-Sonnet | 65.3% | 78.2% | 83.6% |
| 2 | o1-mini | 57.5% | 70.4% | 85.2% |
| 3 | GPT-4o | 55.4% | 68.4% | 77.2% |
| 4 | Gemini-1.5-Pro | 55.3% | 62.6% | 60.9% |
| 5 | DeepSeek-v3 | 54.8% | 69.7% | 71.0% |
| 6 | Gemini-2.0-Flash | 52.6% | 73.5% | 72.5% |
| 7 | Llama-3.1-70B | 51.0% | 65.3% | 69.0% |
| 8 | **Qwen-2.5-72B** | **50.9%** | 66.7% | 64.7% |
| 9 | Claude-3.5-Sonnet | 48.1% | 68.7% | 80.3% |
| 10 | Grok-3 | 40.5% | 67.2% | 70.4% |

Category-specific Pass@1: Stabilizations 65.8%, Signature Changes 58.2%, Behavioral Changes 38.0%, Deprecations 40.4%.

**CRITICAL FINDING #1 — claim is not on leaderboard**:
**Strand-Rust-Coder-14B is NOT on the public RustEvo² leaderboard** as of 2026-05-27 (verified at pinned commit `aed98f6`). Founder's "#1 on RustEvo2" claim (intake-614) is unsourced; only a local bench can verify.

**CRITICAL FINDING #2 — claim magnitude is unusually aggressive**:
For Strand-Rust-Coder-14B to claim #1 it must beat Claude-3.7-Sonnet at **65.3% Pass@1**. Its closest base-family entry, **Qwen-2.5-72B at 50.9%**, is 5× larger and lands rank 8. The claim therefore implies the Strand fine-tune of a 14B base recovers (and exceeds) +14.4 pp over the 72B variant of the same family — extraordinary for a "simplest possible fine-tune" on 191k samples in 8 days. The verification gate's decision matrix should treat any local result below ~50% as a normal-Qwen-family expectation, 50–60% as a strong-but-not-#1 fine-tune signal, and ≥65% as the extraordinary claim that warrants follow-up scrutiny on the eval methodology itself (data contamination, leaderboard submission process, etc.).

**Adapter work — much simpler than initially scoped (no shim needed)**:

The harness ALREADY uses the OpenAI Python SDK with `api_key` + `base_url` as env vars (see `Evaluate/unit.py:1-7` and `Evaluate/eval_models_rq1.py`). `llama-server` exposes a compatible `/v1/chat/completions` natively. So:

1. Start `llama-server` for the model under test on a dev port (e.g., :9091).
2. Set env vars before invoking the harness:
   ```bash
   export API_KEY=dummy            # llama-server ignores; SDK requires non-empty
   export BASE_URL=http://localhost:9091/v1
   ```
3. **Single-file edit**: the canonical Pass@1 / API Usage Accuracy / Coverage numbers (the leaderboard table above) are produced by `Evaluate/eval_models_rq1.py`. Edit its `MODELS` list (lines 18-30) to contain the alias our llama-server reports (e.g., `"strand-rust-coder-14b"`). Use `llama-server --alias strand-rust-coder-14b ...` to set that alias deterministically.
4. Invoke via `cd Evaluate && python eval_models_rq1.py --file_a ./data/final_dataset.json --file_b ./data/final_dataset.json --output ./data/RQ1/rq1_strand.json` (per the harness's own docstring example at the top of `eval_models_rq1.py:1-3`).

**No adapter code to write.** The custom adapter speculation in the earlier version of this handoff was wrong — the harness was already OpenAI-API-compatible from the start.

**HOST PREREQ for Phase B — Rust toolchain not installed on EPYC**:

The harness runs each generated solution + test via `subprocess` calls to `cargo`/`rustc` (see `Evaluate/unit.py:run_rust_code`). Verified 2026-05-27 on the bench host: `cargo` and `rustc` are NOT installed. Without them, every task fails with "Execution error" and Pass@1 collapses to 0%.

Install before Phase B (no special permissions, installs to user home):
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
source $HOME/.cargo/env
cargo --version && rustc --version  # confirm
```
The harness has no documented minimum Rust version; pick the current stable. Approx ~300 MB of disk for the toolchain + Cargo registry; well within `/home` budget.

Also install Python deps from `requirements.txt` (openai 1.66.3, langchain 0.3.x, tree-sitter 0.20.4, semver 3.0.4, etc.) into a clean venv to avoid polluting the orchestrator's Python env.

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

#### C-2: Decision matrix (calibrated against the actual leaderboard distribution)

Reference distribution from the current public leaderboard (10 models, top to bottom: 65.3 / 57.5 / 55.4 / 55.3 / 54.8 / 52.6 / 51.0 / 50.9 / 48.1 / 40.5). Qwen-2.5-72B (the closest base-family entry at 5× Strand's parameter count) lands at 50.9% / rank 8.

| Strand-Rust-Coder-14B Pass@1 result | Rank vs leaderboard | Disposition |
|---|---|---|
| ≥65.3% | **#1 (matches founder claim)** | **STRONG GO + scrutinize methodology**: a 14B model recovering +14.4 pp over its 72B sibling is extraordinary. **Before promoting `swarm-dataset-distillation.md`** verify: (a) the Strandset-Rust-v1 dataset has no overlap with RustEvo² evaluation tasks (data-contamination check), (b) the harness ran against the same dataset version as the leaderboard, (c) sampling parameters match the leaderboard's protocol (RustEvo² README does not document the sampling settings used for its published numbers — this needs reading the paper appendix). Only after these pass: full GO on the distillation handoff. |
| 55–65% | **Top 3-5 (clear overperform vs Qwen-2.5-72B + most frontier APIs)** | **STRONG GO**: strong-but-not-#1 fine-tune. Founder's "#1" framing was hype; the underlying technique still produces a deployable artifact that significantly outperforms its 5×-larger base-family sibling. Proceed with `swarm-dataset-distillation.md`. Note the rank discrepancy in intake-614. |
| 50–55% | **Top 5-8 (matches or slightly beats Qwen-2.5-72B base-family expectation)** | **QUALIFIED GO**: Strand is roughly Qwen-2.5-72B-tier at 1/5 the param count — that itself is a respectable Rust-specialist outcome and validates the dataset-distillation pipeline, but founder's "#1" claim is materially overstated. Tighten `swarm-dataset-distillation.md`'s Phase-3 ranking gate (raise BT margin threshold) and proceed. |
| 40–50% | **Rank 9–10 / bottom of leaderboard** | **WEAK SIGNAL**: Strand is no better than Qwen-2.5-72B base. The fine-tune adds value at the 14B param tier but is not exceptional. Pause `swarm-dataset-distillation.md` and re-evaluate when Fortytwo publishes pipeline details; the marketing claim is doing the heavy lifting. |
| <40% / off-leaderboard | **Below rank 10** | **NO-GO**: kill `swarm-dataset-distillation.md`; record kill-decision back into intake-614 / intake-616 notes citing this Phase-B result. |

In all cases, **also report the Qwen2.5-Coder-14B-Instruct base-model number on the same harness** — that isolates the Strand fine-tune's contribution vs the base's own RustEvo² capability. If the base hits 50%+ on its own, much of Strand's claimed value is base-model capability, not the Strand dataset.

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
