# HS-OD-4 decision prep: `max_tokens` on `/v1`

**Status:** source-backed decision package; published for operator choice. No API behavior has changed.
**Source pins:** APP `79abe3eca50c911d89e5e9855bbd6392bae2b35d` (`src/api/models/openai.py`, `src/api/routes/openai_compat.py`).
**Scope:** choose the request contract for the default text REPL path. The image/vision path already rejects explicit unsupported sampling fields; this note does not change that behavior.

## What the pinned source does

`OpenAIChatRequest.max_tokens` defaults to 1024. Its model description says it is a generation cap only in client-tool mode and `x_disable_repl=true`; in the default REPL mode, it controls turn count, while each turn can generate up to 1024 tokens (`src/api/models/openai.py:127-136`). `max_completion_tokens` aliases the same field, and supplying both is a 422 (`:364-375`).

Both default text REPL implementations use the same mapping:

- Streaming: `max_turns = request.max_tokens // 500`, clamped to 1–5 (`src/api/routes/openai_compat.py:1530-1531`); each call passes `n_tokens=1024` (`:1544-1548`).
- Non-streaming: same turn-count mapping (`:1894-1895`); each call passes `n_tokens=1024` (`:1908-1912`).

The other text paths pass the supplied field as the generation limit:

- Client tool mode calls `chat_completion_call(..., n_tokens=request.max_tokens)` (`:629`).
- Direct `x_disable_repl` mode calls `llm_call(..., n_tokens=request.max_tokens)` in streaming and non-streaming paths (`:1460`, `:1862`).

Vision behavior is already fail-closed. `_unsupported_vision_sampling_field` treats an explicitly supplied non-null `max_tokens` as unsupported (`:797-808`); the request handler checks it before dispatch and returns 422 (`:1190-1198`). `_run_openai_vision_completion` does not forward `max_tokens` into its `ChatRequest` (`:912-937`), but that path is not silently ignoring the field because explicit values have already been rejected. The old HS-OD-4 task sentence saying that vision “drops” the value is stale and should be corrected.

## Options

| Option | Behavior | Benefits | Costs |
|---|---|---|---|
| A. Honor the conventional generation-token budget in default REPL mode | Treat `max_tokens` as one per-request budget across every model generation: final answers, intermediate code, tool-call arguments and hidden reasoning all consume the same budget. Each model call receives at most the known remaining budget and the existing per-call ceiling; do not start another generation once exhausted or once remaining usage becomes unknown. Return `finish_reason="length"` only when exhaustion is positively established. Keep the existing five-turn safety ceiling independent of `max_tokens`. | A client-supplied generation cap means a cap on model generation in every text mode. Fits the OpenAI field name and the HS-OD-1 “refuse, do not ignore” rule without rejecting ordinary requests. | Requires reliable per-request accounting across streaming and non-streaming paths, including intermediate/tool-call generations, cancellation and partial backend results. Tool results may contribute non-model text to `FINAL(...)`, so this budget does **not** guarantee a final rendered answer of at most `max_tokens` tokens or bytes. That separate claim requires tokenizer/accounting coverage of all rendered sources. Default 1024 becomes a total default rather than the current possible two calls × 1024, which can shorten ordinary REPL exchanges. |
| B. Refuse explicit `max_tokens` in default REPL mode until A is implemented | Use request-field presence to return 422 when the caller explicitly supplies this unsupported cap; leave omitted-field legacy behavior unchanged. | Small, fail-closed, and consistent with the image path and HS-OD-1. | Many SDKs send a default `max_tokens`; those callers would receive 422. Omitted-field requests still use the existing implicit 1024-per-call / turn-count behavior until A lands. |
| C. Keep the current turn-count interpretation and document it | `max_tokens` continues to set 1–5 turns; document the fixed 1024-token generation cap per REPL call. | No runtime behavior change and least immediate implementation cost. | Documentation cannot make the standard field name mean a turn count. Clients can ask for 64 and still cause a 1024-token model generation; this preserves the exact mismatch HS-OD-4 records and conflicts with the neighboring fail-closed policy. |

## Recommendation

Choose **A**, contingent on proving that every model call in both REPL branches consumes from a single request budget. Count all model-generated tokens, including code/tool-call arguments and hidden reasoning. When backend usage is absent, partial, or explicitly unknown, keep usage unknown and do not treat it as zero to continue generation or claim the cap was met. A request cap bounds model generation only; it does not bound the final rendered text when a tool result is included by `FINAL(...)`. Any rendered-text cap would need a separate tokenizer-based contract and coverage for both model and tool-provided text.

Preserve the five-turn safety ceiling as a separate control, but recognize that turning it into an independent ceiling can change the number of turns reachable at small budgets. Preserve the current explicit 422 for image requests until the vision handler has a supported token-budget field. If reliable per-request accounting cannot be enforced, use **B** as the fail-closed interim behavior. Do not select C as a compatibility fix; documenting the surprising turn-count mapping leaves the standard generation cap unhonored.

**Compatibility and effort.** The model schema defaults `max_tokens` to 1024. Under A, omission therefore becomes a 1024-token total-generation budget; current behavior can allow two REPL calls of up to 1024 each. This is a meaningful default-path compatibility change and must be reviewed with the `/v1` owner. Preliminary source-only effort estimate: **2–4 engineering days** for shared accounting/call-path changes, cancellation/partial/unknown handling, finish-reason propagation and focused tests across both branches. Basis: the current streaming and non-streaming REPL loops are separate and each hard-codes its own 1024-token call, while client/direct routes and usage accounting are separate. If the API owner judges that effort or behavior too risky, option B is the short fail-closed fallback. Any model-level validation remains with the owning session's normal serving window; this source proposal supplies no live-model evidence.

This recommendation is an engineering proposal for the API contract, not a measurement claim. It does not choose or enable any model, harness, or serving change.

## Acceptance examples

| Request | Current behavior | Acceptance under A |
|---|---|---|
| Text REPL, `max_tokens: 64` | `max_turns` clamps to 1; the model call still receives `n_tokens=1024`. A tool result can also contribute arbitrary non-model text to the returned content. | At most 64 **model-generated** tokens across all calls, if backend accounting confirms that amount. If accounting becomes unknown, do not report the cap as satisfied. The rendered answer length is not bounded by this setting when tool text is included. |
| Text REPL, `max_tokens: 2500` | `max_turns` clamps to 5; up to five calls each receive `n_tokens=1024`. | One 2500-token model-generation budget shared across REPL turns; at most five turns remain possible. Stop safely on cancellation, partial results, or unknown usage. |
| Text client-tool or `x_disable_repl`, `max_tokens: 64` | The backend call receives `n_tokens=64`. | Remains capped at 64. |
| Image request, explicit `max_tokens: 64` | Returns 422 before vision dispatch. | Remains 422 until separately supported; never silently drop the field. |

For a request with no supplied field, schema default `max_tokens=1024` currently permits two REPL turns of up to 1024 tokens each. Under A it becomes one 1024-token total generation budget, so the default turn count can fall from two to one. The five-turn limit remains only a ceiling; it does not promise five turns when the token budget is exhausted.

The implementation review should verify per-request token accounting and stop behavior on both REPL branches before changing the contract. No test run or implementation is included here.
