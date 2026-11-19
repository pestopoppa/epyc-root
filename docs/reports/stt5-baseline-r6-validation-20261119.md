# STT5 baseline r6: terminal validation collection

Row: `codex3-cs8-stt5-validation-baseline-r6-20261105`. Filed verdict: **inconclusive**. The grant ended
2026-11-19T13:31:42Z, rc=0, reason=complete. That is an engine completion,
not a complete accuracy screen. The native terminal record explicitly retains
three unknowns. This report records a committed conclusion, not a retroactive
measurement warrant.

Question: did the resumed frozen-whisper validation collection exhaust its
declared matrix without redrawing exposed units? The collection reached its
terminal boundary: 1,437 validation utterances, turbo/large × forced/auto.
There are 5,792 chunk exposures and 5,789 matching, reaped rc0 results; all
5,789 appear as ok in the native terminal summary. Three exposed units have
no result and remain unknown. No new inference was run for this filing.

| Arm | Mode | en chunks | it chunks | de chunks | fr chunks |
| --- | --- | ---: | ---: | ---: | ---: |
| turbo | forced | 395 | 397 | 367 | 289 |
| turbo | auto | 395 | 397 | 366 + 1 unknown | 287 + 2 unknown |
| large | forced | 395 | 397 | 367 | 289 |
| large | auto | 395 | 397 | 367 | 289 |

The three unknowns are turbo auto:

- `de_de` clip, chunk 0: `88d4febaf9ef68196bcec3e6522a2a67c193d4cbd21a9b0a8479e2899192fd3e`.
- `fr_fr` clip, chunk 0: `8c49fa215b0d11678e3f644bf312a17b1e2585dd7bfb72f527c22c2c27fef83f`.
- `fr_fr` clip, chunk 0: `e47c18fbd6c33d7da58a3b2f751050472e4b6d3a5ac5b9350841a9cb57a2ca4d`.

Do not redraw them or drop them from the denominator. A later scoring pass must
preserve the declared deletion treatment and unknown counts. No WER, interval,
test-set comparison, advancement or promotion is established here; lower WER is
better. The wider CS-8.STT5 screen remains open.

Exposure argv records 2,613 units at 24 threads, 3,140 at 32, and 39 at 8.
This is cumulative across resume windows, not an r6-only count or a uniform
24-thread experiment. Prior r2–r4 CPU-configured runs were not GPU-fence-proven;
this filing does not upgrade their device evidence. Do not infer latency
comparability or runner equivalence from collection completion.

## Existing evidence identities

All native evidence stays at
`/mnt/raid0/llm/tmp/codex3-cs8-stt5-validation-baseline-r2-20261030/`;
nothing was copied into this repository.

- `validation-results/TERMINAL-INCOMPLETE.json` SHA-256:
  `2c5ab112b187aed855ea6248f382286a3efc20084f23e756c20d503e7e4b38a2`.
- Cumulative exposure/result index SHA-256:
  `b12a0e373202375b463a48dcd82b8878ef5b1543f86dce33fa789b4271620b14`.
  Recipe: sort unit keys lexically, then append each exposure and its result
  if present as `filename + " " + SHA256(file bytes) + LF`; SHA-256 the
  concatenated UTF-8 lines. Bindings match within all 5,789 pairs; no orphan
  result was found. This audit does not independently revalidate raw outputs
  already checked by the resumed producer.
- Source catalog SHA-256:
  `c4a05bca9d882008bc114f49feb8d4ea788dfe2888f6d6345d09cdf6b6ddda1c`.
- Plan SHA-256:
  `5f0d7bbadc83646a36cf3a9d4973bb69fb1ca73a3f01a57e8f0214f0dfe035f5`.
- Input SHA-256:
  `1bf2544d1d02d8f72b1a57d293c1e0869953aae31c3c526220b7965df09b536e`.
- Frozen runner source: `epyc-whisper` git
  `b307379226d93d9c5ed790d7cea0626613c0ef4b`; native bindings record binary
  SHA-256 `093cdb5736b50eb8567b0367f24bf0bcaf947f5ddca9f140f43e47531d31330c`.

Filing uses `file_result.py` with no parent-box tick because the parent requires
the remaining arms and a test screen verdict. Automatic reclaim was skipped to
retain the shared ledger for the next offline scoring task; the keeper owns
reclamation. Existing source registration is
`scripts/vidya/adapters/README.md` → CS-8.STT5 native validation and test
transcription / `VB-SPEECH-STT5-RAW`; no new source family or ladder is added.

Next action: inspect the pinned `score_validation.py` against the three retained
unknowns and mixed execution widths, then prepare and publish a source-bound
offline scoring row through the normal publisher. Preserve all denominators
and raw records; do not rerun unknown exposures.
