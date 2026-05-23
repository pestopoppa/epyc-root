# Chat Templates — Per-Model Turn Markers and Routing Endpoints

> Quick reference for which chat template each production model uses, which
> orchestrator code path applies the template (client-side vs server-side
> jinja), and how to wire a newly-onboarded model so it produces clean
> output through the routing layer.

**Compiled**: 2026-05-23
**Primary sources**: `src/api/routes/chat_utils.py`, `src/backends/llama_server.py`,
`src/llm_primitives/backend.py`, `scripts/server/stack_numa.py`,
`progress/2026-05/2026-05-22.md`, `progress/2026-05/2026-05-23.md`

---

## Per-family templates currently in production

The orchestrator's family detector (`_detect_template_family` in
`chat_utils.py`) maps a model name to one of these families and applies
the corresponding template wrap when the request goes through the
`/completion` path. For roles that route via `/v1/chat/completions`, the
orchestrator skips client-side templating entirely — llama-server's
`--jinja` flag applies the GGUF's embedded chat_template server-side.

### Qwen (3.x, 2.5, 3-Next, distillations)

```
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant

```

**Detection key**: name contains `qwen` (case-insensitive). DeepSeek-R1-
Distill-Qwen variants also detect as qwen.

**Special kwargs**: most Qwen models (3.5, 3.6, 3-Next) require
`chat_template_kwargs.enable_thinking=False` at the chat-completions
layer when not explicitly using the reasoning path — without it the
template emits a leading `<think>...</think>` block that the model is
prone to fill with degenerate loops. See
`feedback_qwen3x_enable_thinking_false` for the empirical fix (+33pp
accuracy on frontdoor's cheap-kill task set).

### Gemma 2 / Gemma 3 (`<start_of_turn>` style)

```
<start_of_turn>user
{prompt}<end_of_turn>
<start_of_turn>model

```

**Detection key**: name contains `gemma` but NOT `gemma-4` / `gemma4`.

### Gemma 4 (multi-channel; production: gemma-4-26B-A4B-it)

The proper format per the GGUF's embedded chat_template (12045 chars of
Jinja, verified 2026-05-22 via `llama-server /apply-template`):

```
<|turn>user
{prompt}<turn|>
<|turn>model
<|channel>thought
<channel|>

```

Notes:
- **Asymmetric markers**: `<|turn>X` opens a turn, `<turn|>` closes one.
  This is NOT a balanced pair — they're distinct tokens.
- **Thought channel prefix**: when `enable_thinking | default(false)` is
  false (the default), the template appends a `<|channel>thought\n
  <channel|>` prefix. The model is trained to fill in this channel then
  emit its final answer.
