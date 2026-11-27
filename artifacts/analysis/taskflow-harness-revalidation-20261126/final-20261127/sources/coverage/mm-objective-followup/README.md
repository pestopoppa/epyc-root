# MM-5 verifier-only continuation

The plan carries the completed CPU MM and GPU MM nonthinking candidates into round one of the original two-round allowance. Each candidate retains its original sealed rc0 and separate qualified v2 rc1. The prompt gives only the observed additive assertion from the versioned evaluator, with the candidate's original OpenCode session, context, tool surface, sampling profile, slot and budgets unchanged. It has no proposed code changes.

Set `approved_by` to `main` in a separate approval JSON with `runner_seal_sha256`, `plan` and `plan_sha256`. Then launch the sealed callback directly while the combined owner still holds the exact grant:

```text
/usr/bin/python3 -B -u follow.py launch --seal RUNNER_SHA --approval ABS_APPROVAL --approval-sha256 APPROVAL_SHA --out ABS_PRIVATE_RUN
```

The callback serializes GPU slot 2 and CPU slot 1 independently. It checks that their original static queues have ended and cancels its workers when their existing grant or process identity changes. GPU PFXC and CPU W66 terminal evidence are prerequisites. All workers are in private child processes. No serving process is started or changed.

After reviewing the new Python source, run `follow.py grade --seal RUNNER_SHA --attempt ABS_ATTEMPT --receipt-sha256 WORKER_SHA --reviewed-python-test`. This stores separate original and v2 grade receipts against identical bytes. A possible round two requires separate owner review and measured paid guidance approval. Preparation made zero model calls.
