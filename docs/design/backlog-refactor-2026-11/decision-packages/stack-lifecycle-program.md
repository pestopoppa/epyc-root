# Decision package: stack-lifecycle-program

Destination handoff `handoffs/active/stack-lifecycle-program.md` · fold 4 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 2 · excluded: 0. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. SEC-ART-POST-b.1: sign the review of the `epyc-qwen3x-v2` chat template (no tool-result SYSTEM WARNING injection; research `6df1516a6`)?

- Context: `handoffs/active/model-artifact-integrity.md:66@7eb7a4a3c911` (manifest `handoffs/active/model-artifact-integrity.md:66@3ac825873dfb`, id `e57f9d4596c1`)
- Gated worker box(es): `SEC-ART-POST` (handoffs/active/model-artifact-integrity.md:66)

- **Option A (recommended)**: Sign; publish via `template_store publish` and roll out to frontdoor + architect_critic at the next stack change. *Tradeoff:* Template-authored text stops appearing in tool results; one stack-change rollout.
- **Option B**: Hold. *Tradeoff:* The served template keeps injecting the warning text.

**Recommendation: A.** The removal was filed by operator decision and v2 is prepared; the signature is the remaining gate.

## 2. Wire the compile-blocking strict known-gap for null `ctx_model_max` in `_descriptor_gaps`?

- Context: `handoffs/active/model-stack-update-pipeline-audit.md:636@7eb7a4a3c911` (manifest `handoffs/active/model-stack-update-pipeline-audit.md:636@3ac825873dfb`, id `709a9eaca520`)
- Gated worker box(es): `handoffs/active/model-stack-update-pipeline-audit.md:636`

- **Option A (recommended)**: Enable after native `ctx_max` is populated for every launcher-path model. *Tradeoff:* Strict gate without breaking promotion.
- **Option B**: Enable now. *Tradeoff:* Flips the strict promotion gate to error for every unpopulated model (CRITICAL blast radius).
- **Option C**: Never enable. *Tradeoff:* Null ctx stays a silent gap.

**Recommendation: A.** The box sequences it: populate first, then enable.

