# Chat Templates — Per-Model Turn Markers and Routing Endpoints

**Category**: `chat_templates`
**Last compiled**: 2026-08-23

> Quick reference for which chat template each production model uses, which
> orchestrator code path applies the template (client-side vs server-side
> jinja), and how to wire a newly-onboarded model so it produces clean
> output through the routing layer.

**Compiled**: 2026-06-15
**Primary sources**: `src/api/routes/chat_utils.py`, `src/backends/llama_server.py`,
`src/llm_primitives/backend.py`, `scripts/server/stack_numa.py`,
`src/chat_completions_roles.py`,
`progress/2026-05/2026-05-22.md`, `progress/2026-05/2026-05-23.md`,
`progress/2026-06/2026-06-15.md`,
`handoffs/active/model-stack-single-source-update-pipeline.md`

---

## Summary

Production chat templates are part of the model-serving contract: the selected endpoint, client-side
wrapping, server-side Jinja behavior, and per-model reasoning kwargs must agree. A mismatch can produce
plausible HTTP success while silently degrading output or routing evidence.

## Key Findings

- Prefer `/v1/chat/completions` with server-side Jinja for dynamic or multi-channel templates.
- Treat model-family detection and `enable_thinking` behavior as per-role configuration, not global defaults.
- Validate the rendered turn markers with a live completion whenever a model or endpoint changes.

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
this flag on for all worker_general / worker_fast / etc. instances
(gemma-4-26B-A4B-it Q4_K_M).

**Selection mechanism**: env var `ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES`
(comma-separated role names) still overrides everything, but the
default set is now derived from generated stack priors rather than a
frozen literal list. `src/chat_completions_roles.py` reads the live
artifact and selects roles whose launch metadata says
`launch.runtime.flags.jinja == true` and
`acceleration.enable_thinking == false`. If the priors artifact is
missing or malformed, the helper falls back to a narrow degraded set:
`frontdoor`, `coder_escalation`, `worker_general`, `worker_math`,
`worker_summarize`, `toolrunner`.

`_init_caching_backends` reads the shared set and sets
`use_chat_completions=True` on each affected role's `ServerConfig`.
`LlamaServerBackend.infer()` and `infer_stream_text()` dispatch to the
chat-completions code paths when the flag is set.

`chat.py` and `_try_cheap_first` both check this shared set and SKIP
client-side templating for those roles — sending a pre-templated
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

## Measured 2026-08-21: the terseness prompt pays; thinking-mode deficits were budget artifacts

Sources: `handoffs/active/qwen-chat-template-evaluation.md` (CT-1/CT-1b/CT-5, all dive- and
run-verified same day), artifacts under `artifacts/chat-templates/`.

**CT-1 (embedded vs epyc-qwen3x-v1, 160 paired questions, CPU):** perfect parity — byte-identical
renders on the bare single-turn no-think shape, therefore bit-identical generations. epyc-v1 is a
proven zero-regression drop-in on the production path; the templates only diverge on system
prompts, tools, history and effort steering. (Method lesson: render-diff the arms ON THE EVAL SHAPE
before a long run.)

**CT-1b (+terseness arm, same pinned ids, fixed 900-token budget):** never worse, significantly
better where budget binds, at 34–99.5% fewer answer tokens — math 80=80% at −34%; mmlu_pro
37.5→40.0% at −99% (mean 2.0 tokens: the model finally obeys "letter only"); gpqa_diamond
42.5→60.0% (flips 0:7, p≈0.016, mostly truncation-avoidance); cruxeval 27.5→30.0% at −36%. The
CCoT math-penalty hazard did not materialize. Deployable artifact:
`epyc-qwen3x-v1/chat_template_terse_arm2.jinja` (sha `1443ea9ab4bb…4551`, injection-free).

