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

## Open Questions

- Does the terseness prompt help, hurt, or do nothing on *our* suites at `enable_thinking=false`,
  where there are no thinking tokens to cut?
- What does a template swap cost in voided calibration? Architect-bench arms, `q_scorer`
  baselines and reasoning-effort settings were all measured under the current template.
- A chat template is executable code in the prompt-construction position, sitting on top of the
  in-tree engine's **input-marking** defence against special-token injection
  (`common/jinja/README.md`). What does a third-party template do to that property?

## Tasks

- [ ] **CT-1** — A/B one Qwen3.x role via `llama-server --chat-template-file` against its embedded
      template on a pinned eval set. Report **per-suite, never aggregate** (intake-1214: a
      conciseness instruction near-neutral in aggregate carried a 27.69% math penalty for the
      weaker model). No requantization, no registry change, no kernel touch.
- [ ] **CT-2** — Price the calibration cost before any stack-wide swap: enumerate which measured
      artifacts (architect-bench arms, `q_scorer` baselines, draft-depth settings) are voided by
      changing the rendered prompt.
- [ ] **CT-3** — Check a third-party template against the in-tree input-marking path
      (`common/jinja/`, and the input normalisation `common/chat.cpp` applies before the runtime).
- [ ] **CT-4** — If anything is adopted, pin the exact revision + sha256, not a branch.
- [ ] **CT-5** — Decide the retention question on its own merits, separately from the terseness
      prompt. The three incumbent templates discard history reasoning; the community templates keep
      it. Under `enable_thinking=false` this changes nothing, so the real question is whether any
      role should run thinking-ON with retention — which is where the prefix-cache argument would
      pay and where the reasoning-budget work in `per-request-reasoning-budget.md` already lives.
      Do not bundle this with CT-1.
- [x] **CT-6** — Sweep the embedded template of every production GGUF and tabulate the defect
      matrix ✅ 2026-08-21 (table above; three distinct templates, all defects Qwen3.8-only, the
      retention gap incumbent-only)

## Notes

Any adoption must pin a revision, not a branch: both repos moved on the day they were read, and
the derivative has already been broken once by an upstream rebase (its re-embed scripts hardcoded a
version string that a rebase invalidated).

Artifacts read, with digests, are recorded in the intake entries:
`chat_template.jinja` from each repo, the stock Qwen template (8,952 B), and the Unsloth template
embedded in our production GGUF (9,993 B) — the last extracted by a header read, without loading
the 29 GB model.
