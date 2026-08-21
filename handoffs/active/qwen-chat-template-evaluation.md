# Qwen Chat-Template Evaluation

**Status**: stub
**Created**: 2026-08-21 (via research intake, operator-approved 2026-08-21)
**Categories**: llm_prompting, inference_serving, local_inference

## Objective

Decide whether to move any Qwen3.x role off its GGUF-embedded chat template, and if so onto which
one — evaluated per-suite, on our own hardware, with the calibration cost priced in.

## Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-1212#record | Qwen-Sharp-Chat-Templates | high | adopt_component | dive-verified |
| intake-1213#record | froggeric/Qwen-Fixed-Chat-Templates | high | worth_investigating | dive-overturned |
| intake-1216#record | google/minja (NOT our engine) | medium | superseded | dive-overturned |
| intake-1217#record | Claw-Eval | medium | worth_investigating | dive-verified |

## What the dives already settled (do not re-litigate)

Verified 2026-08-21 against primary source — the stock `Qwen/Qwen3.8-27B` template, the
Unsloth-patched template extracted from our own `/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf`, both
community templates, and the frozen `production-consolidated-v9` tree at `0db32c06e`:

- Sharp's thinking-ON render **minus** its terseness block is **byte-identical** to upstream v22.3's
  render, verified at three kwarg settings. Thinking-OFF differs by exactly the three documented
  fixes. The whole delta against upstream is four regions.
- The upstream "official template raises on `enable_thinking=false`" claim is **false** on both the
  stock template and the Unsloth template in our GGUF. The real fatal trigger is a
  `reasoning_effort` value outside `{xhigh, medium, low}` — and that raise sits *inside* the
  `enable_thinking` gate, so our stack-wide `enable_thinking=false` posture is immune to it.
- The "80% llama.cpp throughput" claim cannot hold: the template is compiled **once at model load**
  (`common_chat_templates_init`, sole server call site `tools/server/server-context.cpp:1454`), and
  the per-request path renders an already-compiled program (`server-common.cpp:1092`). Render *is*
  AST-shaped, but upstream's template is 3.0x larger and deeper than stock, so that mechanism runs
  against it.
- Thinking retention **IS** a differentiator, and it splits our fleet. Sweeping the template embedded
  in every production GGUF (see the table below): Qwen3.6-27B, Qwen3.6-35B-A3B and Qwen3.5-122B all
  **discard history thinking entirely** — both the inline `<think>` shape and the `reasoning_content`
  shape — while Qwen3.8-27B, froggeric and Sharp all retain it. *(An earlier pass tested only the
  Qwen3.8 generation and wrongly concluded retention was not a differentiator; corrected 2026-08-21.)*
- Sharp's only quantified plate is measured on **Claw-Eval, an agent-trajectory benchmark**, not on
  knowledge-work or coding accuracy — and the figures themselves exist only inside a PNG.

## Fleet sweep — the embedded template of every production model (2026-08-21)

Extracted by GGUF header read, no model loaded. **Three distinct templates across four models.**

| Model / role | Template | `enable_thinking=false` | `reasoning_effort` outside {xhigh,medium,low} | `xhigh` by default | Empty-`<think>` duplication | Retains history thinking |
|---|---|---|---|---|---|---|
| Qwen3.8-27B — `architect_general` (per stack template) | 9,993 B `12827f24b742` | ok | **RAISES** on `none`; `high` silently → `xhigh` | **yes** | **yes** | yes |
| Qwen3.6-27B — `architect_general`/`coder_escalation` (per master registry) | 8,057 B `55d4931433fe` | ok | ok | no | no | **no — discards** |
| Qwen3.6-35B-A3B — `frontdoor` | 8,057 B `55d4931433fe` (byte-identical to above) | ok | ok | no | no | **no — discards** |
| Qwen3.5-122B-A10B — `architect_critic` | 7,992 B `8452ca85cb1e` | ok | ok | no | no | **no — discards** |

Two conclusions, opposite in direction:

- **Every defect is Qwen3.8-only.** The `xhigh` default, the `reasoning_effort` raise/coercion and
  the empty-`<think>` duplication do not exist on the three incumbent templates. Those are scoped to
  the model swapped in 2026-08-20 and are tracked in `qwen38-27b-replace-qwen36.md`.