**CT-5 (thinking ON vs OFF on Qwen3.8/MI210, 60 paired GPQA-Diamond-CoT):** at a 4,096 cap,
thinking read −6.7pp — decomposition showed the deficit was ENTIRELY truncation zeros
(completed-subset 95.1% vs 94.9%). At symmetric 16K caps: **85.0% vs 86.7%, flips 2:3 for
thinking (n.s.), truncation 0/1** — a statistical tie at +21% tokens-per-solved. Standing rule
this yields: **an accuracy deficit measured under a token cap is not a quality finding until
decomposed by finish_reason** — and every anti-reasoning datum this stack produced (think-loops,
termination defects, caps) has been infrastructure, not model quality. `enable_thinking=false`
remains posture on economics, now measured on the production model itself.

## The embedded template is per-MODEL, not per-family (measured 2026-08-21)

The family table above answers *which turn markers* a model uses. It does **not** answer what the
GGUF's embedded template actually does, and those diverge — including between two models of the
same family. Extracted by GGUF header read from every production GGUF (no model loaded):

| Model / role | Embedded template | `reasoning_effort` outside {xhigh,medium,low} | `xhigh` by default | Blank-`<think>` duplication | Retains history thinking |
|---|---|---|---|---|---|
| Qwen3.8-27B — `architect_general` | 9,993 B `12827f24b742` | **raises** on `none`; `high` silently → `xhigh` | **yes** | **yes** | yes |
| Qwen3.6-27B — `coder_escalation` | 8,057 B `55d4931433fe` | ok | no | no | **no — discards** |
| Qwen3.6-35B-A3B — `frontdoor` | 8,057 B (byte-identical to above) | ok | no | no | **no — discards** |
| Qwen3.5-122B-A10B — `architect_critic` | 7,992 B `8452ca85cb1e` | ok | no | no | **no — discards** |

Four models, **three distinct templates**. Consequences worth carrying:

- **We do not serve stock Qwen templates.** Every one of these is an Unsloth-patched variant (the
  Qwen3.8 one ends `{#- Unsloth fixes - developer role, merged system messages, tool calling #}`);
  stock `Qwen/Qwen3.8-27B` is 8,952 B. No registry descriptor records this.
- **`reasoning_effort` is a live footgun on Qwen3.8 only.** Stock *raises* on `high`; our Unsloth
  variant silently *coerces* `high → xhigh`. An OpenAI-style client sending the ordinary value
  `high` therefore gets a hard 500 upstream and silent maximum-effort reasoning here — opposite
  failure modes. Both raise on `none` and `minimal`.
- **The `xhigh` default injects tokens.** With no kwargs, Qwen3.8 renders 345 B including a
  209-character reasoning instruction; at `medium` it renders 136 B.
- **All of the above sit INSIDE the `enable_thinking` gate.** Our stack-wide
  `chat_template_kwargs.enable_thinking: false` makes every one of them unreachable — which is why
  the fleet is not currently exposed, and why that setting is load-bearing beyond loop prevention.
- **Three of four incumbents discard history reasoning entirely**, in both history shapes
  (`reasoning_content` field and inline `<think>` tags). Inert under `enable_thinking=false`; it
  becomes a prefix-cache question the moment any role runs thinking-ON.

## The template is compiled once at model load, not per request

Verified in frozen `production-consolidated-v9` (`/mnt/raid0/llm/llama.cpp` @ `0db32c06e`):
`common_chat_templates_init` has exactly one server call site,
`tools/server/server-context.cpp:1454`; the per-request path is
`oaicompat_chat_params_parse` → `common_chat_templates_apply` (`server-common.cpp:1092`), which
renders an **already-compiled** program. So template *parse* cost is a one-time cost at startup and
cannot affect steady-state throughput. Render cost is AST-shaped (the runtime traverses the compiled
program by recursive `execute(ctx)` per node) but is sub-millisecond and invisible against prefill.

**This is the standing refutation of "flatten the template AST to speed up inference" claims.**

## The engine is `common/jinja/`, NOT minja

A grep for `minja` in the production tree returns three hits and **every one is stale** — a TODO
comment at `common/chat.cpp:749`, a test, and a doc. The actual engine is first-party, at
`common/jinja/` (lexer / parser / runtime / value / caps), introduced upstream in
ggml-org/llama.cpp PR#18462 and inspired by huggingface.js's jinja package.