- **`/completion` is broken for this format** (verified empirically
  2026-05-22 against ik_llama.cpp's MTP build): sending the proper
  template via `/completion` times out with 0 tokens. The path forward
  is `/v1/chat/completions` (see below).

### Llama 3.x (header-id style)

```
<|begin_of_text|><|start_header_id|>user<|end_header_id|>

{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>


```

**Detection key**: name contains `llama-3`, `llama3`, or `meta-llama-3`.

### MiniMax-M2 and Phi-4

Both empirically accept Qwen-style ChatML markers. Detected separately
in `_detect_template_family` so future deviations can be caught, but
currently routed through `_TEMPLATE_QWEN_CHATML`.

### Unknown families

Pass-through (no template wrap). The model receives the raw user prompt.
Safer than guessing wrong; logged at `DEBUG` so the operator can flag
miswired roles.

---

## Two routing endpoints — when to use which

### `/completion` (legacy, client-side templating)

The orchestrator wraps the user prompt with the role's chat template
(via `apply_chat_template_for_role` / `apply_chat_template_for_model`)
and POSTs the templated string to `http://llama-server:port/completion`.
llama-server does NOT apply jinja for this endpoint.

**Works for**: Qwen 2.5 / 3.x / 3-Next, Gemma 2/3, Llama 3.x — any model
whose chat template can be replicated as a static prefix/suffix wrap.

**Does NOT work for**: Gemma 4 (multi-channel format with sequence-
sensitive marker semantics) — server returns 0 tokens.

### `/v1/chat/completions` (newer, server-side jinja)

The orchestrator sends `{"messages": [{"role": "user", "content":
prompt}]}` (raw prompt as user content). llama-server's `--jinja` flag
applies the GGUF's embedded chat_template server-side AND parses the
multi-channel response cleanly, returning only the final-channel
content in `choices[0].message.content`.

**Required for**: Gemma 4 (multi-channel format).

**Available for**: any model launched with `--jinja`. Today's stack has
this flag on for all worker_general / worker_explore / etc. instances
(gemma-4-26B-A4B-it Q4_K_M).

**Selection mechanism**: env var
`ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES` (comma-separated role names,
default covers all 5 worker_* roles). `_init_caching_backends` reads
this and sets `use_chat_completions=True` on each affected role's
`ServerConfig`. `LlamaServerBackend.infer()` and
`infer_stream_text()` dispatch to the chat-completions code paths
when the flag is set.

`chat.py:498` and `_try_cheap_first` both check this env list and
SKIP client-side templating for those roles — sending a pre-templated
prompt as messages[].content would inject our markers as literal user
input and confuse the model.

---

## Onboarding a new model — checklist

When swapping in a new model to a production role:

1. **Identify the chat template family** — dump the GGUF metadata:
   ```bash
   python3 -c "import struct; ..."  # see scripts/dump_gguf_kv.py
   ```
   Look for `tokenizer.chat_template` and the `general.architecture`
   field. Compare against the patterns above.

2. **Update `_detect_template_family`** if it's a new family or named
   variant. Add a `if "newfamily" in n: return "newfamily"` branch
   BEFORE the broader Qwen match (the qwen branch is the
   fallthrough-broad catch).

3. **Choose endpoint**:
   - If the template can be replicated as a static prefix wrap → use
     `/completion`, add a `_TEMPLATE_NEWFAMILY` constant and wire it in
     `_wrap_for_family`.
   - If the template is dynamic / multi-channel / version-coupled → use
     `/v1/chat/completions`, add the role name to the default value of
     `ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES` in
     `src/llm_primitives/backend.py:_init_caching_backends`.

4. **Verify with `llama-server /apply-template`**:
   ```bash
   curl -X POST http://127.0.0.1:PORT/apply-template \
     -H 'Content-Type: application/json' \
     -d '{"messages":[{"role":"user","content":"test"}]}'
   ```
   This returns the exact prompt the server would build via jinja. Use
   it as the source of truth when comparing against client-side templates.

5. **Smoke test the role via the orchestrator**:
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H 'Content-Type: application/json' \
     -d '{"prompt":"What is 2+2?","force_role":"NEW_ROLE","real_mode":true,
          "stream":false,"timeout_s":30}'
   ```
   Expect: a clean answer with no marker artifacts. If output contains
   `<|channel>` / `<|turn>` / `<|im_start>` / `<start_of_turn>` literals,
   the template wiring is wrong.

6. **Run the family-detection smoke test in `tests/unit/`** (if
   present): there's a small inline test fixture that exercises
   `apply_chat_template_for_model` against a fixed list of model names.
   Add the new model's expected family.

---

## Historical incidents (anti-patterns this page exists to prevent)

### 2026-05-08 — Worker swap to gemma-4 broke routing silently

The `worker_general` role was swapped from Qwen3-Coder-30B-A3B (Qwen
family) to gemma-4-26B-A4B-it (gemma 4 family). The orchestrator was
hardcoded to apply the Qwen template at `chat.py:498`. After the swap:
- gemma-4 received `<|im_start|>` markers it didn't recognize
- Returned 0 tokens / immediate EOS
- Autopilot fell back to frontdoor for every worker_general request
- Classifier interpreted "worker_general: 0.1% success" as a real signal
  and started routing 97% of traffic to frontdoor

**Discovered 2026-05-22** via inspection of the inference_tap log
showing the worker_general / frontdoor 60s-pause / fall-back pattern.

**Fixed via**:
- `206701f` — per-role template helper in `chat_utils.py`
- `2c1711a` — `/v1/chat/completions` migration for gemma-4 worker roles

**Time-to-discovery**: 14 days. Cost: ~2 weeks of skewed routing data.

### 2026-05-22 — Pre-templated prompts via `/completion` for gemma-4

Even with the per-family template detector landed, gemma-4 still
required the multi-channel format that `/completion` can't apply
server-side. Sending the proper gemma-4 template via `/completion`
empirically TIMES OUT with 0 tokens on the ik_llama.cpp MTP build.

The pragmatic fix was to route gemma-4 worker roles through
`/v1/chat/completions` — server-side jinja handles templating AND
multi-channel response parsing.

**Anti-pattern**: trying to replicate dynamic / multi-channel chat
templates as a client-side static wrap. If the template uses
conditional logic (`{% if enable_thinking %}...`) or auto-emits
channel prefixes based on kwargs, ALWAYS use `/v1/chat/completions`.

---

## Cross-references

- `feedback_qwen3x_enable_thinking_false` (memory) — Qwen reasoning loop
  prevention via `chat_template_kwargs.enable_thinking=False`
- `feedback_verify_current_stack_before_claiming_role_replacement`
  (memory) — verify what's actually deployed in a role before claiming
  a model is a "drop-in replacement"
- `progress/2026-05/2026-05-22.md` — full diagnosis chain for the
  worker_general silent failure
- `progress/2026-05/2026-05-23.md` — `/v1/chat/completions` migration
  and live verification
