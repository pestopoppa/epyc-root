# TD-17 partial progress note for ROOT

Prepared in scratch only for the owner to apply after publication is accepted. Keep the owning checkbox open; no handoff, progress log, or tracked metadata was edited by this lane.

## Task text (verbatim from typed-decision-plane.md)

> **TD-17 — Frozen OOD calibration slice.** Zero-inference adapter over `scienthoon/jev-ood-calibration` `data/val.jsonl` @914d87a (sha256 763949cd…, CC0, byte-reproducible): 300 states x {queue choice, priority score 0-3 with level names as criteria, angry noul}; do not state the priority rule in the catalogue. Also a tier-ablated variant (drop `customer_tier`, fresh `--seed`) so priority depends on a genuinely hidden input. Report the TD-18 metric set per (model pin, catalogue) for the native and JSON arms. The calibrated target is mean max-prob ≈ accuracy, not a near-uniform priority. Cite only the corrected Jev temperatures (1.30 / 1.92), never 3.29 / 3.40 / 2.74. Evidence: intake-1504, intake-1516. The adapter is zero-inference; the run is **GATE: champion-sidecar (CPU window)** (operator ruling 6, 2026-09-29), native and JSON arms on the same sidecar (a JSON-arm-only run keeps `mi210-window`).
>
> *Acceptance amendment 2026-09-25 (intake-1619#record, intake-1622#record):* add matched with-unknown and without-unknown fixtures. Report forced-choice error, abstain precision/recall, candidate eligibility, probability mass, and invalid responses; never infer abstention quality from confidence separation alone.

## Partial work and evidence

- APP source paths and dedicated CI workflow are in candidate branch `codex/ni-td17-calibration-20261101`, commit `027427c223d53a0b5a95541e5e2e49cd2cf0dc5d` (parent `da163c70cc347337f7d76d3ce5acc14fafc75411`). The commit contains exactly five approved paths. Candidate was pushed under the canonical APP P lock; shared APP HEAD/index were not switched by this lane.
- Adapter pins Jev source commit `914d87ab16517f14e833cff63d73b51235b14bd6`, raw `val.jsonl` SHA-256 `763949cdf07f422cbb3c4bd040392944034ae4caf23a07de08fcef04cfd1eb33`, and generator SHA-256 `96c20efe7b82a4416f9ce86d15117edb539847f5b6da206e2a4f96b40c6622ac`; the checked-in fixture is byte-identical.
- Five 300-case variants: frozen-known, fresh-known, matched tier-ablated, priority forced-choice, and matched priority-with-unknown. Fresh data reimplements the pinned 3,000-row generator then seeded 10% grouped validation split, with 5% label noise. Source-observed labels and clean oracle truth are separate; tier ablation removes only the hidden tier; unknown eligibility derives from the complete tier domain. No model calls or metrics are claimed.
- Added tests cover seed-0 exact parity with the pinned 900 rows, all template/tier oracle cases, source-label preservation, noise-outside-eligible singleton control, paired-state identity, all-tier unknown eligibility, actual pinned CLI bundle hashes, and bench-loader question roundtrip. Matched forced/unknown questions retain identical plain text and differ only by the added `unknown` choice.
- Hosted workflow run [41287440906](https://github.com/pestopoppa/epyc-orchestrator/actions/runs/41287440906) succeeded on candidate SHA above: Python 3.13.15, 70 tests passed, pytest exit 0. Original API responses and artifact ZIP are preserved under `/mnt/raid0/llm/tmp/typed-decision-plane/td17-20261101/ci-41287440906/`; `review-note.md` records ZIP integrity, GitHub digest match, and all source-hash checks against candidate blobs.

## Still required before completion

- Await MAIN's independent evidence review and APP publisher's completion; merge/rebase only onto the actual new APP main with a private index/pathspec, preserving TU-owned content and shared HEAD/index constraints.
- The parent acceptance explicitly keeps TD-17 open until TD-18 per-model-pin native/JSON live metrics are recorded. No metrics, model calls, checkbox, quota credit, or task closeout are claimed here. Existing champion-sidecar gate applies to any future live run.
