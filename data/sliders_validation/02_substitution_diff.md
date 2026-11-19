# SLIDERS Phase 0.2: local-model substitution (2026-11-09)

Same clone and HEAD as `01_call_site_catalog.md` (`b66094d8`). Prompt templates are NOT modified.

## The diff is empty: substitution is configuration

Because every call site goes through `get_llm_client` (`sliders/llm/llm.py:145`), and that factory already
supports an OpenAI-compatible endpoint (`llm.py:203-228`), no source line needs to change. The unified
diff of upstream code is therefore zero lines. The substitution is:

```
SLIDERS_LLM_PROVIDER=openai
OPENAI_BASE_URL=http://127.0.0.1:<port>/v1     # a llama-server (production-consolidated-v10 CPU kernel store)
OPENAI_API_KEY=EMPTY
REDIS_HOST/REDIS_PORT unset                    # no Redis here: cache disables itself (llm.py:98-107)
```

and, in a copy of `configs/sec_10q_sliders.yaml` kept outside the clone, every `models.<key>.model` set to the
served model name (llama-server ignores the name when one model is loaded; keep it explicit for the record) and
`max_tokens` left as shipped except where it exceeds the server context (`extract_schema` and `merge_tables`
use 32000: needs `-c` >= 32000 + prompt per slot, which sets the np/ctx the filler row must request).

## Things the substitution does NOT remove (risks for the run, not fixes)

* Structured output: 41 `with_structured_output` / `response_format` sites need llama-server's
  `response_format` JSON-schema support on `/v1/chat/completions`; failures will present as schema
  hallucination or parse errors and must be classified by reason, not lumped.
* Concurrency: `InMemoryRateLimiter` is 40 requests/second (`llm.py:116-125`); the model server, not the
  limiter, bounds throughput. Wall time per question is a measured quantity, not an estimate here.
* The "existing `epyc-orchestrator` Coder-30B wrapper as the Python adapter" named in the handoff is not
  needed: the OpenAI-compatible path makes a wrapper redundant. If the operator still wants it, that is a
  decision about the run, not a prerequisite.

## Correction to the handoff premise for 0.3 (verified in the clone)

The box says to regenerate the FinQ corpus "from SEC EDGAR via SLIDERS' `experiments/sec_10q.py`".
`sliders/experiments/sec_10q.py` only loads a questions text file and reads pre-built filings from
`files_dir` (config placeholders `/path/to/datasets/sec_10q_dec2025_jan2026/...`); the only network call in
the repo is `llm_tools/code.py:9`. No EDGAR downloader exists, the 10-Q questions are not shipped, and the
README describes FinQ100 as 36M tokens. The 5-question FinQ5 run therefore cannot start until a filing set
and a question file exist (the box's own exception: document it and propose an alternative bounded set).
`sample_data/` and `sample_docs/` ship only Loong sample-id CSVs and small sample documents. Proposed
bounded alternative for the operator: the FinanceBench subset or the shipped sample documents, with the
gate numbers (schema hallucination > 20%, calls > 5x) unchanged. Decision needed before 0.3.