- **The retention gap is the incumbents', not Qwen3.8's.** The three incumbent templates throw away
  past reasoning. That is precisely what the community templates fix, and it is the one claim in
  intake-1213 that holds against our actual fleet.

**But it is currently inert for us**, and that is the crux: we serve
`chat_template_kwargs.enable_thinking: false` on every one of these roles, so there is no reasoning
in history to retain. The retention fix only pays if thinking is turned ON for a role — a much
larger change than a template swap, and one this handoff does not assume.


### CT-2 — calibration void inventory (2026-08-21)

**Framing finding, and it decides most of the table:** every measured row this stack owns was produced
through each model's **GGUF-embedded** template. There is no alternative — `--chat-template-file` has
**zero occurrences** in the orchestrator's launcher and registry code (`grep -rn "chat.template.file\|chat_template_file" src/ orchestration/ stack_templates/` → 0 hits; only `chat_template_kwargs` is
plumbed, `src/backends/llama_server.py:581-594`, `src/backends/openai.py:267-284`). The architect-bench
run protocol records server flags with no template override
(`handoffs/active/architect-model-selection-bench.md:218`). So "which arms were measured under which
template" has one answer: **all of them, under the embedded one.** A swap therefore moves *every* row
below off its measured condition simultaneously — there is no already-swapped control arm anywhere.

**Second framing finding: adopting a community template is not a config change.** The flag itself
exists in the frozen kernel (`common/arg.cpp:3487`, `{"--chat-template-file"}, "JINJA_TEMPLATE_FILE"`)
— it is the **orchestrator** that never emits it. So CT-1 is runnable by hand against a directly-invoked
`llama-server`, but *adoption* needs new launcher plumbing. Cost that as a prerequisite of adoption, not
as part of the swap, and note it does **not** block CT-1.

**Third: two rows are already void, before any template question.** The master registry names
`Qwen3.6-27B-MTP-Q8_0` for `architect_general` (`orchestration/model_registry.yaml:1766`) and
`coder_escalation` (`:1655`), while `stack_templates/default.yaml:139` launches **`Qwen3.8-27B-Q8_0`**
(commit `1cff5162`). The registry contains **zero** occurrences of `Qwen3.8` (`grep -n "Qwen3\.8"` → 0;
a bare `grep "Qwen3.8"` returns 4 false hits, all `Qwen3-8B-DFlash-b16` at `:506-511`, where `.` matched
`-`). Under the reasoning-effort-levels invariant — *"a role default is a (model × level) pair. Swapping
the model bound to a role … invalidates the level"* (`handoffs/active/reasoning-effort-levels.md:51-52`)
— the `swe_verified_pct: 57.5` rows at `:1689` and `:1826` are stamped to a model the role no longer
runs. **This is the intake-892 precedent's shape**: intake-892 established that a weights-level change
to reasoning emission is *a different model*, not a dial setting on the same one. A template change is
the same category of change applied to the prompt side. *(UNVERIFIED: I found no text anywhere in the
repo that states the "template change ⇒ different model" precedent in those words —
`grep -rn "different model" handoffs/active/ agents/ docs/` returns nothing template-related. The
extension from intake-892's weights case to the template case is an inference, sound but not yet
ratified doctrine.)*

**Fourth, and this is the actionable gap:** the E-7 re-calibration trigger stamps each certified curve
with `(model, quant, kernel/era)` and fires on *"a model swap, quant change, or kernel promotion"*
(`handoffs/active/reasoning-effort-levels.md:351-355`). **The chat template is not in the stamp and not
in the trigger list** — yet `architect-model-selection-bench.md:267` already ruled that the prompt-template
axis *"is a prompt-template property of each role, not a server flag, and it is the larger effect measured
so far"* (+32pp, `:264-267`). A template swap today would pass E-7's validator silently. Recommend adding
`template_sha256` to the E-7 stamp; that is a cheap fix and it belongs to the reasoning-effort handoff, so
it is recorded here as a cross-handoff finding rather than actioned.

