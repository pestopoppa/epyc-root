# Legacy verifier-only continuation

This sealed callback contains the two qualified TU verifier failures on CPU slot 0 and GPU slot 1. It restores the original OpenCode session and exact profile, reserves each slot separately, verifies the still-owned current grant and expires its private workers when the owner or server exits. It never starts or changes a C22 server. The feedback consists of bounded observed failures from the independently verified rc1 checker output. The candidate's original grade, patch and usage remain immutable.

Approve the exact runner seal and plan in a separate JSON containing `approved_by`, `runner_seal_sha256`, `plan` and `plan_sha256`. Set `approved_by` to `main`. Launch directly while the held owner and idle slots still match:

```text
/usr/bin/python3 -B -u follow.py launch --seal RUNNER_SHA --approval ABS_APPROVAL --approval-sha256 APPROVAL_SHA --out ABS_PRIVATE_RUN
```

Review the changed Python and run `follow.py grade --seal RUNNER_SHA --attempt ABS_ATTEMPT --receipt-sha256 WORKER_SHA --reviewed-python-test` with the unchanged oracle. Generated tokens and timing remain separate per attempt and in cumulative fields. Objective feedback is round one of at most two. Any later paid semantic feedback requires a separately measured owner-approved plan and another independently reviewed terminal result.

A later eligible TU row may be staged with `follow.py draft --out NEW_PLAN_JSON ROW_ID` once its exact independent rc1 receipt exists and its original slot queue drains. The MM candidates already passed the original native contract. Any new objective MM check needs a versioned qualified checker and exact receipts before enabling an extractor. Preparation uses zero inference calls.
