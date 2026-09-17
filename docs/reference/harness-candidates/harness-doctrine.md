# Harness doctrine — re-targetability and evaluation-side randomization

**Promoted 2026-09-17** out of [`handoffs/active/harness-selection-and-integration.md`](../../../handoffs/active/harness-selection-and-integration.md)
(rows HS-7 and HS-10, both ticked 2026-07-29). These are **standing criteria**, not history: HS-7 is
cited as a live constraint by the HS-4 feature map, by
[`handoffs/active/harness-improvement-loop.md`](../../../handoffs/active/harness-improvement-loop.md)
(what a self-improving loop may mutate) and by HS-5b's freeze-before-tuning ordering.

---

### HS-7 Re-targetable-harness selection criterion (2026-07-29)

**Standing HS-4 criterion.** A candidate is re-targetable only when its run-level policy is a
versioned, editable document that can be retained across a model/freeze change. The document
owns role instructions, workflow/stage order, artifact and handoff contracts, tool-use intent,
retry/stop rules, and disclosure requirements. A separate model-adaptation manifest may tune
model/quant, context or token budgets, request overrides, and prompts; it must not silently
replace the policy with accumulated model-specific behavior. Validators, parsers, tool execution,
sandboxing, state transitions, persistence, observability, and the measurement/governance
boundary remain code-owned mechanisms.

**Selection and acceptance evidence.** HS-4 reviews must score this criterion alongside
cooperation: identify the policy-document version, any model-adaptation manifest, and every
model-specific rule. A later model switch is re-targetable only if it preserves that policy
version or supplies an explicit, reviewable migration diff, then republishes the HS-6 Harness
Card disclosure for the realized configuration. Policy adherence and handoff/artifact contracts
can subsequently be checked on saved traces (HS-9); this is a portability requirement, not a
performance or capability claim.

### HS-10 Harness randomization — evaluation-side pattern (2026-07-29)

**Purpose and boundary.** Randomize the harness only to test whether a result survives legitimate
execution scaffolds; do not train on the variants, tune to their traces, or treat variation itself
as an improvement. The outcome oracle remains structured task evidence — for coding work, the
existing FAIL_TO_PASS outcome — rather than a harness-specific trace style. Any execution needs a
separate measurement protocol and its required approval; this entry records the design only.

**Predeclared, attributable variants.** A future harness evaluation may vary one or more of these
axes, recorded in a versioned run manifest: tool-invocation protocol (structured function call,
text code block, or tagged form); context-management strategy (full history, sliding window,
summary compression, or observation truncation); and control-flow complexity (minimal ReAct or
explicit planning/self-reflection). Hold the model, task set, oracle, permissions, tool capability,
budget, and stop condition fixed unless the protocol explicitly studies one of them. Preserve the
manifest and seed/assignment so every outcome can be attributed to a configuration rather than to
an undocumented prompt or trace difference.

**Readout.** Report result and failure taxonomy per configuration: format/protocol failure,
context-structure failure, control-flow failure, and ordinary task failure. Compare the same
predeclared outcome measure across variants; do not select a winner from traces alone. A result
that changes only under a particular harness is an interaction finding that needs replication, not
evidence that the variant should become the default.

**Negative precedent.** This is not a revival of randomized-pool training. EPYC's P4.6 role-dropout
training experiment was a null result: orchestrator commits `688c6076` and `a404e3bc` plus
`orchestration/reports/p46_role_dropout/` found no arm clearing its adoption gate. The later audit
explained why — label dropout did not expose an available-role input/contract — so it supports
neither a randomization uplift claim nor further retuning of that training path.
