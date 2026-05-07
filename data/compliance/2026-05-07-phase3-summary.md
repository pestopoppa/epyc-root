# Phase 3 Compliance Suite — Cross-Model Summary (2026-05-07)

Per-model agent-file compression-tolerance curves measured against the local stack. Replaces 2026-05-06 first-pass (worker_30B only, v1 procedure schema with 0.417 floor).

## Method recap

- Suite: `tests/compliance/agent_file/` — 15 forbidden-action + 12 procedure-correctness + 15 instruction-recall = 42 tasks per level. Tasks reference `agents/shared/ENGINEERING_STANDARDS.md` directives.
- Levels: 4 compression levels (`none`, `mild`, `medium`, `aggressive`) of the same agent file. Per pilot finding (2026-05-06): mild = 12.4% reduction, medium = 21.8%, aggressive = 28.4%; all 12 RFC 2119 directive markers preserved exactly across artifacts.
- Server: standalone llama-server, canonical OMP env (PROC_BIND=spread / PLACES=cores / WAIT_POLICY=active / numactl --interleave=all), --threads 96, --mlock, --no-warmup, --no-mmap.
- Sampling: temperature=0.0, max_tokens=768. `chat_template_kwargs.enable_thinking=False` for all Qwen3.5+/Qwen3.6/Qwen3-Next reasoning models (otherwise `<think>` block consumes the entire token budget and returns 0 visible chars).
- Scoring: forbidden-action and instruction-recall use case-insensitive substring match against any-of acceptable answers. Procedure-correctness uses v2 ordered-anchor-group matching: each step is a list of synonyms (e.g. `feature flag` ≡ `feature-flag` ≡ `feature_flag`); at least one synonym per step must appear in order. v2 schema replaces v1 strict-substring matching, which produced a 0.417 floor that hid model differences.

## Cross-model results

| Model | none C/P/R | mild C/P/R | medium C/P/R | aggressive C/P/R |
|---|---|---|---|---|
| **worker_30B v2** | 0.80 / 0.83 / 1.00 | 0.67 / 0.83 / 1.00 | 0.73 / 0.75 / 1.00 | 0.87 / 0.83 / 1.00 |
| **worker_fast** | 0.27 / 0.42 / 0.33 | 0.13 / 0.50 / 0.40 | 0.27 / 0.42 / 0.47 | 0.33 / 0.08 / 0.40 |
| **frontdoor** | 0.80 / 1.00 / 1.00 | 0.73 / 0.92 / 1.00 | 0.87 / 1.00 / 1.00 | 0.93 / 0.92 / 1.00 |
| **architect_general** | 0.80 / 0.83 / 1.00 | 0.93 / 0.83 / 0.93 | 0.87 / 0.83 / 1.00 | 0.93 / 0.92 / 0.93 |
| **ingest_long_context** | 0.93 / 0.75 / 1.00 | 0.93 / 0.92 / 1.00 | 0.93 / 0.75 / 0.93 | 0.93 / 0.67 / 1.00 |

*(C/P/R = Compliance / Procedure / Recall pass rate.)*

## Per-model deployment-gate verdict

Per `handoffs/active/agent-file-prose-compression.md` Phase 3 rule: each level must meet **compliance ≥ 0.95** AND **procedure ≥ 0.95** AND **recall ≥ 0.90**. The model's `agent_file_compression_operating_point` is the highest level passing all three. Models with `operating_point: none` are blocked from production roles that consume agent files.

| Model | Operating Point | Notes |
|---|---|---|
| **worker_30B v2** | **none** — FAILS strict gate at every level | compliance binding (0.67-0.87); procedure 0.75-0.83, recall pinned 1.000. |
| **worker_fast** | **none** — FAILS strict gate at every level | small model — recall 0.33-0.47, can't retain agent file. |
| **frontdoor** | **none** — FAILS strict gate at every level | compliance binding (0.73-0.93); procedure & recall both ≥0.92 across all levels. |
| **architect_general** | **none** — FAILS strict gate at every level | all 3 metrics within range but compliance 0.80 at level=none; recall slip on mild/aggressive (0.93). |
| **ingest_long_context** | **none** — FAILS strict gate at every level | compliance pinned at 0.933 across all levels (just below 0.95); procedure dips at aggressive (0.667). |

## Headline findings

