# G16 greedy aligned r2 — accepted preparation capsule (2026-10-31)

Publication: `codex-ni-g16-greedy-ab-aligned-r2-20261031`, published 2026-10-31T07:57:35.660731Z, exact READY payload SHA-256 `60b2785db876652ebd6d232ec3c3ed5dff4522ca8872b40e157eb400d65dbbe5`; exact READY row SHA-256 `7b8aea9830c9e2ab932cabac2df972589f1764d8aa98da79cc615c1c03010052`. Publication record is included below as `PUBLICATION.json`.

## Qualification and remaining work

- Fresh production-recipe-aligned HIP image passed the original eight native `1e-7` controls and three long two-sequence dispatch traces.
- Original 2048-token FA-on, two-slot comparison was a valid executed comparison. First token IDs matched; full UTF-8 bytes **failed** (slot 0 first difference at 45: 198 vs 1049; slot 1 at 109: 2824 vs 1326). This scientific failure is retained.
- The 128-token same-arm prefix replay varied slot 0 in both arms and matched slot 1. It supports no unique GDN causality or statistical estimate.
- The new full job explicitly reuses the immutable 2048 evidence; it must freshly capture 8192, 16384, and 24576. All four lengths/ledger rows are required. Normal entry completed in 17.8618 s; actual 8192 compute cutoff returned 75/partial at 9.3876 s and drained descendants. Current validator/grant checks and keeper PID proof passed.
- Published unarmed; keeper later recorded ARMED at 07:58:46Z. This is accepted dispatch preparation, not completed G16, keep-rs qualification, or promotion. G16b was not triggered. Scheduler resumed with new logs around 07:58Z; no whole-run or global-health completion claim.

## Source evidence and custody

Full native records remain at `/mnt/raid0/llm/tmp/codex-ni-g16a-build-prep-20261031/prod-recipe-variant/dispatch/`. The immutable original 2048 evidence is provenance for this job, not newly produced by this publication. Keeper retention reported 137 referenced files plus 16 future-path checks, zero omissions. The published manifest's retention patterns remain authoritative. `SOURCES.sha256` records the raw inputs and selected proof files without copying binaries, model weights, or large run records.

Files: `READY.json` and `READY.row.md` are exact published payload bytes. `PUBLICATION.json` records publication status and scope. This capsule is a compact durable pointer/summary, not a substitute for the full source evidence.