| Artifact | Where it lives | Voided by template swap? | Re-measurement cost |
|---|---|---|---|
| SWE-bench Verified oracle-40 sealed rows (A3 `23/40` = 57.5%; comparators A1 `15/40`, A4 `13/40`, TC `21/40`) | `model_registry.yaml:1689`, `:1826`; `architect-model-selection-bench.md:3` | **YES** — accuracy is measured through the rendered prompt end to end | **expensive** (sealed capture + frozen v4 converter replay per arm) |
| R2a CoT-prompt **+32pp** result | `architect-model-selection-bench.md:264-267` | **YES** — this *is* the prompt-template axis by the handoff's own words | **expensive** |
| R2d `enable_thinking=false` stack-wide vindication (A1 18% / A4 50% non-termination) | `architect-model-selection-bench.md:333-353` | **PARTIAL** — the finding is about the *native channel*, but frog/sharp can flip that channel ON from message content (CT-3) and inject their own effort prose, so the ablation's "thinking OFF" arm is no longer guaranteed to be OFF | **moderate** (re-run the ablation, 2 arms) |
| GPQA-Diamond CoT / letter-only, LiveCodeBench `24/53` | `architect-model-selection-bench.md:113`, `:198`, `:572` | **YES** | **expensive** |
| `q_scorer` **`baseline_tps_by_role`** | `orchestration/repl_memory/q_scorer.py:368`, compiled via `src/registry/stack_priors.py`; registry `:1631`, `:1684`, `:1819`, `:1882` | **NO** — the canonical baseline instrument is `llama-bench`, which never renders a chat template | **cheap** (and not needed) |
| `q_scorer` **`baseline_quality_by_role`** / `quality_pct` 93, `quality_score` 2.57/3 | `q_scorer.py:369`; registry `:1634`, `:1886` | **YES** — quality priors are scored on rendered prompts | **moderate** |
| `optimized_tps` 47.79 / 40.22 / 24.0, `contended_tps` 19.81 | registry `:1633`, `:1687`, `:1822` (attest `P-BENCH-PLACEMENT-1`, published stack record §01) | **PARTIAL** — steady-state decode is bandwidth-bound and prompt-insensitive, but a template that adds a 209-char system preamble (or turns thinking on) changes prefill share and output length, which moves the end-to-end figure | **cheap** (re-run the pinned prodopt harness) |
| `draft_max` spec-dec optimum — registry **4** vs stack override **8** | registry `:1793`, `:1876`, `:1626`; `stack_templates/default.yaml:154` | **PARTIAL** — production runs `--spec-type draft-mtp`, MTP self-draft alone (`speculative_decoding_policy`, `:1271-1280`). Self-draft acceptance is a property of the *token stream*, and a template that enables thinking changes that stream's character wholesale (reasoning prose drafts differently from answer prose) | **moderate** (one draft-depth sweep per affected role) |
| Certified reasoning-effort curves | `reasoning-effort-levels.md:49-56`, E-7 `:351-355` | **YES** if thinking is enabled; **PARTIAL** otherwise — and note the stamp does not currently include the template (gap above) | **expensive** |
| Saved KV prefix slots (`slot_save_path: /tmp/kv_frontdoor_full`) | `stack_templates/default.yaml:91` | **YES** — any byte change to the rendered prefix invalidates every saved slot | **cheap** (self-healing; slots simply re-warm) |
| TB-6 np×L context-batching surface, prefill-to-depth RAG arms | `architect-model-selection-bench.md:536`, `:562` | **PARTIAL** — explicitly throughput-only observations, but they were captured no-think and a template that can flip thinking on changes generated length per cell | **moderate** |
| `swe_verified_shape_caveat` (measured `-c 49152`/f16 KV/`-np 1`; production `-c 16384`/q8_0/slots 2) | registry `:1831` | **PARTIAL** — already an assumed transfer; a template swap adds a second unmeasured transfer on top of it | n/a (compounds an existing caveat) |

