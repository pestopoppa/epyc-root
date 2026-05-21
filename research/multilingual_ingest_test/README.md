# Multilingual Ingest Quality-Gap Test — Harness

Implements the test scoped in `handoffs/active/internal-kb-rag.md` § "Test Scope — Multilingual Ingest Quality-Gap Measurement". Resolves the open question from the 2026-05-21 Hy-MT2 intake: do existing stack models have a measurable quality gap on foreign-language ingest that Hy-MT2-1.8B-1.25bit would close?

**Status**: non-inference-gated infrastructure landed 2026-05-21. Inference + sample curation are user-gated (per `feedback_speed_verify_via_llama_bench` and `feedback_no_concurrent_inference`).

## Layout

```
multilingual_ingest_test/
├── README.md                # this file
├── config.yaml              # endpoints, paths, decision thresholds
├── curate_samples.py        # seeds samples.jsonl from Flores-200 + intake_index foreign entries
├── run_pipeline.py          # Pipeline A/B/C harness; dry-run by default, --execute to call endpoints
├── kb_rag_eval.py           # NDCG@5 / MRR using epyc-orchestrator/src/retrieval/kb_rag.query
├── judge_pairwise.py        # LLM-as-judge harness (gemma4-26B-A4B out-of-loop judge)
├── aggregate_results.py     # applies acceptance criteria → outcome
└── data/                    # gitignored: samples.jsonl, pipeline_outputs/, judge/, results/
```

## Downloaded Weights (2026-05-21)

Hy-MT2-1.8B family + base-repo metadata at `/mnt/raid0/llm/models/hy-mt2-1.8b/`:

| Path | Size | Status / Notes |
|------|------|----------------|
| `Q4_K_M/Hy-MT2-1.8B-Q4_K_M.gguf` | 1080 MiB | Works with current `epyc-llama` fork — primary test artifact |
| `2bit/Hy-MT2-1.8B-2Bit.gguf` | 573 MiB | Likely works (verify quant type at load); secondary |
| `1.25bit/Hy-MT2-1.8B-1.25Bit.gguf` | 440 MiB | Needs llama.cpp PR #22836 (STQ1_0 kernel); the headline artifact, but blocked until merge |
| `base-metadata/chat_template.jinja` | <1 MiB | **Use this** for prompt formatting — Hy-MT2 has a model-specific chat template |
| `base-metadata/tokenizer.json` + `tokenizer_config.json` | ~10 MiB | Reference tokenizer; GGUF files have an embedded copy |
| `base-metadata/HY_MT2_0_Report.pdf` | 2.2 MiB | Tencent's tech report — read for prompt-format details and the IFMTBench eval methodology |
| `base-metadata/LICENSE.txt` | — | Verify license posture before any production use |

**Recommended for the test**: launch `Hy-MT2-1.8B-Q4_K_M.gguf` first (works today). If results justify follow-on work, retry with `2bit` for size sensitivity. The 1.25-bit run is gated on PR #22836 — see [[angelslim-techniques-evaluation]].

### Suggested llama-server launch (user-attended; do NOT run autonomously)

```bash
# Per feedback_speed_verify_via_llama_bench and feedback_no_concurrent_inference —
# this command is documented for the user to invoke; the harness will not launch it.
/mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  --model /mnt/raid0/llm/models/hy-mt2-1.8b/Q4_K_M/Hy-MT2-1.8B-Q4_K_M.gguf \
  --port 8099 \
  --ctx-size 8192 \
  --threads 24 \
  --jinja \
  --chat-template-file /mnt/raid0/llm/models/hy-mt2-1.8b/base-metadata/chat_template.jinja
```

The harness's `config.yaml` already points at `http://localhost:8099/v1/chat/completions` for the `hymt2_specialist` endpoint — adjust the port if you launch elsewhere. Verify the chat template loads correctly (Hy-MT2 is "fast-thinking", `--enable-thinking=false` is the right default — already set in the harness's request body).

## Execution Order (user-attended)

