# PAW-5 — Compile-once candidate

## Candidate: Shadow semantic classifier for UNKNOWN classification outcomes

**Source**: `epyc-orchestrator@332ceb2e14d16f2031bd17b1f7c839ce8276a24b`, `src/graph/error_classifier.py:8–36`, returns `ErrorCategory.UNKNOWN` for error messages that do not match any of its seven keyword gates (TIMEOUT, SCHEMA, FORMAT, EARLY_ABORT, INFRASTRUCTURE, CODE, LOGIC). The classifier is called by the recurring graph execution paths in `src/graph/nodes.py`. The proposed fuzzy subtask is semantic assessment of its UNKNOWN residue. No frequency or quality of UNKNOWN outcomes has been measured for this proposal.

**Prerequisites**: PAW-1 was resolved on 2026-09-17 for internal research only; redistribution, deployed-service use, and shipping compiled outputs remain outside that ruling. PAW-2 remains open. This candidate is filed only and does not trigger compilation or evaluation. See [the owning track](../../../handoffs/active/model-evaluation-queue.md).

---

## Compile-once candidate

An offline shadow program that receives every error message the existing `error_classifier.py` returns UNKNOWN for, runs it through a compiled-model classification step, and records the model's output alongside the original message and the existing classifier's result — without routing changes or runtime authority.

**Inputs**: raw error string (bounded and normalized to ≤512 characters).

**Model context budget**: ≤2 048 tokens.

**Decoding/output budget**: ≤128 tokens.

**Retry budget**: up to 2 retries on invalid output.

**Output schema**: a single JSON object with one field:

```json
{"category": "TIMEOUT" | "SCHEMA" | "FORMAT" | "EARLY_ABORT" | "INFRASTRUCTURE" | "CODE" | "LOGIC" | "UNKNOWN"}
```

The model must always emit one of the seven named categories or the explicit token `"UNKNOWN"` to abstain. The `"UNKNOWN"` value signals the model declined to classify rather than a failure.

**Invalid-output handling**: on parse failure or out-of-schema output, retry up to 2 times with the same bounded input and prompt. After all retries exhausted, record the result as `UNKNOWN`.

**Authority boundary**: the keyword matching and UNKNOWN fallback in `src/graph/error_classifier.py`, and the separate downstream routing gates, remain fully authoritative. The shadow classifier runs only on messages that already returned `UNKNOWN` and never alters routing, escalation, or retry flow.

---

## Direct-model baseline

The same bounded normalized error text (≤512 characters), model context budget (≤2 048 tokens), decoding/output budget (≤128 tokens), retry budget (2 retries on invalid output), and output schema as the compile-once candidate — but invoked directly via model call at evaluation time with no compilation step.

This baseline provides a direct-model reference for comparing the compiled program's accuracy, latency, and cost against an un-compiled model invocation on the identical inputs.

---

## Comparison

**Evaluation setup**: both arms are evaluated against one held-out, human-labeled gold set of UNKNOWN error messages. The gold set is fixed and held out from any model training or prompt tuning.

**Primary rubric**: arm agreement with the human label (top-1 accuracy against the gold label).

**Secondary metric**: raw inter-arm agreement (how often the compiled candidate and the direct-model baseline produce the same category for the same message).

**Abstention measurement**: count and categorize how often each arm emits `"UNKNOWN"` (model abstention), and how often the abstention agrees or disagrees with the human label.

**Category quality measurement**: per-category precision and recall against the human label for each of the seven named categories.

**Coverage measurement**: proportion of the gold set where each arm produces a non-UNKNOWN classification (i.e., the model's willingness to classify vs. abstain).

---

## PAW-1

PAW-1 is satisfied for the internal research scope above. A distribution or productization proposal requires a separate scope decision.

## PAW-2

PAW-2 is a prerequisite. Compilation and evaluation do not proceed until PAW-2 is marked complete.

**Review provenance**: the A3B draft received an independent source review and a human correction to prerequisite status, source citations, and metric wording before landing. This is a design proposal; no specialist has been compiled or evaluated.
