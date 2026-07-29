# Compliance-suite first-pass: Qwen3-Coder-30B-A3B Q4_K_M

Run: 2026-05-06 evening. Live LLM smoke + first Phase 3 datapoint.

**Model**: Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf (worker tier).
**Server**: standalone llama-server on port 8888, 96 threads, ctx=16384, --mlock --no-warmup --no-mmap, full canonical OMP env (PROC_BIND=spread, PLACES=cores, WAIT_POLICY=active, numactl --interleave=all).
**Suite**: tests/compliance/agent_file/ — 15 forbidden-action + 12 procedure-correctness + 15 instruction-recall = 42 tasks per level.
**Sampling**: temperature=0.0, max_tokens=384, agent file = ENGINEERING_STANDARDS{,.compressed-{mild,medium,aggressive}}.md.

## Results

| Level | Tokens | Reduction | Compliance | Procedure | Recall | Wall-time |
|---|---|---|---|---|---|---|
| none | 1300 | +0.0% | 0.800 | 0.417 | 1.000 | 264.3s |
| mild | 1179 | +9.3% | 0.667 | 0.417 | 1.000 | 262.1s |
| medium | 1068 | +17.8% | 0.733 | 0.417 | 1.000 | 272.4s |
| aggressive | 991 | +23.8% | 0.867 | 0.417 | 1.000 | 266.4s |

## Findings

**Recall pinned at 1.000 across all four levels.** The model recalls clauses from the compressed file as well as from the verbose original. Recall is the weakest of the three signals (a model can 'remember' content from training even if the file is uninformative), but the pattern is consistent and matches the a-priori expectation that information density rises with compression.

**Procedure flat at 0.417 across all four levels** (5/12 tasks pass each time). This indicates a *task-design floor*, not a compression effect — the ordered-anchor check requires specific words to appear in exact order, and the model's response style at temperature 0 simply does not produce certain anchors regardless of how the input is compressed. Future Phase 3 iterations should either relax some procedure tasks (allow anchor synonyms) or accept that procedure-pass is bottlenecked by output-style match, not input comprehension.

**Compliance non-monotonic with compression**: 0.800 (none) → 0.667 (mild) → 0.733 (medium) → 0.867 (aggressive). Range 0.667–0.867 = ~20 pp spread. With n=15 per level, the binomial 95% CI half-width is ~13 pp — most of the observed spread is within sampling noise. The aggressive-beats-none result is suggestive but NOT statistically significant at this sample size.

**Per-model deployment-gate verdict** (per the handoff's ≥0.95 compliance / ≥0.95 procedure / ≥0.90 recall threshold): this model would fail the gate at level=none already, so `agent_file_compression_operating_point: none` — blocking production deployment to roles that read agent files. This is the EXPECTED outcome for a 30B-A3B-class model on this task pool — and signals that EITHER the gate threshold is too strict OR the task pool needs design revisions (especially the procedure pool's ordered-anchor design).

**Calibration data extracted**:
1. Full 4-level run on this hardware: ~17 minutes (4 × ~4.4 min per level).
2. Per-task latency: ~6 s/task at 384 max_tokens, T=0, on canonical 96t worker.
3. Token-count reductions match the artifact-level word counts (mild 9.3% / medium 17.8% / aggressive 23.8% on the **system-message tokenization**; the artifact word reductions of 12.4% / 21.8% / 28.4% don't translate 1:1 to tokens because tokenizer compression of repeated patterns differs from word compression).
4. Procedure-pool design needs revision before Phase 3 batch.

## Reproducibility

```bash
# Launch server (canonical OMP env, single-instance):
OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_NUM_THREADS=96 \
  numactl --interleave=all /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
    --model /mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf \
    --port 8888 --host 127.0.0.1 --threads 96 --threads-batch 96 \
    --ctx-size 16384 --batch-size 2048 --ubatch-size 512 --flash-attn auto \
    --mlock --no-warmup --no-mmap

# Run 1 level (4 min):
python3 tests/compliance/agent_file/live_runner.py \
    --base-url http://127.0.0.1:8888 \
    --model-id qwen3-coder-30b-a3b-q4 \
    --agent-file agents/shared/ENGINEERING_STANDARDS.md \
    --level none \
    --max-tokens 384 --temperature 0.0 \
    --output data/compliance/<run-name>/none.json

# Repeat for {mild, medium, aggressive} swapping --agent-file accordingly.
```

## Next steps (deferred)

- Cloud models (Opus 4.7, Sonnet 4.6, Haiku 4.5): wire OpenAI-compatible endpoint via `--base-url` + auth header; same `live_runner.py` reused unchanged.
- Local stack: frontdoor (Qwen3.6-35B-A3B Q8), architect_general (Qwen3.5-122B-A10B Q4_K_M), worker_fast (Qwen2.5-Coder-1.5B Q4_K_M); each gets a 17-minute curve run.
- Procedure-pool revision: relax anchor matching to allow synonyms / drop tasks where 0/N models pass at level=none.
- Sample-size revision: bump each pool to n=30+ to bring binomial CI half-width below 10 pp.
