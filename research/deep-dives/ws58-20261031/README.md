# ws58 research intake 2026-10-31 — deep-dive record (intake-2545..2602)

**Session**: `intake-ws58-20261031` (workspace-58). **Plan**: [`../../intake-stage3-plan-2026-10-31-ws58.md`](../../intake-stage3-plan-2026-10-31-ws58.md),
revision 2, sha256 `043e502133cae214175ea3f2a395f575e6ca13b9f3ee058525ed020264ab5012`, operator-approved 2026-10-31 and applied in Stage 4.

This directory keeps the substance of the dives: what each dive concluded, its per-claim verdicts and anchors, its
derived-actionables ledger, and its surfaced sources. The raw downloads (paper HTML, cloned repos, API JSON) were
scratch and were deleted after this commit. Paths written as `scratch:dive-ws58-20261031/...` inside the files below
point at that deleted scratch. They name the on-disk text a quote was re-found in, which can be re-fetched from the
`source_revision` recorded on each index entry. Every quote is also stored with its `quote_sha256` in
`research/intake_index.yaml`, so the anchors stay checkable without the scratch copy.

## Waves

| Wave | Files | Entries | Models |
|---|---|---|---|
| 1 (Stage 2) | `dives/w1_{spec,mtp,kern,speech,tcap,loop,agent,mem}.yaml` | 29 of intake-2545..2576 | opus: spec, mtp, kern; sonnet: the rest |
| 2 (Stage 2b) | `dives/w2_{spec,speech,loop,kern}.yaml` | intake-2577..2590 | sonnet |
| 3 (Stage 2b) | `dives/w3_{spec,dec}.yaml` | intake-2591..2596 | sonnet |
| 4 (Stage 2b) | `dives/w4_up.yaml` | intake-2597..2602 | sonnet |
| 5 (plan revision) | `dives/w5_{ft,fold,gpu,verif,meta}.yaml` | re-dive of intake-2563; operator points 1-8 | opus: ft, verif; sonnet: fold, gpu, meta |

Each `w*.yaml` has `entries` (per-entry verification record), `ledger` (derived actionables with grounding),
`dive_surfaced_sources`, and, for Stage 2b, `new_entries`. Wave 5 files hold `answer`, `tasks` and `rows`.

## Checks

- **Mechanical second reader.** Every anchor quote was re-found, whitespace-normalized, in its on-disk source before it was written. None were dropped.
- **Semantic second reader.** An independent haiku reader checked each anchor: `dives/second_reader_w1.json`, `second_reader_w23.json`, `second_reader_w4.json`. It returned 7 "no" verdicts. Main dropped 6 of those anchors and narrowed 1 claim.
- **Declines.** Surfaced sources that were not ingested are listed in `dives/declines_w{1..4}.json`. Each decline is also recorded on the entry that surfaced it, in `dive_corrections`.
- **Briefs.** The dive and helper briefs are in `briefs/`.
