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

## Validation record (both completed 2026-08-21, same day)

**Vendored upstream suite** (froggeric's own, fetched at v22.3): `test_v21.py` **9/9**;
`fuzz_template.py` **clean over 2,000 conversations, all nine invariants**; `test_v22.py` **85/100**,
where all 15 failures are tests of the deliberately-deleted inline-tag feature (11, 12, 14, 15, 16,
37, 45–49, 54, 55, 57, 97 — `<|think_medium|>` (13) passes because medium is the no-op default).
The failures are the divergence working as designed, recorded Sharp-shim style rather than shimmed
away. `chat_template_oneline.txt` (19,421 B, sha256 `c24a075e8cdd…4e77d`) generated with the
vendored minifier; oneline/jinja parity holds (fuzz invariant + test 94 logic).

**Real-engine check** (frozen `production-consolidated-v9` `common/jinja`, via
`llama-server --chat-template-file` + `POST /apply-template`, CPU, Qwen3.6-35B-A3B, test port):
**all 7 fixture renders byte-identical to the Jinja2 goldens** — clean render, `enable_thinking=false`,
the injection probe (thinking stays ON, tag stripped, on the real path), retention in both history
shapes, kwargs effort steering, and the top-level `reasoning_effort` drop (the server consumes it;
renders identical to no-kwargs — the live confirmation PRB-T3 was waiting on). The engine also
recognized the template's retention capability at load ("chat template supports preserving
reasoning").

## Still open before any deployment

- CT-1 per-suite A/B (quality effect of the template swap). **Never deploy on the strength of this
  README** — everything above is mechanism validation, not a quality result.
