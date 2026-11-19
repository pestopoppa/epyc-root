# KVU-12.5 quarter exposure: offset recovery result

**Result: historical cursor intervals remain unknown.** The offline replay cannot
recover exact exposed character or byte ranges from the retained receipts, and it
does not select replacement offsets. The safe correction is to retain all known
logical exposure while refusing to infer a corpus boundary or claim an unused
tail.

## Verified source evidence

- The archived native partial is
  `progress/evidence/kvu12-5-quarter-result-20261102/native-partial.tar.gz`
  (SHA-256 `42a549585194b1d0e61195c1d6f93ab6e88fe05d9ee32a002fe6f9050c4475e7`).
- The retained driver is `epyc-inference-research/artifacts/np_context_kvu_cpu_study_20261020/driver/kvu_cpu_matrix.py`
  (SHA-256 `43e4fcad361693cddbed8f616bb0f02895e0f4fd7ab2dc01233cca74459ecdf0`).
  `Corpus.take` resets to cursor zero on wrap and advances by requested characters.
  `make_doc` retries adaptive slice lengths using `/tokenize`; its trim loop shortens
  returned prompt text without rolling back the cursor. The depth path also prepares
  suffixes before submitting requests. Therefore request token totals do not invert
  to exact cursor intervals.
- The exposure audit is content bound to corpus SHA-256
  `476c08ab215e9c852159124ce2c17c574c3efeb304b6f66a3f2cfb72abdf657b` and records
  logical exposure separately from ranges. It records 24 completed start-anchor
  requests, eight submitted but incomplete unified requests, and that later
  unified suffixes were constructed/tokenized but not submitted. The separate 8k
  qualification request and fixed non-corpus warm-up are also exposure facts; they
  do not establish corpus intervals.
- The archive has no retained request bodies, per-call `/tokenize` inputs/responses,
  operation transcript, or selected character lengths. Its partial cell logs and
  launch events cannot supply those missing inputs.

## Replay boundary

`replay.py` verifies the corpus digest and character count before replay. Exact mode
is intentionally available only with an explicit complete operation transcript and
the corresponding ordered tokenizer counts. Without that transcript,
`historical_report` emits `UNKNOWN_CURSOR_INTERVALS`, null ranges, no selection
authority, and no replacement offsets. A synthetic tokenizer or a transcript
invented from token totals would not be historical evidence.

The next admissible recovery input is a complete, content-bound per-launch transcript
of operation order, cursor starts, requested lengths, tokenizer calls and responses,
trim lengths, suffix takes, and wrap events, cross-checked against retained prompts.
If it cannot be recovered, preserve unknown intervals and require a prospectively
declared selection rule before any new cohort is measured. This report authorizes no
compute, publication, grant, or redraw.
