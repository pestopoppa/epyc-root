# DCP render content identity

`cost_candidates()` binds a file body with `content_sha256`. Before rendering any included bound candidate in FULL, SLICES or CODEMAP_ONLY mode, `render_bundle()` now compares its reread UTF-8 body hash with that binding. A changed body raises ValueError before that candidate renders; the function returns no partial bundle. The existing advisory chat caller catches this failure and falls back to base context. Feature defaults and wiring are unchanged.

Unbound manual candidates (`content_sha256=None`) remain compatible. A reader returning None or raising remains an unreadable skip. A readable empty body with a stale binding refuses before the existing empty-body skip. Matching bodies retain their prior rendering behavior.

APP762dadb3/main049ecf5a and ROOTa1a1e789/main1b838f008 retain exact tested bytes. [Off-host original CI37457222213](../../artifacts/ni07/run-37457222213/README.md) passes17/17 injected-reader cases after MAIN source-first full original custody review. This establishes bounded content-identity conformance; headers are not included in planning costs, so it does not establish an absolute serialized prompt budget, AST-complete context, discovery quality or live deployment. DCP-12 and parent live evaluation gates remain open.
