# BULK-hermes-smokes Scope Correction — 2026-07-21

The final run `BULK-hermes-smokes-20260721T042834Z` validated the standalone
Hermes smoke harness only:

- standalone backend health/chat/tool-schema/streaming/override/multi-turn
- standalone reference-client `--send --stream`
- 2/2 parallel subagents serialized through one `8099` single-slot backend
- cleanup back to quiet

It did **not** perform an upstream Hermes checkout, fetch, or pin bump. The
captured `batch_entry_BULK-hermes-smokes_20260721T042834Z.json` entry snapshot
still contains stale pin-bump wording because it records the pre-correction
compiled entry hash used by that run. The source entry was corrected after the
checkpoint audit so future manifests describe this batch as a standalone smoke
harness gate. The actual pin-bump target selection/fetch/checkout/setup remains
open in `handoffs/active/user-facing-harness-index.md`.
