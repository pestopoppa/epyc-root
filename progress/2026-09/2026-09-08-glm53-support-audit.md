# GLM-5.3-Flash support audit — 2026-09-08

Completed the requested champion/source/GGUF and official upstream PR audit.
Found three open architecture PRs and one native-MTP companion. Recommended a pinned
#27773/#27917 adaptation on the consolidated champion, with native speculative decoding
a mandatory gate. Identified metadata-prefix/index-sharing differences, quantization concerns,
hybrid KDA/kpool/mHC integration, and rejection rollback requirements. No kernel edits,
builds or inference runs; no throughput or parity claim.

Evidence and implementation/validation plan:
[support audit](../../docs/reference/models/glm53-flash-support-audit-20260908.md).