**Cost summary.** A stack-wide swap voids **4 expensive** artifacts (SWE-40, +32pp CoT, GPQA/LCB,
effort curves), **5 moderate**, and **2 cheap/none**. The expensive four are the entire comparative
authority of `architect-model-selection-bench.md`. A **single-role pilot** voids only that role's slice
and leaves the cross-arm comparisons intact — which is the whole argument for CT-5 option (b)/(c) over a
fleet swap.

### CT-3 — input-marking analysis of the community templates (2026-08-21)

Method: `common/jinja/README.md` (frozen tree, read-only) names two caveats; both templates were grepped
for those shapes and then **rendered** with Jinja2 3.1.6 from the orchestrator venv with `raise_exception`
stubbed, `enable_thinking=False`, against stock and our GGUF template as controls.

First, input marking **is active** on the serving path: `mark_input = true` is the default
(`common/chat-auto-parser.h:73`) and is passed straight through at `common/chat.cpp:920` →
`jinja::global_from_json(ctx, inp, inputs.mark_input)`. So the defence is on and the question is fair.

| Pattern | frog | sharp | stock / our GGUF | Risk under input marking | Verdict |
|---|---|---|---|---|---|
| Special token **built by concatenation** from a message field — the README's literal caveat `'<\|' + message['role'] + '\|>'` | no | no | no | n/a | **CLEAN.** Stock and our GGUF do `'<\|im_start\|>' + message.role + '\n'` (`stock:109,117,119`; `qwen38_official:112,120,122`) — the token is a **whole literal** in one non-input part, with role appended *after* it, so it is not the caveat shape. frog/sharp put role in a plain-text label inside a user turn: `'<\|im_start\|>user\n[' + message.role + ']: '` (`frog:410`, `sharp:426`) — role never touches a token boundary at all, which is marginally **safer** than stock |
| Template-added leading space (`' ' + content`) — README caveat 2 | 0 | 0 | 0 | n/a | **CLEAN** across all four (grep count 0 each) |
| **In-band control markers parsed out of user content** | **YES** | **YES** | **no** | **Input marking does NOT mitigate this** | **HIGH — see below** |
| Tool-call instruction blocks embedding special-token-like literals (`<tool_call>`, `<tool_response>`, `<function=`, `<parameter=`, `<IMPORTANT>`) | yes | yes | partial | Low — all are template literals (`is_input=false`), and per the tokenizer `<tool_call>`/`</tool_call>`/`<tool_response>`/`</tool_response>` are added tokens with **`special=False`**, while `<function=`/`<parameter=`/`<IMPORTANT>` are not tokens at all | **LOW** (`sharp:188-197`) |
| Tool **name** interpolated between literal grammar markers: `'<tool_call>\n<function=' + tc_name + '>'` | yes | yes | no | Not a special-token issue (`<function=` is not a token), so input marking is silent on it; it is a plain-text **grammar** injection — a `tc_name` containing `</function>` closes the block early | **MEDIUM** (`sharp:347,349,352`) |

#### Headline: this is NOT a clean result — frog and sharp add a user-controlled control channel

Both templates define **ten pseudo-tokens** — `<|think_off|>`, `<|think_on|>`, `<|think_low|>`,
`<|think_minimal|>`, `<|think_medium|>`, `<|think_high|>`, `<|think_xhigh|>`, `<|think_max|>`,
`<|think_extreme|>`, `<|think_ultracode|>` — that exist in **neither model's vocabulary**. The stock
`tokenizer_config.json` has 33 `added_tokens_decoder` entries and the only `think`-bearing ones are
`<think>` / `</think>`; no `<|think_*|>` string appears anywhere in it.

They are not emitted. They are **scanned out of `msg.content`** and used to overwrite the template's own
thinking state (`sharp:38-49` for string content, `:62-73` for multimodal text parts; identical block at
`frog:38-49`, `:62-73`), and the scan is gated to `msg.role in {system, developer, user}` — i.e. it
**includes the untrusted user turn**. The markers are then stripped from the rendered prompt
(`sharp:147-156`, `:234-243`; `frog:147-148`, `:218-219`), so the override leaves **no trace in the
output**.

Crucially the marker scan runs **after** the kwargs are resolved and after
`auto_disable_thinking_with_tools` (`sharp:31-34`), so **message content wins over server configuration.**

