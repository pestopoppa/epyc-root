# Structured output across the kernel and the `/v1` seam

**Promoted 2026-09-17** out of [`handoffs/active/harness-selection-and-integration.md`](../../handoffs/active/harness-selection-and-integration.md)
(row HS-13, ticked 2026-09-16). It is a capability record for the frozen v9 kernel and the
orchestrator seam, cited whenever a harness or instrument needs schema-constrained output.

**Read the layers together.** The kernel *can* serve grammar-constrained JSON; the `:8000` seam
refuses `response_format` with a 422 **by decision** (HS-OD-1). Quoted alone, either half is
misleading.

---

  - **Structured-output capability record — two layers, read together.**

    | Layer | Surface | What it does | Evidence |
    |---|---|---|---|
    | Kernel (frozen v9 `0db32c06e`) | `POST /v1/chat/completions` | `response_format` `{"type":"json_object"[,"schema"]}` and `{"type":"json_schema","json_schema":{"schema":…}}` are converted to `json_schema`; any other non-`text` type → `invalid_argument`. `json_schema`/`grammar` body fields are accepted directly (both at once → error); `json_schema` is compiled by `json_schema_to_grammar` → **grammar-constrained sampling**. `max_completion_tokens` and `max_tokens` alias `n_predict`; `seed` accepted. | `tools/server/server-common.cpp:933-953`; `tools/server/server-schema.cpp:46,184,258-272`; `tools/server/README.md:1239` (all verified with `git show 0db32c06e:<path>`) |
    | Orchestrator internal | `LLMPrimitives.llm_call(json_schema=…)` → llama-server body | Threads `json_schema` (and `grammar`) straight into the backend payload — grammar-constrained. Live internal consumers: native `/chat` **direct** mode (`output_schema`) and consultations. | `src/llm_primitives/primitives.py:636,698`; `src/backends/llama_server.py:1176-1179`; `src/api/routes/chat_pipeline/direct_stage.py:133,186`; `src/orchestration/consultation.py:257` |
    | Orchestrator native `/chat`, REPL mode | `ChatRequest.output_schema` | **Not** grammar-constrained: schema is put in the prompt and `FINAL()` is validated with retry-with-error — i.e. parse-and-retry — and only when feature `final_schema_validation` (default **off**) is on. | `src/api/models/requests.py:258-263`; `src/features.py:148`; `src/api/routes/chat_pipeline/repl_executor.py:579` |
    | Orchestrator `/v1` seam (`:8000`) | `OpenAIChatRequest` | `response_format` other than `{"type":"text"}` → **422 naming the field** (HS-OD-1, by decision). `max_completion_tokens` honoured as alias. | `src/api/models/openai.py:39-51` (orchestrator `cbe551e8`) |

  - **Reading for the HS-4 packet.** A harness that uses OpenAI JSON mode against `:8000` gets a 422 today, not prose — the kernel *could* serve it grammar-constrained, the seam declines. Wiring it is a small orchestrator change (map `response_format` → `json_schema` on the direct path), but REPL-mode requests would need a policy choice because that path is parse-and-retry, not constrained; the "never parse-and-retry" consequence above therefore holds only on the direct/consultation paths. File a task only if a selected harness needs JSON mode (HS-OD-1 standing condition).
  - **Kernel-doc defect found (no action on the frozen tree):** `README.md:1239` shows `{"type":"json_schema","schema":{…}}` (schema at top level), but the code reads `response_format.json_schema.schema` (`server-common.cpp:947-949`), so the README's example form yields an **empty** schema — i.e. unconstrained JSON, silently. Any instrument must use the OpenAI nesting or `json_object`+`schema`. Another instance of the HS-1g silent-no-op class.
