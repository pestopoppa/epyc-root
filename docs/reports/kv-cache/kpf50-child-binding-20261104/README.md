# KPF-50 child evidence bound to Run.finish

`window_evidence.py` composes the raw child-row validator from `kpf50-child-evidence-20261104` with the native `records/<run_id>.json` emitted by `Run.finish()`. It requires the record's native `run_id` to match every JSONL row, the recorded `rows` path to identify the supplied raw JSONL, and `rows_sha256` to match the exact bytes. It refuses a missing/malformed record, an explicitly partial record, or any failed/incomplete check summary.

```sh
python3 window_evidence.py /path/to/rows/<run_id>.jsonl /path/to/records/<run_id>.json --out partial-evidence.json
python3 -m unittest -v test_window_evidence.py
```

The result is always `partial_structural_evidence` with `complete_outcome: false`. A successful validator run establishes only that these child rows structurally match the digest and run identity recorded in the supplied finish record. It does not authenticate who produced that record, establish normal completion of a full KPF-50 window, prove cleanup, assess scientific validity, qualify clocks, or produce a performance verdict. In particular, `Run.finish()` can run from failure/cleanup paths; the record's existence and the absence of `partial: true` are not proof of full-window success.
