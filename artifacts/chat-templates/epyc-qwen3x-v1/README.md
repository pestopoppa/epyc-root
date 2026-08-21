# epyc-qwen3x-v1 — EPYC-owned Qwen3.5/3.6/3.8 chat template

**Built**: 2026-08-21 (CT-7, `handoffs/active/qwen-chat-template-evaluation.md`; operator-directed:
"we build them ourselves if they're valuable to us")
**Base**: froggeric/Qwen-Fixed-Chat-Templates v22.3 (Apache-2.0), 26,681 B,
sha256 `6e1439c913ad7df4a966493ad70de7e7fc5a548d41bbe417c1571f766603629b`
**This artifact**: `chat_template.jinja`, 24,659 B,
sha256 `faaecb215031c149c169e113800d69497b2dd9451602b82069d13aec651d8c15`

## Delta vs base — one deletion, one comment

The upstream **per-turn inline `<|think_*|>` tag scan** (46 lines: the `{%- for msg in messages %}`
loop that read ten control tags out of system/developer/**user** message content to overwrite
reasoning state) is **removed**. It is a prompt-injection surface — any user-supplied text
containing `<|think_off|>` silently disables thinking — and the engine's input-marking cannot
mitigate it (input marking constrains tokenization, not template control flow; CT-3 analysis).
The downstream tag **sanitizer** is kept: stray tag text is still stripped from rendered content,
it just never changes state. Reasoning control flows only through `chat_template_kwargs`
(`enable_thinking`, `reasoning_effort`) — the channel our stack already uses.

**No terseness block.** Sharp's terseness prompt is deliberately excluded: it is the unmeasured
ingredient (intake-1212), and it enters CT-1's A/B as an *arm*, never as a default.

## What this buys over our incumbent templates

Our served Qwen3.6-27B / Qwen3.6-35B-A3B / Qwen3.5-122B templates **discard history thinking
entirely** (fleet sweep 2026-08-21, both history shapes). This template retains it — inert under
`enable_thinking=false`, load-bearing the moment any role runs thinking-ON (CT-5 decision).

## Verification (2026-08-21, Jinja2 3.1.6)

| Probe | froggeric v22.3 | epyc-qwen3x-v1 |
|---|---|---|
| user content `<|think_off|>` flips thinking | **yes (injection)** | **no** |
| tag text stripped from render | yes | yes |
| history retention (`reasoning_content` / inline) | yes / yes | yes / yes |
| `enable_thinking=false` clean; kwargs effort steering | yes | yes |
| render parity with base on tag-free input | — | **byte-identical** |

## Open before any deployment

- Vendored upstream test suite run (with divergences recorded, Sharp-shim style) — CT-7 sub-item.
- minja/`common/jinja` render check on the actual serving path (a Jinja2 pass is not a minja pass).
- CT-1 per-suite A/B. **Never deploy on the strength of this README.**