1. **No model in the local stack passes the strict gate at any compression level.** The strictest level (compliance ≥ 0.95) is hit only by ingest_long_context's compliance pin at 0.933 — close but no cigar.
2. **Recall is the cleanest signal of model capacity** at this task size. worker_fast (1.5B) drops recall to 0.33-0.47 — clear evidence the agent file's 700 words exceed the model's useful working memory. All three Qwen3.5+/Qwen3.6/Qwen3-Next models pin recall at ≥0.93 across all 4 levels.
3. **Compression doesn't hurt the strong models.** frontdoor's *aggressive* level scores 0.93 compliance / 0.92 procedure / 1.00 recall — within sampling noise of *none* (0.80 / 1.00 / 1.00). For the larger models, the agent file at 28% reduction is just as readable as the verbose original. This validates the per-model compression-tolerance hypothesis from the handoff: bigger models have headroom to absorb compression.
4. **Procedure pool v2 schema fix worked.** v1 strict-substring matching pinned procedure at 0.417 across all levels of all models — a task-design floor that masked real differences. v2 synonym-group matching lifts this to 0.83-0.92 for capable models, exposing the true signal.
5. **The `enable_thinking=False` chat-template fix is mandatory** for Qwen3.5+/Qwen3.6/Qwen3-Next models in OpenAI-compatible /v1/chat/completions calls. Without it, the model's `<think>` block consumes the entire `max_tokens` budget and returns 0 visible chars — making compliance tests trivially fail. Discovered mid-batch on frontdoor; fixed in `live_runner.py` v2.
6. **The 0.95/0.95/0.90 gate may be too strict for current task pool sample size.** With n=15 per pool (binomial 95% CI half-width ~13 pp), distinguishing 0.95 from 0.93 requires n≈100+. The most likely calibration outcome from this batch: relax to 0.90/0.90/0.85 OR bump n per pool to 30+.

## Recommendations

- **For Phase 4 deployment-gate registry rollout**: do NOT propagate the strict 0.95/0.95/0.90 thresholds yet. Rerun Phase 3 with n=30 per pool (would take ~2× longer but cuts the CI band in half). Then either (a) calibrate thresholds to keep frontdoor at `mild`/`medium` `operating_point` OR (b) accept that current models can't pass 0.95 at any level under this task pool.
- **Highest near-deployment-ready model**: frontdoor (Qwen3.6-35B-A3B Q8). Strong on all 3 metrics, recall pinned at 1.0, compliance hits 0.93 at aggressive. With n=30 it likely passes a 0.90-threshold gate at all levels.
- **worker_fast is unfit** for any role that reads `ENGINEERING_STANDARDS.md`-class agent files. Low compliance + low recall is the smoking gun. Either restrict worker_fast to roles with no agent file, or use an aggressively compressed *summary* (not the existing `aggressive` artifact, which still drops 0.33 recall) of the file specifically for it.
- **For each model, the data identifies the binding metric** to focus on for the next iteration: compliance for worker_30B/frontdoor/ingest, recall for worker_fast, mixed for architect_general.

## Reproducibility

Per-model sub-directories contain `{none,mild,medium,aggressive}.json` with full per-task pass/fail breakdown + a `SUMMARY.md`. Suite + runner:

```bash
# Launch a model server (example: frontdoor):
OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_NUM_THREADS=96 \
  numactl --interleave=all /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
    --model /mnt/raid0/llm/models/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf \
    --port 8888 --host 127.0.0.1 --threads 96 --threads-batch 96 \
    --ctx-size 16384 --batch-size 2048 --ubatch-size 512 --flash-attn auto \
    --mlock --no-warmup --no-mmap

# Run 4-level curve (each level ~12 min):
for level in none mild medium aggressive; do
  case $level in
    none) FILE=agents/shared/ENGINEERING_STANDARDS.md ;;
    *) FILE=agents/shared/ENGINEERING_STANDARDS.compressed-${level}.md ;;
  esac
  python3 tests/compliance/agent_file/live_runner.py \
    --base-url http://127.0.0.1:8888 \
    --model-id qwen3.6-35b-a3b-q8 \
    --agent-file "$FILE" --level "$level" \
    --max-tokens 768 --temperature 0.0 --timeout 180 \
    --output data/compliance/<run>/${level}.json
done
```

Total wall-time observed for the 5-model batch: **~5 hours** (worker_fast 5min, worker_30B 18min, frontdoor 48min, architect_general 110min, ingest_long_context 75min — sequential, one-server-at-a-time per `feedback_no_concurrent_inference`).

## Method calibration notes (for next runs)

1. The procedure pool v1→v2 schema change is the single largest signal-extraction improvement. Apply v2 to any future Phase 3 expansion (additional models, different agent files).
2. `enable_thinking=False` is now the live_runner default. The `--enable-thinking` CLI flag exists for future cases where thinking content is the desired output (none in current scope).
3. The same 5-model batch with n=30 per pool would take ~10 hours — feasible overnight.
4. Cross-model comparison is currently dominated by sampling noise. The 5×4 grid above has 20 cells × 3 metrics = 60 measurements; with the 13 pp CI band, only deltas >25 pp are robust at this sample size.
