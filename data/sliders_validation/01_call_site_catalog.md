# SLIDERS Phase 0.1: LLM call-site catalogue (2026-11-09)

Source: upstream `stanford-oval/sliders` (MIT), scratch clone `/mnt/raid0/llm/scratch/sliders`, HEAD
`b66094d89b8068458c86a649668bed5fd0d6201c` ("initial commit", 44 Python files). Read by grep for every
`get_llm_client(` / `.ainvoke(` site plus the per-stage model block of `configs/sec_10q_sliders.yaml`
(the FinQ100 config). Reading only; nothing was run, nothing vendored.

## The one substitution point

Every call site obtains its client from `sliders/llm/llm.py:145 get_llm_client(*, model, ...)`. Provider
selection (`llm.py:152-157`): kwarg `provider`, else context var, else env `SLIDERS_LLM_PROVIDER`
(default `azure`). Providers `openai` and `vllm` return `CachedChatOpenAI(base_url=..., api_key=...)`
(`llm.py:203-228`); the base URL comes from `OPENAI_BASE_URL` (provider `openai`) or `VLLM_BASE_URL`
(provider `vllm`, default `http://localhost:8000/v1`). Responses are cached in Redis when reachable
(`llm.py:84-110`, fails open to no cache).

## Stage to call-site map (code sites; model per `configs/sec_10q_sliders.yaml`)

Stage names are the handoff's nine, mapped to the code. "cfg" = the `models:` key (yaml lines 33-87).

| Stage | Call sites (file:line of `get_llm_client` / first `ainvoke`) | cfg key and model |
|---|---|---|
| schema_induction | `modules/generate_schema.py:134` (`:157`), `:295` (`:301`); task guidelines `system.py:249` (`:343`); guideline selection `system.py:141` (`:177`) | `generate_schema` gpt-4.1; `task_guidelines` gpt-4.1; `select_guidelines_for_schema` gpt-4.1-mini |
| relevance_gating | chunk relevance and extraction path in `modules/extract_schema.py:85,94,103,112,121` (`:131`); absence arbiter `:554` (`:612`) | `is_relevant_chunk` gpt-4.1-mini; `extract_schema` gpt-4.1-mini |
| extraction | `modules/extract_schema.py:131` (shared chain runner) | `extract_schema` gpt-4.1-mini (max_tokens 32000) |
| primary_key_selection | `modules/primary_key_selector.py:187` (`:242`); null keys `modules/handle_null_primary_keys.py:317` (`:365`, `:483`), `:1252` (`:1292`) | model from caller kwargs (not a named cfg key in this yaml) |
| reconciliation_controller | `modules/merge_techniques/reconciliation.py:164` (`:188`), `:259` (`:306`), controller chain `:415` | `merge_tables` gpt-4.1 (max_tokens 32000); `check_if_merge_needed` gpt-4.1 (`system.py:220`, `:523`) |
| reconciliation_executor | `reconciliation.py:524`, `:666` (verification), `:992` (merge SQL), `:1622` | `merge_tables` gpt-4.1 |
| sql_generation | inspect loop `modules/answer_techniques/inspect_answer.py:129` (`:185`) | `answer` gpt-4.1 (strategy `sql_inspect`) |
| answer_synthesis | `system.py:197` (answer), `:204` (force_answer), `:213` (direct_answer), `:231` (answer_no_table), `:241` (answer_tool_output); chains at `:701,721,761,801,863,882,1005-1134`; `inspect_answer.py:283` verbalise | `answer`, `force_answer`, `direct_answer` gpt-4.1; `answer_no_table` gpt-4.1-mini; `answer_tool_output` gpt-4.1 |
| citation_generation | `inspect_answer.py:360`, `:463`, reconciliation summary `:527` | follows the inspect model config |

Additional sites outside the nine stages: question rephrasing `modules/question_rephraser.py:79` (`:296`;
cfg `rephrase_question` gpt-4.1); field canonicalisation `modules/canonicalize_fields.py:79` (`:199`);
document title and description pass `document.py:149,214,253,312` (`:244,:283,:351`; `title_model` gpt-4.1,
`description_model` / `table_summary_model` gpt-4.1-mini); LLM evaluator `evaluation.py:199` (`:229`,
gpt-4.1 soft/hard evaluators); baselines `baselines.py` (not on the SLIDERS path).

## Counts and what was NOT done

* 14 `models:` keys in the yaml (10 gpt-4.1, 4 gpt-4.1-mini) plus 3 document-processing models (1 gpt-4.1, 2 gpt-4.1-mini).
* Prompt template lengths in tokens: NOT measured (would need the prompt files tokenised; no tokenizer was run).
* Output structure: pydantic models are imported from `sliders/llm_models.py` (`Tables`, `ExtractedTable`,
  `TableProcessingNeeded`, `SQLAnswer`, `Action`, `RephrasedQuestion`, `DocumentTitle`, `DocumentDescriptions`,
  `AbsenceArbiterOutput`, `Evaluation`); 41 `with_structured_output` / `response_format` mentions. Which
  chain is JSON, SQL or free-form was taken from those imports, not from reading every chain.
* The paper's GPT-4.1 call-count baseline (gate "per-question calls <= 5x") is not in this repo.