**Rendered proof** (`enable_thinking=False` passed explicitly, as our stack does on all four roles):

| Template | benign user turn | user turn containing `<\|think_max\|>` |
|---|---|---|
| `sharp.jinja` | 797 B, ends `<think>\n\n</think>\n\n` → thinking **OFF** | **1003 B, ends `<think>\n` → thinking ON**, +206 B of injected effort prose, marker stripped |
| `frog.jinja` | 81 B, thinking **OFF** | **307 B, thinking ON**, marker stripped |
| `qwen38_official.jinja` | 81 B, OFF | 95 B, **still OFF** — marker passes through as inert text |
| `stock_chat_template.jinja` | 81 B, OFF | 95 B, **still OFF** — inert |

Scope, by injecting role (both community templates behave identically):

| Injection point | flips thinking? | marker visible in prompt? |
|---|---|---|
| `user` (last turn) | **yes** | no (stripped) |
| `user` (turn 1 of 3) | **yes** | no |
| `system` | **yes** | no |
| multimodal `{"type":"text"}` part | **yes** | no |
| `assistant` | no | yes |
| `tool` | no | yes |

**Why input marking cannot help here.** `is_input` is a provenance flag on the *output* string parts,
consumed downstream by the tokenizer to decide what may parse as a special token. It constrains what
input text can *become*; it places no constraint on what the template's **control flow** may branch on.
`{%- if '<|think_off|>' in msg.content %}` is an ordinary Jinja string test against an input-marked
string, and it evaluates exactly the same whether the flag is set or not. The engine's defence is
correctly scoped and simply does not cover this class. **The hazard is upstream of the mechanism the
README describes, so a swap does not weaken input marking — it adds a channel that input marking was
never designed to see.**

**Impact on our posture.** The stack sets `chat_template_kwargs.enable_thinking: false` role-keyed on
`architect_general`, `coder_escalation`, `frontdoor` and `architect_critic`. Under frog or sharp, **any
client able to place fourteen literal characters into a user or system message silently revokes that
setting** for the whole conversation — turning on a reasoning channel that
`architect-model-selection-bench.md:342` measured as *worse on quality and 2.8–6× the tokens*. That is a
low-trust input overriding a high-trust generation policy, with no audit trace in the prompt. It is also
directly a **cost** channel: unmetered token amplification triggerable from message content.

**Mitigations, if adoption is ever pursued** (cheap, and they preserve the retention fix that motivated
these templates): (i) delete the two marker-scan blocks and the ten strip lines — the retention behaviour
is independent of them; (ii) or restrict the scan to `msg.role == 'system'` only; (iii) or strip
`<|think_*|>` from message content at the orchestrator boundary before the request leaves
`src/backends/llama_server.py`. Option (i) is the smallest diff and is what CT-4's pinning should record
if anything is adopted.

**Verdict: sharp and frog are NOT drop-in safe.** The finding is independent of the terseness question
and independent of retention, and it applies to both community templates equally.

### CT-5 decision package (drafted 2026-08-21, operator decision pending)

**The question, stated narrowly.** Not "should we swap templates" and not "is the terseness prompt good".
Only: **should any role run `enable_thinking=true` with prior-turn reasoning retained in history?**
Retention is inert at `enable_thinking=false`, so retention has no value of its own — it is a rider on a
thinking-ON decision, and it must be decided in that order.

**Two facts reframe the options before the options start.**

1. **Retention does not require a community template.** `Qwen3.8-27B` — the model
   `stack_templates/default.yaml:139` actually launches on `architect_general` — **already retains
   history thinking with its own embedded template.** Rendered proof: with
   `enable_thinking=True` and an assistant turn carrying `reasoning_content`, `qwen38_official.jinja`
   emits the prior reasoning (`retains_prior_reasoning=True`), while `Qwen3.6-27B-MTP-Q8_0.gguf.jinja`
   and the `Qwen3.5-122B` template both drop it (`False`, `False`). So the retention fix that motivates
   frog/sharp is **already in the tree**, on the one role most likely to want it, at zero template risk.
