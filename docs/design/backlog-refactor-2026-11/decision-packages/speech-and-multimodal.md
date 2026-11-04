# Decision package: speech-and-multimodal

Destination handoff `handoffs/active/speech-and-multimodal.md` · fold 1 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 3 · excluded: 0. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. CS-12: prepare and sign the stack change putting whisper + qwentts on the second MI210 beside 35B-A3B?

- Context: `handoffs/active/conversation-stack.md:307@7eb7a4a3c911` (manifest `handoffs/active/conversation-stack.md:307@3ac825873dfb`, id `d7dab497b758`)
- Gated worker box(es): `CS-12` (handoffs/active/conversation-stack.md:307)

- **Option A (recommended)**: Prepare now, sign when the card is in service. *Tradeoff:* Resolves the CPU speech collapse; package must pass the RTF/first-packet gates.
- **Option B**: Keep the cascade on CPU. *Tradeoff:* No change; the collapse that led to option D remains.

**Recommendation: A.** The box says landing it resolves the speech collapse; one signature covers it.

## 2. CS-27: enable a persona voice under the voice-cloning guardrail?

- Context: `handoffs/active/conversation-stack.md:378@7eb7a4a3c911` (manifest `handoffs/active/conversation-stack.md:378@3ac825873dfb`, id `4e64fde40d3d`)
- Gated worker box(es): `CS-27` (handoffs/active/conversation-stack.md:378)

- **Option A**: Enable one enrolled voice with recorded rightsholder authorisation. *Tradeoff:* Nice-to-have feature; guardrail obligations (disclosure, audit, revocation).
- **Option B (recommended)**: Keep default deny. *Tradeoff:* No risk; no persona voice.

**Recommendation: B.** It is a nice-to-have with legal obligations; keep deny until a rightsholder authorisation exists.

## 3. CS-41: move to model-decided LOCAL answers after CS-24?

- Context: `handoffs/active/conversation-stack.md:435@7eb7a4a3c911` (manifest `handoffs/active/conversation-stack.md:435@3ac825873dfb`, id `5bcf7d9ec4ec`)
- Gated worker box(es): `CS-41` (handoffs/active/conversation-stack.md:435)

- **Option A (recommended)**: Proceed when CS-24 meets the operator-set precision/recall target. *Tradeoff:* Fewer escalations; depends on the target.
- **Option B**: Keep D5 routing. *Tradeoff:* No change.

**Recommendation: A.** Gate it on CS-24; the operator must also set the target value.

