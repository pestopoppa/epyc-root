# KPF-50 raw child JSONL validation

`child_evidence.py` consumes raw `rows/<run_id>.jsonl` output using the fields written by `Run.row` in `kpf50-no-redraw-prep-20261104/runner/kpf18_gate.py`. It requires one `role="child"` row for each suffix 0, 1, 2, and 3; every nonblank row must match the caller-supplied run ID; each child must have HTTP 200 without an error; and `timings.n_fork_tokens` must be an exact integer of at least 60000. Boolean and string counts, malformed JSON, foreign-run rows, duplicate suffixes, and extra suffixes are refused.

```sh
python3 child_evidence.py /path/to/rows.jsonl --run-id kpf18-... --out partial-evidence.json
python3 -m unittest -v test_child_evidence.py
```

Output includes the raw input SHA-256 and validated structural observations, and is marked `partial_structural_evidence` with `complete_outcome: false`. This is model-free validation only. It does not establish custody or authenticity of the JSONL, independently verify run identity, reconcile the digest to the runner record, assess scientific validity, qualify clocks, prove descendant cleanup, or produce a complete outcome or performance verdict.
