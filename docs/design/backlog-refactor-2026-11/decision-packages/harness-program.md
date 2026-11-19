# Decision package: harness-program

Destination handoff `handoffs/active/harness-program.md` · fold 13 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 5 · excluded: 5. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. UFH14-B4a: sign the PFX-SEL-1 stack-change package after >=1 window of >=200 calls?

- Context: `handoffs/active/agentic-serving-harness-fixes.md:281@7eb7a4a3c911` (manifest `handoffs/active/agentic-serving-harness-fixes.md:281@3ac825873dfb`, id `e57a68353104`)
- Gated worker box(es): `UFH14-B4a` (handoffs/active/agentic-serving-harness-fixes.md:281)

- **Option A (recommended)**: Sign when the baseline window exists. *Tradeoff:* Prefix-cache selection becomes declarative; no flag change today.
- **Option B**: Defer. *Tradeoff:* Hand-set values stay.

**Recommendation: A.** Derived values equal today's, so the risk is low; :8083 cache-ram rises only if §4.3 fires.

## 2. UFH14-C1 scope: should harnesses reach a multi-endpoint fleet (e.g. frontdoor) through the passthrough?

- Context: `handoffs/active/agentic-serving-harness-fixes.md:634@7eb7a4a3c911` (manifest `handoffs/active/agentic-serving-harness-fixes.md:634@3ac825873dfb`, id `ffa5ca3aff22`)
- Gated worker box(es): `UFH14-C1.` (handoffs/active/agentic-serving-harness-fixes.md:634)

- **Option A (recommended)**: Keep 422 by design. *Tradeoff:* Passthrough stays single-endpoint; harness traffic to fleets goes through routing.
- **Option B**: Allow it. *Tradeoff:* More harness reach; passthrough must take on routing.

**Recommendation: A.** The declined note under UFH14-B6 already argues it; keep it until the C1 review says otherwise.

## 3. HIL-6: select architecture A, B or C per the HIL-4 decision package.

- Context: `handoffs/active/harness-improvement-loop.md:96@7eb7a4a3c911` (manifest `handoffs/active/harness-improvement-loop.md:96@3ac825873dfb`, id `9be778684453`)
- Gated worker box(es): `HIL-6` (handoffs/active/harness-improvement-loop.md:96)

- **Option A**: A. *Tradeoff:* Per HIL-4 package tradeoffs.
- **Option B (recommended)**: B (package recommendation). *Tradeoff:* Per HIL-4 package tradeoffs.
- **Option C**: C. *Tradeoff:* Per HIL-4 package tradeoffs.

**Recommendation: B.** The reviewed package recommends B; the pilot-only lift is separate and already decided.

## 4. Change the default of `ORCHESTRATOR_DOCUMENT_BODY_INJECTION_POLICY` from `source` (no body scan) to `warn`?

- Context: `handoffs/active/qwen-chat-template-evaluation.md:613@7eb7a4a3c911` (manifest `handoffs/active/qwen-chat-template-evaluation.md:613@3ac825873dfb`, id `b1435e18d7c2`)
- Gated worker box(es): `CT-12` (handoffs/active/qwen-chat-template-evaluation.md:613), `CT-12.3` (handoffs/active/qwen-chat-template-evaluation.md:616), `CT-12.3d` (handoffs/active/qwen-chat-template-evaluation.md:620)

- **Option A**: Keep `source`. *Tradeoff:* No new notes in prompts; document-body injection goes unflagged.
- **Option B (recommended)**: Switch to `warn`. *Tradeoff:* Flags injected control-token text in bodies; adds a note to some prompts.

**Recommendation: B.** The neutraliser is landed and tested (934 passed); warn adds a flag only, not a policy change.

## 5. UFH-12-PROD-ADOPT: swap the validated R3 private EmbeddingGemma store into production?

- Context: `handoffs/active/repl-embedding-retrieval.md:253@7eb7a4a3c911` (manifest `handoffs/active/repl-embedding-retrieval.md:253@3ac825873dfb`, id `c760aad69c22`)
- Gated worker box(es): `UFH-12-PROD-ADOPT` (handoffs/active/repl-embedding-retrieval.md:253)

- **Option A (recommended)**: Adopt via a stack change. *Tradeoff:* Production gets the validated store; one swap with rollback.
- **Option B**: Keep the current store. *Tradeoff:* No change.

**Recommendation: A.** Validated and the migration tool fix landed; adoption goes through the normal stack-change gate.

## Excluded (not delivered)

- `HS-19` (handoffs/active/harness-selection-and-integration.md:233): **decided**. Operator decisions 2026-09-27 recorded in the box (orchestrator owns model selection, etc.).
- `handoffs/active/harness-selection-and-integration.md:258`: **decided**. Frozen 2026-09-27 until the UFH-13 thesis experiment shows A2 pays (standing freeze).
- `CT-12.3` (handoffs/active/qwen-chat-template-evaluation.md:616): **merged** into choice for `CT-12`. Same policy-default choice as CT-12.
- `CT-12.3d` (handoffs/active/qwen-chat-template-evaluation.md:620): **merged** into choice for `CT-12`. Same policy-default choice as CT-12.
- `CT-15` (handoffs/active/qwen-chat-template-evaluation.md:653): **not-a-choice**. Investigation with "report only"; the decision is the investigator's finding, not an operator choice.
