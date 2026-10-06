# Outer eval reconnect cost

Eval-only outer reconnect metadata survives successful, refused and exhausted returns through QuestionResult into the original compact question JSONL row. It records outer attempts, explicit outer backoff seconds and a closed terminal reason independently of inner resilient-post retries. Legacy rows remain readable; invalid metadata is omitted. Retry eligibility, budgets, answer grading and aggregate metrics are unchanged.

The optional `epyc.eval_reconnect.v1` carrier accepts non-boolean nonnegative integer attempts, finite nonnegative non-boolean backoff, and one of preflight_refusal, response_returned, non_reconnectable_terminal or reconnect_budget_exhausted. No inner-count sum, elapsed-time proxy or automatic aggregation is introduced. Appending the field preserves existing QuestionResult positional fields.

[Original native evidence](../../artifacts/ni07/run-37466167911/README.md) passes 42 seeding and 15 persistence cases using fake transports/clocks and generation-to-original-row controls. No live network, model, serving or inference result is claimed.