It implements **input marking** as a security property: `jinja::string` carries an `is_input` flag
through one-to-one, one-to-many and many-to-one transformations so user content cannot forge special
tokens, and `common/chat.cpp` normalises input *before* it reaches the runtime
(`common/jinja/README.md`). **A chat template is executable code in the prompt-construction
position** — substituting a third-party template moves that code and must be checked against this
path. No community template repository mentions it.

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

## Open Questions

- Which template invariants should be promoted into automated per-role startup attestations?
  The 2026-08-21 sweep makes three concrete candidates: the embedded-template digest per role, a
  `reasoning_effort` round-trip probe, and a stock-vs-served divergence check.
- Should any role run thinking-ON with history retention, which is the only configuration where the
  incumbents' discard behaviour costs anything? Tracked as CT-5 in
  `handoffs/active/qwen-chat-template-evaluation.md`.

## Related Categories

- [LLM Prompting](llm-prompting.md)
- [Model Serving](model-serving.md)
- [Tool Implementation](tool-implementation.md)

## Source References

- `src/api/routes/chat_utils.py`
- `src/backends/llama_server.py`
- `src/llm_primitives/backend.py`
- `scripts/server/stack_numa.py`
- `progress/2026-05/2026-05-22.md`
- `progress/2026-05/2026-05-23.md`
- `handoffs/active/model-stack-single-source-update-pipeline.md`
- `handoffs/active/qwen-chat-template-evaluation.md` (2026-08-21) — the fleet sweep, the defect
  matrix, and the template-swap decision
- `progress/2026-08/2026-08-21-research-intake.md` (2026-08-21)
- `research/intake_index.yaml` — intake-1212, intake-1213, intake-1216 (dive-verified /
  dive-overturned; digests and per-claim anchors recorded there)
- `/mnt/raid0/llm/llama.cpp` @ `0db32c06e` — `tools/server/server-context.cpp:1454`,
  `tools/server/server-common.cpp:1092`, `common/jinja/README.md`

## Compiled Update — 2026-08-21 (evening): CT-5(c) measured — at a 4K budget thinking does not pay, and the deficit is a truncation artifact, not a capability fact

The (c) arm ran to completion on the MI210 (60 paired gpqa_diamond_cot, Qwen3.8-27B, v9 HIP
residency proven by three instruments, 0 errors). Two-part result, then a same-day correction that
changes what it may be cited for:

1. **The R2d think-loop tail did NOT reproduce** on Qwen3.8 — non-termination 19/60 (thinking OFF)
   vs 21/60 (ON): mode-independent, driven by the 4,096 cap plus the suite's own CoT prompt.
2. **Thinking-ON failed to pay at this operating point**: 63.3% vs 70.0% accuracy, paired flips 7:3
   against (n.s., McNemar p≈0.34), +23% tokens-per-solved. Posture (a) stands; (c) declined for
   deployment.
