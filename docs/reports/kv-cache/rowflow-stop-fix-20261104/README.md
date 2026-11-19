# Rowflow hard-stop completion guard (review packet)

This packet proposes a patch to `scripts/coordination/rowflow/filler_run15.sh`; it does not modify or install that shared engine or any keeper. Apply only after owner review.

The patch routes post-job finalization through `finish_job`: `hard-end` and `disk-floor` remain rc 75 ended outcomes even if the native completion predicate has become true. Other successful complete jobs still produce `.complete`; successful but incomplete jobs remain `partial-native-incomplete`. At launcher startup, an existing rc=75 `hard-end`/`disk-floor` `.ended` receipt takes precedence over a now-true native completion predicate and exits 75 without rewriting the receipt.

`test_patch.py` applies the proposed diff to a temporary copy of the exact engine, extracts and executes the patched shell functions/startup branch with stubbed predicates and writers, and checks hard-end, disk-floor, normal completion, partial output, and restart behavior. It performs no inference, grant, keeper, or live-engine action. Run with `python3 docs/reports/kv-cache/rowflow-stop-fix-20261104/test_patch.py`.

## Limitation

There remains a crash window after a hard-end/disk-floor stop is detected and before `write_ended` durably records the stop. A restart cannot identify that lost stop event from an absent receipt; this patch does not invent stop evidence or change receipt durability. Existing `write_ended` refuses to overwrite an already-present `.ended` receipt; the startup guard preserves a recorded hard-stop receipt and exits. The patch also does not change resource cleanup or the disk-floor measurement.
