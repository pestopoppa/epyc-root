# Served quality evaluation input

`served_quality_100.jsonl` is a fixed 70-item GSM8K / 30-item HumanEval subset. The source files, their digests, the deterministic selection key and the subset digest are in `served_quality_100.provenance.json`. The source IDs and test code are retained in the subset. Do not change the file without creating a new pinned evaluation era.

For `mk_ak_row.py gate new`, copy the data as a sealed input and declare the noise arm alongside the other arms:

```
--copy-input scripts/coordination/rowflow/data/served_quality_100.jsonl:inputs/served_quality_100.jsonl \
--correctness '{"kind":"served_quality","input":"inputs/served_quality_100.jsonl","noise_arm":"OFF2","gate":true,"n_predict":512,"n_probs":5,"k":3,"abs_floor_items":1,"test_timeout_s":5}'
```

`OFF2` must be a declared arm distinct from the first baseline and should differ from the baseline only by the order perturbation being measured. The author must configure that arm in the served argv/arm declaration. `--copy-input` pins the input SHA-256 in the generated job spec. `gate:false` records the comparisons without failing on quality loss. The exact one-sided McNemar tail is reported for the candidate-worse direction; a p-value strictly below 0.05 rejects a worse arm, in addition to the noise-based accuracy bound. Divergence indices are zero-based; a null index means equal token sequences. Overlaps are per-token fractions of the larger top-k set before divergence.

Code scoring uses an isolated Python subprocess with a seccomp network deny and a timeout. It fails closed if the seccomp filter cannot be installed. Model completions are executable code: run this only in the designated evaluation environment.
