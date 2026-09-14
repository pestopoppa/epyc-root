# An extracted shared library with one consumer left on its private copy

**Category**: `search_retrieval`
**Confidence**: verified (local code + unit tests, zero inference)
**Date**: 2026-09-14
**Source**: PREFIX-1, `epyc-orchestrator` `f876d989`; prior KB-side fixes `fe55b228`, `4e5e84c0`;
handoff `handoffs/active/colbert-reranker-web-research.md`
**Folds into**: [Search & Retrieval](../search-retrieval.md) — ColBERT/late-interaction section

## The mechanism

`src/retrieval/colbert_encoder.py` was extracted in 2026-08 explicitly so that *two* consumers —
the web-snippet reranker and the internal KB-RAG index — would share one model load, one tokenizer
and one encoding convention. Its own docstring and `src/retrieval/__init__.py` both name
`src.tools.web.colbert_reranker` as consumer number one.

It never was. The extraction created the shared module and migrated only the KB side; the web
reranker kept the private `_encode` it already had. For a month the two paths then diverged in one
direction only, because **every subsequent fix was made in the shared module, which the web path did
not call**:

| Fix landed in the shared encoder | State of the web reranker's private copy (`colbert_reranker.py:153-196`) |
|---|---|
| `[Q]`/`[D]` trained role prefix, required keyword-only `role=` (`fe55b228`) | no role parameter at all — both sides encoded off-distribution |
| feed exactly the inputs `session.get_inputs()` declares (K1, `4e5e84c0`) | hardcoded two-input feed → `None` for every text on any graph declaring `token_type_ids` |
| honour `do_lower_case` (K8) | absent |
| encode-round-trip prefix probe, not `token_to_id` (K6) | absent |
| load failures at WARNING, not DEBUG (K7) | `logger.debug` — a total encoding failure presented as an ordinary miss |

The perturbation is not marginal: measured on the reference model with no ONNX in the loop, dropping
the prefix moves MaxSim by max |Δ| 1.63e-01 and flips top-1 on 37.5% of queries, ~25× the
perturbation of the INT8 quantization the same pipeline accepts (6.60e-03, top-1 agreement 100%).

**The cost was invisible because the feature flag was off.** Nothing served wrong answers. What was
lost is the ability to *measure*: the A/B this handoff exists to run would have compared two models
through a broken encoder and attributed the result to the models.

## Why this is not the same as ordinary duplication

Duplicated code drifts in both directions and eventually someone notices both copies. An **extracted
library with an unmigrated consumer** drifts in exactly one direction, and the direction is the one
that looks like progress: the shared module accumulates fixes, the import graph says the consumer is
served by it, the module docstring says so too, and the stale copy is never touched again — so
nothing about it looks recently wrong.

Grep is a weak detector here. The KB-side commits were searched for `[Q]`, `token_type_ids` and
friends; the web copy hit *none* of those patterns, because the defect is the ABSENCE of them. The
reliable question is not "which files mention the convention" but "which files build the model's
inputs at all" — `grep -rln "enable_padding\|InferenceSession"`.

## The rule

1. **An extraction is not complete until the old private path is DELETED.** A migration that leaves
   the previous implementation in place has not removed a code path, it has created a fork.
2. **Guard it statically, on absence.** A behavioural test cannot catch the *reappearance* of a
   parallel path — the parallel path passes its own tests. Assert the consumer module has no
   `_encode`, no `_session`/`_tokenizer` singleton, and no model-plumbing import at all
   (`tests/unit/test_colbert_reranker.py::TestNoDuplicatedEncoder`).
3. **Mock the shared library in the consumer's tests.** The consumer's contract is *which* call it
   makes with *which* arguments (role per call, cap per call) — not the numbers that come back. As a
   side effect the reranker suite stopped loading a real 144 MB ONNX graph: 26.5 s → 7.4 s.

## Model-declared parameters are data, not constants

A second, independent trap in the same file: `_MAX_QUERY_TOKENS = 48`. Every ColBERT checkpoint
declares its own `query_length` / `document_length`, and they differ per slot:

| Slot | `query_length` | `document_length` |
|---|---|---|
| GTE-ModernColBERT-v1 (default) | 48 | 300 |
| LateOn (primary candidate) | **32** | 300 |
| Reason-mxbai-32M (fallback) | **256** | 2048 |

48 was GTE's number, hardcoded in a module whose own docstring advertises a `LATEON_MODEL_PATH`
override — so activating the primary slot would silently have fed a 32-token model 48-token queries.
Any parameter the checkpoint declares must be *read* from the checkpoint
(`colbert_encoder.max_query_tokens()` / `max_document_tokens()`), because a slot swap is an env var
and must not require a code edit to stay correct.

The direction matters and is not symmetric: spending **fewer** tokens than declared is a legitimate
caller budget (web snippets are two sentences, and the encoder pads to `max_tokens`, so obeying
`document_length: 300` would pad ten snippets to 300 tokens for no content — hence
`min(declared, 64)`); **exceeding** the declared cap is off-distribution and never a budget choice.

## Cross-reference

Same defect class as [a canonical builder that no live writer
calls](canonical-builder-with-no-live-callers.md): in both cases the artifact was correct and the
path that was supposed to reach it was not. The two enforcement layers rhyme — assert about the
*call*, and pin the guard to absence rather than to output.