2. **Turning thinking ON unlocks the Qwen3.8 defects, which are currently unreachable.** Rendering
   `qwen38_official.jinja` across `reasoning_effort ∈ {none, minimal, low, medium, high, xhigh, unset}`:
   at `enable_thinking=False` **all seven render fine** (71 B each). At `enable_thinking=True`,
   `none` and `minimal` **raise** (`Unexpected reasoning effort …`), `high` silently renders identically
   to `xhigh` and to the default (297 B each, vs `medium` 60 B, `low` 226 B). The stack's immunity to
   these is *entirely* a side effect of thinking being off. **Any thinking-ON pilot must first fix the
   request path to never send `none`/`minimal`, or it will return 500s in production.**

**Option (a) — status quo: `enable_thinking=false` everywhere; retention moot.**
- *Cost:* zero. No calibration voided (CT-2 table untouched).
- *Pays:* keeps the R2d vindication (`architect-model-selection-bench.md:333-353`) and the +33pp
  frontdoor no-think finding intact and load-bearing; keeps the Qwen3.8 `reasoning_effort` raise
  unreachable; keeps every sealed SWE/GPQA/LCB row on its measured condition.
- *Gated by:* nothing. This is the null action.
- *Risk:* the only thing forgone is an **unmeasured** upside. Note also that R2d certified the thinking
  axis on **A1 (122B-IQ2)** and **A4 (35B-A3B)** — *not* on the 27B dense, and certainly not on
  Qwen3.8-27B. Under `reasoning-effort-levels.md:49-50` ("certified per model"), `architect_general`'s
  current thinking-OFF setting is an **uncertified inheritance**, not a measured result for its model.

**Option (b) — pilot thinking-ON + retained history on ONE role, with a community template.**
- *Natural pilot, by elimination:* `coder_escalation` **cannot** be piloted independently — it is
  `alias_to: architect_general` (`stack_templates/default.yaml:101`), one process under two names.
  `frontdoor` is the worst candidate: highest traffic, holds the saved KV prefix slots
  (`default.yaml:91`), and owns the strongest contrary evidence (+33pp no-think). `architect_general`
  carries the most calibration at risk (the entire SWE-40 authority row). That leaves **`architect_critic`**
  (`model_registry.yaml:1851`, 122B on CPU `:8074`, own process, terminal escalation rung, lowest traffic)
  as the only role that is independently pilotable with a small calibration slice — it has no
  `swe_verified` row and no `quality_pct`, only `quality_score: 2.57/3` (`:1886`) and `baseline_tps: 11.3`.
  A critic is also, on its face, the role where retained reasoning should pay most.
- *Cost:* new `--chat-template-file` launcher plumbing (does not exist today — CT-2); voids
  `architect_critic`'s `quality_score` and its `draft_max: 4` (`:1876`); **and accepts the CT-3 injection
  channel into production.**
- *Pays:* prefix-cache hit on multi-turn critic exchanges; the untested quality delta from retained
  reasoning.
- *Gated by:* CT-1's A/B, **plus** a CT-3 mitigation landing first.
- *Verdict as drafted:* **not recommended.** It is the most expensive option (new plumbing + eval on the
  slowest model at 11.3 t/s baseline) and it is the only option that imports the CT-3 hazard. Its one
  distinctive benefit — retention — is available for free under option (c).

**Option (c) — thinking-ON with the STOCK/embedded template, on `architect_general` (Qwen3.8-27B).**
- *Cost:* voids `architect_general`'s `quality_score`/`swe_verified` slice — **which CT-2 shows is
  already void**, since those rows are stamped to `Qwen3.6-27B` (`:1766`, `:1826`) and the role launches
  `Qwen3.8-27B`. So the marginal calibration cost is close to zero: it re-measures a row that must be
  re-measured anyway. Also requires the `reasoning_effort` request-path fix (fact 2 above), and a
  `draft_max` re-check (`default.yaml:154` is `8`, swept on Qwen3.8 but swept **no-think**).
- *Pays:* retention on multi-turn architect exchanges with **no third-party code in the prompt-construction
  position**; no new launcher plumbing; the Qwen3.8 `xhigh`-by-default 209 B instruction becomes a lever
  rather than a latent defect.
