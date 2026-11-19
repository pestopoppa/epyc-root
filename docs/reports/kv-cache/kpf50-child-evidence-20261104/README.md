# KPF-50 raw child JSONL validation

`child_evidence.py` consumes raw `rows/<run_id>.jsonl` output using the fields written by `Run.row` in `kpf50-no-redraw-prep-20261104/runner/kpf18_gate.py`. It requires one `role="child"` row for each suffix 0, 1, 2, and 3; every nonblank row must match the caller-supplied run ID; each child must have HTTP 200 without an error; and `timings.n_fork_tokens` must be an exact integer of at least 60000. Boolean and string counts, malformed JSON, foreign-run rows, duplicate suffixes, and extra suffixes are refused.

```sh
python3 child_evidence.py /path/to/rows.jsonl --run-id kpf18-... --out partial-evidence.json
python3 -m unittest -v test_child_evidence.py
```

Output includes the raw input SHA-256 and validated structural observations, and is marked `partial_structural_evidence` with `complete_outcome: false`. This is model-free validation only. It does not establish custody or authenticity of the JSONL, independently verify run identity, reconcile the digest to the runner record, assess scientific validity, qualify clocks, prove descendant cleanup, or produce a complete outcome or performance verdict.

**Input preservation:** `--out` exclusively creates a new file and refuses every existing destination, including the input path, symlinks (also dangling ones), hard links and unrelated output files. Use a new separate output path, or omit `--out` for stdout. Rejection preserves the existing bytes. Creation and refusal use one filesystem operation, without a separate alias check. Output is not published atomically as a complete document: a write failure may leave a partial new output. This does not provide crash durability or protect directory entries from concurrent replacement by a writer with directory access.

The pre-edit source blob `77283607c42763f5123f7c9bca9cfa2a8b91e807` matches source commit `3796423904552652f4b3614d5a6b1497e84266e2`. The filed source-bound upstream impact row `kpf50-child-evidence-main-impact-20261104-r2-q2` reports LOW for `main`, with only the file itself as a direct caller. Its native result SHA-256 is `340fd57797a9f886b737d07021218ba6aa6299d1da330f9521bd30ff7cd44f60`; skipped source remains outside its scope. The regression suite exercises the actual CLI and verifies input-byte preservation for aliases, separate output, and refusal of existing destinations.