3. **THE CORRECTION (operator-prompted): the 6.7pp deficit is ENTIRELY a truncation/budget
   artifact.** Completed-subset accuracy is 95.1% vs 94.9% (paired both-completed flips 1:0);
   every truncated thinking row is an automatic zero (0/21 ever emitted an answer line; truncated
   rows' median think 11,078 chars vs 3,187 completed). Public Qwen thinking numbers run ~32K
   budgets where truncation ≈ 0. **So CT-5(c) answered the OPERATING-POINT question (at 4K total,
   thinking does not pay) — NOT the capability question.** Prior anti-reasoning findings here
   (+33pp no-think, R2d tails) were broken-serving artifacts on other models; reasoning has never
   been measured on this stack with working serving AND adequate budget. A symmetric-16K rerun was
   launched the same day; until it reports, cite this measurement only with the operating-point
   scope attached.

**Standing citation rule this creates: never cite a thinking-vs-no-thinking accuracy delta without
its token budget and per-arm truncation rates.** A capped budget converts runaway thinking into
automatic zeros and manufactures an anti-reasoning result that vanishes on the completed subset —
the survivorship-bias shape, inverted.

### Source References

- [`handoffs/active/qwen-chat-template-evaluation.md`](../handoffs/active/qwen-chat-template-evaluation.md) — CT-5 ✅ full result + correction + operator ruling; 16K rerun tracking
- `artifacts/chat-templates/ct5c-gpu-20260821/` — per-question JSONL, paired ids, server log

## Compiled Update — 2026-08-23: Qwen3.8 template evaluation + CT-5c/ab-cpu runs

**Confidence: verified** for the measured arms and the rendered proofs; `inference` for the E-7
stamp-gap recommendation (extension from the intake-892 precedent, sound but not yet ratified
doctrine).

The CT-5(c) 4K/16K arms and the CT-1b ab-cpu terseness arms are compiled above (2026-08-21); this
section adds what landed around and after them — the calibration-price inventory, the injection
verdict on the community templates, the EPYC-owned build, the live deployment, and the first
decision-gating stamps.

- **CT-2 — a template swap is not a config change, and it voids the calibration this stack was
  measured under.** `--chat-template-file` has **zero occurrences** in the orchestrator's launcher
  and registry code, so every measured row this stack owns was produced through each model's
  GGUF-embedded template and there is **no already-swapped control arm anywhere**. The flag exists
  in the frozen kernel (`common/arg.cpp:3487`) — adoption needs new launcher plumbing, priced as a
  prerequisite of adoption, not of the swap. A stack-wide swap voids **4 expensive / 5 moderate /
  2 cheap** artifacts — and the expensive four (SWE-verified oracle-40, the R2a +32pp CoT-prompt
  result, GPQA/LCB, the certified reasoning-effort curves) are the entire comparative authority of
  `architect-model-selection-bench.md`. A **single-role pilot** voids only that role's slice.
  Related gap, still open: the E-7 re-calibration stamp `(model, quant, kernel/era)` omits the
  template, yet the prompt-template axis is the *larger* measured effect so far — a swap would pass
  E-7's validator silently; `template_sha256` belongs in the stamp (recorded as a cross-handoff
  finding for `reasoning-effort-levels.md`).
