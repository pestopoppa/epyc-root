# TD-16 Hunch look-alike fixture

This directory freezes the source and a deterministic JSONL export for the TD-16 label-word bias control. It contains no model outputs and makes no inference or calibration claim.

## Provenance and license

- Repository: [`ihubanov/hunch`](https://github.com/ihubanov/hunch)
- Pinned commit: `8bac3f2b5e64690ca5be7d99dfc0705ce986cb83`
- Upstream source: [`hunch/lookalikes.py`](https://github.com/ihubanov/hunch/blob/8bac3f2b5e64690ca5be7d99dfc0705ce986cb83/hunch/lookalikes.py)
- Upstream license: MIT, copyright 2026 Infosec Consult Ltd; the exact upstream `LICENSE` is included here.
- Source SHA-256: `356db0d8d9594a2c705b4a31672d17a8ec996249a465bfc57c0469db84e791ba`

The source describes fictional examples and uses reserved `.example` names and documentation-range IP addresses. The source was checked out at the full pinned commit before copying; the local source hash matches the source file from that checkout.

## Fixture

`td16-lookalikes.jsonl` is the output of the pinned module's `build()` with its default `vague=False`, serialized as UTF-8 JSONL with sorted keys and compact separators. Each line is one source item, retaining its source `id`, `task`, `kind`, integer `label`, `context`, and `check` fields. No rows were filtered, relabeled, or augmented.

- Rows: 240 (40 source skeletons × 3 relation kinds × 2 tasks)
- Labels: 80 positive, 160 negative
- Relation kinds: 80 each of `change`, `restate`, and `other`
- Tasks: 120 each of `replaces` and `agrees`
- IDs: 240 unique
- JSONL SHA-256: `937c4ff28332e7541c92aa62d5ab7b7100c4b4c322cb2524141e807889e0f315`

The 80/160 label balance gives the always-negative accuracy baseline of 66.7%; the base-rate Brier baseline is 0.222 (2/9, rounded). These are class-balance constants, not measured model results.

## Integrity checks

The following were checked during preparation:

1. `git rev-parse HEAD` in the source checkout returned `8bac3f2b5e64690ca5be7d99dfc0705ce986cb83`.
2. `sha256sum hunch/lookalikes.py` returned the source digest above.
3. Executing `build()` returned 240 items with 80 label-1 and 160 label-0 rows; all IDs were unique and the relation/task counts matched the table above.
4. The exported JSONL parsed as 240 records and its SHA-256 is recorded above.
5. The included license is the pinned repository's MIT `LICENSE`.

This is a source/fixture preparation artifact only. TD-16's worker-model comparisons (native noul, neutral-key A/B in both orders, JSON, and question-only variants), metrics, paired-bootstrap intervals, and the champion-sidecar inference gate remain to be run by the handoff owner.
