# PIP-02 selection invalidation

The earlier r32 `selection-review.json` is invalid: its exposure scan missed an unpadded inner shard directory. The five pages it selected, 64–68, each have an existing page-start record. `INVALIDATION.json` records their exact paths and hashes and the invalidated selection hash. Do not redraw these pages.

The discovery snapshot is itself incomplete: later review found missing attempt roots and incomplete capture-result and region-provenance checks. It is evidence for invalidation only, not a basis for selecting other pages or a claim that the rest of the cohort is unexposed. No inference was run during this audit. [belief: cc]
