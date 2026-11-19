# Reuse decision — 2026-11-04

Do not publish or execute the newly prepared `handoff-kvu-kvu19a2-repeatability-20261104` GPU row. The current KVU-19a-2 handoff already points to source-bound research `f8878bf145490c43458aab0fad27eac6514918d5` and the barrier diagnostic `7a8a2d8fade9ee17368c374c3da42df4f69dfbd6`. Those committed records answer the bounded repeatability question in cases78 and80: five matching baseline outputs versus five distinct candidate outputs per case, using matched input bytes and runtime witnesses. A new repeat to establish the same point would spend compute without resolving the remaining upstream-report task.

Case79 is not covered by these two repeated experiments; no repeatability result for it is inferred. Its omission does not prevent reporting the already demonstrated two-case observation. The prepared three-case packet is retained unchanged as an unused preparation artifact, not described as executed or published.

The concrete next artifact is `ISSUE-DRAFT.md`, supported by `EVIDENCE-INDEX.json`. Its scope is historical model-free repeatability in a local experimental source pair. The unsuccessful barrier change establishes no cause and supplies no fix. Posting is not authorized by artifact preparation; explicit operator authorization is required before sending it upstream.

This decision and draft reuse committed results. No new GPU measurement, compilation, benchmark, production modification, upstream posting, shared handoff/index edit, or commit was performed.
