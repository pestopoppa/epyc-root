# GPU-PLT-1: prospective LiveCodeBench selection

This preparation utility freezes item IDs after a reviewed, evidence-bound model
cutoff. It is not an inference launcher, scorer, or contamination proof. It
refuses to run under a row grant, refuses incomplete or changed shards, requires
at least 200 eligible IDs, and creates output only after all checks pass.

`official-shards.json` captures the nine release-v6 LFS SHA-256 and byte counts
reported by the official Hugging Face dataset tree at revision
`28efd4d97f479657d49989f83e30b9d51481ad9e`. The code pins those metadata bytes.
Supply all nine files with their original names using repeated `--shard` flags,
an output path that does not exist, and a separately reviewed witness JSON:

```json
{"model_revision":"b87cf3aa2186937b0d0362a684d7d30f234543e3",
 "kind":"author_cutoff", "cutoff_date":"YYYY-MM-DD",
 "source_url":"https://primary-source.example/", "source_sha256":"<64 lowercase hex>"}
```

The source SHA-256 must match the separately supplied `--witness-evidence` bytes.
`publication_upper_bound` is also accepted as a conservative evidence kind only
when a reviewer establishes that the publication actually fixes an upper bound
on training data. The tool checks the evidence identity, not its truth. `contest_date` is only a
candidate filter: a problem could have appeared earlier elsewhere. Every
candidate additionally needs a reviewed, per-item original-publication audit
and a separately retained source-evidence file. Provide `--release-audit` JSON
with `dataset_revision`, `reviewed_by`, and `items`; each item has
`question_id`, `finding` exactly `original_release_not_before_contest`,
`original_release_date`, `source_url`, `evidence_file` (relative to
`--release-evidence-root`) and `evidence_sha256`. The audit must cover every
selected candidate exactly; a missing or changed evidence file, an earlier
original publication, a symlink escape, or a partial audit refuses the whole
selection. A contest on the cutoff date is excluded. This is an evidence gate,
not an automatic determination that the audit is correct or a contamination-free
claim. Inspect benchmark terms before selecting a corpus.

At preparation time, neither the pinned [model card](https://huggingface.co/Multilingual-Multimodal-NLP/LoopCoder-V2/tree/b87cf3aa2186937b0d0362a684d7d30f234543e3)
nor the [paper](https://arxiv.org/html/2606.18023) states a training-data cutoff.
The official [LiveCodeBench release list](https://github.com/LiveCodeBench/LiveCodeBench)
places v6 through April 2025, before the model's June 2026 paper, so a publication
upper bound would produce zero v6 post-bound items. No witness or selection is
invented here. LiveCodeBench Pro is a separate benchmark and cannot be silently
substituted for the task's required LCB subset.

Run model-free checks with `python3 -m unittest discover -s
scripts/coordination/gpu-serving-tie-in/plt-lcb-selection -p 'test_*.py'`.
The selector's Parquet mode needs `pyarrow` in the preparation environment.