- *Gated by:* CT-1's A/B, run on this model — and CT-1 becomes *cheaper* here, because it is a
  `chat_template_kwargs` flag flip rather than a template swap.
- *Risk:* R2d says native `<think>` lost on two other models via a non-termination tail (18%/50%). That
  is real prior evidence against, but it is **not evidence about this model**, and the
  `--reasoning-budget N --reasoning-budget-message` lever that `reasoning-effort-levels.md:359-362`
  records as force-closing the think block is available to bound the tail.

**Recommendation.** Hold **option (a)** as the standing posture, and authorise **option (c) as a
measurement only** — not a stack change — on `architect_general`. Rationale: it is the only option whose
calibration cost is already sunk, the only one needing no new code, and the only one that gets retention
without importing the CT-3 injection channel. **Option (b) should be declined outright** unless CT-3's
mitigation (i) is applied and pinned under CT-4. Reject any *fleet-wide* thinking-ON change regardless of
outcome — the three incumbent templates discard history, so retention would not even function on
`frontdoor` or `architect_critic` without the template swap that option (b) prices.

**Single cheapest discriminating measurement.** On `architect_general` (Qwen3.8-27B, already loaded), run
the pinned GPQA-Diamond-CoT item set twice — `enable_thinking=false` vs `enable_thinking=true` with
`reasoning_effort=medium` and `--reasoning-budget` set — reporting **per-suite, never aggregate**, with
non-termination rate and tokens-per-solved captured alongside accuracy. It is a two-arm flag flip on a
resident model, it needs no launcher change and no template file, it directly tests the one claim
option (c) rests on (does *this* model's native channel behave like A1/A4 did?), and its result is
decision-sufficient: if the non-termination tail reproduces on Qwen3.8, retention is dead for the whole
fleet and CT-5 closes at option (a) permanently.

**Prerequisite before that run:** confirm the request path cannot emit `reasoning_effort` of `none` or
`minimal`, which raise once thinking is on (fact 2). That check is grep-cheap and is not gated on
anything.

## Open Questions

- Does the terseness prompt help, hurt, or do nothing on *our* suites at `enable_thinking=false`,
  where there are no thinking tokens to cut?
- What does a template swap cost in voided calibration? Architect-bench arms, `q_scorer`
  baselines and reasoning-effort settings were all measured under the current template.
- A chat template is executable code in the prompt-construction position, sitting on top of the
  in-tree engine's **input-marking** defence against special-token injection
  (`common/jinja/README.md`). What does a third-party template do to that property?

## Tasks

- [ ] **CT-1** — A/B one Qwen3.x role via `llama-server --chat-template-file` — arms per CT-1a (the
      built epyc-qwen3x-v1, not the community file) — against its embedded
      template on a pinned eval set. Report **per-suite, never aggregate** (intake-1214: a
      conciseness instruction near-neutral in aggregate carried a 27.69% math penalty for the
      weaker model). No requantization, no registry change, no kernel touch.
- [x] **CT-2** — Price the calibration cost before any stack-wide swap: enumerate which measured
      artifacts (architect-bench arms, `q_scorer` baselines, draft-depth settings) are voided by
      changing the rendered prompt. ✅ 2026-08-21 (inventory above: 4 expensive / 5 moderate / 2 cheap
      voids; every measured row in the fleet was captured under the embedded template because
      `--chat-template-file` has zero occurrences in the orchestrator; `architect_general` +
      `coder_escalation` SWE rows are ALREADY void on the registry/stack-template model divergence; and
      the E-7 re-calibration stamp omits the template entirely)
- [x] **CT-3** — Check a third-party template against the in-tree input-marking path
      (`common/jinja/`, and the input normalisation `common/chat.cpp` applies before the runtime).
      ✅ 2026-08-21 (NOT clean: neither README caveat fires, but frog and sharp both parse ten
      out-of-vocab `<|think_*|>` markers out of user/system message content, silently overriding
      `enable_thinking=false` and stripping the marker — input marking cannot see it, because it
      constrains tokenization, not template control flow. Rendered proof in the analysis above)
- [ ] **CT-4** — If anything is adopted, pin the exact revision + sha256, not a branch.
- [ ] **CT-5** — Decide the retention question on its own merits, separately from the terseness
      prompt. The three incumbent templates discard history reasoning; the community templates keep
      it. Under `enable_thinking=false` this changes nothing, so the real question is whether any
      role should run thinking-ON with retention — which is where the prefix-cache argument would
      pay and where the reasoning-budget work in `per-request-reasoning-budget.md` already lives.
      Do not bundle this with CT-1. *(package drafted 2026-08-21, awaiting operator — see
      "CT-5 decision package" above; recommendation is hold status quo + authorise a measurement-only
      thinking-ON A/B on `architect_general`, and decline the community-template pilot on CT-3 grounds)*
- [x] **CT-6** — Sweep the embedded template of every production GGUF and tabulate the defect
      matrix ✅ 2026-08-21 (table above; three distinct templates, all defects Qwen3.8-only, the
      retention gap incumbent-only)
- [x] **CT-7 — Build the EPYC-owned template (operator-directed 2026-08-21: "we build them ourselves
      if they're valuable to us").** Do not wait on or track community releases. Feature-mine
      froggeric v22.3 under Apache-2.0: graft **history retention** (the one mechanism our three
      incumbent templates lack) onto our serving posture, **minus the two `<|think_*|>` marker-scan
      blocks by construction** (the CT-3 injection surface — a deliberate upstream feature we do not
      want), terseness block **excluded** from v1 (it is the unmeasured ingredient; it becomes an
      A/B *arm*, not a default). Validate: render-equivalence probes (retention holds in both history
      shapes; a user message containing `<|think_off|>` does NOT change reasoning state;
      `enable_thinking=false` path clean), then the vendored upstream test suite with divergences
      recorded the way Sharp's shim documents its own. Pin sha256. Artifact home:
      `artifacts/chat-templates/epyc-qwen3x-v1/`.
      **BUILT + probe-verified ✅ 2026-08-21** — 24,659 B, sha256 `faaecb215031…d8c15`; scan loop
      (46 lines) deleted, sanitizer kept; all four probes pass incl. the decisive one (user-content
      `<|think_off|>` flips froggeric, does NOT flip epyc-v1) and byte-parity with base on tag-free
      input. **COMPLETED ✅ 2026-08-21 (all sub-items):** vendored suite run — v21 9/9, fuzz clean
      over 2,000 conversations (nine invariants), v22 85/100 with ALL 15 failures being the
      deliberately-deleted inline-tag feature; oneline build generated (19,421 B, parity holds); and
      the REAL-ENGINE check — frozen v9 `common/jinja` via `/apply-template` rendered all 7 fixtures
      **byte-identical** to Jinja2 goldens, injection dead and retention alive on the actual serving
      path. Validation record: `artifacts/chat-templates/epyc-qwen3x-v1/README.md`.
- [ ] **CT-1a — idle-window protocol (operator-directed 2026-08-21).** CT-1's A/B and PRB-T4 run on
      **CPU inference during the autokernel session's GPU-busy windows** — do not wait for a dedicated
      slot. Protocol: acquire a CPU region claim on the session bus before serving (claims are
      acquired, never observed); serve the A/B model CPU-side (Qwen3.6-35B-A3B or 27B); production
      sampling (temp+seed42 — these suites are sampling-sensitive); per-question JSONL persistence so
      any window end is a clean drain point; per-suite reporting. Arms for CT-1: (0) embedded
      template, (1) CT-7's epyc-qwen3x-v1, (2) optionally +terseness variant. Gated on CT-7 for the
      arm-1 artifact.

## Notes

Any adoption must pin a revision, not a branch: both repos moved on the day they were read, and
the derivative has already been broken once by an upstream rebase (its re-embed scripts hardcoded a
version string that a rebase invalidated).

Artifacts read, with digests, are recorded in the intake entries:
`chat_template.jinja` from each repo, the stock Qwen template (8,952 B), and the Unsloth template
embedded in our production GGUF (9,993 B) — the last extracted by a header read, without loading
the 29 GB model.