- **CT-3 — the community templates are NOT drop-in safe: they add a user-controlled thinking
  channel that input marking cannot see.** frog and sharp both scan **ten out-of-vocabulary
  `<|think_*|>` pseudo-tokens** (in neither model's vocabulary) out of `msg.content` for roles
  `{system, developer, user}` and use them to overwrite the template's own thinking state, then
  strip the markers from the rendered prompt — so a client able to place fourteen literal
  characters into a user or system message **silently revokes the stack's role-keyed
  `enable_thinking=false`** for the whole conversation, with no trace in the output. Input marking
  cannot mitigate it: `is_input` constrains what input text may *become* (tokenization); it places
  no constraint on what template **control flow** may branch on. Rendered proof at
  `enable_thinking=False`: `sharp.jinja` 797 B → 1003 B with a marker-carrying user turn (thinking
  ON, +206 B injected effort prose), `frog.jinja` 81 B → 307 B; stock and our GGUF template stay
  inert (95 B). That is a low-trust input overriding a high-trust generation policy — a direct
  cost channel (unmetered token amplification). Mitigations if adoption is ever pursued:
  delete the two marker-scan blocks (retention behaviour is independent of them), restrict the
  scan to `system`-only, or strip the markers at the orchestrator boundary.
- **CT-7 — the EPYC-owned template `epyc-qwen3x-v1` is built and validated.** Feature-mined from
  froggeric v22.3 (Apache-2.0): history retention grafted, the two `<|think_*|>` marker-scan
  blocks **deleted by construction** (the CT-3 surface), the tag sanitizer kept, terseness excluded
  (an A/B arm, not a default). 24,659 B, sha256 `faaecb215031…d8c15`; vendored suite v21 9/9, fuzz
  clean over 2,000 conversations (nine invariants), v22 85/100 with all 15 failures being the
  deliberately-deleted feature; oneline build (19,421 B) parity holds; the decisive probe — a
  user-content `<|think_off|>` flips froggeric and does NOT flip epyc-v1; and frozen v9
  `common/jinja` renders all 7 fixtures **byte-identical** to Jinja2 goldens via `/apply-template`.
- **CT-DEPLOY — the terseness pilot is LIVE IN PRODUCTION (2026-08-22)** on frontdoor (all three
  instances, render-verified) and architect_general (+ coder_escalation via alias):
  `server_mode.<role>.chat_template_file` plumbing landed (orchestrator `34ff6fcc`), registry
  blocks with per-role one-line reverts (research `b9ba66e6`), stack-change check fully green
  INCLUDING runtime attestation (declared == compiled == live cmdlines — first time). The pilot
  serves the measured arm-2 template (`1443ea9ab4bb…4551`), not the community file.
- **CT-E7 — the CT-1b numbers REPRODUCE on the live path, and architect_general gets first-ever
  stamps** at `(model, quant, v9 0db32c06e/10125, template 1443ea9ab4bb)`: frontdoor (35B, CPU)
  math 82.5% @281 tok · mmlu_pro 37.5% @45 · gpqa_diamond 55.0% @2 · cruxeval 32.5% @394 —
  live == measured. architect_general (Qwen3.8, GPU) 85.0 / 27.5 / 47.5 / 22.5%, zero errors.
  `gpqa_diamond_cot` was VOIDED at maxtok 900 by the finish_reason rule (48/60 truncated — the
  budget trap again, self-inflicted this time); the 4096 rerun supersedes: **75.0% (45/60)**,
  +45pp from the cap fix alone and ABOVE the embedded template's CT-5 baseline (70.0%) on the same
  pinned ids. All 8 valid cells emitted as producer-authored belief rows grading
  Witnessed/Attested, empty reasons — the program's first decision-gating measurements.
- **CT-8 — the belief-kernel write side is wired for this axis**: producer writer
  `chat_template_ab_capture.py` (atomic sidecar at summarize-time, fail-loud on any guessable
  field — 40-hex kernel commit, 64-hex template sha, results-file hash attestation) + strict
  reader `chat_template_ab.py` (registered `chat-template-ab-measurement`; grading 100% delegated
  to `claim_tuple.grade()`); completed CT-1/CT-1b/CT-5/16K runs are pre-hook and emit zero rows by
  doctrine.

**Standing rule the sweep reinforces:** never adopt a third-party template without auditing its
control-flow surface — the marker-scan channel is the template-era analogue of the injection
classes the engine's input marking exists to stop — and keep the compiled citation rule for
thinking-vs-no-thinking deltas (budget + per-arm truncation rates, above).

### Source References (2026-08-23 Qwen3.8 template evaluation)

- [`handoffs/active/qwen-chat-template-evaluation.md`](../handoffs/active/qwen-chat-template-evaluation.md) — CT-2/CT-3/CT-5/CT-7 closures, CT-DEPLOY/CT-E7/CT-8 records, rendered proofs and artifact digests
- [`handoffs/active/qwen38-27b-replace-qwen36.md`](../handoffs/active/qwen38-27b-replace-qwen36.md) — Q38-T1/T3: reachability of the two Qwen3.8-only defects and the non-stock Unsloth template digest
- [`progress/2026-08/2026-08-21-research-intake.md`](../progress/2026-08/2026-08-21-research-intake.md) — the intake dives, the fleet-sweep correction, CT-7 build/validation, CT-1/1b arms
- [`progress/2026-08/2026-08-22-research-intake.md`](../progress/2026-08/2026-08-22-research-intake.md) — CT-DEPLOY end state, E-7 stamps and the voided/4096-rerun cells, CT-8 wiring, belief rows
- [`progress/2026-08/2026-08-21-operator.md`](../progress/2026-08/2026-08-21-operator.md) — the coordination-day context (EVL-50 closure, four-agent fan-out) around the CT work
