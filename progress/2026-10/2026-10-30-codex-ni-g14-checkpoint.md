# G14 exporter preparation checkpoint — 2026-10-30

Verified the READY packet at
`/mnt/raid0/llm/tmp/codex-ni-g14-reason32m-20261030` against its public manifest,
SOURCE hashes and native final/cutoff receipts. Corrected reviewed draft wording
from a claimed 600-second minimum to the manifest's 300-second minimum and
600-second booked window; preserved historical keeper-scan stdout. Manifest
SHA-256: `c8547a4e05987da8a01c47d72560274b4e313db0582ae27c94630342dc38876b`.
SOURCE SHA-256: `857000058e6a990051db8f11774eac92333895a65321cfceb6d3afc732e72f39`.
All SOURCE entries pass `sha256sum -c`; SOURCE matches both RESULT receipts.

Updated the existing G14 evidence in
`handoffs/active/colbert-reranker-web-research.md`. Python 3.12 / PyLate 1.4.0 /
exporter 1.7.0 at `00e26aae0006b322727db277672211d9a0e3ccec` generated
experimental FP32/INT8 graphs with all three Dense projections and dimension
128. The existing old graph remains unchanged. One-snippet native smoke has
15 rows and six pairwise graph comparisons. Candidate FP32 maxabs vs aligned
PyLate.forward is `1.7881393432617188e-7`; candidate INT8 max cosine divergence
is `0.0006961226463317871`. Corrected-contract old graph divergences range from
`0.006514549255371094` to `0.007153213024139404` at caps 32/64/128; lower is
better. Raw old-contract token mismatch has no cosine. Native output is 18×128
while independent PyLate.encode returns 17×128 after punctuation pruning.
Full 20-snippet/110-row diagnostic and retrieval evaluation have not run;
PREFIX-3 is unmet, G14 remains open, scientific checkbox flips **0**.
No artificial preparation checkbox or new source-family task was created.
[no-belief: compute-preparation]

Same-entry final supervisor runtime 26.8240 s (child 24.9707 s), sampled peak
process-tree RSS 1,982,087,168 bytes; rc 0 and children drained. Cutoff proof
retained four rows, rc 75, supervisor 8.9393 s and children drained. Existing
SC50 is sufficient; future producer projection retains token/mask/shape refusal
records, pins, coverage and phase. No adapter or canary completion is claimed.

GitNexus: lane unindexed; shared index stale. Required impact attempt found no
G14 symbol; refresh wrapper refused CPU admission. Scope is documentation only.
README freshness check passed without warnings. Belief sync check: FRESH,
intake-2521, lag 0. Bus drain found no routed assignment and reported the dead
coordinator daemon; owning session notified. Per-task wrap-up does not run
operator-only index pruning or wiki compilation. Packet evidence is retained
for its admitted diagnostic; no cleanup of the live packet is authorized here.