```bash
cd research/multilingual_ingest_test

# 1. Curate samples (one-time; some manual additions required for Mandarin-minority/dialect)
python3 curate_samples.py --output data/samples.jsonl --strata-target 10 --flores-cache data/flores200

# 2. Dry-run the pipeline (prints commands, does not call endpoints)
python3 run_pipeline.py --samples data/samples.jsonl --pipelines A,B,C --output data/pipeline_outputs/

# 3. Confirm endpoints + Hy-MT2 launch recipe, then execute (per-pipeline approval expected)
python3 run_pipeline.py --samples data/samples.jsonl --pipelines A,B,C --output data/pipeline_outputs/ --execute

# 4. Evaluate KB-RAG retrieval quality of each pipeline's summaries
python3 kb_rag_eval.py --inputs data/pipeline_outputs/ --query-set data/eval_queries.jsonl --output data/results/kb_rag_scores.json

# 5. Run pairwise judge (dry-run first; --execute to actually call gemma4-26B-A4B)
python3 judge_pairwise.py --inputs data/pipeline_outputs/ --output data/judge/ --execute

# 6. Aggregate + map to acceptance criteria outcome
python3 aggregate_results.py --kb-rag data/results/kb_rag_scores.json --judge data/judge/ --output data/results/decision.md
```

## Sample Format (`data/samples.jsonl`)

One JSON object per line:

```json
{
  "id": "sample-001",
  "stratum": "european_mainstream",
  "language": "it",
  "source_url": "https://...",
  "source_type": "paper_abstract|blog|structured_doc",
  "char_count": 423,
  "content": "<raw foreign-language text>",
  "notes": "optional manual notes"
}
```

Strata (target ≥10 each, total 40) — refined 2026-05-21:

| Stratum | Language codes | Why |
|---------|---------------|-----|
| `chinese_english_control` | zh, en | Strong-coverage control; H1 must not regress here |
| `european_mainstream` | it, fr, de, ru | **Primary interest** — user's actual ingest language mix; high-resource EU where existing models should be strong, so a Hy-MT2 win here is a meaningful niche finding |
| `cjk_technical` | ja, ko | Medium-coverage; CJK shared-script edge cases |
| `mixed_script_structured` | zh+en+code, ja+latex, structured-json-mt | Tests structural fidelity (IFMTBench-style) |

Mandarin-minority/dialect stratum (Tibetan/Mongolian/Uyghur/Cantonese) intentionally dropped — not represented in the actual research-intake ingest workflow.

## Acceptance Criteria (encoded in `aggregate_results.py`)

| Outcome | Trigger | Action |
|---------|---------|--------|
| H0 confirmed | No stratum sees ≥60% B-win AND NDCG@5 lift <0.05 across all strata | Downgrade `intake-586` to `not_applicable`; close MT translation sub-track |
| H1 confirmed (specialist) | ≥1 non-CN/EN stratum: B-win ≥60% AND NDCG@5 lift ≥0.05, AND B ≫ C (specialist > decomposition) | Adopt Hy-MT2-1.8B-1.25bit as optional pre-encode tool; gate by detected language; upgrade `intake-586` verdict to `adopt_component` |
| H1 confirmed (decomposition only) | Same as above but B ≈ C | Switch ingest_long_context to 2-step prompt for affected strata; do NOT adopt Hy-MT2; mark `intake-586` `not_applicable` |
| Mixed / regression on CN/EN | B wins some strata but loses CN/EN | Escalate to user |
| Infeasible | Samples missing OR endpoints unavailable | Document blocker; defer |

## What This Harness Does NOT Do

- Does not download or launch Hy-MT2 weights — that's a user-attended prerequisite (`feedback_sequential_model_loading`)
- Does not fire inference autonomously — every endpoint-calling script defaults to dry-run
- Does not modify orchestrator config or registry — read-only access to ports + KB-RAG index
- Does not curate samples for the Mandarin-minority/dialect stratum automatically — Flores-200 partial coverage; manual additions needed (see `curate_samples.py` output for the gap list)

## References

- Handoff: [`handoffs/active/internal-kb-rag.md`](../../handoffs/active/internal-kb-rag.md) § "Test Scope — Multilingual Ingest Quality-Gap Measurement"
- Related: [`handoffs/active/angelslim-techniques-evaluation.md`](../../handoffs/active/angelslim-techniques-evaluation.md) (independent — Sherry/SpecExit/Tequila/DAQ are NOT in scope of this test)
- Intake: `research/intake_index.yaml` entries intake-586 through intake-596
